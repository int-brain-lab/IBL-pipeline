import datajoint as dj
from .. import subject, action, acquisition, behavior
from ..utils import psychofit as psy
import numpy as np
import pandas as pd


def compute_psych_pars(trials):

    trials = trials.proj(
        'trial_response_choice',
        signed_contrast='trial_stim_contrast_right \
        - trial_stim_contrast_left')
    q = dj.U('signed_contrast').aggr(trials, n='count(*)',
                                     n_right='sum(trial_response_choice="CCW")')
    signed_contrasts, n_trials_stim, n_trials_stim_right = q.fetch(
        'signed_contrast', 'n', 'n_right'
    )
    signed_contrasts = signed_contrasts.astype(float)
    n_trials_stim = n_trials_stim.astype(int)
    n_trials_stim_right = n_trials_stim_right.astype(int)

    # merge left 0 and right 0
    data = pd.DataFrame({
        'signed_contrasts': signed_contrasts,
        'n_trials_stim': n_trials_stim,
        'n_trials_stim_right': n_trials_stim_right
    })
    data = data.groupby('signed_contrasts').sum()

    signed_contrasts = np.unique(signed_contrasts)
    n_trials_stim_right = np.array(data['n_trials_stim_right'])
    n_trials_stim = np.array(data['n_trials_stim'])

    prob_choose_right = np.divide(n_trials_stim_right,
                                  n_trials_stim)

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


def compute_performance_easy(trials):
    trials = trials.proj(
        'trial_response_choice',
        signed_contrast='trial_stim_contrast_right \
        - trial_stim_contrast_left')

    trials_easy = trials & 'ABS(signed_contrast)>0.499'

    if not len(trials_easy):
        return
    else:
        trials_response_choice, trials_signed_contrast = \
            trials_easy.fetch('trial_response_choice', 'signed_contrast')
        n_correct_trials_easy = \
            np.sum((trials_response_choice == "CCW") &
                   (trials_signed_contrast > 0)) + \
            np.sum((trials_response_choice == "CW") &
                   (trials_signed_contrast < 0))
        return n_correct_trials_easy/len(trials_easy)


def compute_reaction_time(trials):
    # median reaction time
    trials_rt = trials.proj(
            signed_contrast='trial_stim_contrast_left- \
                             trial_stim_contrast_right',
            rt='trial_response_time-trial_stim_on_time')

    rt = trials_rt.fetch(as_dict=True)
    rt = pd.DataFrame(rt)
    rt = rt[['signed_contrast', 'rt']]
    median_rt = rt.groupby('signed_contrast').median()

    return np.array(median_rt['rt'])
