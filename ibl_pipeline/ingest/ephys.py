import datajoint as dj
import json
import uuid
import re

from . import alyxraw, reference, acquisition
from . import get_raw_field as grf

schema = dj.schema(dj.config.get('database.prefix', '') +
                   'ibl_ingest_ephys')


@schema
class ProbeModel(dj.Imported):
    definition = """
    (probe_uuid) -> alyxraw.AlyxRaw
    ---
    probe_name                          : varchar(128)
    probe_model                         : varchar(32)         # 3A, 3B
    probe_manufacturer                  : varchar(32)
    probe_description=null              : varchar(2048)
    probe_model_ts=CURRENT_TIMESTAMP    : timestamp
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
    probe_idx               : int          # 0 for probe00, 1 for probe01
    probe_label=null        : varchar(255) # name in the alyx model experiments.probeinsertion
    subject_uuid            : uuid         # subject uuid from session
    session_start_time      : datetime     # session start time from session
    probe_name=null         : varchar(32)  # probe name, from ProbeModel table
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
                (ProbeModel & dict(probe_uuid=probe_uuid)).fetch1(
                'probe_name')

        key_pi['probe_label'] = grf(key, 'name')

        if re.search('[Pp]robe.?0([0-3])',
                     key_pi['probe_label']):
            key_pi['probe_idx'] = \
                re.search('[Pp]robe.?0([0-3])',
                          key_pi['probe_label']).group(1)
        elif re.search('g([0-3])',
                       key_pi['probe_label']):
            key_pi['probe_idx'] = \
                re.search('g([0-3])',
                          key_pi['probe_label']).group(1)
        else:
            key_pi['probe_idx'] = probe_mapping[key_pi['probe_label']]

        self.insert1(key_pi)
