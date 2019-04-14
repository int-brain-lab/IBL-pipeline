'''
This script creates a summary of the training status of animals in each lab.
'''

import datajoint as dj
from ibl_pipeline import reference, subject, action, acquisition, behavior
from ibl_pipeline.analyses import behavior as behavior_analyses
import pandas as pd
import numpy as np
from datetime import datetime


for ilab in reference.Lab:
    ingested_sessions = acquisition.Session & 'task_protocol!="NULL"' \
        & behavior.TrialSet
    subjects = ((subject.Subject*subject.SubjectLab & ilab) - subject.Death) \
        & 'sex != "U"' & \
        action.Weighing & action.WaterAdministration & ingested_sessions

    if not len(subjects):
        continue

    last_sessions = subjects.aggr(
        ingested_sessions,
        'subject_nickname', session_start_time='max(session_start_time)') \
        * acquisition.Session \
        * behavior_analyses.SessionTrainingStatus
    summary = last_sessions.proj(
        'subject_nickname', 'task_protocol', 'training_status').fetch(
            as_dict=True)

    task_protocols = last_sessions.fetch('task_protocol')
    protocols = [protocol.partition('ChoiceWorld')[0]
                 for protocol in task_protocols]
    for i, entry in enumerate(summary):
        subj = subject.Subject & entry
        protocol = protocols[i]
        entry['lastest_session_start_time'] = entry.pop('session_start_time')
        entry['latest_task_protocol'] = entry.pop('task_protocol')
        entry['latest_training_status'] = entry.pop('training_status')
        # get all sessions with this protocol
        entry['n_sessions'] = len(
            ingested_sessions & subj &
            'task_protocol LIKE "{}%"'.format(protocol))

    summary = pd.DataFrame(summary)
    summary.sort_values(by='subject_nickname')
    summary.pop('subject_uuid')
    summary.index += 1
    cols = summary.columns.tolist()
    cols = cols[-1:] + cols[:-1]
    summary = summary[cols]
    last_session_date = \
        np.max(summary['lastest_session_start_time']).date().strftime('%Y-%m-%d')
    summary.to_csv(
        '/src/IBL-pipeline/snapshots/{}_{}_summary.csv'.format(
            last_session_date, ilab['lab_name']))
    print('Saved {} current training status summary.'.format(ilab['lab_name']))
