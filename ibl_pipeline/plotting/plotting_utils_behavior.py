from ibl_pipeline.analyses import behavior
from ibl_pipeline import behavior as behavior_ingest
from ibl_pipeline import subject, action, acquisition, ephys
from ibl_pipeline.utils import psychofit as psy
from uuid import UUID
import numpy as np
import datetime
import datajoint as dj
import plotly.graph_objs as go
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import plotly
from plotly import tools
import statsmodels.stats.proportion as smp
import scipy.signal as signal


def get_date_range(subj):

    # get date range of session
    session_range = subj.aggr(
        acquisition.Session,
        first_session_date='min(DATE(session_start_time))',
        last_session_date='max(DATE(session_start_time))')

    if session_range:
        first_session_date, last_session_date = session_range.fetch1(
            'first_session_date', 'last_session_date'
        )
    else:
        first_session_date = None
        last_session_date = None

    # get date range of water restriction
    water_res_range = subj.aggr(
        action.WaterRestriction,
        first_res_date='min(DATE(restriction_start_time))',
        last_res_date='max(DATE(restriction_end_time))')

    if water_res_range:
        first_water_res_date, last_water_res_date = water_res_range.fetch1(
            'first_res_date', 'last_res_date'
        )
    else:
        first_water_res_date = None
        last_water_res_date = None

    # get date range of water administration
    water_admin_range = subj.aggr(
        action.WaterAdministration,
        first_admin_date='min(DATE(administration_time))',
        last_admin_date='max(DATE(administration_time))')

    if water_admin_range:
        first_water_admin_date, last_water_admin_date = \
            water_admin_range.fetch1(
                'first_admin_date', 'last_admin_date'
            )
    else:
        first_water_admin_date = None
        last_water_admin_date = None

    # get date range of weighing
    weighing_range = subj.aggr(
        action.Weighing,
        first_weighing_date='min(DATE(weighing_time))',
        last_weighing_date='max(DATE(weighing_time))')

    if weighing_range:
        first_weighing_date, last_weighing_date = weighing_range.fetch1(
            'first_weighing_date', 'last_weighing_date'
        )
    else:
        first_weighing_date = None
        last_weighing_date = None

    # get overall date range
    first_date_array = [first_session_date,
                        first_water_res_date,
                        first_water_admin_date,
                        first_weighing_date]
    first_date_array = [x for x in first_date_array if x is not None]
    last_date_array = [last_session_date,
                       last_water_admin_date,
                       last_weighing_date]
    last_date_array = [x for x in last_date_array if x is not None]
    first_date = np.min(first_date_array) \
        - datetime.timedelta(days=3)

    last_date = np.max(last_date_array) \
        + datetime.timedelta(days=3)

    first_date_str = first_date.strftime('%Y-%m-%d')
    last_date_str = last_date.strftime('%Y-%m-%d')

    date_array = [first_date + datetime.timedelta(days=day)
                  for day in range(0, (last_date-first_date).days)]

    # get Mondays
    mondays = [day.strftime('%Y-%m-%d')
               for day in date_array if day.weekday() == 0]

    # get dates for good enough for brainwide map
    ephys_sessions = behavior.SessionTrainingStatus & subj & \
        (acquisition.Session & 'task_protocol like "%ephys%"')

    if len(ephys_sessions):
        ephys_dates, good_enough = ephys_sessions.fetch(
            'session_start_time', 'good_enough_for_brainwide_map')
        ephys_dates = [day.strftime('%Y-%m-%d') for day in ephys_dates]
    else:
        ephys_dates = None
        good_enough = None

    # check whether the animal is already 7 months
    dob = subj.fetch1('subject_birth_date')
    if dob:
        seven_months_date = dob + datetime.timedelta(days=210)
        if seven_months_date > last_date:
            seven_months_date = None
    else:
        seven_months_date = None

    return dict(
        first_date=first_date,
        last_date=last_date,
        first_date_str=first_date_str,
        last_date_str=last_date_str,
        date_array=date_array,
        mondays=mondays,
        ephys_dates=ephys_dates,
        good_enough=good_enough,
        seven_months_date=seven_months_date)


