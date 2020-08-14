'''
Create global variables for table names
'''


def init():

    global REF_TABLES, SUBJECT_TABLES, ACTION_TABLES, \
        ACQUISITION_TABLES, DATA_TABLES, EPHYS_TABLES

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
