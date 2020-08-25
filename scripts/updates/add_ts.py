'''
This script add ts field to the tables.
'''

import datajoint as dj
from ibl_pipeline.ingest import reference as reference_ingest
from ibl_pipeline.ingest import subject as subject_ingest
from ibl_pipeline.ingest import action as action_ingest
from ibl_pipeline.ingest import acquisition as acquisition_ingest
from ibl_pipeline.ingest import data as data_ingest
from ibl_pipeline import reference, subject, action, acquisition, data
from ibl_pipeline.utils import dj_alter_table
import tables_with_ts as tables


def table_add_column(schema, table_name):
    print('Altering' + table_name + '...')
    table = getattr(schema, table_name)
    dj_alter_table.add_column(
        table, table_name.lower()+'_ts', dtype='timestamp',
        default_value='CURRENT_TIMESTAMP', use_keyword_default=True)


if __name__ == '__main__':

    tables.init()

    for table in tables.REF_TABLES:
        table_add_column(reference_ingest, table)
    #     table_add_column(reference, table)

    for table in tables.SUBJECT_TABLES:
        table_add_column(subject_ingest, table)
    #     table_add_column(subject, table)

    for table in tables.ACTION_TABLES:
        table_add_column(action_ingest, table)
    #     table_add_column(action, table)

    for table in tables.ACQUISITION_TABLES:
        table_add_column(acquisition_ingest, table)
    #     table_add_column(acquisition, table)

    for table in tables.DATA_TABLES:
        table_add_column(data_ingest, table)
    #     table_add_column(data, table)
