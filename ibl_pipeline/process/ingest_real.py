'''
This script copies tuples in the shadow tables into the real tables for alyx.
'''

import datajoint as dj
from ibl_pipeline.ingest.common import *
from ibl_pipeline.common import *
import traceback

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
    'OtherActionProcedure'
)

ACQUISITION_TABLES = (
    'Session',
    'ChildSession',
    'SessionUser',
    'SessionProcedure',
    'SessionProject',
    'WaterAdministrationSession'
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

def copy_table(target_schema, src_schema, table_name, fresh=False, **kwargs):
    target_table = getattr(target_schema, table_name)
    src_table = getattr(src_schema, table_name)

    if fresh:
        target_table.insert(src_table, **kwargs)
    else:
        try:
            target_table.insert(src_table - target_table.proj(),
                                skip_duplicates=True, **kwargs)
        except Exception:
            for t in (src_table - target_table.proj()).fetch(as_dict=True):
                try:
                    if table_name == 'DataSet' and \
                         not len(t['dataset_created_by']):
                        t.pop('dataset_created_by')
                    target_table.insert1(t, skip_duplicates=True, **kwargs)
                except Exception:
                    print("Error when inserting {}".format(t))
                    traceback.print_exc()

def main(excluded_tables=[], public=False):
    mods = [
        [reference, reference_ingest, REF_TABLES],
        [subject, subject_ingest, SUBJECT_TABLES],
        [action, action_ingest, ACTION_TABLES],
        [acquisition, acquisition_ingest, ACQUISITION_TABLES],
        [data, data_ingest, DATA_TABLES]
    ]

    for (target, source, table_list) in mods:
        for table in table_list:
            if table in excluded_tables:
                continue
            print(table)
            copy_table(target, source, table)

    if public:
        return

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

if __name__ == '__main__':

    dj.config['safemode'] = False
    main()
