import datajoint as dj
from .. import subject, action, acquisition, behavior
from ..utils import psychofit as psy
import numpy as np
import pandas as pd
import scipy
import scikits.bootstrap as bootstrap


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


def compute_reaction_time(trials, compute_ci=False):

    if not len(trials):
        if compute_ci:
            return np.nan, np.nan, np.nan
        else:
            return np.nan

    # check whether:
    # 1. There were trials where stim_on_time is not available,
    #    but go_cue_trigger_time is;
    # 2. There were any trials where stim_on_time is available.
    trials_go_cue_only = trials & \
        'trial_stim_on_time is NULL and trial_go_cue_trigger_time is not NULL'
    trials_stim_on = trials & \
        'trial_stim_on_time is not NULL'

    rt = []
    if len(trials_go_cue_only):
        trials_rt_go_cue_only = trials_go_cue_only.proj(
            signed_contrast='trial_stim_contrast_left- \
                trial_stim_contrast_right',
            rt='trial_response_time-trial_go_cue_trigger_time')
        rt += trials_rt_go_cue_only.fetch(as_dict=True)

    if len(trials_stim_on):
        trials_rt_stim_on = trials.proj(
            signed_contrast='trial_stim_contrast_left- \
                            trial_stim_contrast_right',
            rt='trial_response_time-trial_stim_on_time')
        rt += trials_rt_stim_on.fetch(as_dict=True)

    rt = pd.DataFrame(rt)
    rt = rt[['signed_contrast', 'rt']]
    grouped_rt = rt['rt'].groupby(rt['signed_contrast'])
    median_rt = grouped_rt.median()

    if compute_ci:
        ci_rt = grouped_rt.apply(
            lambda x: bootstrap.ci(x, scipy.nanmedian, alpha=0.32))
        ci_low = np.array(
            [x[0] if not np.isnan(x[0]) else None for x in ci_rt])
        ci_high = np.array(
            [x[1] if not np.isnan(x[1]) else None for x in ci_rt])
        return median_rt.values, ci_low, ci_high
    else:
        return median_rt.values
