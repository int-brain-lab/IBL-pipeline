'''
This script copies tuples in the shadow tables into the real tables for alyx.
'''

import datajoint as dj
from ibl_pipeline.ingest.common import *
from ibl_pipeline import reference, subject, action, acquisition, data, ephys
import traceback
import datetime
import os


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
        attrs = table_name.split('.')

        target_table = target_schema
        src_table = src_schema
        for a in attrs:
            target_table = getattr(target_table, a)
            src_table = getattr(src_table, a)
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

        try:
            target_table.insert(q_insert, skip_duplicates=True, **kwargs)

        except Exception:
            for t in (q_insert).fetch(as_dict=True):
                try:
                    if table_name == 'DataSet' and \
                         not len(t['dataset_created_by']):
                        t.pop('dataset_created_by')
                    target_table.insert1(t, skip_duplicates=True, **kwargs)
                except Exception:
                    print("Error when inserting {}".format(t))
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

    dj.config['safemode'] = False
    main()
