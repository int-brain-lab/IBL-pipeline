import datajoint as dj
import ibl_pipeline
import inspect
import re
import pdb


class Graph():

    def __init__(self, table):

        self.table = table
        self.graph = table.connection.dependencies
        self.graph.load()
        self.descendants = self.graph.descendants(table.full_table_name)

    @staticmethod
    def get_virtual_module(full_table_name, context=None):

        if not context:
            context = inspect.currentframe().f_back.f_locals
        schema_name = re.match('`(.*)`\.', full_table_name).group(1)
        vmod = dj.create_virtual_module(schema_name, schema_name)
        context[vmod.__name__] = vmod

    def get_table_list(self, virtual_only=False):

        context = inspect.currentframe().f_back.f_locals
        table_list = []
        for t_db in self.descendants:
            try:
                int(t_db)
                continue
            except Exception as e:
                pass
            t = dj.table.lookup_class_name(t_db, context)

            if t:
                table_list.append(dict(label='package', table=t))
            else:
                Graph.get_virtual_module(t_db, context)
                t = dj.table.lookup_class_name(
                    t_db, context)
                table_list.append(dict(label='virtual', table=t))

        if virtual_only:
            return [t['table'] for t in table_list if t['label'] == 'virtual']
        else:
            return table_list
