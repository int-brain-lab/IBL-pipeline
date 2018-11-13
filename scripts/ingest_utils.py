'''
Utility functions for ingestion
'''


def copy_table(target_schema, src_schema, table_name, fresh=False):
    target_table = getattr(target_schema, table_name)
    src_table = getattr(src_schema, table_name)

    if fresh:
        target_table.insert(src_table, skip_duplicates=True)
    else:
        target_table.insert(src_table - target_table.proj(), skip_duplicates=True)
