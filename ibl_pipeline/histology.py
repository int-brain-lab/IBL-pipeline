import datajoint as dj
from . import reference, acquisition, data, ephys, qc
import numpy as np
from .utils import atlas
from tqdm import tqdm
from ibllib.pipes.ephys_alignment import EphysAlignment
import warnings
from os import environ

try:
    from oneibl.one import ONE
    import alf.io
    one = ONE(silent=True)
except ImportError:
    warnings.warn('ONE not installed, cannot use populate')
    pass

mode = environ.get('MODE')

if mode == 'update':
    schema = dj.schema('ibl_histology')
else:
    schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_histology')


# ================= The temporary tables before the probe trajectories are finally resolved ===================

@schema
class Provenance(dj.Lookup):
    definition = """
    # Method to estimate the probe trajectory, including Ephys aligned histology track, Histology track, Micro-manipulator, and Planned
    provenance       :    tinyint unsigned             # provenance code
    ---
    provenance_description       : varchar(128)     # type of trajectory
    """
    contents = [
        (70, 'Ephys aligned histology track'),
        (50, 'Histology track'),
        (30, 'Micro-manipulator'),
        (10, 'Planned'),
    ]


@schema
class ProbeTrajectoryTemp(dj.Imported):
    definition = """
    # Probe trajectory estimated with each method, ingested from Alyx table experiments.trajectoryestimate
    -> ephys.ProbeInsertion
    -> Provenance
    ---
    -> [nullable] reference.CoordinateSystem
    probe_trajectory_uuid: uuid
    x:                  float           # (um) medio-lateral coordinate relative to Bregma, left negative
    y:                  float           # (um) antero-posterior coordinate relative to Bregma, back negative
    z:                  float           # (um) dorso-ventral coordinate relative to Bregma, ventral negative
    phi:                float           # (degrees)[-180 180] azimuth
    theta:              float           # (degrees)[0 180] polar angle
    depth:              float           # (um) insertion depth
    roll=null:          float           # (degrees) roll angle of the probe
    trajectory_ts:      datetime
    """
    # this table rely on copying from the shadow table in ibl_pipeline.ingest.histology


@schema
class ChannelBrainLocationTemp(dj.Imported):
    definition = """
    # Brain coordinates and region assignment of each channel, ingested from Alyx table experiments.channel
    -> ProbeTrajectoryTemp
    channel_brain_location_uuid    : uuid
    ---
    channel_axial   : decimal(6, 1)
    channel_lateral : decimal(6, 1)
    channel_x       : decimal(6, 1)
    channel_y       : decimal(6, 1)
    channel_z       : decimal(6, 1)
    -> reference.BrainRegion
    """
    # this table rely on copying from the shadow table in ibl_pipeline.ingest.histology


@schema
class DepthBrainRegionTemp(dj.Computed):
    definition = """
    # For each ProbeTrajectory, assign depth boundaries relative to the probe tip to each brain region covered by the trajectory
    -> ProbeTrajectoryTemp
    ---
    region_boundaries   : blob
    region_label        : blob
    region_color        : blob
    region_id           : blob
    """
    key_source = ProbeTrajectoryTemp & ChannelBrainLocationTemp

    def make(self, key):

        x, y, z, axial = (ChannelBrainLocationTemp & key).fetch(
            'channel_x', 'channel_y', 'channel_z', 'channel_axial',
            order_by='channel_axial')
        xyz_channels = np.c_[x, y, z]
        key['region_boundaries'], key['region_label'], \
            key['region_color'], key['region_id'] = \
            EphysAlignment.get_histology_regions(
                xyz_channels.astype('float')/1e6, axial.astype('float'))

        self.insert1(key)


@schema
class ClusterBrainRegionTemp(dj.Computed):
    definition = """
    # Brain region assignment to each cluster
    -> ephys.DefaultCluster
    -> ProbeTrajectoryTemp
    -> ephys.ChannelGroup
    ---
    -> reference.BrainRegion
    """
    key_source = ephys.DefaultCluster * Provenance & \
        ProbeTrajectoryTemp & ephys.ChannelGroup & ChannelBrainLocationTemp

    def make(self, key):
        # pdb.set_trace()
        channel_raw_inds, channel_local_coordinates = \
            (ephys.ChannelGroup & key).fetch1(
                'channel_raw_inds', 'channel_local_coordinates')
        channel = (ephys.DefaultCluster & key).fetch1('cluster_channel')
        if channel in channel_raw_inds:
            channel_coords = np.squeeze(
                channel_local_coordinates[channel_raw_inds == channel])
        else:
            return

        q = ChannelBrainLocationTemp & key & \
            dict(channel_lateral=channel_coords[0],
                 channel_axial=channel_coords[1])

        if len(q) == 1:
            key['ontology'], key['acronym'] = q.fetch1(
                'ontology', 'acronym')

            self.insert1(key)
        elif len(q) > 1:
            ontology, acronym = q.fetch('ontology', 'acronym')
            if len(np.unique(acronym)) == 1:
                key['ontology'] = 'CCF 2017'
                key['acronym'] = acronym[0]
                self.insert1(key)
            else:
                print('Conflict regions')
        else:
            return


