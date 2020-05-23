import datajoint as dj
from ..analyses import behavior
from .. import behavior as behavior_ingest
from .. import reference, subject, action, acquisition, data
from . import plotting_utils_behavior as putils
import numpy as np
import pandas as pd
from ..utils import psychofit as psy
import plotly
import plotly.graph_objs as go
import statsmodels.stats.proportion as smp
import datetime
import matplotlib.pyplot as plt
import os

schema = dj.schema(dj.config.get('database.prefix', '') +
                   'ibl_plotting_behavior')


@schema
class SessionPsychCurve(dj.Computed):
    definition = """
    -> behavior.PsychResults
    ---
    plotting_data:  longblob     # dictionary for the plotting info
    fit_pars:       longblob     # dictionary list for fit parameters
    """
    key_source = behavior.PsychResults & behavior.PsychResultsBlock.proj()

    def make(self, key):

        sessions = behavior.PsychResultsBlock & key
        fig = putils.create_psych_curve_plot(sessions)
        key['plotting_data'] = fig.to_plotly_json()
        key['fit_pars'] = putils.get_fit_pars(sessions)
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
        fig = putils.create_rt_contrast_plot(sessions)
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
            'stim_on_times_status in ("Complete", "Partial") or \
             go_cue_trigger_times_status in ("Complete", "Partial")')

    def make(self, key):
        # get all trial of the session
        trials = behavior_ingest.TrialSet.Trial & key & \
            'trial_stim_on_time is not NULL or \
             trial_go_cue_trigger_time is not NULL'

        fig = putils.create_rt_trialnum_plot(trials)
        key['plotting_data'] = fig.to_plotly_json()
        self.insert1(key)


@schema
class DatePsychCurve(dj.Computed):
    definition = """
    -> behavior.BehavioralSummaryByDate
    ---
    plotting_data:  longblob     # dictionary for the plotting info
    fit_pars:       longblob     # dictionary list for fit parameters
    """

    def make(self, key):

        sessions = behavior.BehavioralSummaryByDate.PsychResults & key
        fig = putils.create_psych_curve_plot(sessions)
        key['plotting_data'] = fig.to_plotly_json()
        key['fit_pars'] = putils.get_fit_pars(sessions)
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
        fig = putils.create_rt_contrast_plot(sessions)
        key['plotting_data'] = fig.to_plotly_json()
        self.insert1(key)


@schema
class DateReactionTimeTrialNumber(dj.Computed):
    definition = """
    -> behavior.BehavioralSummaryByDate
    ---
    plotting_data:  longblob   # dictionary for the plotting info
    """

    def make(self, key):
        trial_sets = (behavior_ingest.TrialSet &
                      (behavior_ingest.CompleteTrialSession &
                       'stim_on_times_status in ("Complete", "Partial") or \
                        go_cue_trigger_times_status in ("Complete", "Partial")')).proj(
                session_date='DATE(session_start_time)')
        trials = behavior_ingest.TrialSet.Trial & \
            (behavior_ingest.TrialSet * trial_sets & key)

        if not len(trials):
            return

        fig = putils.create_rt_trialnum_plot(trials)
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
class WaterTypeColor(dj.Computed):
    definition = """
    -> action.WaterType
    ---
    water_type_color:  varchar(32)
    """

    def make(self, key):

        original_water_types = ['Citric Acid Water 2%', 'Hydrogel',
                                'Hydrogel 5% Citric Acid',
                                'Water', 'Water 1% Citric Acid',
                                'Water 10% Sucrose',
                                'Water 15% Sucrose', 'Water 2% Citric Acid']
        original_colors = ['red', 'orange', 'blue', 'rgba(55, 128, 191, 0.7)',
                           'rgba(200, 128, 191, 0.7)',
                           'purple', 'rgba(50, 171, 96, 0.9)', 'red']

        mapping = {
            watertype: color
            for watertype, color in zip(original_water_types, original_colors)}

        if key['watertype_name'] in original_water_types:
            water_type_color = dict(
                **key, water_type_color=mapping[key['watertype_name']])
        else:
            water_type_color = dict(
                **key, water_type_color='rgba({}, {}, {}, 0.7)'.format(
                    np.random.randint(255), np.random.randint(255), np.random.randint(255)))

        self.insert1(water_type_color)


