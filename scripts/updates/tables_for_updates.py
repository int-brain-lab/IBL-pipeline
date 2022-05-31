"""
Create global variables for table names
"""


def init():

    global REF_TABLES, SUBJECT_TABLES, ACTION_TABLES, ACQUISITION_TABLES, DATA_TABLES

    REF_TABLES = ("Lab", "LabMember", "LabLocation", "Project")

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
        "BreedingPair",
        "Litter",
        "LitterSubject",
        "Weaning",
        "Death",
        "Caging",
        "GenotypeTest",
        "Zygosity",
        "Implant",
    )

    ACTION_TABLES = (
        "ProcedureType",
        "Weighing",
        "WaterType",
        "Surgery",
        "SurgeryUser",
        "SurgeryProcedure",
        "OtherAction",
        "OtherActionUser",
        "OtherActionProcedure",
    )

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
    )
