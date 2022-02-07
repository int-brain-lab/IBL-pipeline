import datajoint as dj
import pandas as pd

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

discrepancy = {}
for full_table_name, table_detail in job.DJ_TABLES.items():
    real_table = table_detail['real']
    if real_table is None:
        continue

    schema_name, table_name = full_table_name.split('.')
    vm_real_table = getattr(real_vmods[schema_name], table_name)

    missing = (vm_real_table & session_keys) - (real_table & session_keys).proj()
    extra = (real_table & session_keys) - (vm_real_table & session_keys).proj()

    discrepancy[full_table_name] = {'missing': len(missing), 'extra': len(extra)}

discrepancy = pd.DataFrame(discrepancy).T
print(discrepancy)
