import datajoint as dj
from .. import subject, action, acquisition, behavior
from ..utils import psychofit as psy
import numpy as np


def compute_psych_pars(trials):

    trials = trials.proj(
        'trial_response_choice',
        signed_contrast='trial_stim_contrast_right \
        - trial_stim_contrast_left')
    q_all = dj.U('signed_contrast').aggr(trials, n='count(*)')
    q_right = dj.U('signed_contrast').aggr(
        trials, n_right='sum(trial_response_choice="CCW")')
    signed_contrasts, n_trials_stim = q_all.fetch(
        'signed_contrast', 'n'
    )
    signed_contrasts = signed_contrasts.astype(float)
    n_trials_stim = n_trials_stim.astype(int)
    n_trials_stim_right = q_right.fetch('n_right').astype(int)
    prob_choose_right = np.divide(n_trials_stim_right, n_trials_stim)

    # convert to percentage and fit psychometric function
    contrasts = signed_contrasts * 100
    pars, L = psy.mle_fit_psycho(
        np.vstack([contrasts, n_trials_stim, prob_choose_right]),
        P_model='erf_psycho_2gammas',
        parstart=np.array([np.mean(contrasts), 20., 0.05, 0.05]),
        parmin=np.array([np.min(contrasts), 0., 0., 0.]),
        parmax=np.array([np.max(contrasts), 100., 1, 1]))

    return {
        'signed_contrasts': signed_contrasts,
        'n_trials_stim': n_trials_stim,
        'n_trials_stim_right': n_trials_stim_right,
        'prob_choose_right': prob_choose_right,
        'bias': pars[0],
        'threshold': pars[1],
        'lapse_low': pars[2],
        'lapse_high': pars[3]
    }


def compute_reaction_time(trials):
    trials_rt = trials.proj(
            signed_contrast='trial_stim_contrast_left- \
                             trial_stim_contrast_right',
            rt='trial_response_time-trial_stim_on_time')

    q = dj.U('signed_contrast').aggr(trials_rt, mean_rt='avg(rt)')
    return q.fetch('mean_rt').astype(float)
