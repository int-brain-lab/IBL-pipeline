'''
This script inserts tuples in the alyxraw table into the shadow tables \
via auto-populating.
'''

import datajoint as dj
from ibl_pipeline.ingest import \
    (alyxraw, reference, subject, action, acquisition)

kwargs = dict(
    display_progress=True,
    suppress_errors=True)

tables = [
    reference.Lab,
    reference.LabMember,
    reference.LabMembership,
    reference.LabLocation,
    reference.Project,
    subject.Species,
    subject.Source,
    subject.Strain,
    subject.Sequence,
    subject.Allele,
    subject.Line,
    subject.Subject,
    subject.BreedingPair,
    subject.Litter,
    subject.LitterSubject,
    subject.SubjectProject,
    subject.SubjectUser,
    subject.SubjectLab,
    subject.Caging,
    subject.Weaning,
    subject.Death,
    subject.SubjectCullMethod,
    subject.GenotypeTest,
    subject.Zygosity,
    action.ProcedureType,
    action.Weighing,
    action.WaterType,
    action.WaterAdministration,
    action.WaterRestriction,
    action.Surgery,
    action.OtherAction
    acquisition.Session,
    ]

for table in tables:
    print('Populating {}...'.format(table.__name))
    table.populate(**kwargs)
