import datajoint as dj
import numpy as np
from ibl_pipeline import behavior, acquisition
from oneibl.one import ONE


trial_sets_go_cue = behavior.CompleteTrialSession & \
    'go_cue_times_status = "Complete"'
trial_sets_go_cue_trigger = behavior.CompleteTrialSession & \
    'go_cue_trigger_times_status = "Complete"'

if len(trial_sets_go_cue):
    for key in trial_sets_go_cue.fetch('KEY'):
        # download data
        eID = str((acquisition.Session & key).fetch1('session_uuid'))
        go_cue_times = np.squeeze(ONE().load(
            eID, dataset_types='_ibl_trials.goCue_times'))

        # update go cue time value
        trials = behavior.TrialSet & key
        for trial in trials.fetch('KEY'):
            dj.Table._update(
                behavior.TrialSet.Trial & trial, 'trial_go_cue_time',
                go_cue_times[trial['trial_id']])


if len(trial_sets_go_cue_trigger):
    for key in trial_sets_go_cue_trigger.fetch('KEY'):
        # download data
        eID = str((acquisition.Session & key).fetch1('session_uuid'))
        go_cue_times = np.squeeze(ONE().load(
            eID, dataset_types='_ibl_trials.goCueTrigger_times'))

        # update go cue time value
        trials = behavior.TrialSet & key
        for trial in trials.fetch('KEY'):
            dj.Table._update(
                behavior.TrialSet.Trial & trial, 'trial_go_cue_trigger_time',
                go_cue_times[trial['trial_id']])
