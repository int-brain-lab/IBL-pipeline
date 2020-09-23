import datajoint as dj
from ibl_pipeline import acquisition, behavior, ephys, histology
from ibl_pipeline.analyses import behavior as behavior_analyses
from ibl_pipeline.analyses import ephys as ephys_analyses
from ibl_pipeline.plotting import behavior as behavior_plotting
from ibl_pipeline.plotting import ephys as ephys_plotting
from ibl_pipeline.group_shared import wheel
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
        return vmod.__name__

    def get_table_list(self, virtual_only=False):

        context = inspect.currentframe().f_globals
        table_list = []
        for t_db in self.descendants:
            try:
                int(t_db)
                continue
            except Exception as e:
                pass
            t = dj.table.lookup_class_name(t_db, context, depth=3)

            if t:
                table_list.append(dict(label='package', table=t,
                                       full_table_name=t_db))
            else:
                vmod_name = Graph.get_virtual_module(t_db, context)
                t = dj.table.lookup_class_name(
                    t_db, context)
                table_list.append(dict(label='virtual', table=t,
                                       full_table_name=t_db))
                context.pop(vmod_name)

        if virtual_only:
            return [t for t in table_list if t['label'] == 'virtual']
        else:
            return table_list
