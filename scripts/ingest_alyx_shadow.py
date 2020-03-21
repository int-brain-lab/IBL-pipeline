'''
This script inserts tuples in the alyxraw table into the shadow tables \
via auto-populating.
'''

import datajoint as dj
from ibl_pipeline.ingest import \
    (alyxraw, reference, subject, action, acquisition, data, ephys)

kargs = dict(
    display_progress=True,
    suppress_errors=True)

# reference tables
print('---------- Ingesting reference tables ---------')
reference.Lab.populate(**kargs)
reference.LabMember.populate(**kargs)
reference.LabMembership.populate(**kargs)
reference.LabLocation.populate(**kargs)
reference.Project.populate(**kargs)
reference.CoordinateSystem.populate(**kargs)

# subject tables
print('---------- Ingesting subject tables ---------')
subject.Species.populate(**kargs)
subject.Source.populate(**kargs)
subject.Strain.populate(**kargs)
subject.Sequence.populate(**kargs)
subject.Allele.populate(**kargs)
subject.Line.populate(**kargs)
subject.Subject.populate(**kargs)
subject.BreedingPair.populate(**kargs)
subject.Litter.populate(**kargs)
subject.LitterSubject.populate(**kargs)
subject.SubjectProject.populate(**kargs)
subject.SubjectUser.populate(**kargs)
subject.SubjectLab.populate(**kargs)
subject.Caging.populate(**kargs)
subject.UserHistory.populate(**kargs)
subject.Weaning.populate(**kargs)
subject.Death.populate(**kargs)
subject.SubjectCullMethod.populate(**kargs)
subject.GenotypeTest.populate(**kargs)
subject.Zygosity.populate(**kargs)

# action tables
print('---------- Ingesting action tables ---------')
action.ProcedureType.populate(**kargs)
action.Weighing.populate(**kargs)
action.WaterType.populate(**kargs)
action.WaterAdministration.populate(**kargs)
action.WaterRestriction.populate(**kargs)
action.Surgery.populate(**kargs)
action.OtherAction.populate(**kargs)

# acquisition tables
print('---------- Ingesting acquisition tables ---------')
acquisition.Session.populate(**kargs)

# data tables
print('---------- Ingesting data tables ---------')
data.DataFormat.populate(**kargs)
data.DataRepositoryType.populate(**kargs)
data.DataRepository.populate(**kargs)
data.DataSetType.populate(**kargs)
# data.DataSet.populate(**kargs)
# data.FileRecord.populate(**kargs)

# ephys tables
print('------------ Ingesting ephys tables -----------')
ephys.Probe.populate(**kargs)
ephys.ProbeInsertion.populate(**kargs)
ephys.ProbeTrajectory.populate(**kargs)
