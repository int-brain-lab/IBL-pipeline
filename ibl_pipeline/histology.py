import datajoint as dj
from . import reference, acquisition, ephys
from .ingest import histology as histology_ingest

from os import path, environ
import numpy as np
from .utils import atlas

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
    # data imported from probes.trajectory
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
        else:
            return


@schema
class SessionBrainRegion(dj.Computed):
    definition = """
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
