import datajoint as dj
from ibl_pipeline.ingest import alyxraw, reference, subject, \
    action, acquisition, data


dj.config['safemode'] = False

# delete alyxraw for data.filerecord if exists = 0
print('Deleting alyxraw entries corresponding to file records...')
alyxraw.AlyxRaw.delete()

# delete shadow membership tables
print('Deleting membership tables...')
# reference tables
reference.Lab.delete()
reference.LabMember.delete()
reference.LabMembership.delete()
reference.LabLocation.delete()
reference.Project.delete()

# subject tables
subject.Species.delete()
subject.Source.delete()
subject.Strain.delete()
subject.Sequence.delete()
subject.Allele.delete()
subject.Line.delete()
subject.Subject.delete()
subject.BreedingPair.delete()
subject.Litter.delete()
subject.LitterSubject.delete()
subject.SubjectProject.delete()
subject.SubjectUser.delete()
subject.SubjectLab.delete()
subject.Caging.delete()
subject.UserHistory.delete()
subject.Weaning.delete()
subject.Death.delete()
subject.GenotypeTest.delete()
subject.Zygosity.delete()

# action tables
action.ProcedureType.delete()
action.Weighing.delete()
action.WaterType.delete()
action.WaterAdministration.delete()
action.WaterRestriction.delete()
action.Surgery.delete()
action.OtherAction.delete()

# acquisition tables
acquisition.Session.delete()

# data tables
data.DataFormat.delete()
data.DataRepositoryType.delete()
data.DataRepository.delete()
data.DataSetType.delete()
