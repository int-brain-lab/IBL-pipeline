'''
This script populate all behavioral plotting table for the website
'''

import datajoint as dj
from ibl_pipeline.plotting import behavior
from ibl_pipeline import subject


kwargs = dict(
    suppress_errors=True, display_progress=True
)

print('------------ Populating plotting.SessionPsychCurve -----------')
behavior.SessionPsychCurve.populate(**kwargs)
print('------ Populating plotting.SessionReactionTimeContrast -------')
behavior.SessionReactionTimeContrast.populate(**kwargs)
print('---- Populating plotting.SessionReactionTimeTrialNumber ------')
behavior.SessionReactionTimeTrialNumber.populate(**kwargs)
print('--------------- Populating plotting.DatePsychCurve -----------')
behavior.DatePsychCurve.populate(**kwargs)
print('-------- Populating plotting.DateReactionTimeContrast --------')
behavior.DateReactionTimeContrast.populate(**kwargs)
print('--------------- Populating plotting.WaterTypeColor -----------')
behavior.WaterTypeColor.populate(**kwargs)
print('------------ Populating plotting.CumulativeSummary -----------')
with dj.config(safemode=False):
    (behavior.CumulativeSummary
     & behavior.CumulativeSummary.get_outdated_entries().fetch('KEY')).delete()
behavior.CumulativeSummary.populate(**kwargs)
