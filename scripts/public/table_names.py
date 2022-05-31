"""
Create global variables for table names
"""


def init():

    global REF_TABLES, SUBJECT_TABLES, ACTION_TABLES, ACQUISITION_TABLES, DATA_TABLES

    REF_TABLES = (
        "Lab",
        "LabMember",
        "LabMembership",
        "LabLocation",
        "Project",
        "ProjectLabMember",
    )

    SUBJECT_TABLES = (
        "Species",
        "Strain",
        "Source",
        "Sequence",
        "Allele",
        "AlleleSequence",
        "Line",
        "LineAllele",
        "Subject",
        "SubjectUser",
        "SubjectProject",
        "SubjectLab",
        "Caging",
        "Death",
        "Weaning",
        "SubjectCullMethod",
        "GenotypeTest",
        "Zygosity",
        "Implant",
    )

    ACTION_TABLES = ("ProcedureType", "Surgery", "SurgeryUser", "SurgeryProcedure")

    ACQUISITION_TABLES = (
        "Session",
        "ChildSession",
        "SessionUser",
        "SessionProcedure",
        "SessionProject",
    )

    DATA_TABLES = (
        "DataFormat",
        "DataRepositoryType",
        "DataRepository",
        "ProjectRepository",
        "DataSetType",
        "DataSet",
        "FileRecord",
    )
