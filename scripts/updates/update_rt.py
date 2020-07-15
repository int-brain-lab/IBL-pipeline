
from ibl_pipeline import subject, acquisition, behavior
from ibl_pipeline.analyses import behavior as behavior_analyses
from ibl_pipeline.plotting import behavior as behavior_plotting
import datajoint as dj

from tqdm import tqdm
from oneibl.one import ONE
import alf
import numpy as np

one = ONE()
# sessions to be updated

sessions_with_dates = \
    behavior_analyses.BehavioralSummaryByDate.ReactionTimeByDate & \
    'median_reaction_time<0.01'

keys, eIDs = (acquisition.Session.proj(
    'session_uuid', session_date="date(session_start_time)") &
    behavior.TrialSet & sessions_with_dates).fetch(
        'KEY', 'session_uuid')

# update response time of behavior.TrialSet.Trial
sessions_with_small_rts = []
unupdated_keys = []
updated_keys = []

for key, eID in tqdm(zip(keys, eIDs), position=0):
    dtypes = ['trials.stimOn_times', 'trials.response_times']
    try:
        files = one.load(str(eID), dataset_types=dtypes, download_only=True)
        ses_path = alf.io.get_session_path(files[0])
        trials = alf.io.load_object(ses_path.joinpath('alf'), '_ibl_trials')
    except Exception as e:
        print(str(eID) + ': ' + str(e))
        continue

    if np.median(trials.response_times - trials.stimOn_times) < 0.01:
        print('\n Still having small rt:' + str(eID))
        unupdated_keys.append(key)
        sessions_with_small_rts.append(eID)
    else:
        for itrial, response_time in enumerate(trials.response_times):
            if len(behavior.TrialSet.Trial & key & {'trial_id': itrial+1}) == 1:
                dj.Table._update(
                    behavior.TrialSet.Trial & key & {'trial_id': itrial+1},
                    'trial_response_time', response_time)
        updated_keys.append(key)


np.save('sessions_with_small_rts.npy', sessions_with_small_rts)
np.save('updated_keys.npy', updated_keys)
np.save('unupdated_keys.npy', unupdated_keys)
