'''
This script populate all behavioral plotting table for the website
'''

from ibl_pipeline.plotting import behavior

kargs = dict(
    suppress_errors=True, display_progress=True
)

behavior.DatePsychCurve.populate(**kargs)
behavior.DateReactionTimeContrast.populate(**kargs)
behavior.DateReactionTimeTrialNumber.populate(**kargs)
behavior.SessionPsychCurve.populate(**kargs)
behavior.CumulativeSummary.populate(**kargs)
behavior.DailyLabSummary.populate(**kargs)
