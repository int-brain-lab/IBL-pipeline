'''
table names
'''

REF_TABLES = (
    'Lab',
    'LabMember',
    'LabMembership',
    'LabLocation',
    'Project',
    'ProjectLabMember'
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
