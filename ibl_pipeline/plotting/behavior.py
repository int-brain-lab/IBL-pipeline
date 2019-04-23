import datajoint as dj
from ..analyses import behavior
from .. import behavior as behavior_ingest
from .. import subject, action, acquisition
import numpy as np
import pandas as pd
from ..utils import psychofit as psy
import plotly
import plotly.graph_objs as go
import statsmodels.stats.proportion as smp

schema = dj.schema('ibl_plotting_behavior')


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
            yaxis={'title': 'Probability choose right',
                   'range': [-0.05, 1.05]}
        )

        fig = go.Figure(data=[go.Scatter(behavior_data),
                              go.Scatter(behavior_fit)], layout=layout)

        key['plotting_data'] = fig.to_plotly_json()
        self.insert1(key)


@schema
class DatePsychCurve(dj.Computed):
    definition = """
    -> behavior.BehavioralSummaryByDate
    ---
    plotting_data:  longblob     # dictionary for the plotting info
    """

    def make(self, key):

        sessions = behavior.BehavioralSummaryByDate.PsychResults & key

        data = []
        for session in sessions.fetch('KEY'):
            contrasts, prob_right, prob_left, \
                threshold, bias, lapse_low, lapse_high, \
                n_trials, n_trials_right = \
                (sessions & session).fetch1(
                    'signed_contrasts', 'prob_choose_right', 'prob_left',
                    'threshold', 'bias', 'lapse_low', 'lapse_high',
                    'n_trials_stim', 'n_trials_stim_right')
            pars = [bias, threshold, lapse_low, lapse_high]
            contrasts = contrasts * 100
            contrasts_fit = np.arange(-100, 100)
            prob_right_fit = psy.erf_psycho_2gammas(pars, contrasts_fit)
            ci = smp.proportion_confint(
                n_trials_right, n_trials,
                alpha=0.032, method='normal') - prob_right

            if prob_left == 0.2:
                curve_color = 'orange'
            elif prob_left == 0.5:
                curve_color = 'black'
            elif prob_left == 0.8:
                curve_color = 'cornflowerblue'
            else:
                continue

            behavior_data = go.Scatter(
                x=contrasts.tolist(),
                y=prob_right.tolist(),
                error_y=dict(
                    type='data',
                    array=ci[0].tolist(),
                    arrayminus=np.negative(ci[1]).tolist(),
                    visible=True
                ),
                marker=dict(
                    size=6,
                    color=curve_color),
                mode='markers',
                name=f'p_left = {prob_left}, data'
            )

            behavior_fit = go.Scatter(
                x=contrasts_fit.tolist(),
                y=prob_right_fit.tolist(),
                name=f'p_left = {prob_left} model fits',
                marker=dict(color=curve_color)
            )

            data.append(behavior_data)
            data.append(behavior_fit)

        layout = go.Layout(
            width=630,
            height=400,
            title='Psychometric Curve',
            xaxis={'title': 'Contrast(%)'},
            yaxis={'title': 'Probability choosing right',
                   'range': [-0.05, 1.05]},
        )

        fig = go.Figure(data=data, layout=layout)
        key['plotting_data'] = fig.to_plotly_json()
        self.insert1(key)


@schema
class TrialCountsSessionDuration(dj.Computed):
    definition = """
    -> subject.Subject
    last_session_date:  date      # last date of session
    ---
    plotting_data:      longblob  # dictionary for the plotting info
    """
    key_source = dj.U('subject_uuid', 'last_session_date') & \
        subject.Subject.aggr(
            behavior_ingest.TrialSet,
            last_session_date='DATE(MAX(session_start_time))'
        )

    def make(self, key):
        session_info = \
            (behavior_ingest.TrialSet * acquisition.Session & key).proj(
                'n_trials', session_date='DATE(session_start_time)',
                session_duration='TIMESTAMPDIFF(MINUTE, session_start_time, \
                    session_end_time)').fetch(as_dict=True)
        session_info = pd.DataFrame(session_info)

        trial_counts = go.Scatter(
            x=[t.strftime('%Y-%m-%d')
                for t in session_info['session_date'].tolist()],
            y=session_info['n_trials'].tolist(),
            mode='markers+lines',
            marker=dict(
                size=6,
                color='black'),
            name='trial counts',
            yaxis='y1'
        )
        session_length = go.Scatter(
            x=[t.strftime('%Y-%m-%d')
                for t in session_info['session_date'].tolist()],
            y=session_info['session_duration'].tolist(),
            mode='markers+lines',
            marker=dict(
                size=6,
                color='red'),
            name='session duration',
            yaxis='y2'
        )

        data = [trial_counts, session_length]

        layout = go.Layout(
            yaxis=dict(
                title='Trial counts',
            ),
            yaxis2=dict(
                title='Session duration (mins)',
                overlaying='y',
                color='red',
                side='right'
            ),
            xaxis=dict(
                title='Date'),
            width=500,
            height=400,
            title='Trial counts and session duration',
            showlegend=False
        )
        fig = go.Figure(data=data, layout=layout)
        key['plotting_data'] = fig.to_plotly_json()
        self.insert1(key)


