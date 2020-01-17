"""
Plot various criteria for each mouse session,
Author: Miles Well
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datajoint as dj

from ibl_pipeline import acquisition, behavior


def session_end_indices(trials, make_plot=False, ax=None):
    # CALCULATE CRITERIA
    rt_win_size = 20  # Size of reaction time rolling window
    perf_win_size = 50  # Size of performance rolling window
    min_trials = 400  # Minimum number of trials for criteria to apply

    trials['correct_easy'] = trials.correct
    trials.loc[np.abs(trials['signed_contrast']) < .5, 'correct_easy'] = np.NaN
    trials['n_trials_last_5'] = trials['trial_start_time'].expanding().apply(
        lambda x: sum((x[-1] - x[0:-1]) < 5 * 60), raw=True)

    # Local and session median reaction times
    trials['RT_local'] = trials['rt'].rolling(rt_win_size).median()
    trials['RT_global'] = trials['rt'].expanding().median()
    trials['RT_delta'] = trials['RT_local'] > (trials['RT_global'] * 5)

    # Local and global performance
    trials['perf_local'] = trials['correct'].rolling(perf_win_size).apply(lambda x: sum(x) / x.size, raw=True)
    trials['perf_global'] = trials['correct'].expanding().apply(lambda x: sum(x) / x.size, raw=True)
    trials['perf_delta'] = (trials['perf_global'] - trials['perf_local']) / trials['perf_global']

    # Performance for easy trials only
    def last(x): return x[~np.isnan(x)][-perf_win_size:]  # Find last n values that aren't nan
    trials['perf_local_ez'] = (trials['correct_easy'].expanding()
                               .apply(lambda x: sum(last(x)) / last(x).size if last(x).size else np.nan, raw=True))
    trials['perf_global_ez'] = trials['correct_easy'].expanding().apply(
        lambda x: (sum(x == 1) / sum(~np.isnan(x))), raw=True)
    trials['perf_delta_ez'] = (trials['perf_global_ez'] - trials['perf_local_ez']) / trials['perf_global_ez']

    status_idx = dict.fromkeys(EndCriteria.contents)
    status_idx['long_rt'] = (trials.RT_delta & (trials.index > min_trials)).idxmax() if (
            trials.RT_delta & (trials.index > min_trials)).any() else np.nan
    status_idx['perf_ez<40'] = ((trials['perf_delta_ez'] > 0.4) & (trials.index > min_trials)).idxmax()
    status_idx['perf<40'] = ((trials['perf_delta_ez'] > 0.4) & (trials.index > min_trials)).idxmax()
    status_idx['<400_trials'] = ((trials.trial_start_time > 45 * 60) & (trials.index < min_trials)).idxmax()
    status_idx['>45_min_&_stopped'] = (
            (trials.trial_start_time > 45 * 60) & (trials['n_trials_last_5'] < 45)).idxmax()
    status_idx['>90_min'] = (trials.trial_start_time > 90 * 60).idxmax()

    if make_plot:
        if not ax:
            fig, ax = plt.subplots(1, 1)
        c = ['#ba0f00','#00aaba','#aaba00','#0f00ba']
        trials.plot(y=['RT_local','RT_global','perf_local_ez','perf_global_ez'], ax=ax, color=c)
        ax.set_ylim([0,2])
        [plt.plot([v,v],[0,2],'k:') for (k, v) in status_idx.items() if v > 0]
        #  plt.show()

    return {k: v for (k, v) in status_idx.items() if v > 0}


schema = dj.schema('ibl_end_criteria')


@schema
class EndCriteria(dj.Lookup):
    definition = """
    end_criteria: varchar(32)
    """
    contents = zip(['long_rt',
                    'perf<40',
                    'perf_ez<40',
                    '<400_trials',
                    '>45_min_&_stopped',
                    '>90_min'
                    ])


@schema
class SessionEndCriteria(dj.Computed):
    definition = """
    -> acquisition.Session
    ---
    end_status:         varchar(32) # First end status to be triggered
    end_status_index:   int # trial_id index when status first triggered
    """

    key_source = behavior.CompleteTrialSession

    def make(self, key):

        query = behavior.TrialSet.Trial & key
        query = query.proj(
            'trial_response_choice',
            'trial_response_choice',
            'trial_response_time',
            'trial_stim_on_time',
            'trial_start_time',
            signed_contrast='trial_stim_contrast_right \
                - trial_stim_contrast_left',
            rt='trial_response_time - trial_stim_on_time',
            correct='trial_feedback_type = 1')
        trials = pd.DataFrame(query.fetch(order_by='trial_id'))

        if trials.empty:
            return
        # task_protocol = (acquisition.Session & key).fetch1('task_protocol')  # TODO
        status_idx = session_end_indices(trials)
        if status_idx:
            criterion = min(status_idx, key=status_idx.get)
            key['end_status'] = criterion
            key['end_status_index'] = status_idx[criterion]
            self.insert1(key)


@schema
class SessionEndCriteriaImplemented(dj.Computed):
    definition = """
    -> acquisition.Session
    ---
    end_status:         varchar(32) # First end status to be triggered
    end_status_index:   int # trial_id index when status first triggered
    """
    # This is the same as SessionEndCriteria but only includes indices of the criteria that have
    # been implemented
    key_source = behavior.CompleteTrialSession

    def make(self, key):

        query = behavior.TrialSet.Trial & key
        query = query.proj(
            'trial_response_choice',
            'trial_response_choice',
            'trial_response_time',
            'trial_stim_on_time',
            'trial_start_time',
            signed_contrast='trial_stim_contrast_right \
                - trial_stim_contrast_left',
            rt='trial_response_time - trial_stim_on_time',
            correct='trial_feedback_type = 1')
        trials = pd.DataFrame(query.fetch(order_by='trial_id'))

        if trials.empty:
            return

        status_idx = session_end_indices(trials)
        exclude = ['>45_min_&_stopped', 'perf<40', 'perf_ez<40'] # List of unimplemented criteria
        status_idx = {k: v for (k, v) in status_idx.items() if k not in exclude} # Remove from dict

        if status_idx:
            criterion = min(status_idx, key=status_idx.get)
            key['end_status'] = criterion
            key['end_status_index'] = status_idx[criterion]
            self.insert1(key)
