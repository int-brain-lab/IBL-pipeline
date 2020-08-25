'''
This script copies tuples in the shadow tables into the real tables for alyx.
'''

import datajoint as dj
from ibl_pipeline.ingest import reference as reference_ingest
from ibl_pipeline.ingest import subject as subject_ingest
from ibl_pipeline.ingest import action as action_ingest
from ibl_pipeline.ingest import acquisition as acquisition_ingest
from ibl_pipeline.ingest import data as data_ingest
from ibl_pipeline.ingest import ephys as ephys_ingest
from ibl_pipeline.ingest import histology as histology_ingest
from ibl_pipeline import reference, subject, action, acquisition, data, ephys, histology
from ingest_utils import copy_table
from table_names import *


if __name__ == '__main__':

    dj.config['safemode'] = False

    mods = [
        [reference, reference_ingest, REF_TABLES],
        [subject, subject_ingest, SUBJECT_TABLES],
        [action, action_ingest, ACTION_TABLES],
        [acquisition, acquisition_ingest, ACQUISITION_TABLES],
        [data, data_ingest, DATA_TABLES]
    ]

    for (target, source, table_list) in mods:
        for table in table_list:
            print(table)
            copy_table(target, source, table)

    # ephys tables
    table = 'ProbeModel'
    print(table)
    copy_table(ephys, ephys_ingest, table)

    table = 'ProbeInsertion'
    print(table)
    copy_table(ephys, ephys_ingest, table, allow_direct_insert=True)

    # histology tables
    print('ProbeTrajectory')
    histology.ProbeTrajectory.populate(suppress_errors=True, display_progress=True)

    print('ChannelBrainLocation')
    copy_table(histology, histology_ingest, 'ChannelBrainLocation',
            allow_direct_insert=True)
