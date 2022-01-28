import datajoint as dj

from ibl_pipeline import (reference, subject, action,
                          acquisition, data, ephys, qc, histology)

from ibl_pipeline.ingest import reference as shadow_reference
from ibl_pipeline.ingest import subject as shadow_subject
from ibl_pipeline.ingest import action as shadow_action
from ibl_pipeline.ingest import acquisition as shadow_acquisition
from ibl_pipeline.ingest import data as shadow_data
from ibl_pipeline.ingest import ephys as shadow_ephys
from ibl_pipeline.ingest import qc as shadow_qc
from ibl_pipeline.ingest import histology as shadow_histology

from ibl_pipeline.ingest import job


real_vmods = {}
for m in (reference, subject, action,
          acquisition, data, ephys, qc, histology):
    assert m.schema.database.startswith('test_')
    schema_name = m.__name__.split('.')[-1]
    real_vmods[schema_name] = dj.create_virtual_module(schema_name, m.schema.database[5:])

session_res = 'session_start_time BETWEEN "2022-01-20" AND "2022-01-22"'
session_keys = (real_vmods['acquisition'].Session & session_res).fetch('KEY')

for full_table_name, table_detail in job.DJ_TABLES.items():
    real_table = table_detail['real']
    if real_table is None:
        continue

    print(f'Inspecting: {full_table_name} - ', end='')

    schema_name, table_name = full_table_name.split('.')
    vm_real_table = getattr(real_vmods[schema_name], table_name)

    missing = (vm_real_table & session_keys) - (real_table & session_keys).proj()

    print(f'missing {len(missing)}')
