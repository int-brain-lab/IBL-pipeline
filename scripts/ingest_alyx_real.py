'''
This script copy tuples in the shadow tables into the real tables for alyx.
'''

import datajoint as dj
from ibl.ingest import reference as reference_ingest
from ibl.ingest import subject as subject_ingest
from ibl.ingest import action as action_ingest
from ibl.ingest import acquisition as acquisition_ingest
from ibl.ingest import data as data_ingest
from ibl import reference, subject, action, acquisition, data

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
    eval('reference.{table_name}.insert(reference_ingest.{table_name}(), skip_duplicates=True)'.format(table_name=table))

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
    eval('subject.{table_name}.insert(subject_ingest.{table_name}(), skip_duplicates=True)'.format(table_name=table))

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
    eval('action.{table_name}.insert(action_ingest.{table_name}(), skip_duplicates=True)'.format(table_name=table))

ACQUISITION_TABLES = (
    'Session',
    'ChildSession',
    'SessionLabMember',
    'SessionProcedureType'
)

for table in ACQUISITION_TABLES:
    print(table)
    eval('acquisition.{table_name}.insert(acquisition_ingest.{table_name}(), skip_duplicates=True)'.format(table_name=table))

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
    eval('data.{table_name}.insert(data_ingest.{table_name}(), skip_duplicates=True)'.format(table_name=table))