import tqdm
from ibl_pipeline import subject, acquisition, behavior
from ibl_pipeline.analyses import behavior as behavior_analyses
import numpy as np


for key in tqdm(
        (behavior_analyses.BehavioralSummaryByDate &
         'n_trials_date is null').fetch('KEY')):
    trial_sets = behavior.TrialSet.proj(
        session_date='date(session_start_time)') & key
    n_trials_date = len(behavior.TrialSet.Trial & trial_sets)
    training_day = len(
        dj.U('session_date') &
        acquisition.Session.proj(session_date='date(session_start_time)') &
        'session_date<="{}"'.format(key['session_date'].strftime('%Y-%m-%d')))
    training_week = np.floor(training_day / 5)
    q = behavior_analyses.BehavioralSummaryByDate & key
    dj.Table._update(q, 'n_trials_date', n_trials_date)
    dj.Table._update(q, 'training_day', training_day)
    dj.Table._update(q, 'training_week', training_week)
