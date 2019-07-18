from ibl_pipeline.analyses import behavior
from ibl_pipeline import behavior as behavior_ingest
from ibl_pipeline import subject, action, acquisition
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

    return dict(
        first_date=first_date,
        last_date=last_date,
        first_date_str=first_date_str,
        last_date_str=last_date_str,
        date_array=date_array,
        mondays=mondays)


def get_status(subj):
    # get the first date when animal became "trained" and "ready for ephys"
    first_trained = subj.aggr(
        behavior.SessionTrainingStatus & 'training_status = "trained"',
        first_session='DATE(min(session_start_time))')
    first_biased = subj.aggr(
        behavior.SessionTrainingStatus & 'training_status = "ready for ephys"',
        first_session='DATE(min(session_start_time))')

    result = dict()
    if len(first_trained):
        first_trained_date = first_trained.fetch1(
            'first_session').strftime('%Y-%m-%d')
        result.update(is_trained=True, first_trained_date=first_trained_date)
    else:
        result.update(is_trained=False)

    if len(first_biased):
        first_biased_date = first_biased.fetch1(
            'first_session').strftime('%Y-%m-%d')
        result.update(is_biased=True, first_biased_date=first_biased_date)
    else:
        result.update(is_biased=False)

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
        err_c = color.copy()
        err_c[3] = err_c[3]*opacity
        curve_color = 'rgba{}'.format(tuple(color))
        error_color = 'rgba{}'.format(tuple(err_c))
    elif prob_left == 0.5:
        color = cmap[1]
        err_c = color.copy()
        err_c[3] = err_c[3]*opacity
        curve_color = 'rgba{}'.format(tuple(color))
        error_color = 'rgba{}'.format(tuple(err_c))
    elif prob_left == 0.8:
        color = cmap[2]
        err_c = color.copy()
        err_c[3] = err_c[3]*opacity
        curve_color = 'rgba{}'.format(tuple(color))
        error_color = 'rgba{}'.format(tuple(err_c))
    else:
        return

    return curve_color, error_color


def create_psych_curve_plot(sessions):
    data_mean = []
    data_errorbar = []
    data_fit = []
    data_text = []

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
    )

    return go.Figure(data=data, layout=layout)


