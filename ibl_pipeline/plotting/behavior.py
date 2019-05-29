import datajoint as dj
from ..analyses import behavior
from .. import behavior as behavior_ingest
from .. import reference, subject, action, acquisition, data
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
    key_source = behavior.PsychResults & behavior.PsychResultsBlock

    def make(self, key):
        sessions = behavior.PsychResultsBlock & key
        data = []

        for session in sessions.fetch('KEY'):
            contrasts, prob_right, prob_left, \
                threshold, bias, lapse_low, lapse_high, \
                n_trials, n_trials_right = \
                (sessions & session).fetch1(
                    'signed_contrasts', 'prob_choose_right', 'prob_left', 'threshold', 'bias',
                    'lapse_low', 'lapse_high', 'n_trials_stim', 'n_trials_stim_right')
            pars = [bias, threshold, lapse_low, lapse_high]
            contrasts = contrasts * 100
            contrasts_fit = np.arange(-100, 100)
            prob_right_fit = psy.erf_psycho_2gammas(pars, contrasts_fit)
            ci = smp.proportion_confint(
                n_trials_right, n_trials, alpha=0.032, method='normal') - prob_right

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
class SessionReactionTimeContrast(dj.Computed):
    definition = """
    -> behavior_ingest.TrialSet
    ---
    plotting_data:  longblob     # dictionary for the plotting info
    """
    key_source = behavior_ingest.TrialSet & behavior.ReactionTimeContrastBlock

    def make(self, key):
        sessions = behavior.PsychResultsBlock * \
            behavior.ReactionTimeContrastBlock & key

        data = []
        for session in sessions.fetch('KEY'):
            contrasts, prob_left, reaction_time, ci_low, ci_high = \
                (sessions & session).fetch1(
                    'signed_contrasts', 'prob_left', 'reaction_time_contrast',
                    'reaction_time_ci_low', 'reaction_time_ci_high')
            error_low = reaction_time - ci_low
            error_high = ci_high - reaction_time

            contrasts = contrasts * 100

            if prob_left == 0.2:
                curve_color = 'orange'
            elif prob_left == 0.5:
                curve_color = 'black'
            elif prob_left == 0.8:
                curve_color = 'cornflowerblue'
            else:
                continue

            rt_data = go.Scatter(
                x=contrasts.tolist(),
                y=reaction_time.tolist(),
                error_y=dict(
                    type='data',
                    array=error_high.tolist(),
                    arrayminus=error_low.tolist(),
                    visible=True
                ),
                marker=dict(
                    size=6,
                    color=curve_color),
                mode='markers+lines',
                name=f'p_left = {prob_left}'
            )

            data.append(rt_data)

        layout = go.Layout(
            width=630,
            height=400,
            title='Reaction time - contrast',
            xaxis={'title': 'Contrast (%)'},
            yaxis={'title': 'Reaction time (s)'},
        )

        fig = go.Figure(data=data, layout=layout)
        key['plotting_data'] = fig.to_plotly_json()
        self.insert1(key)


