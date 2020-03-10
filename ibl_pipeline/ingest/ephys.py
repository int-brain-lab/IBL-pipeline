import datajoint as dj
import json
import uuid
import re

from . import alyxraw, reference, acquisition
from . import get_raw_field as grf

schema = dj.schema(dj.config.get('database.prefix', '') +
                   'ibl_ingest_ephys')


@schema
class Probe(dj.Imported):
    definition = """
    (probe_uuid) -> alyxraw.AlyxRaw
    ---
    probe_name:                     varchar(128)        # String naming probe model, from probe.description
    probe_model:                    varchar(32)         # 3A, 3B
    probe_manufacturer:             varchar(32)
    probe_description=null:             varchar(2048)
    probe_ingest_ts=CURRENT_TIMESTAMP : timestamp
    """
    key_source = (alyxraw.AlyxRaw & 'model="experiments.probemodel"').proj(
        probe_uuid='uuid')

    def make(self, key):
        key_probe = key.copy()
        key['uuid'] = key['probe_uuid']

        key_probe.update(
            probe_name=grf(key, 'name'),
            probe_model=grf(key, 'probe_model'),
            probe_manufacturer=grf(key, 'probe_manufacturer'))

        probe_description = grf(key, 'description')
        if probe_description != 'None':
            key_probe['probe_description'] = probe_description

        self.insert1(key_probe)


probe_mapping = dict(probe_left=0, probe_right=1)


@schema
class ProbeInsertion(dj.Imported):
    definition = """
    (probe_insertion_uuid) -> alyxraw.AlyxRaw
    ---
    probe_idx:            int          # 0 for probe00, 1 for probe01
    probe_label=null:     varchar(32)  # probe_name in the alyx model experiments.probeinsertion
    subject_uuid:         uuid         # subject uuid from session
    session_start_time:   datetime     # session start time from session
    probe_name=null:      varchar(32)  # probe model name, 3A, 3B
    probe_insertion_ts=CURRENT_TIMESTAMP :   timestamp
    """
    key_source = (alyxraw.AlyxRaw & 'model="experiments.probeinsertion"').proj(
        probe_insertion_uuid='uuid')

    def make(self, key):
        key_pi = key.copy()
        key['uuid'] = key['probe_insertion_uuid']

        session_uuid = grf(key, 'session')
        subject_uuid, session_start_time = \
            (acquisition.Session & dict(session_uuid=session_uuid)).fetch1(
                'subject_uuid', 'session_start_time')

        key_pi.update(
            subject_uuid=subject_uuid,
            session_start_time=session_start_time)

        probe_uuid = grf(key, 'model')
        if probe_uuid != 'None':
            key_pi['probe_name'] = \
                (Probe & dict(probe_uuid=probe_uuid)).fetch1(
                'probe_name')

        key_pi['probe_label'] = grf(key, 'name')

        if re.search('probe.?0([0-3])',
                     key_pi['probe_label']):
            key_pi['probe_idx'] = \
                re.search('probe.?0([0-3])',
                          key_pi['probe_label'])
        else:
            key_pi['probe_idx'] = probe_mapping[key_pi['probe_label']]

        self.insert1(key_pi)


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
    roll:                       float
    insertion_data_source:      varchar(128)
    coorindate_system_name:     varchar(32)
    """
    key_source = (alyxraw.AlyxRaw & 'model="experiments.trajectoryestimate"').proj(
        probe_insertion_uuid='uuid')

    def make(self, key):
        key_traj = key.copy()
        key['uuid'] = key_traj['probe_trajectory_uuid']

        session_uuid = grf(key, 'session')
        subject_uuid, session_start_time, probe_idx = \
            (acquisition.Session & dict(session_uuid=session_uuid)).fetch1(
                'subject_uuid', 'session_start_time', 'probe_idx')
        coord_uuid = grf(key, 'coordinate_system')
        coordinate_system_name = \
            (reference.CoordindateSystem &
             {'coordinate_system_uuid': coord_uuid}).fetch1(
                 'coordinate_system_name'
             )
        provenance = grf(key, 'provenance')
        insertion_data_source = \
            (InsertionDataSource &
             dict(provenance=provenance)).fetch1('insertion_data_source')

        key_traj.update(
            x=grf(key, 'x'),
            y=grf(key, 'y'),
            z=grf(key, 'z'),
            depth=grf(key, 'depth'),
            theta=grf(key, 'theta'),
            phi=grf(key, 'phi'),
            roll=grf(key, 'roll'),
            subject_uuid=subject_uuid,
            session_start_time=session_start_time,
            probe_idx=probe_idx,
            insertion_data_source=insertion_data_source,
            coordinate_system_name=coordinate_system_name
        )

        self.insert1(key_traj)
