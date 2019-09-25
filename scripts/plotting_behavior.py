'''
This script populate all behavioral plotting table for the website
'''

from ibl_pipeline.plotting import behavior

kargs = dict(
    suppress_errors=True, display_progress=True
)

print('------------ Populating plotting.SessionPsychCurve -----------')
behavior.SessionPsychCurve.populate(**kargs)
print('------ Populating plotting.SessionReactionTimeContrast -------')
behavior.SessionReactionTimeContrast.populate(**kargs)
print('---- Populating plotting.SessionReactionTimeTrialNumber ------')
behavior.SessionReactionTimeTrialNumber.populate(**kargs)
print('--------------- Populating plotting.DatePsychCurve -----------')
behavior.DatePsychCurve.populate(**kargs)
print('-------- Populating plotting.DateReactionTimeContrast --------')
behavior.DateReactionTimeContrast.populate(**kargs)
print('--------------- Populating plotting.WaterTypeColor -----------')
behavior.WaterTypeColor.populate(**kargs)
print('------------ Populating plotting.CumulativeSummary -----------')
behavior.CumulativeSummary.populate(**kargs)