@schema
class SessionReactionTimeTrialNumber(dj.Computed):
    definition = """
    -> behavior_ingest.TrialSet
    ---
    plotting_data:  longblob     # dictionary for the plotting info
    """

    key_source = behavior_ingest.TrialSet & \
        (behavior_ingest.CompleteTrialSession &
            'stim_on_times_status="Complete"')

    def make(self, key):
        # get all trial of the session
        trials = behavior_ingest.TrialSet.Trial & key
        rt_trials = trials.proj(
            rt='trial_response_time-trial_stim_on_time').fetch(as_dict=True)
        rt_trials = pd.DataFrame(rt_trials)
        rt_trials.index = rt_trials.index + 1
        rt_rolled = rt_trials['rt'].rolling(window=10).median()
        rt_rolled = rt_rolled.where((pd.notnull(rt_rolled)), None)
        data = dict(
            x=rt_trials.index.tolist(),
            y=rt_trials['rt'].tolist(),
            name='data',
            type='scatter',
            mode='markers',
            marker=dict(
                color='lightgray'
            )
        )

        rolled = dict(
            x=rt_trials.index.tolist(),
            y=rt_rolled.values.tolist(),
            name='rolled data',
            type='scatter',
            marker=dict(
                color='black'
            )
        )

        layout = go.Layout(
            width=630,
            height=400,
            title='Reaction time - trial number',
            xaxis=dict(title='Trial number'),
            yaxis=dict(
                title='Reaction time (s)',
                type='log',
                range=np.log10([0.1, 100]).tolist(),
                dtick=np.log10([0.1, 1, 10, 100]).tolist()),
        )

        fig = go.Figure(data=[data, rolled], layout=layout)
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
class DateReactionTimeContrast(dj.Computed):
    definition = """
    -> behavior.BehavioralSummaryByDate
    ---
    plotting_data:  longblob     # dictionary for the plotting info
    """
    key_source = behavior.BehavioralSummaryByDate & \
        behavior.BehavioralSummaryByDate.ReactionTimeContrast

    def make(self, key):
        sessions = behavior.BehavioralSummaryByDate.PsychResults * \
            behavior.BehavioralSummaryByDate.ReactionTimeContrast & key

        data = []
        for session in sessions.fetch('KEY'):
            contrasts, prob_left, reaction_time, ci_low, ci_high = \
                (sessions & session).fetch1(
                    'signed_contrasts', 'prob_left', 'reaction_time_contrast',
                    'reaction_time_ci_low', 'reaction_time_ci_high')
            error_low = reaction_time - ci_low
            error_high = ci_high - reaction_time

            contrasts = contrasts * 100

            if prob_left == 0.2:
                curve_color = 'orange'
            elif prob_left == 0.5:
                curve_color = 'black'
            elif prob_left == 0.8:
                curve_color = 'cornflowerblue'
            else:
                continue

            rt_data = go.Scatter(
                x=contrasts.tolist(),
                y=reaction_time.tolist(),
                error_y=dict(
                    type='data',
                    array=error_high.tolist(),
                    arrayminus=error_low.tolist(),
                    visible=True
                ),
                marker=dict(
                    size=6,
                    color=curve_color),
                mode='markers+lines',
                name=f'p_left = {prob_left}'
            )

            data.append(rt_data)

        layout = go.Layout(
            width=630,
            height=400,
            title='Reaction time - contrast',
            xaxis={'title': 'Contrast (%)'},
            yaxis={'title': 'Reaction time (s)'},
        )

        fig = go.Figure(data=data, layout=layout)
        key['plotting_data'] = fig.to_plotly_json()
        self.insert1(key)


@schema
class DateReactionTimeTrialNumber(dj.Computed):
    definition = """
    -> behavior.BehavioralSummaryByDate
    ---
    plotting_data:  longblob     # dictionary for the plotting info
    """

    key_source = behavior.BehavioralSummaryByDate & \
        behavior.BehavioralSummaryByDate.ReactionTimeContrast

    def make(self, key):
        # get all trial of the day
        trial_sets = (behavior_ingest.TrialSet &
                      (behavior_ingest.CompleteTrialSession &
                       'stim_on_times_status="Complete"')).proj(
            session_date='DATE(session_start_time)')
        trials = behavior_ingest.TrialSet.Trial & \
            (behavior_ingest.TrialSet * trial_sets & key)
        rt_trials = trials.proj(
            rt='trial_response_time-trial_stim_on_time').fetch(as_dict=True)
        rt_trials = pd.DataFrame(rt_trials)
        rt_trials.index = rt_trials.index + 1
        rt_rolled = rt_trials['rt'].rolling(window=10).median()
        rt_rolled = rt_rolled.where((pd.notnull(rt_rolled)), None)
        data = dict(
            x=rt_trials.index.tolist(),
            y=rt_trials['rt'].tolist(),
            name='data',
            type='scatter',
            mode='markers',
            marker=dict(
                color='lightgray'
            )
        )

        rolled = dict(
            x=rt_trials.index.tolist(),
            y=rt_rolled.values.tolist(),
            name='rolled data',
            type='scatter',
            marker=dict(
                color='black'
            )
        )

        layout = go.Layout(
            width=630,
            height=400,
            title='Reaction time - trial number',
            xaxis=dict(title='Trial number'),
            yaxis=dict(
                title='Reaction time (s)',
                type='log',
                range=np.log10([0.1, 100]).tolist(),
                dtick=np.log10([0.1, 1, 10, 100]).tolist()),
        )

        fig = go.Figure(data=[data, rolled], layout=layout)
        key['plotting_data'] = fig.to_plotly_json()
        self.insert1(key)


