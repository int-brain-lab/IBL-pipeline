'''
This script copies tuples in the shadow tables into the real tables for alyx.
'''

import datajoint as dj
from ibl_pipeline.ingest.common import *
from ibl_pipeline import reference, subject, action, acquisition, data, ephys
import traceback
import datetime
import os
import numpy as np


mode = os.environ.get('MODE')

REF_TABLES = (
    'Lab',
    'LabMember',
    'LabMembership',
    'LabLocation',
    'Project',
    'ProjectLabMember',
    'CoordinateSystem'
)

SUBJECT_TABLES = (
    'Species',
    'Strain',
    'Source',
    'Sequence',
    'Allele',
    'AlleleSequence',
    'Line',
    'LineAllele',
    'Subject',
    'SubjectUser',
    'SubjectProject',
    'SubjectLab',
    'BreedingPair',
    'Litter',
    'LitterSubject',
    'Weaning',
    'Death',
    'SubjectCullMethod',
    'Caging',
    'UserHistory',
    'GenotypeTest',
    'Zygosity',
    'Implant',
    'Food',
    'CageType',
    'Enrichment',
    'Housing',
    'SubjectHousing'
)

if mode != 'public':
    ACTION_TABLES = (
        'ProcedureType',
        'Weighing',
        'WaterType',
        'WaterAdministration',
        'WaterRestriction',
        'WaterRestrictionUser',
        'WaterRestrictionProcedure',
        'Surgery',
        'SurgeryUser',
        'SurgeryProcedure',
        'OtherAction',
        'OtherActionUser',
        'OtherActionProcedure',
        'CullMethod',
        'CullReason',
        'Cull'
    )
else:
    ACTION_TABLES = (
        'ProcedureType',
        'Surgery',
        'SurgeryUser',
        'SurgeryProcedure',
    )

if mode != 'public':
    ACQUISITION_TABLES = (
        'Session',
        'ChildSession',
        'SessionUser',
        'SessionProcedure',
        'SessionProject',
        'WaterAdministrationSession'
    )
else:
    ACQUISITION_TABLES = (
        'Session',
        'ChildSession',
        'SessionUser',
        'SessionProcedure',
        'SessionProject'
    )

DATA_TABLES = (
    'DataFormat',
    'DataRepositoryType',
    'DataRepository',
    'ProjectRepository',
    'DataSetType',
    'DataSet',
    'FileRecord'
)

EPHYS_TABLES = (
    'Probe',
)


def copy_table(target_schema, src_schema, table_name,
               fresh=False, use_uuid=True, backtrack_days=None, **kwargs):
    if '.' in table_name:
        # handling part-table
        master_name, part_name = table_name.split('.')
        target_table = getattr(getattr(target_schema, master_name), part_name)
        src_table = getattr(getattr(src_schema, master_name), part_name)
    else:
        target_table = getattr(target_schema, table_name)
        src_table = getattr(src_schema, table_name)

    if fresh:
        target_table.insert(src_table, **kwargs)
    else:
        # only ingest entries within certain number of days
        if backtrack_days and 'session_start_time' in src_table.heading.attributes:
            date_cutoff = \
                (datetime.datetime.now().date() -
                 datetime.timedelta(days=backtrack_days)).strftime('%Y-%m-%d')
            q_src_table = src_table & f'session_start_time > "{date_cutoff}"'
        else:
            q_src_table = src_table

        if use_uuid:
            pk = src_table.heading.primary_key
            if len(pk) == 1 and 'uuid' in pk[0]:
                q_insert = q_src_table - (dj.U(pk[0]) & target_table & f'{pk[0]} is not null')
            else:
                q_insert = q_src_table - target_table.proj()
        else:
            q_insert = q_src_table - target_table.proj()

        # keep only records in "q_insert" HAVING entries in the parent tables
        for parent_table, parent_fk_info in target_table.parents(
                as_objects=True, foreign_key_info=True):
            # skipping "nullable" foreign key
            if np.all([target_table.heading.attributes[attr].nullable
                       for attr in parent_fk_info['attr_map']]):
                continue
            # skipping `BrainRegion` table, collations conflicts
            if dj.utils.to_camel_case(
                parent_table.full_table_name.split('.')[-1].replace('`', '')) in ('BrainRegion'):
                continue

            parent_table = parent_table.proj(**parent_fk_info['attr_map'])
            q_insert &= parent_table

        kwargs = {**kwargs, 'skip_duplicates': True,
                  'ignore_extra_fields': True,
                  'allow_direct_insert': True}

        try:
            target_table.insert(q_insert, **kwargs)
        except Exception:
            for key in q_insert.fetch('KEY'):
                try:
                    target_table.insert(q_insert & key, **kwargs)
                except Exception:
                    print("Error when inserting {}".format((q_insert & key).fetch1()))
                    traceback.print_exc()


def main(excluded_tables=[]):
    mods = [
        [reference, reference_ingest, REF_TABLES],
        [subject, subject_ingest, SUBJECT_TABLES],
        [action, action_ingest, ACTION_TABLES],
        [acquisition, acquisition_ingest, ACQUISITION_TABLES],
        [data, data_ingest, DATA_TABLES]
    ]
    if mode == 'public':
        backtrack_days = None
    else:
        backtrack_days = 30

    for (target, source, table_list) in mods:
        for table in table_list:
            if table in excluded_tables:
                continue
            print(table)
            copy_table(target, source, table, backtrack_days=backtrack_days)

    # ephys tables
    table = 'ProbeModel'
    print(table)
    copy_table(ephys, ephys_ingest, table)

    table = 'ProbeInsertion'
    print(table)
    copy_table(ephys, ephys_ingest, table, allow_direct_insert=True)


if __name__ == '__main__':

    with dj.config(safemode=False):
        main()
