import datajoint as dj
from ..analyses import behavior
import numpy as np
from ..utils import psychofit as psy
import plotly
import plotly.graph_objs as go
import statsmodels.stats.proportion as smp

schema = dj.schema('ibl_dj_plotting_behavior')


@schema
class SessionPsychCurve(dj.Computed):
    definition = """
    -> behavior.PsychResults
    ---
    plotting_data:  longblob     # dictionary for the plotting info
    """

    def make(self, key):
        contrasts, prob_right, \
            threshold, bias, lapse_low, lapse_high, \
            n_trials, n_trials_right = (behavior.PsychResults & key).fetch1(
                'signed_contrasts', 'prob_choose_right',
                'threshold', 'bias', 'lapse_low', 'lapse_high',
                'n_trials_stim', 'n_trials_stim_right')
        pars = [bias, threshold, lapse_low, lapse_high]
        contrasts = contrasts * 100
        contrasts_fit = np.arange(-100, 100)
        prob_right_fit = psy.erf_psycho_2gammas(pars, contrasts_fit)

        ci = smp.proportion_confint(
            n_trials_right, n_trials,
            alpha=0.032, method='normal') - prob_right

        behavior_data = dict(
            x=contrasts.tolist(),
            y=prob_right.tolist(),
            error_y=dict(
                type='data',
                array=ci[0].tolist(),
                arrayminus=np.negative(ci[1]).tolist(),
                visible=True
                ),
            mode='markers',
            name='data'
        )

        behavior_fit = dict(
            x=contrasts_fit.tolist(),
            y=prob_right_fit.tolist(),
            name='model fits'
        )

        data = [behavior_data, behavior_fit]
        layout = go.Layout(
            width=600,
            height=400,
            title='Psychometric Curve',
            xaxis={'title': 'Contrast(%)'},
            yaxis={'title': 'Probability choose right'}
        )

        fig = go.Figure(data=[go.Scatter(behavior_data),
                              go.Scatter(behavior_fit)], layout=layout)

        key['plotting_data'] = fig.to_plotly_json()
        self.insert1(key)
