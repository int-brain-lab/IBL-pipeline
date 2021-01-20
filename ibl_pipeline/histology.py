import datajoint as dj
from . import reference, acquisition, ephys
from .ingest import histology as histology_ingest

from os import path, environ
import numpy as np
from .utils import atlas
import pdb

try:
    from ibllib.pipes.ephys_alignment import EphysAlignment
except Exception as e:
    Warning('Need to install the WIPhistologymayo branch for ibllib')

mode = environ.get('MODE')

if mode == 'update':
    schema = dj.schema('ibl_histology')
else:
    schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_histology')


@schema
class InsertionDataSource(dj.Lookup):
    definition = """
    # Method to estimate the probe trajectory, including Ephys aligned histology track, Histology track, Micro-manipulator, and Planned
    insertion_data_source:    varchar(128)     # type of trajectory
    ---
    provenance:         int             # provenance code
    """
    contents = [
        ('Ephys aligned histology track', 70),
        ('Histology track', 50),
        ('Micro-manipulator', 30),
        ('Planned', 10),
    ]


@schema
class ProbeTrajectory(dj.Imported):
    definition = """
    # Probe trajectory estimated with each method, ingested from Alyx table experiments.probetrajectory
    -> ephys.ProbeInsertion
    -> InsertionDataSource
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
    keys = histology_ingest.ProbeTrajectory.fetch(
        'subject_uuid', 'session_start_time', 'probe_idx',
        'insertion_data_source', as_dict=True)
    key_source = ephys.ProbeInsertion * InsertionDataSource & keys

    def make(self, key):

        trajs = (histology_ingest.ProbeTrajectory & key).fetch(as_dict=True)
        for traj in trajs:
            if not traj['coordinate_system_name']:
                traj.pop('coordinate_system_name')
            self.insert1(traj, skip_duplicates=True)


@schema
class ChannelBrainLocation(dj.Imported):
    definition = """
    # Brain coordinates and region assignment of each channel, ingested from Alyx table experiments.channel
    -> ProbeTrajectory
    channel_brain_location_uuid    : uuid
    ---
    channel_axial   : decimal(6, 1)
    channel_lateral : decimal(6, 1)
    channel_x       : decimal(6, 1)
    channel_y       : decimal(6, 1)
    channel_z       : decimal(6, 1)
    -> reference.BrainRegion
    """


@schema
class ClusterBrainRegion(dj.Computed):
    definition = """
    # Brain region assignment to each cluster
    -> ephys.DefaultCluster
    -> InsertionDataSource
    ---
    -> reference.BrainRegion
    """
    key_source = ephys.DefaultCluster * InsertionDataSource & \
        ProbeTrajectory & ephys.ChannelGroup & ChannelBrainLocation

    def make(self, key):
        channel_raw_inds, channel_local_coordinates = \
            (ephys.ChannelGroup & key).fetch1(
                'channel_raw_inds', 'channel_local_coordinates')
        channel = (ephys.DefaultCluster & key).fetch1('cluster_channel')
        if channel in channel_raw_inds:
            channel_coords = np.squeeze(
                channel_local_coordinates[channel_raw_inds == channel])
        else:
            return

        q = ChannelBrainLocation & key & \
            dict(channel_lateral=channel_coords[0],
                 channel_axial=channel_coords[1])

        if len(q) == 1:
            key['ontology'], key['acronym'] = q.fetch1(
                'ontology', 'acronym')

            self.insert1(key)
        elif len(q) > 1:
            ontology, acronym = q.fetch('ontology', 'acronym')
            if len(set(acronym)) == 1:
                key['ontology'] = 'CCF 2017'
                key['acronym'] = acronym[0]
                self.insert1(key)
            else:
                print('Conflict regions')
        else:
            return


@schema
class SessionBrainRegion(dj.Computed):
    definition = """
    # Brain regions assignment to each session
    # including the regions of finest granularity and their upper-level areas.
    -> acquisition.Session
    -> reference.BrainRegion
    """
    key_source = acquisition.Session & ClusterBrainRegion

    def make(self, key):
        regions = (dj.U('acronym') & (ClusterBrainRegion & key)).fetch('acronym')

        associated_regions = [
            atlas.BrainAtlas.get_parents(acronym)
            for acronym in regions] + list(regions)

        self.insert([dict(**key, ontology='CCF 2017', acronym=region)
                     for region in np.unique(np.hstack(associated_regions))])


@schema
class DepthBrainRegion(dj.Computed):
    definition = """
    # For each ProbeTrajectory, assign depth boundaries relative to the probe tip to each brain region covered by the trajectory
    -> ProbeTrajectory
    ---
    region_boundaries   : blob
    region_label        : blob
    region_color        : blob
    region_id           : blob
    """
    key_source = ProbeTrajectory & ChannelBrainLocation

    def make(self, key):

        x, y, z, axial = (ChannelBrainLocation & key).fetch(
            'channel_x', 'channel_y', 'channel_z', 'channel_axial',
            order_by='channel_axial')
        xyz_channels = np.c_[x, y, z]
        key['region_boundaries'], key['region_label'], \
            key['region_color'], key['region_id'] = \
            EphysAlignment.get_histology_regions(
                xyz_channels.astype('float')/1e6, axial.astype('float'))

        self.insert1(key)


# ================= The following tables will replace the above ones eventually ====================

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
    keys = histology_ingest.ProbeTrajectory.fetch(
        'subject_uuid', 'session_start_time', 'probe_idx',
        'insertion_data_source', as_dict=True)
    key_source = ephys.ProbeInsertion * InsertionDataSource & keys

    def make(self, key):

        trajs = (histology_ingest.ProbeTrajectory & key).fetch(as_dict=True)
        for traj in trajs:
            if not traj['coordinate_system_name']:
                traj.pop('coordinate_system_name')
            self.insert1(traj, skip_duplicates=True)


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