def get_status(subj):
    # get the first date when animal achieved the next stage
    first_trained_1a = subj.aggr(
        behavior.SessionTrainingStatus & 'training_status = "trained_1a"',
        first_session='DATE(min(session_start_time))')
    first_trained_1b = subj.aggr(
        behavior.SessionTrainingStatus & 'training_status = "trained_1b"',
        first_session='DATE(min(session_start_time))')
    first_ready4ephysrig = subj.aggr(
        behavior.SessionTrainingStatus & 'training_status = "ready4ephysrig"',
        first_session='DATE(min(session_start_time))')
    first_ready4delay = subj.aggr(
        behavior.SessionTrainingStatus & 'training_status = "ready4delay"',
        first_session='DATE(min(session_start_time))')
    first_ready4recording = subj.aggr(
        behavior.SessionTrainingStatus & 'training_status = "ready4recording"',
        first_session='DATE(min(session_start_time))')
    first_ephys_session = subj.aggr(
        behavior.SessionTrainingStatus & ephys.ProbeInsertion,
        first_session='DATE(min(session_start_time))')

    result = dict()
    if len(first_trained_1a):
        first_trained_1a_date = first_trained_1a.fetch1(
            'first_session').strftime('%Y-%m-%d')
        result.update(is_trained_1a=True,
                      first_trained_1a_date=first_trained_1a_date)
    else:
        result.update(is_trained_1a=False)

    if len(first_trained_1b):
        first_trained_1b_date = first_trained_1b.fetch1(
            'first_session').strftime('%Y-%m-%d')
        result.update(is_trained_1b=True,
                      first_trained_1b_date=first_trained_1b_date)
    else:
        result.update(is_trained_1b=False)

    if len(first_ready4ephysrig):
        first_ready4ephysrig_date = first_ready4ephysrig.fetch1(
            'first_session').strftime('%Y-%m-%d')
        result.update(is_ready4ephysrig=True,
                      first_ready4ephysrig_date=first_ready4ephysrig_date)
    else:
        result.update(is_ready4ephysrig=False)

    if len(first_ready4delay):
        first_ready4delay_date = first_ready4delay.fetch1(
            'first_session').strftime('%Y-%m-%d')
        result.update(is_ready4delay=True,
                      first_ready4delay_date=first_ready4delay_date)
    else:
        result.update(is_ready4delay=False)

    if len(first_ready4recording):
        first_ready4recording_date = first_ready4recording.fetch1(
            'first_session').strftime('%Y-%m-%d')
        result.update(is_ready4recording=True,
                      first_ready4recording_date=first_ready4recording_date)
    else:
        result.update(is_ready4recording=False)

    if len(first_ephys_session):
        first_ephys_session_date = first_ephys_session.fetch1(
            'first_session').strftime('%Y-%m-%d')
        result.update(
            has_ephys_session=True,
            first_ephys_session_date=first_ephys_session_date)
    else:
        result.update(has_ephys_session=False)

    return result


def get_fit_pars(sessions):
    fit_pars_list = []
    for session in sessions.fetch('KEY'):
        prob_left, threshold, bias, lapse_low, lapse_high = \
            (sessions & session).fetch1(
                'prob_left', 'threshold', 'bias', 'lapse_low', 'lapse_high'
            )
        fit_pars_list.append(
            dict(
                prob_left=prob_left,
                threshold=threshold,
                bias=bias,
                lapse_high=lapse_high,
                lapse_low=lapse_low
            )
        )
    return fit_pars_list


def get_color(prob_left, opacity=0.3):

    cmap = sns.diverging_palette(20, 220, n=3, center="dark")

    if prob_left == 0.2:
        color = cmap[0]
    elif prob_left == 0.5:
        color = cmap[1]
    elif prob_left == 0.8:
        color = cmap[2]
    else:
        return

    curve_color = 'rgba{}'.format(color + tuple([1]))
    error_color = 'rgba{}'.format(color + tuple([opacity]))

    return curve_color, error_color


