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
reference.ProjectLabMember.delete()

# subject tables
subject.AlleleSequence.delete()
subject.LineAllele.delete()

# action tables
action.WaterRestrictionUser.delete()
action.WaterRestrictionProcedure.delete()
action.SurgeryUser.delete()
action.SurgeryProcedure.delete()
action.OtherActionUser.delete()
action.OtherActionProcedure.delete()

# acquisition tables
acquisition.ChildSession.delete()
acquisition.SessionProject.delete()
acquisition.SessionUser.delete()
acquisition.WaterAdministrationSession.delete()

# data tables
data.ProjectRepository.delete()
