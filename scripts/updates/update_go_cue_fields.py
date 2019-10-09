import datajoint as dj
import numpy as np
from ibl_pipeline import behavior, acquisition
from oneibl.one import ONE

trial_sets_go_cue = behavior.CompleteTrialSession & \
    (behavior.TrialSet.Trial & 'trial_go_cue_time is NULL') & \
    'go_cue_times_status = "Complete"'
n_go_cue = len(trial_sets_go_cue)

trial_sets_go_cue_trigger = behavior.CompleteTrialSession & \
    (behavior.TrialSet.Trial & 'trial_go_cue_trigger_time is NULL') & \
    'go_cue_trigger_times_status = "Complete"'
n_go_cue_trigger = len(trial_sets_go_cue_trigger)


if len(trial_sets_go_cue):
    for ikey, key in enumerate(trial_sets_go_cue.fetch('KEY')):
        # download data
        try:
            eID = str((acquisition.Session & key).fetch1('session_uuid'))
            go_cue_times = np.squeeze(ONE().load(
                eID, dataset_types='_ibl_trials.goCue_times'))

            # update go cue time value
            trials = behavior.TrialSet.Trial & key & \
                'trial_go_cue_time is NULL'
            for trial in trials.fetch('KEY'):
                dj.Table._update(
                    behavior.TrialSet.Trial & trial, 'trial_go_cue_time',
                    go_cue_times[trial['trial_id']-1])

            if ikey % 100 == 0:
                print('Go Cue entry number: {}/{}'.format(ikey, n_go_cue))
        except:
            print(key)


if len(trial_sets_go_cue_trigger):
    for ikey, key in enumerate(trial_sets_go_cue_trigger.fetch('KEY')):
        try:
            # download data
            eID = str((acquisition.Session & key).fetch1('session_uuid'))
            go_cue_times = np.squeeze(ONE().load(
                eID, dataset_types='_ibl_trials.goCueTrigger_times'))

            # update go cue trigger time value
            trials = behavior.TrialSet.Trial & key & \
                'trial_go_cue_trigger_time is NULL'
            for trial in trials.fetch('KEY'):
                dj.Table._update(
                    behavior.TrialSet.Trial & trial,
                    'trial_go_cue_trigger_time',
                    go_cue_times[trial['trial_id']-1])
            if ikey % 100 == 0:
                print('Go Cue Trigger entry number: {}/{}'.format(ikey, n_go_cue_trigger))

        except:
            print(key)
