'''
Utility functions for ingestion
'''
import traceback
import datajoint as dj
from ibl_pipeline.ingest import reference as reference_ingest
from ibl_pipeline.ingest import subject as subject_ingest
from ibl_pipeline.ingest import action as action_ingest
from ibl_pipeline.ingest import acquisition as acquisition_ingest
from ibl_pipeline.ingest import data as data_ingest
from ibl_pipeline import reference, subject, action, acquisition, data


def copy_table(target_schema, src_schema, table_name, fresh=False):
    target_table = getattr(target_schema, table_name)
    src_table = getattr(src_schema, table_name)

    if fresh:
        target_table.insert(src_table)
    else:
        try:
            target_table.insert(src_table - target_table.proj(),
                                skip_duplicates=True)
        except:
            for t in (src_table - target_table.proj()).fetch(as_dict=True):
                try:
                    target_table.insert1(t, skip_duplicates=True)
                except Exception:
                    print("Error when inserting {}".format(t))
                    traceback.print_exc()