@schema
class ProbeBrainRegionTemp(dj.Computed):
    definition = """
    # Brain regions assignment to each probe insertion, including the regions of finest granularity and their upper-level areas.
    -> ProbeTrajectoryTemp
    -> reference.BrainRegion
    """
    key_source = ProbeTrajectoryTemp & ClusterBrainRegionTemp

    def make(self, key):

        regions = (dj.U('acronym') & (ClusterBrainRegionTemp & key)).fetch('acronym')

        associated_regions = [
            atlas.BrainAtlas.get_parents(acronym)
            for acronym in regions] + list(regions)

        self.insert([dict(**key, ontology='CCF 2017', acronym=region)
                     for region in np.unique(np.hstack(associated_regions))])


@schema
class ProbeTrajectory(dj.Imported):
    definition = """
    # Probe Trajectory resolved by 3 users, ingested from ALF dataset probes.trajectory
    -> ephys.ProbeInsertion
    ---
    -> [nullable] reference.CoordinateSystem
    probe_trajectory_uuid: uuid
    x:                  float           # (um) medio-lateral coordinate relative to Bregma, left negative
    y:                  float           # (um) antero-posterior coordinate relative to Bregma, back negative
    z:                  float           # (um) dorso-ventral coordinate relative to Bregma, ventral negative
    phi:                float           # (degrees)[-180 180] azimuth
    theta:              float           # (degrees)[0 180] polar angle
    depth:              float           # (um) insertion depth
    roll=null:          float           # (degrees) roll angle of the probe
    trajectory_ts=CURRENT_TIMESTAMP:      timestamp
    """
    key_source = ephys.ProbeInsertion & \
        (qc.ProbeInsertionExtendedQC & 'qc_type="alignment_resolved"') & \
        (ProbeTrajectoryTemp & 'provenance=70')

    def make(self, key):
        probe_trajectory = (ProbeTrajectoryTemp & 'provenance=70' & key).fetch1()
        probe_trajectory.pop('provenance')
        self.insert1(probe_trajectory)

        if data_missing:
            ephys.ProbeInsertionMissingDataLog.insert1(
                dict(**key, missing_data='trajectory',
                     error_message='No probes.trajectory data for this probe insertion')
            )


@schema
class ChannelBrainLocation(dj.Imported):
    definition = """
    # Brain coordinates and region assignment of each channel, ingested from Alyx table experiments.channel
    -> ProbeTrajectory
    channel_idx     : int
    ---
    channel_ml      : decimal(6, 1)  # (um) medio-lateral coordinate relative to Bregma, left negative
    channel_ap      : decimal(6, 1)  # (um) antero-posterior coordinate relative to Bregma, back negative
    channel_dv      : decimal(6, 1)  # (um) dorso-ventral coordinate relative to Bregma, ventral negative
    -> reference.BrainRegion
    """
    key_source = (ProbeTrajectory & \
        (data.FileRecord & 'dataset_name like "%channels.brainLocationIds%"') & \
        (data.FileRecord & 'dataset_name like "%channels.mlapdv%"')) - \
            (ephys.ProbeInsertionMissingDataLog & 'missing_data="channels_brain_region"')

    def make(self, key):

        eID = str((acquisition.Session & key).fetch1('session_uuid'))
        dtypes = [
            'channels.brainLocationIds_ccf_2017',
            'channels.mlapdv'
        ]

        files = one.load(eID, dataset_types=dtypes, download_only=True,
                         clobber=True)
        ses_path = alf.io.get_session_path(files[0])

        probe_label = (ephys.ProbeInsertion & key).fetch1('probe_label')
        if not probe_label:
            probe_label = 'probe0' + key['probe_idx']

        try:
            channels = alf.io.load_object(
                ses_path.joinpath('alf', probe_label), 'channels')
        except Exception as e:
            ephys.ProbeInsertionMissingDataLog.insert1(
                dict(**key, missing_data='channels_brain_region',
                     error_message=str(e))
            )
            return

        channel_entries = []
        for ichannel, (brain_loc_id, loc) in tqdm(
                enumerate(zip(channels['brainLocationIds_ccf_2017'],
                              channels['mlapdv']))):
            brain_region_key = (reference.BrainRegion &
                                {'brain_region_pk': brain_loc_id}).fetch1('KEY')

            channel_entries.append(
                dict(
                    channel_idx=ichannel,
                    **key, **brain_region_key,
                    channel_ml=loc[0],
                    channel_ap=loc[1],
                    channel_dv=loc[2]
                )
            )

        self.insert(channel_entries)


