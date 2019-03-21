import datajoint as dj
from .. import subject, action, acquisition, behavior
from ..utils import psychofit as psy
from . import analysis_utils as utils
from datetime import datetime
import numpy as np

schema = dj.schema(dj.config.get('database.prefix', '') +
                   'ibl_analyses_behavior')


@schema
class PsychResults(dj.Computed):
    definition = """
    -> behavior.TrialSet
    ---
    performance:            float   # percentage correct in this session
    signed_contrasts:       blob    # contrasts used in this session, negative when on the left
    n_trials_stim:          blob    # number of trials for each contrast
    n_trials_stim_right:    blob   # number of reporting "right" trials for each contrast
    prob_choose_right:      blob    # probability of choosing right, same size as contrasts
    threshold:              float
    bias:                   float
    lapse_low:              float
    lapse_high:             float
    """

    def make(self, key):

        trials = behavior.TrialSet.Trial & key
        psych_results_tmp = utils.compute_psych_pars(trials)
        psych_results = {**key, **psych_results_tmp}

        n_trials, n_correct_trials = (behavior.TrialSet & key).fetch1(
            'n_trials', 'n_correct_trials')
        psych_results['performance'] = n_correct_trials/n_trials
        self.insert1(psych_results)


@schema
class ReactionTime(dj.Computed):
    definition = """
    -> PsychResults
    ---
    reaction_time:     blob   # reaction time for all contrasts
    """
    key_source = PsychResults & \
        (behavior.CompleteTrialSession &
         'stim_on_times_status = "Complete"')

    def make(self, key):
        trials = behavior.TrialSet.Trial & key
        trials_rt = trials.proj(
            signed_contrast='trial_stim_contrast_left- \
                             trial_stim_contrast_right',
            rt='trial_response_time-trial_stim_on_time')

        q = dj.U('signed_contrast').aggr(trials_rt, mean_rt='avg(rt)')
        key['reaction_time'] = q.fetch('mean_rt').astype(float)

        self.insert1(key)


@schema
class TrainingStatus(dj.Lookup):
    definition = """
    training_status: varchar(32)
    """
    contents = zip(['training in progress', 'trained', 'ready for ephys'])


@schema
class SessionTrainingStatus(dj.Computed):
    definition = """
    -> PsychResults
    ---
    -> TrainingStatus
    """

    def make(self, key):
        cum_psych_results = key.copy()
        subject_key = key.copy()
        subject_key.pop('session_start_time')

        # if the protocol for the current session is a biased session,
        # set the status to be "trained" and check up the criteria for
        # "read for ephys"
        task_protocol = (acquisition.Session & key).fetch1('task_protocol')
        if task_protocol and 'biased' in task_protocol:
            key['training_status'] = 'trained'
            self.insert1(key)
            return
            # Criteria for "ready for ephys" status in the future

        # if the current session is not a biased session,
        key['training_status'] = 'training in progress'
        # training in progress if the animals was trained in < 3 sessions
        sessions = (acquisition.TrialSet & subject_key &
                    'session_start_time <= "{}"'.format(
                        key['session_start_time'].strftime('%Y-%m-%d %H:%M:%S')
                        )).fetch('KEY')
        if len(sessions) < 3:
            self.insert1(key)
            return

        # training in progress if any of the last three sessions have
        # < 200 trials
        sessions_rel = sessions[-3:]
        n_trials = (behavior.TrialSet & sessions_rel).fetch('n_trials')
        if np.any(n_trials < 200):
            self.insert1(key)
            return

        # training in progress if the current session does not have 0 contrast
        contrasts = (PsychResults & key).fetch1('signed_contrasts')
        if 0 not in contrasts:
            self.insert1(key)
            return

        # compute psych results of last three sessions
        trials = behavior.TrialSet.Trial & sessions_rel
        psych = utils.compute_psych_pars(trials)
        criterion = np.abs(psych['bias']) < 16 and \
            psych['threshold'] < 19 and \
            psych['lapse_low'] < 0.2 and psych['lapse_high'] < 0.2

        if criterion:
            key['training_status'] = 'trained'

        self.insert1(key)

        # insert computed results into the part table
        n_trials, n_correct_trials = (behavior.TrialSet & key).fetch(
            'n_trials', 'n_correct_trials')
        cum_psych_results.update({
            'cum_performance': np.divide(np.sum(n_correct_trials),
                                         np.sum(n_trials)),
            'cum_signed_contrasts': psych['signed_contrasts'],
            'cum_n_trials_stim': psych['n_trials_stim'],
            'cum_n_trials_stim_right': psych['n_trials_stim_right'],
            'cum_prob_choose_right': psych['prob_choose_right'],
            'cum_bias': psych['bias'],
            'cum_threshold': psych['threshold'],
            'cum_lapse_low': psych['lapse_low'],
            'cum_lapse_high': psych['lapse_high']
        })

        self.CumulativePsychResults.insert1(cum_psych_results)

    class CumulativePsychResults(dj.Part):
        definition = """
        # cumulative psych results from the last three sessions
        -> master
        ---
        cum_performance:            float   # percentage correct in this session
        cum_signed_contrasts:       blob    # contrasts used in this session, negative when on the left
        cum_n_trials_stim:          blob    # number of trials for each contrast
        cum_n_trials_stim_right:    blob   # number of reporting "right" trials for each contrast
        cum_prob_choose_right:      blob    # probability of choosing right, same size as contrasts
        cum_threshold:              float
        cum_bias:                   float
        cum_lapse_low:              float
        cum_lapse_high:             float
        """
