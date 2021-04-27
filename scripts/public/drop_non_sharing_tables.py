
import datajoint as dj
from ibl_pipeline import reference, subject, action, acquisition
import table_names as tables
import inspect


reference_tables = [m[0] for m in inspect.getmembers(reference,
                                                     inspect.isclass)]
subject_tables = [m[0] for m in inspect.getmembers(subject, inspect.isclass)]
action_tables = [m[0] for m in inspect.getmembers(action, inspect.isclass)]
acquisition_tables = [m[0] for m in inspect.getmembers(acquisition,
                                                       inspect.isclass)]

print('============ Dropping non-sharing tables =============')

tables.init()

for table_name in reference_tables:
    print('------------- Dropped ' + table + ' --------------')
    table = getattr(target_schema, table_name)