@schema
class CumulativeSummary(dj.Computed):
    # This table contains four plots of the cumulative summary
    definition = """
    -> subject.Subject
    latest_date:  date      # last date of any event for the subject
    """
    latest = subject.Subject.aggr(
        LatestDate,
        checking_ts='MAX(checking_ts)') * LatestDate
    key_source = dj.U('subject_uuid', 'latest_date') & latest

    def make(self, key):
        self.insert1(key)

        # check the environment, public or internal

        if os.environ.get('MODE') == 'public':
            public = True
        else:
            public = False

        subj = subject.Subject & key
        # get the first date when animal became "trained" and "ready for ephys"
        status = putils.get_status(subj)
        # get date range and mondays
        d = putils.get_date_range(subj)

        if d['seven_months_date']:
            status['is_over_seven_months'] = True
            status['seven_months_date'] = d['seven_months_date']
        else:
            status['is_over_seven_months'] = False

        # plot for trial counts and session duration
        if behavior_ingest.TrialSet & key:
            trial_cnts = key.copy()
            # get trial counts and session length to date
            session_info = (behavior_ingest.TrialSet *
                            acquisition.Session & subj).proj(
                'n_trials', session_date='DATE(session_start_time)',
                session_duration='TIMESTAMPDIFF(MINUTE, \
                    session_start_time, session_end_time)').fetch(as_dict=True)
            session_info = pd.DataFrame(session_info)
            session_info = session_info.where((pd.notnull(session_info)), None)

            n_trials = session_info['n_trials'].tolist()
            max_trials = max(n_trials)
            yrange = [0, max_trials+50]

            trial_counts = go.Scatter(
                x=[t.strftime('%Y-%m-%d') for t in session_info['session_date'].tolist()],
                y=session_info['n_trials'].tolist(),
                mode='markers+lines',
                marker=dict(
                    size=6,
                    color='black',
                    line=dict(
                        color='white',
                        width=1
                    )
                ),
                name='trial counts',
                yaxis='y1',
                showlegend=False
            )

            session_length = go.Scatter(
                x=[t.strftime('%Y-%m-%d') for t in session_info['session_date'].tolist()],
                y=session_info['session_duration'].tolist(),
                mode='markers+lines',
                marker=dict(
                    size=6,
                    color='red',
                    line=dict(
                        color='white',
                        width=1
                    )
                ),
                name='session duration',
                yaxis='y2',
                showlegend=False
            )

            data = [trial_counts, session_length]

            # add monday plots
            data = putils.create_monday_plot(data, yrange, d['mondays'])

            # add ephys dates and good enough markers
            if d['ephys_dates']:
                data = putils.create_good_enough_brainmap_plot(
                    data, yrange, d['ephys_dates'], d['good_enough'])

            # add status plots
            data = putils.create_status_plot(
                data, yrange, status, public=public)

            layout = go.Layout(
                yaxis=dict(
                    title='Trial counts',
                    range=yrange
                ),
                yaxis2=dict(
                    title='Session duration (mins)',
                    overlaying='y',
                    color='red',
                    side='right'
                ),
                xaxis=dict(
                    title='Date',
                    range=[d['first_date_str'], d['last_date_str']],
                    showgrid=False
                ),
                width=700,
                height=400,
                title=dict(
                    text='Trial counts and session duration',
                    x=0.18,
                    y=0.85
                ),
                legend=dict(
                    x=1.2,
                    y=0.8,
                    orientation='v'),
                template=dict(
                    layout=dict(
                        plot_bgcolor="white"
                    )
                )
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
            yrange = [0, 1.1]
            perf_easy = [None if np.isnan(p) else p
                         for p in session_info['performance_easy']]

            median_rt = [None if np.isnan(p) else p
                         for p in session_info['median_reaction_time']]

            performance_easy = go.Scatter(
                x=[t.strftime('%Y-%m-%d') for t in session_info['session_date'].tolist()],
                y=perf_easy,
                mode='markers+lines',
                marker=dict(
                    size=6,
                    color='black',
                    line=dict(
                        color='white',
                        width=1
                    )
                ),
                name='performance easy',
                yaxis='y1',
                showlegend=False
            )
            rt = go.Scatter(
                x=[t.strftime('%Y-%m-%d') for t in session_info['session_date'].tolist()],
                y=median_rt,
                mode='markers+lines',
                marker=dict(
                    size=6,
                    color='red',
                    line=dict(
                        color='white',
                        width=1)
                ),
                name='reaction time',
                yaxis='y2',
                showlegend=False
            )

            data = [performance_easy, rt]

            # add monday plots
            data = putils.create_monday_plot(data, yrange, d['mondays'])

            # add good enough for brain map plot
            if d['ephys_dates']:
                data = putils.create_good_enough_brainmap_plot(
                    data, yrange, d['ephys_dates'], d['good_enough'])

            # add status plots
            data = putils.create_status_plot(
                data, yrange, status, public=public)

            layout = go.Layout(

                yaxis=dict(
                    title='Performance on easy trials',
                    range=yrange
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
                    showgrid=False
                ),
                width=700,
                height=400,
                title=dict(
                    text='Performance and median reaction time',
                    x=0.14,
                    y=0.85
                ),
                legend=dict(
                    x=1.2,
                    y=0.8,
                    orientation='v'),
                template=dict(
                    layout=dict(
                        plot_bgcolor="white"
                    )
                )
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
            thresholds = [[19, 19], [16, 16, -16, -16], [0.2, 0.2], [0.2, 0.2]]
            xranges = \
                [[d['first_date_str'], d['last_date_str']],
                 [d['first_date_str'], d['last_date_str'], d['last_date_str'], d['first_date_str']],
                 [d['first_date_str'], d['last_date_str']],
                 [d['first_date_str'], d['last_date_str']]]
            yranges = [[0, 100], [-100, 100], [0, 1], [0, 1]]

            pars = dict()
            for par_name in par_names:
                pars[par_name] = []

            prob_lefts = fit_pars['prob_left'].unique()

            for iprob_left, prob_left in enumerate(prob_lefts):
                prob_left_filter = fit_pars['prob_left'] == prob_left
                dot_color, error_color = putils.get_color(prob_left)

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
                                color=dot_color,
                                opacity=0.8
                            ),
                            name=f'p_left = {prob_left}',
                            xaxis='x{}'.format(4-ipar),
                            yaxis='y{}'.format(4-ipar),
                            showlegend=show_legend,
                            legendgroup='p_left'
                        ))

            pars_data = [pars[par_name][i]
                         for i, prob_left in enumerate(prob_lefts)
                         for par_name in par_names]

            for ipar, par_name in enumerate(par_names):
                if ipar == 0:
                    show_legend = True
                else:
                    show_legend = False

                pars_data.append(
                    go.Scatter(
                        x=xranges[ipar],
                        y=thresholds[ipar],
                        mode="lines",
                        line=dict(
                            width=1,
                            color='darkgreen',
                            dash='dashdot'),
                        name='threshold for trained',
                        xaxis='x{}'.format(4-ipar),
                        yaxis='y{}'.format(4-ipar),
                        showlegend=show_legend,
                        legendgroup='date'
                    )
                )

                # add monday plots
                pars_data = putils.create_monday_plot(
                    pars_data, yranges[ipar], d['mondays'],
                    xaxis='x{}'.format(4-ipar),
                    yaxis='y{}'.format(4-ipar),
                    show_legend_external=show_legend
                )

                # add good enough for brainmap plots
                if d['ephys_dates']:
                    pars_data = putils.create_good_enough_brainmap_plot(
                        pars_data, yranges[ipar], d['ephys_dates'],
                        d['good_enough'],
                        xaxis='x{}'.format(4-ipar),
                        yaxis='y{}'.format(4-ipar),
                        show_legend_external=show_legend)

                # add status plots
                pars_data = putils.create_status_plot(
                    pars_data, yranges[ipar], status,
                    xaxis='x{}'.format(4-ipar),
                    yaxis='y{}'.format(4-ipar),
                    show_legend_external=show_legend,
                    public=public
                )

            x_axis_range = \
                [d['first_date_str'],
                 (d['last_date'] - datetime.timedelta(days=1)).strftime('%Y-%m-%d')]
            layout = go.Layout(
                xaxis1=dict(
                    domain=[0, 1],
                    range=x_axis_range,
                    title='Date',
                    showgrid=False
                ),
                yaxis1=dict(
                    domain=[0, 0.2],
                    anchor='x1',
                    showgrid=False,
                    range=[-0.02, 1.02],
                    title='$Lapse high\ (\\lambda)$'
                ),
                xaxis2=dict(
                    domain=[0, 1],
                    range=x_axis_range,
                    showgrid=False
                ),
                yaxis2=dict(
                    domain=[0.25, 0.45],
                    anchor='x2',
                    showgrid=False,
                    range=[-0.02, 1.02],
                    title='$Lapse low\ (\\gamma)$'
                ),
                xaxis3=dict(
                    domain=[0, 1],
                    range=x_axis_range,
                    showgrid=False
                ),
                yaxis3=dict(
                    domain=[0.5, 0.7],
                    anchor='x3',
                    showgrid=False,
                    range=[-105, 105],
                    title='$Bias\ (\\mu)$'
                ),
                xaxis4=dict(
                    domain=[0, 1],
                    range=x_axis_range,
                    showgrid=False
                ),
                yaxis4=dict(
                    domain=[0.75, 1],
                    anchor='x4',
                    showgrid=False,
                    range=[-5, 105],
                    title='$Threshold\ (\\sigma)$'
                ),
                height=1000,
                width=600,
                title=dict(
                    text='Fit Parameters',
                    x=0.3,
                    y=0.93
                ),
                legend=dict(
                    x=1.1,
                    y=1,
                    orientation='v'),
                template=dict(
                    layout=dict(
                        plot_bgcolor="white"
                    )
                )
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
                        'prob_left=0.5' & key).proj(
                'session_date', 'signed_contrasts', 'prob_choose_right')

            # get date ranges and mondays
            d = putils.get_date_range(subj)

            # get contrast and p_prob_choose_right per day
            contrast_list = []
            for day in d['date_array']:
                if sessions & {'session_date': day}:
                    session = (sessions & {'session_date': day}).fetch(
                        as_dict=True)
                    session = session[0]
                    for icontrast, contrast in \
                            enumerate(session['signed_contrasts']):
                        contrast_list.append(
                            {'session_date': session['session_date'],
                             'signed_contrast': round(contrast, 2)*100,
                             'prob_choose_right': session['prob_choose_right'][icontrast]})
                else:
                    contrast_list.append(
                        {'session_date': day,
                         'signed_contrast': 100,
                         'prob_choose_right': np.nan})

            contrast_df = pd.DataFrame(contrast_list)
            contrast_map = contrast_df.pivot(
                'signed_contrast',
                'session_date',
                'prob_choose_right').sort_values(
                    by='signed_contrast', ascending=False)

            contrast_map = contrast_map.where(pd.notnull(contrast_map), None)
            contrasts = np.sort(contrast_df['signed_contrast'].unique())

            data = [dict(
                x=[t.strftime('%Y-%m-%d')
                   for t in contrast_map.columns.tolist()],
                y=list(range(len(contrast_map.index.tolist())))[::-1],
                z=contrast_map.values.tolist(),
                zmax=1,
                zmin=0,
                xgap=1,
                ygap=1,
                type='heatmap',
                colorbar=dict(
                    thickness=10,
                    title='Rightward Choice (%)',
                    titleside='right',
                ),
                colorscale='PuOr'

            )]

            data = putils.create_monday_plot(data, [-100, 100], d['mondays'])

            layout = go.Layout(
                xaxis=dict(
                    title='Date',
                    showgrid=False
                ),
                yaxis=dict(
                    title='Contrast (%)',
                    range=[0, len(contrast_map.index.tolist())],
                    tickmode='array',
                    tickvals=list(range(0, len(contrast_map.index.tolist()))),
                    ticktext=[str(contrast) for contrast in contrasts]
                ),
                width=700,
                height=400,
                title=dict(
                    text='Contrast heatmap',
                    x=0.3,
                    y=0.85
                ),
                legend=dict(
                    x=1.2,
                    y=0.8,
                    orientation='v'
                ),
                template=dict(
                    layout=dict(
                        plot_bgcolor="white"
                    )
                )
            )

            fig = go.Figure(data=data, layout=layout)
            con_hm['contrast_heatmap'] = fig.to_plotly_json()
            self.ContrastHeatmap.insert1(con_hm)

        # plot for water weight
        water_type_names, water_type_colors = WaterTypeColor.fetch(
            'watertype_name', 'water_type_color')
        water_type_map = dict()

        for watertype, color in zip(water_type_names, water_type_colors):
            water_type_map.update({watertype: color})

        if action.WaterAdministration * action.Weighing & key:
            water_weight_entry = key.copy()
            # get water and date
            water_info_query = (action.WaterAdministration & subj).proj(
                'water_administered', 'watertype_name',
                water_date='DATE(administration_time)')
            water_info = water_info_query.fetch(as_dict=True)
            water_info = pd.DataFrame(water_info)
            water_types = water_info.watertype_name.unique()
            water_info_type = water_info.pivot_table(
                index='water_date', columns='watertype_name',
                values='water_administered', aggfunc='sum')
            max_water_intake = np.nanmax(water_info_type.values) + 0.2
            yrange_water = [0, max_water_intake]
            water_info_type = water_info_type.where(
                (pd.notnull(water_info_type)), None)
            weight_info_query = (action.Weighing & subj).proj(
                'weight', weighing_date='DATE(weighing_time)')
            weight_info = weight_info_query.fetch(as_dict=True)
            weight_info = pd.DataFrame(weight_info)
            weight_info = weight_info.where((pd.notnull(weight_info)), None)

            # get water restriction period
            water_restrictions = (action.WaterRestriction & subj).proj(
                'reference_weight',
                res_start='DATE(restriction_start_time)',
                res_end='DATE(restriction_end_time)')

            data = [
                go.Bar(
                    x=[t.strftime('%Y-%m-%d')
                       for t in water_info_type.index.tolist()],
                    y=water_info_type[water_type].tolist(),
                    marker=dict(color=water_type_map[water_type]),
                    name=water_type,
                    yaxis='y1'
                )
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
                        color='black',
                        line=dict(
                            color='white',
                            width=1)
                    ),
                    legendgroup='weight',
                    yaxis='y2'
                ))

            # monday marks
            data = putils.create_monday_plot(data, yrange_water, d['mondays'])

            # water restriction marks and reference weight marks
            for iwater, water_res in \
                    enumerate(water_restrictions.fetch(as_dict=True)):

                if iwater == 0:
                    show_res_legend = True
                else:
                    show_res_legend = False

                res_start = water_res['res_start'].strftime('%Y-%m-%d')

                if water_res['res_end']:
                    res_end = water_res['res_end'].strftime('%Y-%m-%d')
                else:
                    res_end = d['last_date_str']
                data.append(
                    go.Scatter(
                        x=[res_start, res_start],
                        y=yrange_water,
                        mode="lines",
                        line=dict(
                            width=1,
                            color='red',
                        ),
                        name='Water restriction start',
                        yaxis='y1',
                        showlegend=show_res_legend,
                        legendgroup='restriction'
                    )
                )

                if water_res['res_end']:

                    data.append(
                        go.Scatter(
                            x=[res_end, res_end],
                            y=yrange_water,
                            mode="lines",
                            line=dict(
                                width=1,
                                color='darkgreen',
                            ),
                            name='Water restriction end',
                            yaxis='y1',
                            showlegend=show_res_legend,
                            legendgroup='restriction'
                        )
                    )

                data.append(
                    go.Scatter(
                        x=[res_start, res_end],
                        y=[water_res['reference_weight']*0.85,
                           water_res['reference_weight']*0.85],
                        mode="lines",
                        line=dict(
                            width=1,
                            color='orange',
                            dash='dashdot'
                        ),
                        name='85% reference weight',
                        yaxis='y2',
                        showlegend=show_res_legend,
                        legendgroup='weight_ref',
                        hoverinfo='y'
                    )
                )

                data.append(
                    go.Scatter(
                        x=[res_start, res_end],
                        y=[water_res['reference_weight']*0.75,
                           water_res['reference_weight']*0.75],
                        mode="lines",
                        line=dict(
                            width=1,
                            color='red',
                            dash='dashdot'
                        ),
                        name='75% reference weight',
                        yaxis='y2',
                        showlegend=show_res_legend,
                        legendgroup='weight_ref',
                        hoverinfo='y'
                    )
                )

            layout = go.Layout(
                yaxis=dict(
                    title='Water intake (mL)',
                    range=yrange_water
                ),
                yaxis2=dict(
                    title='Weight (g)',
                    overlaying='y',
                    side='right',
                ),
                width=1000,
                height=500,
                title=dict(
                    text='Water intake and weight',
                    x=0.3,
                    y=0.9
                ),
                xaxis=dict(
                    title='Date',
                    range=[d['first_date_str'], d['last_date_str']]
                ),
                legend=dict(
                    x=1.1,
                    y=0.9,
                    orientation='v'),
                barmode='stack',
                template=dict(
                    layout=dict(
                        plot_bgcolor="white"
                    )
                )
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
            ingested_sessions * behavior.SessionTrainingStatus,
            'subject_nickname', session_start_time='max(session_start_time)')
        last_sessions = last_sessions * acquisition.Session * \
            behavior.SessionTrainingStatus

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

            # --- check for data availability ---

            # last session_start_time in table acquisition.Session
            if not len(acquisition.Session & subj):
                data_update_status = 'No behavioral data collected'
            else:
                # get the latest session query
                last_session = subj.aggr(
                    acquisition.Session,
                    session_start_time='max(session_start_time)')

                last_session_date = last_session.proj(
                    session_date='date(session_start_time)')

                last_date = last_session_date.fetch1(
                    'session_date').strftime('%Y-%m-%d')

                # existence of CompleteTrialSet tuple for latest session
                if not len(behavior_ingest.CompleteTrialSession & last_session):
                    data_update_status = """
                    Data in the last session on {} were not uploaded
                    or partially uploaded to FlatIron.
                    """.format(last_date)
                elif not len(behavior_ingest.TrialSet & last_session):
                    data_update_status = """
                    Ingest error in TrialSet for data on {}.
                    """.format(last_date)
                elif not len(behavior.BehavioralSummaryByDate & last_session_date):
                    data_update_status = """
                    Ingest error in BehavioralSummaryByDate for
                    data on {}
                    """.format(last_date)
                elif not len(CumulativeSummary & last_session.proj(latest_session='session_date')):
                    data_update_status = """
                    Error in creating cumulative plots for data on {}
                    """.format(last_date)
                else:
                    data_update_status = """
                    Data up to date
                    """.format(last_date)

                # existence of plotting tuples
                CumulativeSummary & last_session.proj(latest_session='')

            subject_summary = dict(
                **key,
                subject_uuid=entry['subject_uuid'],
                subject_nickname=entry['subject_nickname'],
                latest_session_ingested=entry['session_start_time'],
                latest_session_on_flatiron=entry['latest_session_on_flatiron'],
                latest_task_protocol=entry['task_protocol'],
                latest_training_status=entry['training_status'],
                n_sessions_current_protocol=len(
                    ingested_sessions & subj &
                    'task_protocol LIKE "{}%"'.format(protocol)),
                data_update_status=data_update_status
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
        data_update_status:          varchar(255)
        subject_summary_ts=CURRENT_TIMESTAMP:      timestamp
        """
