'''
This script populate all behavioral plotting table for the website
'''

import datajoint as dj
from ibl_pipeline.plotting import behavior
from ibl_pipeline import subject

dj.config['safemode'] = False

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
behavior.DateReactionTimeTrialNumber.populate(**kargs)
print('--------------- Populating plotting.WaterTypeColor -----------')
behavior.WaterTypeColor.populate(**kargs)
print('------------ Populating plotting.CumulativeSummary -----------')
latest = subject.Subject.aggr(
        behavior.LatestDate,
        checking_ts='MAX(checking_ts)') * behavior.LatestDate
(behavior.CumulativeSummary & latest).delete()
behavior.CumulativeSummary.populate(**kargs)