def create_psych_curve_plot(sessions):
    data_mean = []
    data_errorbar = []
    data_fit = []

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

        curve_color, error_color = get_color(prob_left, 0.3)

        behavior_data = go.Scatter(
            x=contrasts.tolist(),
            y=prob_right.tolist(),
            marker=dict(
                size=6,
                color=curve_color,
                line=dict(
                    color='white',
                    width=1
                )
            ),
            mode='markers',
            name=f'p_left = {prob_left}, data with 68% CI'
        )

        behavior_errorbar = go.Scatter(
            x=contrasts.tolist(),
            y=prob_right.tolist(),
            error_y=dict(
                type='data',
                array=ci[0].tolist(),
                arrayminus=np.negative(ci[1]).tolist(),
                visible=True,
                color=error_color
            ),
            marker=dict(
                size=6,
            ),
            mode='none',
            showlegend=False
        )

        behavior_fit = go.Scatter(
            x=contrasts_fit.tolist(),
            y=prob_right_fit.tolist(),
            name=f'p_left = {prob_left} model fits',
            marker=dict(color=curve_color)
        )

        data_mean.append(behavior_data)
        data_errorbar.append(behavior_errorbar)
        data_fit.append(behavior_fit)

    layout = go.Layout(
        width=630,
        height=350,
        title=dict(
            text='Psychometric Curve',
            x=0.25,
            y=0.85
        ),
        xaxis=dict(
            title='Contrast (%)'),
        yaxis=dict(
            title='Probability choosing right',
            range=[-0.05, 1.05]),
        template=dict(
            layout=dict(
                plot_bgcolor="white"
            )
        )
    )

    data = data_errorbar
    for element in data_fit:
        data.append(element)

    for element in data_mean:
        data.append(element)

    return go.Figure(data=data, layout=layout)


def create_rt_contrast_plot(sessions):
    data = []
    for session in sessions.fetch('KEY'):
        contrasts, prob_left, reaction_time, ci_low, ci_high = \
            (sessions & session).fetch1(
                'signed_contrasts', 'prob_left', 'reaction_time_contrast',
                'reaction_time_ci_low', 'reaction_time_ci_high')

        contrasts = contrasts * 100
        error_low = reaction_time - ci_low
        error_high = ci_high - reaction_time

        curve_color, error_color = get_color(prob_left, 0.3)

        rt_data = go.Scatter(
            x=contrasts.tolist(),
            y=reaction_time.tolist(),
            marker=dict(
                size=6,
                color=curve_color,
                line=dict(
                    color='white',
                    width=1
                )
            ),
            mode='markers+lines',
            name=f'p_left = {prob_left}'
        )

        rt_errorbar = go.Scatter(
            x=contrasts.tolist(),
            y=reaction_time.tolist(),
            error_y=dict(
                type='data',
                array=error_high.tolist(),
                arrayminus=error_low.tolist(),
                visible=True,
                color=error_color
            ),
            marker=dict(
                size=6,
            ),
            mode='none',
            name='median with 68% CI',
        )

        data.append(rt_data)
        data.append(rt_errorbar)

    layout = go.Layout(
        width=630,
        height=350,
        title=dict(
            text='Reaction time - Contrast',
            x=0.25,
            y=0.85
        ),
        xaxis=dict(
            title='Contrast (%)'),
        yaxis=dict(
            title='Reaction time (s)'),
        legend=dict(
            x=1.1,
            y=0.9,
            orientation='v'),
        template=dict(
            layout=dict(
                plot_bgcolor="white"
            )
        )
    )

    return go.Figure(data=data, layout=layout)


def create_rt_trialnum_plot(trials):

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

    rt_trials = pd.DataFrame(rt)
    rt_trials.index = rt_trials.index + 1
    rt_rolled = rt_trials['rt'].rolling(window=10).median()
    rt_rolled = rt_rolled.where((pd.notnull(rt_rolled)), None)
    rt_trials = rt_trials.where((pd.notnull(rt_trials)), None)

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
        title=dict(
            text='Reaction time - trial number',
            x=0.26,
            y=0.85
        ),
        xaxis=dict(title='Trial number'),
        yaxis=dict(
            title='Reaction time (s)',
            type='log',
            range=np.log10([0.1, 100]).tolist(),
            dtick=np.log10([0.1, 1, 10, 100]).tolist()),
        template=dict(
            layout=dict(
                plot_bgcolor="white"
            )
        )
    )

    return go.Figure(data=[data, rolled], layout=layout)


