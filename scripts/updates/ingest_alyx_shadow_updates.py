'''
This script inserts tuples in the alyxraw table into the shadow tables \
via auto-populating, to detect the latest values.
'''

import datajoint as dj
from ibl_pipeline.ingest import alyxraw, reference, subject, action, acquisition, data

# reference tables
reference.Lab.populate(suppress_errors=True)
reference.LabMember.populate(suppress_errors=True)
reference.LabMembership.populate(suppress_errors=True)
reference.LabLocation.populate(suppress_errors=True)
reference.Project.populate(suppress_errors=True)

# subject tables
subject.Species.populate(suppress_errors=True)
subject.Source.populate(suppress_errors=True)
subject.Strain.populate(suppress_errors=True)
subject.Sequence.populate(suppress_errors=True)
subject.Allele.populate(suppress_errors=True)
subject.Line.populate(suppress_errors=True)
subject.Subject.populate(suppress_errors=True)
subject.BreedingPair.populate(suppress_errors=True)
subject.Litter.populate(suppress_errors=True)
subject.LitterSubject.populate(suppress_errors=True)
subject.SubjectProject.populate(suppress_errors=True)
subject.SubjectUser.populate(suppress_errors=True)
subject.SubjectLab.populate(suppress_errors=True)
subject.Caging.populate(suppress_errors=True)
subject.UserHistory.populate(suppress_errors=True)
subject.Weaning.populate(suppress_errors=True)
subject.Death.populate(suppress_errors=True)
subject.GenotypeTest.populate(suppress_errors=True)
subject.Zygosity.populate(suppress_errors=True)

# # action tables
# action.ProcedureType.populate(suppress_errors=True)
# action.Weighing.populate(suppress_errors=True)
# action.WaterType.populate(suppress_errors=True)
# action.WaterAdministration.populate(suppress_errors=True)
# action.WaterRestriction.populate(suppress_errors=True)
# action.Surgery.populate(suppress_errors=True)
# action.OtherAction.populate(suppress_errors=True)

# # acquisition tables
# acquisition.Session.populate(suppress_errors=True)

# # data tables
# data.DataFormat.populate(suppress_errors=True)
# data.DataRepositoryType.populate(suppress_errors=True)
# data.DataRepository.populate(suppress_errors=True)
# data.DataSetType.populate(suppress_errors=True)
