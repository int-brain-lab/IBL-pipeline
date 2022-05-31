import datajoint as dj
from datajoint.errors import DataJointError
import json
import uuid
import re
import pdb

from ibl_pipeline.ingest import alyxraw, reference, acquisition, ephys, ShadowIngestionError
from ibl_pipeline.ingest import get_raw_field as grf

from ibl_pipeline import acquisition as acquisition_real
from ibl_pipeline import ephys as ephys_real

schema = dj.schema(dj.config.get('database.prefix', '') +
                   'ibl_ingest_histology')


# Temporary probe trajectories and channel brain location based on methods
@schema
class Provenance(dj.Lookup):
    definition = """
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
    (probe_trajectory_uuid) -> alyxraw.AlyxRaw
    ---
    subject_uuid:               uuid
    session_start_time:         datetime
    probe_idx:                  int
    x:                          float
    y:                          float
    z:                          float
    depth:                      float
    theta:                      float
    phi:                        float
    roll=null:                  float
    provenance:                 tinyint unsigned
    coordinate_system_name=null:     varchar(32)
    trajectory_ts:              datetime
    """

    key_source = ((alyxraw.AlyxRaw - alyxraw.ProblematicData) & 'model="experiments.trajectoryestimate"').proj(
        probe_trajectory_uuid='uuid')

    def make(self, key):
        key_traj = key.copy()
        key['uuid'] = key_traj['probe_trajectory_uuid']

        probe_insertion_uuid = grf(key, 'probe_insertion')
        probe_insertion_key = dict(probe_insertion_uuid=probe_insertion_uuid)

        if (ephys_real.ProbeInsertion & probe_insertion_key):
            subject_uuid, session_start_time, probe_idx = \
                (ephys_real.ProbeInsertion & probe_insertion_key).fetch1(
                    'subject_uuid', 'session_start_time', 'probe_idx')
        elif (ephys.ProbeInsertion & probe_insertion_key):
            subject_uuid, session_start_time, probe_idx = \
                (ephys.ProbeInsertion & probe_insertion_key).fetch1(
                    'subject_uuid', 'session_start_time', 'probe_idx')
        else:
            raise ShadowIngestionError('Non existing probe insertion: {}'.format(probe_insertion_uuid))

        key_traj.update(
            x=grf(key, 'x'),
            y=grf(key, 'y'),
            z=grf(key, 'z'),
            depth=grf(key, 'depth'),
            theta=grf(key, 'theta'),
            phi=grf(key, 'phi'),
            subject_uuid=subject_uuid,
            session_start_time=session_start_time,
            probe_idx=probe_idx,
            provenance=grf(key, 'provenance'),
            trajectory_ts=grf(key, 'datetime')
        )

        roll = grf(key, 'roll')
        if roll != 'None':
            key_traj.update(roll=roll)

        coord_uuid = grf(key, 'coordinate_system')
        if coord_uuid != 'None':
            key['coordinate_system_uuid'] = \
                (reference.CoordinateSystem &
                 {'coordinate_system_uuid': coord_uuid}).fetch1(
                    'coordinate_system_name')

        self.insert1(key_traj)


@schema
class ChannelBrainLocationTemp(dj.Imported):
    definition = """
    (channel_brain_location_uuid) -> alyxraw.AlyxRaw
    ---
    subject_uuid            : uuid
    session_start_time      : datetime
    probe_idx               : tinyint
    channel_axial           : decimal(6, 1)
    channel_lateral         : decimal(6, 1)
    channel_x               : decimal(6, 1)
    channel_y               : decimal(6, 1)
    channel_z               : decimal(6, 1)
    provenance              : tinyint unsigned
    ontology                : varchar(32)
    acronym                 : varchar(32)
    """
    key_source = (alyxraw.AlyxRaw & 'model="experiments.channel"').proj(
        channel_brain_location_uuid='uuid')

    @classmethod
    def create_entry(cls, key):
        key_brain_loc = key.copy()
        key['uuid'] = key_brain_loc['channel_brain_location_uuid']

        probe_trajectory_uuid = grf(key, 'trajectory_estimate')
        if (ProbeTrajectoryTemp & dict(probe_trajectory_uuid=probe_trajectory_uuid)):
            subject_uuid, session_start_time, probe_idx, provenance = \
                (ProbeTrajectoryTemp & dict(probe_trajectory_uuid=probe_trajectory_uuid)).fetch1(
                    'subject_uuid', 'session_start_time', 'probe_idx',
                    'provenance')
        else:
            raise ShadowIngestionError('Non existing trajectory: {}'.format(probe_trajectory_uuid))

        brain_region_pk = grf(key, 'brain_region')
        ontology, acronym = (reference.BrainRegion &
                             dict(brain_region_pk=brain_region_pk)).fetch1(
                                 'ontology', 'acronym')

        key_brain_loc.update(
            channel_x=grf(key, 'x'),
            channel_y=grf(key, 'y'),
            channel_z=grf(key, 'z'),
            channel_axial=grf(key, 'axial'),
            channel_lateral=grf(key, 'lateral'),
            subject_uuid=subject_uuid,
            session_start_time=session_start_time,
            probe_idx=probe_idx,
            provenance=provenance,
            ontology=ontology,
            acronym=acronym
        )
        return key_brain_loc

    def make(self, key):
        entry = ChannelBrainLocationTemp.create_entry(key)
        if entry:
            self.insert1(entry)
