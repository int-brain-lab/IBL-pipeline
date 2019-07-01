import datajoint as dj
import numpy as np
from ibl_pipeline import behavior, acquisition
from oneibl.one import ONE


trial_sets_reward_volume = behavior.CompleteTrialSession & \
    (behavior.TrialSet.Trial & 'trial_reward_volume is NULL') & \
    'reward_volume_status = "Complete"'
n_reward_volume = len(trial_sets_reward_volume)

trial_sets_iti_duration = behavior.CompleteTrialSession & \
    (behavior.TrialSet.Trial & 'trial_iti_duration is NULL') & \
    'iti_duration_status = "Complete"'
n_reward_volume = len(trial_sets_iti_duration)


if len(trial_sets_reward_volume):
    for ikey, key in enumerate(trial_sets_reward_volume.fetch('KEY')):
        # download data
        try:
            eID = str((acquisition.Session & key).fetch1('session_uuid'))
            go_cue_times = np.squeeze(ONE().load(
                eID, dataset_types='_ibl_trials.rewardVolume'))

            # update reward volume value
            trials = behavior.TrialSet.Trial & key & \
                'trial_reward_volume is NULL'
            for trial in trials.fetch('KEY'):
                dj.Table._update(
                    behavior.TrialSet.Trial & trial, 'trial_reward_volume',
                    trial['trial_id']-1)
            if ikey % 100 == 0:
                print('reward volume entry number: {}/{}'.format(ikey, n_reward_volume))
        except:
            print(key)


if len(trial_sets_iti_duration):
    for ikey, key in enumerate(trial_sets_iti_duration.fetch('KEY')):
        # download data
        try:
            eID = str((acquisition.Session & key).fetch1('session_uuid'))
            go_cue_times = np.squeeze(ONE().load(
                eID, dataset_types='_ibl_trials.itiDuration'))

            # update iti duration value
            trials = behavior.TrialSet.Trial & key & \
                'trial_iti_duration is NULL'
            for trial in trials.fetch('KEY'):
                dj.Table._update(
                    behavior.TrialSet.Trial & trial, 'trial_iti_duration',
                    trial['trial_id']-1)
            if ikey % 100 == 0:
                print('iti duration entry number: {}/{}'.format(ikey, n_iti_duration))

        except:
            print(key)