@schema
class ClusterBrainRegion(dj.Imported):
    definition = """
    # Brain region assignment to each cluster
    -> ephys.DefaultCluster
    -> ProbeTrajectory
    ---
    cluster_ml      : decimal(6, 1)  # (um) medio-lateral coordinate relative to Bregma, left negative
    cluster_ap      : decimal(6, 1)  # (um) antero-posterior coordinate relative to Bregma, back negative
    cluster_dv      : decimal(6, 1)  # (um) dorso-ventral coordinate relative to Bregma, ventral negative
    -> reference.BrainRegion
    """
    key_source = ProbeTrajectory & \
        (data.FileRecord & 'dataset_name like "%clusters.brainLocationIds%"') & \
        (data.FileRecord & 'dataset_name like "%clusters.mlapdv%"')

    def make(self, key):

        eID = str((acquisition.Session & key).fetch1('session_uuid'))
        dtypes = [
            'clusters.brainLocationIds_ccf_2017',
            'clusters.mlapdv'
        ]

        files = one.load(eID, dataset_types=dtypes, download_only=True,
                         clobber=True)
        ses_path = alf.io.get_session_path(files[0])

        probe_label = (ephys.ProbeInsertion & key).fetch1('probe_label')
        if not probe_label:
            probe_label = 'probe0' + key['probe_idx']

<<<<<<< HEAD
        try:
            clusters = alf.io.load_object(
                ses_path.joinpath('alf', probe_label), 'clusters')
        except Exception as e:
            ephys.ProbeInsertionMissingDataLog.insert1(
                dict(**key, missing_data='clusters_brain_region',
                     error_message=str(e))
            )
            return
=======
        clusters = alf.io.load_object(
            ses_path.joinpath('alf', probe_label), 'clusters')
>>>>>>> 7a5f687fb95ad49d98cf6c546f357bb843a0ddfb

        cluster_entries = []
        for icluster, (brain_loc_id, loc) in tqdm(
                enumerate(zip(clusters['brainLocationIds_ccf_2017'],
                              clusters['mlapdv']))):
            brain_region_key = (reference.BrainRegion &
                                {'brain_region_pk': brain_loc_id}).fetch1('KEY')

            cluster_entries.append(
                dict(
                    cluster_id=icluster,
                    **key, **brain_region_key,
                    cluster_ml=loc[0],
                    cluster_ap=loc[1],
                    cluster_dv=loc[2]
                )
            )

        self.insert(cluster_entries)


# @schema
# class ProbeBrainRegion(dj.Computed):
#     definition = """
#     # Brain regions assignment to each probe insertion, including the regions of finest granularity and their upper-level areas.
#     -> ProbeTrajectory
#     -> reference.BrainRegion
#     """
#     key_source = ProbeTrajectory & ClusterBrainRegion

#     def make(self, key):

#         regions = (dj.U('acronym') & (ClusterBrainRegion & key)).fetch('acronym')

#         associated_regions = [
#             atlas.BrainAtlas.get_parents(acronym)
#             for acronym in regions] + list(regions)

#         self.insert([dict(**key, ontology='CCF 2017', acronym=region)
#                      for region in np.unique(np.hstack(associated_regions))])


# @schema
# class DepthBrainRegion(dj.Computed):
#     definition = """
#     # For each ProbeTrajectory, assign depth boundaries relative to the probe tip to each brain region covered by the trajectory
#     -> ProbeTrajectory
#     ---
#     region_boundaries   : blob
#     region_label        : blob
#     region_color        : blob
#     region_id           : blob
#     """
#     key_source = ProbeTrajectory & ChannelBrainLocation

#     def make(self, key):

#         x, y, z, axial = (ChannelBrainLocation & key).fetch(
#             'channel_x', 'channel_y', 'channel_z', 'channel_axial',
#             order_by='channel_axial')
#         xyz_channels = np.c_[x, y, z]
#         key['region_boundaries'], key['region_label'], \
#             key['region_color'], key['region_id'] = \
#             EphysAlignment.get_histology_regions(
#                 xyz_channels.astype('float')/1e6, axial.astype('float'))

#         self.insert1(key)