@schema
class LatestDate(dj.Manual):
    # compute the last date of any event for individual subjects
    definition = """
    -> subject.Subject
    checking_ts=CURRENT_TIMESTAMP: timestamp
    ---
    latest_date: date
    """


@schema
class CumulativeSummary(dj.Computed):
    # This table contains four plots of the cumulative summary
    definition = """
    -> subject.Subject
    latest_date:  date      # last date of any event for the subject
    """
    key_source = dj.U('subject_uuid', 'latest_date') \
        & subject.Subject.aggr(
            LatestDate, 'latest_date',
            lastest_timestamp='MAX(checking_ts)')

    def make(self, key):
        self.insert1(key)

        # plot for trial counts and session duration
        if behavior_ingest.TrialSet & key:
            trial_cnts = key.copy()

            session_info = \
                (behavior_ingest.TrialSet * acquisition.Session & key).proj(
                    'n_trials', session_date='DATE(session_start_time)',
                    session_duration='TIMESTAMPDIFF(MINUTE, session_start_time, \
                        session_end_time)').fetch(as_dict=True)
            session_info = pd.DataFrame(session_info)
            session_info = session_info.where((pd.notnull(session_info)), None)

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
            trial_cnts['trial_counts_session_duration'] = fig.to_plotly_json()
            self.TrialCountsSessionDuration.insert1(trial_cnts)

        # plot for performance reaction time and fit pars
        if behavior.BehavioralSummaryByDate & key:
            perf_rt = key.copy()
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
            perf_rt['performance_reaction_time'] = fig.to_plotly_json()
            self.PerformanceReactionTime.insert1(perf_rt)

            # plot for fit parameter changes over time
            # get trial counts and session length to date
            fit_pars_entry = key.copy()
            fit_pars = (behavior.BehavioralSummaryByDate.PsychResults &
                        key).proj(
                'session_date', 'prob_left',
                'threshold', 'bias',
                'lapse_low', 'lapse_high').fetch(as_dict=True)
            fit_pars = pd.DataFrame(fit_pars)

            par_names = ['threshold', 'bias', 'lapse_low', 'lapse_high']

            pars = dict()
            for par_name in par_names:
                pars[par_name] = []

            prob_lefts = fit_pars['prob_left'].unique()

            for prob_left in prob_lefts:
                prob_left_filter = fit_pars['prob_left'] == prob_left
                if prob_left == 0.2:
                    dot_color = 'orange'
                elif prob_left == 0.5:
                    dot_color = 'black'
                elif prob_left == 0.8:
                    dot_color = 'cornflowerblue'
                else:
                    dot_color = 'gray'

                fit_pars_sub = fit_pars[prob_left_filter]

                for ipar, par_name in enumerate(par_names):
                    if ipar == 0:
                        show_legend = True
                    else:
                        show_legend = False
                    pars[par_name].append(
                        go.Scatter(
                            x=[t.strftime('%Y-%m-%d')
                                for t in fit_pars_sub['session_date'].tolist()],
                            y=fit_pars_sub[par_name].tolist(),
                            mode='markers',
                            marker=dict(
                                size=5,
                                color=dot_color),
                            name=f'p_left = {prob_left}',
                            xaxis='x{}'.format(4-ipar),
                            yaxis='y{}'.format(4-ipar),
                            showlegend=show_legend
                        )
                    )

            pars_data = [pars[par_name][i]
                         for i, prob_left in enumerate(prob_lefts)
                         for par_name in par_names]

            layout = go.Layout(
                xaxis1=dict(
                    domain=[0, 1],
                    title='Date'
                ),
                yaxis1=dict(
                    domain=[0, 0.2],
                    anchor='x1',
                    range=[-0.02, 1.02],
                    title='$Lapse\ high\ (\\lambda)$'
                ),
                xaxis2=dict(
                    domain=[0, 1],
                ),
                yaxis2=dict(
                    domain=[0.25, 0.45],
                    anchor='x2',
                    range=[-0.02, 1.02],
                    title='$Lapse\ low\ (\\gamma)$'
                ),
                xaxis3=dict(
                    domain=[0, 1],
                ),
                yaxis3=dict(
                    domain=[0.5, 0.7],
                    anchor='x3',
                    range=[-105, 105],
                    title='$Bias\ (\\mu)$'
                ),
                xaxis4=dict(
                    domain=[0, 1],
                ),
                yaxis4=dict(
                    domain=[0.75, 1],
                    anchor='x4',
                    range=[-5, 105],
                    title='$Threshold\ (\\sigma)$'
                ),
                height=1000,
                width=500,
                title='Fit Parameters',
            )

            fig = go.Figure(data=pars_data, layout=layout)

            fit_pars_entry['fit_pars'] = fig.to_plotly_json()
            self.FitPars.insert1(fit_pars_entry)

        # plot for contrast heatmap
        if behavior.BehavioralSummaryByDate.PsychResults & key \
                & 'ABS(prob_left-0.5)<0.001':
            con_hm = key.copy()
            # get trial counts and session length to date
            sessions = (behavior.BehavioralSummaryByDate.PsychResults &
                        'ABS(prob_left-0.5)<0.001' & key).proj(
                            'session_date', 'signed_contrasts',
                            'prob_choose_right').fetch(as_dict=True)
            # reshape to a heatmap format
            contrast_list = []
            for session in sessions:
                for i, contrast in enumerate(session['signed_contrasts']):
                    contrast_list.append(
                        {'session_date': session['session_date'],
                         'signed_contrast': round(contrast, 2)*100,
                         'prob_choose_right': session['prob_choose_right'][i]})
            contrast_df = pd.DataFrame(contrast_list)
            contrast_map = contrast_df.pivot(
                'signed_contrast', 'session_date',
                'prob_choose_right').sort_values(
                    by='signed_contrast', ascending=False)

            contrast_map = contrast_map.where((pd.notnull(contrast_map)), None)

            data = dict(
                x=[t.strftime('%Y-%m-%d')
                    for t in contrast_map.columns.tolist()],
                y=contrast_map.index.tolist(),
                z=contrast_map.values.tolist(),
                zmax=1,
                zmin=0,
                type='heatmap',
                colorbar=dict(
                    thickness=10,
                    title='prob choosing left',
                    titleside='right',
                )

            )

            layout = go.Layout(
                xaxis=dict(title='Date'),
                yaxis=dict(
                    title='Contrast (%)',
                    range=[-100, 100]
                ),
                width=500,
                height=400,
                title='Contrast heatmap',
                showlegend=False
            )

            fig = go.Figure(data=[data], layout=layout)
            con_hm['contrast_heatmap'] = fig.to_plotly_json()
            self.ContrastHeatmap.insert1(con_hm)

        # plot for water weight
        if action.WaterAdministration * action.Weighing & key:
            water_weight_entry = key.copy()
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
            water_info_type = water_info_type.where(
                (pd.notnull(water_info_type)), None)

            weight_info_query = (action.Weighing & subj).proj(
                'weight', weighing_date='DATE(weighing_time)')

            weight_info = pd.DataFrame(
                weight_info_query.fetch(as_dict=True))
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
            water_weight_entry['water_weight'] = fig.to_plotly_json()
            self.WaterWeight.insert1(water_weight_entry)

    class TrialCountsSessionDuration(dj.Part):
        definition = """
        -> master
        ---
        trial_counts_session_duration: longblob    # dict for the plotting info
        """

    class PerformanceReactionTime(dj.Part):
        definition = """
        -> master
        ---
        performance_reaction_time: longblob    # dict for the plotting info
        """

    class ContrastHeatmap(dj.Part):
        definition = """
        -> master
        ---
        contrast_heatmap: longblob    # dict for the plotting info
        """

    class FitPars(dj.Part):
        definition = """
        -> master
        ---
        fit_pars: longblob  # dict for the plotting info
        """

    class WaterWeight(dj.Part):
        definition = """
        -> master
        ---
        water_weight: longblob    # dict for the plotting info
        """