@schema
class PerformanceReactionTime(dj.Computed):
    definition = """
    -> subject.Subject
    last_session_date:      date        # last date of session
    ---
    plotting_data:          longblob    # dictionary for the plotting info
    """

    key_source = dj.U('subject_uuid', 'last_session_date') & \
        subject.Subject.aggr(
            behavior.BehavioralSummaryByDate,
            last_session_date='MAX(session_date)'
        )

    def make(self, key):
        session_info = \
            (behavior.BehavioralSummaryByDate *
             behavior.BehavioralSummaryByDate.ReactionTimeByDate &
             key).proj(
                 'session_date',
                 'performance_easy',
                 'median_reaction_time').fetch(as_dict=True)
        session_info = pd.DataFrame(session_info)

        performance_easy = go.Scatter(
            x=[t.strftime('%Y-%m-%d') for t in session_info['session_date'].tolist()],
            y=session_info['performance_easy'].tolist(),
            mode='markers+lines',
            marker=dict(
                size=6,
                color='black'),
            name='performance easy',
            yaxis='y1'
        )
        rt = go.Scatter(
            x=[t.strftime('%Y-%m-%d')
                for t in session_info['session_date'].tolist()],
            y=session_info['median_reaction_time'].tolist(),
            mode='markers+lines',
            marker=dict(
                size=6,
                color='red'),
            name='reaction time',
            yaxis='y2'
        )

        data = [performance_easy, rt]

        layout = go.Layout(
            yaxis=dict(
                title='Performance on easy trials',
                range=[0, 1]
            ),
            yaxis2=dict(
                title='Median reaction time (s)',
                overlaying='y',
                color='red',
                side='right',
                type='log',
                range=np.log10([0.1, 10]).tolist(),
                dtick=np.log10([0.1, 1, 10]).tolist()

            ),
            xaxis=dict(
                title='Date',
            ),
            width=500,
            height=400,
            title='Performance and median reaction time',
            showlegend=False
        )

        fig = go.Figure(data=data, layout=layout)
        key['plotting_data'] = fig.to_plotly_json()
        self.insert1(key)


@schema
class WaterWeight(dj.Computed):
    definition = """
    -> subject.Subject
    water_weight_date:   date    # last date of water weight
    ---
    plotting_data:  longblob     # dictionary for the plotting info
    """

    key_source = dj.U('subject_uuid', 'water_weight_date') & \
        subject.Subject.aggr(
            action.Weighing * action.WaterAdministration,
            water_weight_date='DATE(GREATEST(MAX(weighing_time), \
                MAX(administration_time)))'
        )

    def make(self, key):
        subj = subject.Subject & key

        water_info_query = (action.WaterAdministration & subj).proj(
            'water_administered', 'watertype_name',
            water_date='DATE(administration_time)')
        water_info = pd.DataFrame(water_info_query.fetch(as_dict=True))
        water_types = water_info.watertype_name.unique()
        water_info.pop('administration_time')
        water_info.pop('subject_uuid')
        water_info_type = water_info.pivot_table(
            index='water_date', columns='watertype_name',
            values='water_administered', aggfunc='sum')
        water_info_type = water_info_type.where((pd.notnull(water_info_type)),
                                                None)

        weight_info_query = (action.Weighing & subj).proj(
            'weight', weighing_date='DATE(weighing_time)')

        weight_info = pd.DataFrame(
            weight_info_query.fetch(as_dict=True))
        weight_info.pop('subject_uuid')
        weight_info.pop('weighing_time')
        weight_info = weight_info.where((pd.notnull(weight_info)), None)

        data = [
            go.Bar(
                x=[t.strftime('%Y-%m-%d')
                    for t in water_info_type.index.tolist()],
                y=water_info_type[water_type].tolist(),
                name=water_type,
                yaxis='y1')
            for water_type in water_types
        ]

        data.append(
            go.Scatter(
                x=[t.strftime('%Y-%m-%d')
                    for t in weight_info['weighing_date'].tolist()],
                y=weight_info['weight'].tolist(),
                mode='lines+markers',
                name='Weight',
                marker=dict(
                    size=6,
                    color='black'),
                yaxis='y2'
            ))

        layout = go.Layout(
            yaxis=dict(
                title='Water intake (mL)'),
            yaxis2=dict(
                title='Weight (g)',
                overlaying='y',
                side='right'
            ),
            width=600,
            height=400,
            title='Water intake and weight',
            xaxis=dict(title='Date'),
            legend=dict(
                x=0,
                y=1.2,
                orientation='h'),
            barmode='stack'
        )
        fig = go.Figure(data=data, layout=layout)
        key['plotting_data'] = fig.to_plotly_json()
        self.insert1(key)
