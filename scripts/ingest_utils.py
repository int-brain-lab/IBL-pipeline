'''
Utility functions for ingestion
'''


def copy_table(target_schema, src_schema, table_name, fresh=False):
    target_table = getattr(target_schema, table_name)
    src_table = getattr(src_schema, table_name)
   
    if fresh:
        target_table.insert(src_table)
    else:
        try:
            target_table.insert(src_table - target_table.proj())
        except:
            for t in (src_table - target_table.proj()).fetch(as_dict=True):
                try:
                    target_table.insert1(t)
                except:
                    print("Error when inserting {}".format(t))