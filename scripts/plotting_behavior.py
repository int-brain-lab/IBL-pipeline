'''
This script populate all behavioral plotting table for the website
'''

import datajoint as dj
from ibl_pipeline.plotting import behavior
from ibl_pipeline import subject, reference
import compute_latest_date
from tqdm import tqdm

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

print('------------ Populating plotting.CumulativeSummary and update SubjectLatestDate -----------')
latest = subject.Subject.aggr(
        behavior.LatestDate,
        checking_ts='MAX(checking_ts)') * behavior.LatestDate & \
            ['latest_date between curdate() - interval 30 day and curdate()',
             (subject.Subject - subject.Death)] & \
            (subject.Subject & 'subject_nickname not like "%human%"').proj()

subj_keys = (subject.Subject & latest).fetch('KEY')

# delete and repopulate subject by subject
for subj_key in tqdm(subj_keys):
    (behavior.CumulativeSummary & subj_key & latest).delete()
    behavior.CumulativeSummary.populate(
        latest & subj_key, suppress_errors=True)
    # --- update the latest date of the subject -----
    # get the latest date of the CumulativeSummary of the subject
    subj_with_latest_date = (subject.Subject & subj_key).aggr(
        behavior.CumulativeSummary, latest_date='max(latest_date)')
    new_date = subj_with_latest_date.fetch1('latest_date')
    current_subj = behavior.SubjectLatestDate & subj_key
    if len(current_subj):
        current_subj._update('latest_date', new_date)
    else:
        behavior.SubjectLatestDate.insert1(
            subj_with_latest_date.fetch1())

print('------ Populating plotting.DailyLabSummary ------')
last_sessions = (reference.Lab.aggr(
    behavior.DailyLabSummary,
    last_session_time='max(last_session_time)')).fetch('KEY')
(behavior.DailyLabSummary & last_sessions).delete()
behavior.DailyLabSummary.populate(**kargs)
