import datajoint as dj
import numpy as np
from ibl_pipeline import behavior, acquisition
from oneibl.one import ONE

trial_sets_go_cue = behavior.CompleteTrialSession & \
    'go_cue_times_status = "Complete"'
n_go_cue = len(trial_sets_go_cue)

trial_sets_go_cue_trigger = behavior.CompleteTrialSession & \
    'go_cue_trigger_times_status = "Complete"'
n_go_cue_trigger = len(trial_sets_go_cue_trigger)

trial_sets_reward_volume = behavior.CompleteTrialSession & \
    'reward_volume_status = "Complete"'
n_reward_volume = len(trial_sets_reward_volume)

trial_sets_iti_duration = behavior.CompleteTrialSession & \
    'iti_duration_status = "Complete"'
n_reward_volume = len(trial_sets_iti_duration)

if len(trial_sets_go_cue):
    for ikey, key in enumerate(trial_sets_go_cue.fetch('KEY')):
        # download data
        try:
            eID = str((acquisition.Session & key).fetch1('session_uuid'))
            go_cue_times = np.squeeze(ONE().load(
                eID, dataset_types='_ibl_trials.goCue_times'))

            # update go cue time value
            trials = behavior.TrialSet.Trial & key & \
                'trial_go_cue_time is not NULL'
            if not len(trials):
                continue
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

            # update go cue time value
            trials = behavior.TrialSet.Trial & key & \
                'trial_go_cue_trigger_time is not NULL'

            if not len(trials):
                continue

            for trial in trials.fetch('KEY'):
                dj.Table._update(
                    behavior.TrialSet.Trial & trial,
                    'trial_go_cue_trigger_time',
                    go_cue_times[trial['trial_id']-1])
            if ikey % 100 == 0:
                print('Entry number: {}/{}'.format(ikey, n_go_cue_trigger))

        except:
            print(key)

if len(trial_sets_reward_volume):
    for ikey, key in enumerate(trial_sets_reward_volume.fetch('KEY')):
        # download data
        try:
            eID = str((acquisition.Session & key).fetch1('session_uuid'))
            go_cue_times = np.squeeze(ONE().load(
                eID, dataset_types='_ibl_trials.rewardVolume'))

            # update go cue time value
            trials = behavior.TrialSet.Trial & key & \
                'trial_reward_volume is not NULL'

            if not len(trials):
                continue

            for trial in trials.fetch('KEY'):
                dj.Table._update(
                    behavior.TrialSet.Trial & trial, 'trial_reward_volume',
                    [trial['trial_id']-1])
            if ikey % 100 == 0:
                print('Entry number: {}/{}'.format(ikey, n_reward_volume))
        except:
            print(key)


if len(trial_sets_iti_duration):
    for ikey, key in enumerate(trial_sets_iti_duration.fetch('KEY')):
        # download data
        try:
            eID = str((acquisition.Session & key).fetch1('session_uuid'))
            go_cue_times = np.squeeze(ONE().load(
                eID, dataset_types='_ibl_trials.itiDuration'))

            # update go cue time value
            trials = behavior.TrialSet.Trial & key & \
                'trial_iti_duration is not NULL'

            if not len(trials):
                continue

            for trial in trials.fetch('KEY'):
                dj.Table._update(
                    behavior.TrialSet.Trial & trial, 'trial_iti_duration',
                    [trial['trial_id']-1])
            if ikey % 100 == 0:
                print('Entry number: {}/{}'.format(ikey, n_iti_duration))

        except:
            print(key)
