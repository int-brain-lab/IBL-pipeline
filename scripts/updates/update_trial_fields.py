
import datajoint as dj
from ibl_pipeline import behavior
from tqdm import tqdm
from oneibl.one import ONE

one = ONE()


def update_field(key, eID, trials, alf, dj, dtype=float, status,
                 message_record):

    data_status = (behavior.CompleteTrialSession & key).fetch1(status)

    if data_status != 'Missing' and \
            len(trials & f'{dj} is null'):
        dataset = np.squeeze(one.load(
            eID, dataset_types=alf))

        if len(dataset) != len(trials):
            message_record.append(
                dict(**key, error=alf))
        else:
            for itrial, trial_key in enumerate(trials.fetch('KEY')):
                dj.Table._update(
                    behavior.TrialSet.Trial & trial_key,
                    dj, dtype(dataset[itrial]))
    else:
        return


# fetch keys with reward_volume but null in table TrialSet.Trial

keys = (behavior.TrialSet &
        (behavior.TrialSet.Trial & 'trial_reward_volume is null') &
        (behavior.CompleteTrialSession &
         'reward_volume_status="Complete"')).fetch('KEY')

fields = [
    {'alf': 'trials.repNum',             'dj': 'trial_rep_num',             'dtype': int,   'status': 'rep_num_status'},
    {'alf': 'trials.included',           'dj': 'trial_included',            'dtype': bool,  'status': 'included_status'},
    {'alf': 'trials.goCue_times',        'dj': 'trial_go_cue_time',         'dtype': float, 'status': 'go_cue_times_status'},
    {'alf': 'trials.goCueTrigger_times', 'dj': 'trial_go_cue_trigger_time', 'dtype': float, 'status': 'go_cue_trigger_times_status'},
    {'alf': 'trials.rewardVolume',       'dj': 'trial_reward_volume',       'dtype': float, 'status': 'reward_volume_status'},
    {'alf': 'trials.itiDuration',        'dj': 'trial_iti_duration',        'dtype': float, 'status': 'iti_duration_status'},
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
