import datajoint as dj
from .. import subject, action, acquisition, behavior
from . import psychofit as psy
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
        trials = trials * trials.proj(
            signed_contrast='trial_stim_contrast_right \
            - trial_stim_contrast_left')
        q_all = dj.U('signed_contrast').aggr(trials, n='count(*)')
        q_right = (dj.U('signed_contrast') & trials).aggr(
            trials & 'trial_response_choice="CCW"', n='count(*)',
            keep_all_rows=True)
        signed_contrasts, n_trials_stim = q_all.fetch(
            'signed_contrast', 'n'
        )
        signed_contrasts = signed_contrasts.astype(float)
        n_trials_stim = n_trials_stim.astype(int)
        n_trials_stim_right = q_right.fetch('n').astype(int)
        prob_choose_right = np.divide(n_trials_stim_right, n_trials_stim)

        n_trials, n_correct_trials = (behavior.TrialSet & key).fetch1(
            'n_trials', 'n_correct_trials')

        # convert to percentage
        contrasts = signed_contrasts * 100
        pars, L = psy.mle_fit_psycho(
            np.vstack([contrasts, n_trials_stim, prob_choose_right]),
            P_model='erf_psycho_2gammas',
            parstart=np.array([np.mean(contrasts), 20., 0.05, 0.05]),
            parmin=np.array([np.min(contrasts), 0., 0., 0.]),
            parmax=np.array([np.max(contrasts), 100., 1, 1]))

        key.update({
            'performance': n_correct_trials/n_trials,
            'signed_contrasts': signed_contrasts,
            'n_trials_stim': n_trials_stim,
            'n_trials_stim_right': n_trials_stim_right,
            'prob_choose_right': prob_choose_right,
            'bias': pars[0],
            'threshold': pars[1],
            'lapse_low': pars[2],
            'lapse_high': pars[3]
        })
        self.insert1(key)


@schema
class ReactionTime(dj.Computed):
    definition = """
    -> PsychResults
    ---
    reaction_time:     blob   # reaction time for all contrasts
    """

    key_source = behavior.TrialSet & \
        (behavior.CompleteTrialSession &
         'stim_on_times_status = "Complete"') & \
        PsychResults

    def make(self, key):
        trials = behavior.TrialSet.Trial & key
        trials_rt = trials.proj(
            signed_contrast='trial_stim_contrast_left- \
                             trial_stim_contrast_right',
            rt='trial_response_time-trial_stim_on_time')

        q = dj.U('signed_contrast').aggr(trials_rt, n='count(*)')
        key['reaction_time'] = q.fetch('rt').astype(float)

        self.insert1(key)
