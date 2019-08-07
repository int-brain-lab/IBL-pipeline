'''
This script detects the updates and ingest the result into the table update.UpdateRecord
'''

import datajoint as dj

# import updated tables
from ibl_pipeline.ingest import reference as reference_shadow
from ibl_pipeline.ingest import subject as subject_shadow
from ibl_pipeline.ingest import action as action_shadow
from ibl_pipeline.ingest import data as data_shadow
from ibl_pipeline.ingest import acquisition as acquisition_shadow

from ibl_pipeline.utils import dj_compare_table
import numpy as np
import tables_for_updates as tables

# import real tables as virtual module
reference = dj.create_virtual_module('reference', 'ibl_reference')
subject = dj.create_virtual_module('subject', 'ibl_subject')
action = dj.create_virtual_module('action', 'ibl_action')
acquisition = dj.create_virtual_module('acquisition', 'ibl_acquisition')
data = dj.create_virtual_module('data', 'ibl_data')


tables.init()
schemas = [reference, subject, action, data, acquisition]
schemas_shadow = [reference_shadow, subject_shadow, action_shadow, data_shadow, acquisition_shadow]
tablenames = [
    tables.REF_TABLES,
    tables.SUBJECT_TABLES,
    tables.ACTION_TABLES,
    tables.DATA_TABLES,
    tables.ACQUISITION_TABLES
]

tablepairs = {t: (getattr(s_src, t), getattr(s_dest, t))
              for tablename, s_src, s_dest
                in zip(tablenames, schemas_shadow, schemas) for t in tablename}

tablenames = np.hstack(tablenames)
dj_compare_table.diff(tablenames, tablepairs)
