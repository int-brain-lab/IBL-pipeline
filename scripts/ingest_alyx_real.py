'''
This script copies tuples in the shadow tables into the real tables for alyx.
'''

import datajoint as dj
from ibl_pipeline.ingest import reference as reference_ingest
from ibl_pipeline.ingest import subject as subject_ingest
from ibl_pipeline.ingest import action as action_ingest
from ibl_pipeline.ingest import acquisition as acquisition_ingest
from ibl_pipeline.ingest import data as data_ingest
from ibl_pipeline.ingest import ephys as ephys_ingest
from ibl_pipeline import reference, subject, action, acquisition, data, ephys, histology
from ingest_utils import copy_table
import table_names as tables

dj.config['safemode'] = False

tables.init()

for table in tables.REF_TABLES:
    print(table)
    copy_table(reference, reference_ingest, table)


for table in tables.SUBJECT_TABLES:
    print(table)
    copy_table(subject, subject_ingest, table)


for table in tables.ACTION_TABLES:
    print(table)
    copy_table(action, action_ingest, table)


for table in tables.ACQUISITION_TABLES:
    print(table)
    copy_table(acquisition, acquisition_ingest, table)


for table in tables.DATA_TABLES:
    print(table)
    copy_table(data, data_ingest, table)


# ephys tables
table = 'ProbeModel'
print(table)
copy_table(ephys, ephys_ingest, table)

table = 'ProbeInsertion'
print(table)
copy_table(ephys, ephys_ingest, table, allow_direct_insert=True)

# update and populate the ProbeTrajectory
# print('Updating and populate ProbeTrajectory')
# for key in ephys.ProbeTrajectory.fetch('KEY'):
#     (ephys.ProbeTrajectory & key).delete()
#     ephys.ProbeTrajectory.populate(key, suppress_errors=True,
#                                    display_progress=True)

histology.ProbeTrajectory.populate(suppress_errors=True, display_progress=True)
