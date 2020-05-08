
import datajoint as dj
from ibl_pipeline import acquisition, behavior
import numpy as np
from tqdm import tqdm
from oneibl.one import ONE
import sys

one = ONE()


def update_field(key, eID, trials, alf, djattr, dtype, status,
                 message_record):

    data_status = (behavior.CompleteTrialSession & key).fetch1(status)

    if data_status != 'Missing':
        dataset = np.squeeze(one.load(eID, dataset_types=alf))

        if len(dataset) != len(trials):
            message_record.append(
                dict(**key, error=alf))
        else:
            for itrial, trial_key in enumerate(trials.fetch('KEY')):
                # print(dtype(dataset[itrial]))
                dj.Table._update(
                    behavior.TrialSet.Trial & trial_key,
                    djattr, dtype(dataset[itrial]))
    else:
        return


# fetch keys with reward_volume but null in table TrialSet.Trial

sessions = behavior.TrialSet.aggr(
    behavior.TrialSet.Trial,
    n_prob_trials='sum(trial_id=floor(trial_reward_volume)+1)',
    n_total_trials='count(*)') & 'n_prob_trials=n_total_trials'

if len(sys.argv) < 2:
    keys = sessions.fetch('KEY')
else:
    keys = (sessions & sys.argv[1]).fetch('KEY')

fields = [
    # {'alf': 'trials.repNum',             'djattr': 'trial_rep_num',             'dtype': int,   'status': 'rep_num_status'},
    # {'alf': 'trials.included',           'djattr': 'trial_included',            'dtype': bool,  'status': 'included_status'},
    # {'alf': 'trials.goCue_times',        'djattr': 'trial_go_cue_time',         'dtype': float, 'status': 'go_cue_times_status'},
    # {'alf': 'trials.goCueTrigger_times', 'djattr': 'trial_go_cue_trigger_time', 'dtype': float, 'status': 'go_cue_trigger_times_status'},
    {'alf': 'trials.rewardVolume',       'djattr': 'trial_reward_volume',       'dtype': float, 'status': 'reward_volume_status'},
    # {'alf': 'trials.itiDuration',        'djattr': 'trial_iti_duration',        'dtype': float, 'status': 'iti_duration_status'},
]

problematic_keys = []

for key in tqdm(keys):
    try:
        eID = str((acquisition.Session & key).fetch1('session_uuid'))
        trials = behavior.TrialSet.Trial & key

        for field in fields:
            update_field(key, eID, trials, **field,
                         message_record=problematic_keys)

    except Exception:
        problematic_keys.append(dict(**key, error='other'))
        print(
            'problem updating {}'.format(
                ', '.join('{}: {}'.format(k, value) for k, value in key.items())))

np.save('problematic_keys.npy', problematic_keys)
