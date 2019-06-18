import datajoint as dj
import numpy as np
from ibl_pipeline import behavior, acquisition, data

required_datasets = ["_ibl_trials.feedback_times.npy",
                     "_ibl_trials.feedbackType.npy",
                     "_ibl_trials.intervals.npy", "_ibl_trials.choice.npy",
                     "_ibl_trials.response_times.npy",
                     "_ibl_trials.contrastLeft.npy",
                     "_ibl_trials.contrastRight.npy",
                     "_ibl_trials.probabilityLeft.npy"]

for key in behavior.CompleteTrialSession.fetch('KEY'):
    #try:
    datasets = (data.FileRecord & key & 'repo_name LIKE "flatiron_%"' &
                {'exists': 1}).fetch('dataset_name')
    is_complete = bool(np.all([req_ds in datasets
                                for req_ds in required_datasets]))
    if is_complete is True:
        if '_ibl_trials.rewardVolume.npy' in datasets:
            dj.Table._update(behavior.CompleteTrialSession & key,
                                'reward_volume_status', 'Complete')

        if '_ibl_trials.itiDuration.npy' in datasets:
            dj.Table._update(behavior.CompleteTrialSession & key,
                             'iti_duration_status', 'Complete')

    # print(key)
