'''
This script copies tuples in the shadow tables into the real tables for alyx.
'''

import datajoint as dj
from ibl.ingest import reference as reference_ingest
from ibl.ingest import subject as subject_ingest
from ibl.ingest import action as action_ingest
from ibl.ingest import acquisition as acquisition_ingest
from ibl.ingest import data as data_ingest
from ibl import reference, subject, action, acquisition, data


def copy_table(target_schema, src_schema, table_name):
    target_table = getattr(target_schema, table_name)
    src_table = getattr(src_schema, table_name)
    target_table.insert(src_table, skip_duplicates=True)

REF_TABLES = (
    'Lab',
    'LabMember',
    'LabMembership',
    'LabLocation',
    'Project',
    'ProjectLabMember'
)

for table in REF_TABLES:
    print(table)
    copy_table(reference, reference_ingest, table)

SUBJECT_TABLES = (
    'Species',
    'Strain',
    'Source',
    'Sequence',
    'Allele',
    'Line',
    'LineAllele',
    'Subject',
    'BreedingPair',
    'Litter',
    'LitterSubject',
    'Weaning',
    'Death',
    'GenotypeTest',
    'Zygosity',
    'Implant'
)

for table in SUBJECT_TABLES:
    print(table)
    copy_table(subject, subject_ingest, table)


ACTION_TABLES = (
    'ProcedureType',
    'Weighing',
    'WaterAdministration',
    'WaterRestriction',
    'Surgery',
    'SurgeryLabMember',
    'SurgeryProcedure'
)

for table in ACTION_TABLES:
    print(table)
    copy_table(action, action_ingest, table)

ACQUISITION_TABLES = (
    'Session',
    'ChildSession',
    'SessionLabMember',
    'SessionProcedureType'
)

for table in ACQUISITION_TABLES:
    print(table)
    copy_table(acquisition, acquisition_ingest, table)


DATA_TABLES = (
    'DataFormat',
    'DataRepositoryType',
    'DataRepository',
    'ProjectRepository',
    'DataSetType',
    'DataSet',
    'FileRecord'
)

for table in DATA_TABLES:
    print(table)
    copy_table(data, data_ingest, table)