def create_status_plot(data, yrange, status, xaxis='x1', yaxis='y1',
                       show_legend_external=True, public=False):

    if public:
        trained_marker_name = 'first day got trained'
    else:
        trained_marker_name = 'first day got trained 1a'
    if status['is_trained_1a']:
        data.append(
           go.Scatter(
               x=[status['first_trained_1a_date'],
                  status['first_trained_1a_date']],
               y=yrange,
               mode="lines",
               marker=dict(color='rgba(195, 90, 80, 1)'),
               name=trained_marker_name,
               xaxis=xaxis,
               yaxis=yaxis,
               showlegend=show_legend_external,
               hoverinfo='x'
            )
        )

    if status['is_trained_1b'] and (not public):
        data.append(
           go.Scatter(
               x=[status['first_trained_1b_date'],
                  status['first_trained_1b_date']],
               y=yrange,
               mode="lines",
               marker=dict(color='rgba(255, 153, 20, 1)'),
               name='first day got trained 1b',
               xaxis=xaxis,
               yaxis=yaxis,
               showlegend=show_legend_external,
               hoverinfo='x'
            )
        )

    if status['is_ready4ephysrig'] and (not public):
        data.append(
           go.Scatter(
               x=[status['first_ready4ephysrig_date'],
                  status['first_ready4ephysrig_date']],
               y=yrange,
               mode="lines",
               marker=dict(color='rgba(28, 20, 255, 1)'),
               name='first day got ready4ephysrig',
               xaxis=xaxis,
               yaxis=yaxis,
               showlegend=show_legend_external,
               hoverinfo='x'
            )
        )

    if status['is_ready4delay'] and (not public):
        data.append(
           go.Scatter(
               x=[status['first_ready4delay_date'],
                  status['first_ready4delay_date']],
               y=yrange,
               mode="lines",
               marker=dict(color='rgba(117, 117, 117, 1)'),
               name='first day got ready4delay',
               xaxis=xaxis,
               yaxis=yaxis,
               showlegend=show_legend_external,
               hoverinfo='x'
            )
        )

    if status['is_ready4recording'] and (not public):
        data.append(
           go.Scatter(
               x=[status['first_ready4recording_date'],
                  status['first_ready4recording_date']],
               y=yrange,
               mode="lines",
               marker=dict(color='rgba(20, 255, 91, 1)'),
               name='first day got ready4recording',
               xaxis=xaxis,
               yaxis=yaxis,
               showlegend=show_legend_external,
               hoverinfo='x'
            )
        )

    if status['is_over_seven_months']:
        data.append(
           go.Scatter(
               x=[status['seven_months_date'],
                  status['seven_months_date']],
               y=yrange,
               mode="lines",
               marker=dict(color='rgba(0, 0, 0, 1)'),
               name='mouse became seven months',
               xaxis=xaxis,
               yaxis=yaxis,
               showlegend=show_legend_external,
               hoverinfo='x'
            )
        )
    if status['has_ephys_session']:
        data.append(
           go.Scatter(
               x=[status['first_ephys_session_date'],
                  status['first_ephys_session_date']],
               y=yrange,
               mode="lines",
               line=dict(
                   width=2,
                   color='rgba(5, 142, 255, 1)',
                   dash='dashdot'),
               name='first ephys session date',
               xaxis=xaxis,
               yaxis=yaxis,
               showlegend=show_legend_external,
               hoverinfo='x',
               legendgroup='ephys_good_enough'
            )
        )

    return data


def create_monday_plot(data, yrange, mondays, xaxis='x1', yaxis='y1',
                       show_legend_external=True):

    for imonday, monday in enumerate(mondays):
        if imonday == 0 and show_legend_external:
            show_legend = True
        else:
            show_legend = False

        data.append(
            go.Scatter(
                x=[monday, monday],
                y=yrange,
                mode="lines",
                line=dict(
                    width=0.5,
                    color='gray',
                    dash='dot'
                ),
                name='Mondays',
                xaxis=xaxis,
                yaxis=yaxis,
                showlegend=show_legend,
                legendgroup='monday',
                hoverinfo='skip'
            )
        )

    return data


def create_good_enough_brainmap_plot(data, yrange, ephys_dates,
                                     good_enough,
                                     xaxis='x1', yaxis='y1',
                                     show_legend_external=True):

    shown_red = 0
    shown_blue = 0
    for i_good_date, (ephys_date, good) in \
            enumerate(zip(ephys_dates, good_enough)):

        if good:
            color = 'rgba(5, 142, 255, 0.3)'
            legend = 'good enough for brainwide map'
            if shown_blue:
                show_legend = False
            elif show_legend_external:
                show_legend = True
                shown_blue = 1
            else:
                show_legend = False
        else:
            color = 'rgba(255, 18, 18, 0.2)'
            legend = 'not good enough for brainwide map'
            if shown_red:
                show_legend = False
            elif show_legend_external:
                show_legend = True
                shown_red = 1
            else:
                show_legend = False

        data.append(
            go.Scatter(
                x=[ephys_date, ephys_date],
                y=yrange,
                mode="lines",
                line=dict(
                    width=2,
                    color=color
                ),
                name=legend,
                xaxis=xaxis,
                yaxis=yaxis,
                showlegend=show_legend,
                legendgroup='ephys_good_enough',
                hoverinfo='skip'
            )
        )

    return data
