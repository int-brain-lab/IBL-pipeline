import datajoint as dj
import numpy as np
from ibl_pipeline.utils import atlas
from tqdm import tqdm
import warnings

from ibl_pipeline import reference, subject, acquisition, data, ephys, qc
from ibl_pipeline import mode, one


if mode == 'update':
    schema = dj.schema('ibl_histology')
else:
    schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_histology')

if mode != 'public':
    from ibl_pipeline.histology_internal import ProbeTrajectoryTemp


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

    if mode != 'public':
        key_source = ephys.ProbeInsertion & \
            (qc.ProbeInsertionExtendedQC & 'qc_type="alignment_resolved"') & \
            (ProbeTrajectoryTemp & 'provenance=70')

    def make(self, key):

        if mode != 'public':
            # get the result from temp
            probe_trajectory = (ProbeTrajectoryTemp & 'provenance=70' & key).fetch1()
            probe_trajectory.pop('provenance')
        else:
            subject_nickname = (subject.Subject & key).fetch1('subject_nickname')
            probe_insertion_uuid = str((ephys.ProbeInsertion & key).fetch1('probe_insertion_uuid'))
            # get the result from Alyx with ONE
            traj = one.alyx.rest(
                'trajectories', 'list', subject=subject_nickname,
                probe_insertion=probe_insertion_uuid,
                provenance='Ephys aligned histology track')[0]
            # here is an example data returned by ONE
            # [{'id': 'c652f72e-e1f4-4067-8961-1a61235f0dbc',
            # 'probe_insertion': 'da8dfec1-d265-44e8-84ce-6ae9c109b8bd',
            # 'x': 585.9999999999997,
            # 'y': 599.9999999999999,
            # 'z': -543.0,
            # 'depth': 6239.691633611871,
            # 'theta': 16.106094538625694,
            # 'phi': 9.68423519711809,
            # 'roll': 0.0,
            # 'provenance': 'Ephys aligned histology track',
            # 'session': {'subject': 'SWC_043',
            # 'start_time': '2020-09-21T19:02:16.707541',
            # 'number': 1,
            # 'lab': 'hoferlab',
            # 'id': '4ecb5d24-f5cc-402c-be28-9d0f7cb14b3a',
            # 'task_protocol': '_iblrig_tasks_ephysChoiceWorld6.4.2'},
            # 'probe_name': 'probe00',
            # 'coordinate_system': 'IBL-Allen',
            # 'datetime': '2021-04-02T15:03:42.018298',
            # 'json': {'2021-04-02T15:03:41_nate': [[-1.006,
            #     0.0003564881889763793,
            #     0.0011120000000000006,
            #     0.002233338582677166,
            #     1.006],
            #     [-1.0991938799064143,
            #     -0.0002876850393700751,
            #     0.0004916850393700805,
            #     0.0017561732283464578,
            #     1.0978058600524505],
            #     'PASS: None']}}]
            kept_fields = ['x', 'y', 'z', 'depth', 'theta', 'phi', 'roll']
            probe_trajectory = dict(
                **key, **{f: traj[f] for f in kept_fields},
                coordinate_system_name=traj['coordinate_system'],
                probe_trajectory_uuid=traj['id'])

        self.insert1(probe_trajectory)


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

    if mode != 'public':
        key_source = (ProbeTrajectory
                      & (data.FileRecord & 'dataset_name like "%channels.brainLocationIds%"')
                      & (data.FileRecord & 'dataset_name like "%channels.mlapdv%"')) - \
            (ephys.ProbeInsertionMissingDataLog & 'missing_data="channels_brain_region"')

    def make(self, key):

        eID = str((acquisition.Session & key).fetch1('session_uuid'))
        probe_name = (ephys.ProbeInsertion & key).fetch1('probe_label')
        probe_name = probe_name or 'probe0' + key['probe_idx']

        try:
            channels = one.load_object(eID, obj='channels',
                                       collection=f'alf/{probe_name}')
        except Exception as e:
            ephys.ProbeInsertionMissingDataLog.insert1(
                dict(**key, missing_data='channels_brain_region',
                     error_message=str(e)))
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
        probe_name = (ephys.ProbeInsertion & key).fetch1('probe_label')
        probe_name = probe_name or 'probe0' + key['probe_idx']

        try:
            clusters = one.load_object(eID, obj='clusters', collection=f'alf/{probe_name}')
        except Exception as e:
            ephys.ProbeInsertionMissingDataLog.insert1(
                dict(**key, missing_data='clusters_brain_region',
                     error_message=str(e)))
            return

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

        self.insert(cluster_entries, skip_duplicates=True)


@schema
class ProbeBrainRegion(dj.Computed):
    definition = """
    # Brain regions assignment to each probe insertion, including the regions of finest granularity and their upper-level areas.
    -> ProbeTrajectory
    -> reference.BrainRegion
    """
    key_source = ProbeTrajectory & ClusterBrainRegion

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
    region_boundaries   : blob  # 2d numpy array for depths of the boundaries [[20, 40], [40, 60], [60, 120]]
    region_label        : blob  # ['VISa', 'LGN' ...]
    region_color        : blob
    region_id           : blob
    """
    key_source = ProbeTrajectory & ChannelBrainLocation

    def make(self, key):
        from ibllib.pipes.ephys_alignment import EphysAlignment

        x, y, z = (ChannelBrainLocation & key).fetch(
            'channel_ml', 'channel_ap', 'channel_dv')

        coords = (ephys.ChannelGroup & key).fetch1('channel_local_coordinates')

        xyz_channels = np.c_[x, y, z]
        key['region_boundaries'], key['region_label'], \
            key['region_color'], key['region_id'] = \
            EphysAlignment.get_histology_regions(
                xyz_channels.astype('float')/1e6, coords[:, 1])

        self.insert1(key)

    @classmethod
    def check_boundaries_duplicates(cls, restrictor={}):
        """check the duplications of boundaries

        Args:
            restrictor: valid restrictor for current table
        Returns:
            keys_with_duplicated_boundaries (list of dicts): a list of keys that have duplicated boundaries.
        """

        keys = (cls & restrictor).fetch('KEY')

        keys_with_duplicated_boundaries = []
        for key in keys:
            region_labels = (cls & key).fetch1('region_label')

            if len(region_labels) != len(set(region_labels[:, 0])):
                keys_with_duplicated_boundaries.append(key)

        return keys_with_duplicated_boundaries
