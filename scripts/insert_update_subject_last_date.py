'''
This script insert or update the latest date of each subject.
'''

import datajoint as dj
from ibl_pipeline.plotting import behavior
from ibl_pipeline import subject

subjects = subject.Subject.aggr(
    behavior.CumulativeSummary,
    latest_date='MAX(latest_date)')

for subj in subjects.fetch('KEY'):
    current_subj = behavior.SubjectLatestDate & subj
    new_date = (subjects & subj).fetch1('latest_date')
    if len(current_subj):
        current_subj._update('latest_date', new_date)
    else:
        behavior.SubjectLatestDate.insert1(subj)
