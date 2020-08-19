'''
Utility functions for ingestion
'''
import traceback


def copy_table(target_schema, src_schema, table_name, fresh=False, **kwargs):
    target_table = getattr(target_schema, table_name)
    src_table = getattr(src_schema, table_name)

    if fresh:
        target_table.insert(src_table, **kwargs)
    else:
        try:
            target_table.insert(src_table - target_table.proj(),
                                skip_duplicates=True, **kwargs)
        except Exception as e:
            for t in (src_table - target_table.proj()).fetch(as_dict=True):
                try:
                    if table_name == 'DataSet' and \
                         not len(t['dataset_created_by']):
                        t.pop('dataset_created_by')
                    target_table.insert1(t, skip_duplicates=True, **kwargs)
                except Exception:
                    print("Error when inserting {}".format(t))
                    traceback.print_exc()
