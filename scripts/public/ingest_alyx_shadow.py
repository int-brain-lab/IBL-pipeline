'''
This script inserts tuples in the alyxraw table into the shadow tables \
via auto-populating.
'''

import datajoint as dj
from ibl_pipeline.ingest import alyxraw, reference, subject, action, acquisition, data
from ibl_pipeline import public
import utils

kargs = dict(suppress_errors=True, display_progress=True, reserve_jobs=True)

# reference tables
print('-------- Populating reference shadow tables ------------')
reference.Lab.populate(**kargs)
reference.LabMember.populate(**kargs)
reference.LabMembership.populate(**kargs)
reference.LabLocation.populate(**kargs)
reference.Project.populate(**kargs)

# subject tables
print('-------- Populating subject shadow tables ------------')
subject.Species.populate(**kargs)
subject.Source.populate(**kargs)
subject.Strain.populate(**kargs)
subject.Sequence.populate(**kargs)
subject.Allele.populate(**kargs)
subject.Line.populate(**kargs)

subject.Subject.populate(**kargs)
# subject.BreedingPair.populate(**kargs)
# subject.Litter.populate(**kargs)
# subject.LitterSubject.populate(**kargs)
subject.SubjectProject.populate(**kargs)
subject.SubjectUser.populate(**kargs)
subject.SubjectLab.populate(**kargs)
subject.SubjectCullMethod.populate(**kargs)
subject.Caging.populate(**kargs)
# subject.UserHistory.populate(**kargs)
subject.Weaning.populate(**kargs)
subject.Death.populate(**kargs)
subject.GenotypeTest.populate(**kargs)
subject.Zygosity.populate(**kargs)

# action tables
print('-------- Populating action shadow tables -----------')
action.ProcedureType.populate(**kargs)
action.Surgery.populate(**kargs)


# acquisition tables
print('-------- Populating session entries -----------')
acquisition.Session.populate(**kargs)

# data tables
print('-------- Populating data shadow tables -----------')
data.DataFormat.populate(**kargs)
data.DataRepositoryType.populate(**kargs)
data.DataRepository.populate(**kargs)
data.DataSetType.populate(**kargs)
print('-------- Populating dataset entries -----------')
data.DataSet.populate(**kargs)
print('-------- Populating file record entries ----------')
data.FileRecord.populate(**kargs)