def create_status_plot(data, yrange, status, xaxis='x1', yaxis='y1',
                       show_legend_external=True):

    if status['is_trained']:
        data.append(
           go.Scatter(
               x=[status['first_trained_date'], status['first_trained_date']],
               y=yrange,
               mode="lines",
               marker=dict(color='orange'),
               name='first day got trained',
               xaxis=xaxis,
               yaxis=yaxis,
               showlegend=show_legend_external,
               hoverinfo='x'
            )
        )

    if status['is_biased']:
        data.append(
           go.Scatter(
               x=[status['first_biased_date'], status['first_biased_date']],
               y=yrange,
               mode="lines",
               marker=dict(color='forestgreen'),
               name='first day got biased',
               xaxis=xaxis,
               yaxis=yaxis,
               showlegend=show_legend_external,
               hoverinfo='x'
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


def create_raster_plot(trials, align_event,
                       sorting_var='trial_id', x_lim=[-1, 1],
                       show_plot=False):

    if sorting_var == 'response - stim on':
        sort_by = 'trial_response_time + trial_start_time - trial_stim_on_time'
        if align_event == 'stim on':
            mark = sort_by
            label = sorting_var
        elif align_event == 'response':
            mark = """trial_stim_on_time -
                      trial_response_time - trial_start_time"""
            label = 'stim on - response'
        else:
            raise NameError(
                f"""
                Wrong combination of alignment and sorting:\n
                {sorting_var}, {align_event}
                """
            )
    elif sorting_var == 'feedback - stim on':
        sort_by = 'trial_feedback_time - trial_stim_on_time'
        if align_event == 'stim on':
            mark = sort_by
            label = sorting_var
        elif align_event == 'feedback':
            mark = 'trial_stim_on_time - trial_feedback_time'
            label = 'stim on - feedback'
        else:
            raise NameError(
                f"""
                Wrong combination of alignment and sorting:\n
                {sorting_var}, {align_event}
                """
            )
    elif sorting_var == 'feedback - response':
        sort_by = """trial_feedback_time -
                     trial_response_time - trial_start_time"""
        if align_event == 'response':
            mark = sort_by
            label = sorting_var
        elif align_event == 'feedback':
            mark = """trial_response_time + trial_start_time -
                      trial_feedback_time"""
            label = 'response - feedback'
        else:
            raise NameError(
                f"""
                Wrong combination of alignment and sorting:\n
                {sorting_var}, {align_event}
                """
            )
    elif sorting_var == 'trial_id':
        sort_by = 'trial_id'
    else:
        raise NameError("""
            'Unknown sorting variable.\n
            It has to be one of the following:\n
            ["trial_id", \n
             "response - stim on", \n
             "feedback - stim on", \n
             "feedback - response"]'""")

    if sorting_var != 'trial_id':
        trials = (trials & 'event="{}"'.format(align_event)).proj(
            'trial_id', 'trial_spike_times', sort_by=sort_by, mark=mark)
        spk_times, marking_points = trials.fetch(
            'trial_spike_times', 'mark', order_by='sort_by')
    else:
        trials = (trials & 'event="{}"'.format(align_event)).proj(
            'trial_id', 'trial_spike_times', sort_by=sort_by)
        spk_times = trials.fetch(
            'trial_spike_times', order_by='sort_by')

    spk_times_all = np.hstack(spk_times)
    id_all = [[i] * len(spike_time) for i, spike_time in enumerate(spk_times)]
    id_all = np.hstack(id_all)

    fig = plt.figure(dpi=300, frameon=False, figsize=[10, 5])
    ax = plt.Axes(fig, [0., 0., 1., 1.])
    ax.plot(spk_times_all, id_all, 'k.', alpha=0.4, markeredgewidth=0)
    if sorting_var != 'trial_id':
        ax.plot(marking_points, range(len(spk_times)), 'b', label=label)
    ax.set_axis_off()
    fig.add_axes(ax)

    # hide the axis
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)

    # set the limits to be exactly what you want
    ax.set_xlim(x_lim[0], x_lim[1])
    y_lim = len(trials) * 1.15
    ax.set_ylim(0, y_lim)
    ax.axvline(0, linewidth=2, alpha=0.5, color='k', label=align_event)
    ax.legend(loc=[0.01, 0.87], prop=dict(size=14))

    # save the figure with `pad_inches=0` to remove
    # any padding in the image
    import tempfile
    temp = tempfile.NamedTemporaryFile(suffix=".png")
    fig.savefig(temp.name, pad_inches=0)

    if not show_plot:
        plt.close(fig)

    import base64
    with open(temp.name, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
    temp.close()
    return encoded_string, [0, y_lim]

def create_psth_plot(trials, align_event, nbins, window_size, x_lim=[-1, 1], show_plot=False):
    spk_times = (trials & 'event="{}"'.format(align_event)).fetch('trial_spike_times')
    mean_counts = np.divide(
        np.histogram(np.hstack(spk_times),
                    range=x_lim,
                    bins=nbins)[0],
        len(spk_times))
    time_bins=np.linspace(x_lim[0], x_lim[1], num=nbins)

    # convolve with a box-car filter
    dt = np.mean(np.diff(time_bins))
    psth = np.divide(signal.convolve(mean_counts, signal.boxcar(window_size), mode='same'),
                    window_size*dt)
    fig = plt.figure(dpi=300, frameon=False, figsize=[10, 5])
    ax = plt.Axes(fig, [0., 0., 1., 1.])
    ax.plot(time_bins, psth, markeredgewidth=0)

    ax.set_axis_off()
    fig.add_axes(ax)

    # hide the axis
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)

    # set the limits to be exactly what you want
    ax.set_xlim(x_lim[0], x_lim[1])
    ax.axvline(0, linewidth=2, alpha=0.5, color='k', label=align_event)
    ax.legend(loc=[0.01, 0.87], prop=dict(size=14))
    y_lim = ax.get_ylim()

    # save the figure with `pad_inches=0` to remove
    # any padding in the image
    import tempfile
    temp = tempfile.NamedTemporaryFile(suffix=".png")
    fig.savefig(temp.name, pad_inches=0)

    if not show_plot:
        plt.close(fig)

    import base64
    with open(temp.name, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
    temp.close()
    return encoded_string, y_lim
