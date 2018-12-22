'''
This script copies tuples in the shadow tables into the real tables for alyx, for fresh ingestion.
'''

import datajoint as dj
from ibl_pipeline.ingest import reference as reference_ingest
from ibl_pipeline.ingest import subject as subject_ingest
from ibl_pipeline.ingest import action as action_ingest
from ibl_pipeline.ingest import acquisition as acquisition_ingest
from ibl_pipeline.ingest import data as data_ingest
from ibl_pipeline import reference, subject, action, acquisition, data
from ingest_utils import copy_table


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
    'AlleleSequence',
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
    'WaterType',
    'WaterAdministration',
    'WaterRestriction',
    'WaterRestrictionUser',
    'WaterRestrictionProcedure',
    'Surgery',
    'SurgeryUser',
    'SurgeryProcedure'
)

for table in ACTION_TABLES:
    print(table)
    copy_table(action, action_ingest, table)

ACQUISITION_TABLES = (
    'Session',
    'ChildSession',
    'SessionUser',
    'SessionProcedure'
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
