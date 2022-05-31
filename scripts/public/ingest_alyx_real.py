"""
This script copies tuples in the shadow tables into the real tables for alyx.
"""

import datajoint as dj
import table_names as tables

from ibl_pipeline import acquisition, action, data, reference, subject
from ibl_pipeline.ingest import acquisition as acquisition_ingest
from ibl_pipeline.ingest import action as action_ingest
from ibl_pipeline.ingest import data as data_ingest
from ibl_pipeline.ingest import reference as reference_ingest
from ibl_pipeline.ingest import subject as subject_ingest
from ibl_pipeline.ingest.ingest_utils import copy_table

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
