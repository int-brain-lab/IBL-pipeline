import datajoint as dj
import json
import uuid

from . import alyxraw, reference, acquisition
from . import get_raw_field as grf

schema = dj.schema(dj.config.get('database.prefix', '') +
                   'ibl_ingest_ephys')


@schema
class Probe(dj.Imported):
    definition = """
    (probe_uuid) -> alyxraw.AlyxRaw
    ---
    probe_name:             varchar(128)        # String naming probe model, from probe.description
    probe_model:            varchar(32)         # 3A, 3B
    probe_manufacturer:     varchar(32)
    probe_description=null:      varchar(2048)
    probe_ingest_ts=CURRENT_TIMESTAMP :   timestamp
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