@schema
class SubjectLatestDate(dj.Lookup):
    definition = """
    -> subject.Subject
    ---
    latest_date: date
    """


ingested_sessions = acquisition.Session & 'task_protocol is not NULL' \
    & behavior_ingest.TrialSet
subjects_alive = (subject.Subject - subject.Death) & 'sex != "U"' \
    & action.Weighing & action.WaterAdministration & ingested_sessions


@schema
class DailyLabSummary(dj.Computed):
    definition = """
    -> reference.Lab
    last_session_time:      datetime        # last date of session
    """

    sessions_lab = acquisition.Session * subjects_alive * subject.SubjectLab \
        * behavior.SessionTrainingStatus
    key_source = dj.U('lab_name', 'last_session_time') & reference.Lab.aggr(
        sessions_lab, last_session_time='MAX(session_start_time)')

    def make(self, key):

        self.insert1(key)
        subjects = subjects_alive * subject.SubjectLab & key

        last_sessions = subjects.aggr(
            ingested_sessions,
            'subject_nickname', session_start_time='max(session_start_time)') \
            * acquisition.Session \
            * behavior.SessionTrainingStatus

        filerecord = data.FileRecord & subjects & 'relative_path LIKE "%alf%"'
        last_filerecord = subjects.aggr(
            filerecord, latest_session_on_flatiron='max(session_start_time)')

        summary = (last_sessions*last_filerecord).proj(
            'subject_nickname', 'task_protocol', 'training_status',
            'latest_session_on_flatiron').fetch(
                as_dict=True)

        for entry in summary:
            subj = subject.Subject & entry
            protocol = entry['task_protocol'].partition('ChoiseWorld')[0]
            subject_summary = key.copy()
            subject_summary.update(
                subject_uuid=entry['subject_uuid'],
                subject_nickname=entry['subject_nickname'],
                latest_session_ingested=entry['session_start_time'],
                latest_session_on_flatiron=entry['latest_session_on_flatiron'],
                latest_task_protocol=entry['task_protocol'],
                latest_training_status=entry['training_status'],
                n_sessions_current_protocol=len(
                    ingested_sessions & subj &
                    'task_protocol LIKE "{}%"'.format(protocol))
            )
            self.SubjectSummary.insert1(subject_summary)

    class SubjectSummary(dj.Part):
        definition = """
        -> master
        subject_uuid:                uuid
        ---
        subject_nickname:            varchar(64)
        latest_session_ingested:     datetime
        latest_session_on_flatiron:  datetime
        latest_task_protocol:        varchar(128)
        latest_training_status:      varchar(64)
        n_sessions_current_protocol: int
        """
