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
import os


def get_sort_and_marker(align_event, sorting_var):

    if sorting_var == 'response - stim on':
        sort_by = 'trial_response_time + trial_start_time - trial_stim_on_time'
        if align_event == 'stim on':
            mark = sort_by
            label = 'response'
        elif align_event == 'response':
            mark = """trial_stim_on_time -
                      trial_response_time - trial_start_time"""
            label = 'stim on'
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
            label = 'feedback'
        elif align_event == 'feedback':
            mark = 'trial_stim_on_time - trial_feedback_time'
            label = 'stim on'
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
            label = 'feedback'
        elif align_event == 'feedback':
            mark = """trial_response_time + trial_start_time -
                      trial_feedback_time"""
            label = 'response'
        else:
            raise NameError(
                f"""
                Wrong combination of alignment and sorting:\n
                {sorting_var}, {align_event}
                """
            )
    elif sorting_var == 'trial_id':
        sort_by = 'trial_id'
        mark = None
        label = None
    else:
        raise NameError("""
            'Unknown sorting variable.\n
            It has to be one of the following:\n
            ["trial_id", \n
             "response - stim on", \n
             "feedback - stim on", \n
             "feedback - response"]'""")
    return sort_by, mark, label


def create_raster_plot(trials, align_event,
                       sorting_var='trial_id', x_lim=[-1, 1],
                       show_plot=False):

    sort_by, mark, label = get_sort_and_marker(
        align_event, sorting_var)

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

    fig = plt.figure(dpi=150, frameon=False, figsize=[10, 5])
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


def create_psth_plot(trials, align_event,
                     nbins, window_size, x_lim=[-1, 1],
                     show_plot=False):
    spk_times = (trials & 'event="{}"'.format(align_event)).fetch(
        'trial_spike_times')
    mean_counts = np.divide(
        np.histogram(np.hstack(spk_times),
                     range=x_lim,
                     bins=nbins)[0],
        len(spk_times))
    time_bins = np.linspace(x_lim[0], x_lim[1], num=nbins)

    # convolve with a box-car filter
    dt = np.mean(np.diff(time_bins))
    psth = np.divide(
        signal.convolve(mean_counts, signal.boxcar(window_size), mode='same'),
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


def compute_psth(trials, trial_type, align_event, nbins, window_size, x_lim=[-1, 1]):

    if trial_type == 'left':
        color = 'green'
    elif trial_type == 'right':
        color = 'blue'
    elif trial_type == 'all':
        color = 'black'
    elif trial_type == 'incorrect':
        color = 'red'
    else:
        raise NameError('Invalid type name')

    spk_times = trials.fetch('trial_spike_times')
    mean_counts = np.divide(
        np.histogram(np.hstack(spk_times),
                     range=x_lim,
                     bins=nbins)[0],
        len(spk_times))

    time_bins = np.linspace(x_lim[0], x_lim[1], num=nbins)

    # convolve with a box-car filter
    dt = np.mean(np.diff(time_bins))
    psth = np.divide(
        signal.convolve(mean_counts, signal.boxcar(window_size), mode='same'),
        window_size*dt)

    data = go.Scatter(
        x=list(time_bins),
        y=list(psth),
        mode='lines',
        marker=dict(
            size=6,
            color=color),
        name='{} trials'.format(trial_type)
    )

    return data


def get_spike_times(trials, sorting_var, align_event,
                    sort_by=None,
                    mark=None):
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
        marking_points = None

    return spk_times, marking_points


def get_spike_times_trials(trials, sorting_var, align_event,
                           sort_by=None,
                           mark=None):

    trials_left = trials & 'trial_response_choice="CW"' & \
        'trial_signed_contrast < 0'
    trials_right = trials & 'trial_response_choice="CCW"' & \
        'trial_signed_contrast > 0'

    trials_incorrect = trials - trials_left.proj() - trials_right.proj()

    kargs = dict(
        sorting_var=sorting_var,
        align_event=align_event,
        sort_by=sort_by,
        mark=mark
    )

    spk_times_left, marking_points_left = get_spike_times(trials_left, **kargs)
    spk_times_right, marking_points_right = get_spike_times(trials_right, **kargs)
    spk_times_incorrect, marking_points_incorrect = \
        get_spike_times(trials_incorrect, **kargs)

    return spk_times_left, \
        marking_points_left, \
        spk_times_right, \
        marking_points_right, \
        spk_times_incorrect, \
        marking_points_incorrect


def create_raster_plot_combined(trials, align_event,
                                sorting_var='trial_id',
                                x_lim=[-10, 10],
                                show_plot=False,
                                fig_dir=None):

    sort_by, mark, label = get_sort_and_marker(
        align_event, sorting_var
    )

    spk_times_left, marking_points_left, \
        spk_times_right, marking_points_right, \
        spk_times_incorrect, marking_points_incorrect = \
        get_spike_times_trials(
            trials, sorting_var, align_event, sort_by, mark)

    id_gap = len(trials) * 0.02

    if len(spk_times_incorrect):
        spk_times_all_incorrect = np.hstack(spk_times_incorrect)
        id_incorrect = [[i] * len(spike_time)
                        for i, spike_time in enumerate(spk_times_incorrect)]
        id_incorrect = np.hstack(id_incorrect)
    else:
        id_incorrect = [0]

    if len(spk_times_left):
        spk_times_all_left = np.hstack(spk_times_left)
        id_left = [[i + max(id_incorrect) + id_gap] * len(spike_time)
                   for i, spike_time in enumerate(spk_times_left)]
        id_left = np.hstack(id_left)
    else:
        id_left = [max(id_incorrect)]

    if len(spk_times_right):
        spk_times_all_right = np.hstack(spk_times_right)
        id_right = [[i + max(id_left) + id_gap] * len(spike_time)
                    for i, spike_time in enumerate(spk_times_right)]
        id_right = np.hstack(id_right)
    else:
        id_right = [max(id_right)]

    fig = plt.figure(dpi=150, frameon=False, figsize=[10, 5])
    ax = plt.Axes(fig, [0., 0., 1., 1.])
    if len(spk_times_left):
        ax.plot(spk_times_all_left, id_left, 'g.',
                alpha=0.5, markeredgewidth=0, label='left trials')
    if len(spk_times_right):
        ax.plot(spk_times_all_right, id_right, 'b.',
                alpha=0.5, markeredgewidth=0, label='right trials')
    if len(spk_times_incorrect):
        ax.plot(spk_times_all_incorrect, id_incorrect, 'r.',
                alpha=0.5, markeredgewidth=0, label='incorrect trials')

    if sorting_var != 'trial_id':
        if len(spk_times_incorrect):
            ax.plot(marking_points_incorrect,
                    range(len(spk_times_incorrect)), 'r', label=label)
        if len(spk_times_left):
            ax.plot(marking_points_left,
                    np.add(range(len(spk_times_left)), max(id_incorrect) + id_gap), 'g')
        if len(spk_times_right):
            ax.plot(marking_points_right,
                    np.add(range(len(spk_times_right)), max(id_left) + id_gap), 'b')

    ax.set_axis_off()
    fig.add_axes(ax)

    # hide the axis
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)

    # set the limits
    ax.set_xlim(x_lim[0], x_lim[1])
    y_lim = max(id_right) * 1.02
    ax.set_ylim(-2, y_lim)

    if not show_plot:
        plt.close(fig)

    # save the figure with `pad_inches=0` to remove
    # any padding in the image
    if fig_dir:
        if not os.path.exists(os.path.dirname(fig_dir)):
            try:
                os.makedirs(os.path.dirname(fig_dir))
            except OSError as exc:  # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise
        fig.savefig(fig_dir, pad_inches=0)
        return [0, y_lim], label
    else:
        import tempfile
        temp = tempfile.NamedTemporaryFile(suffix=".png")
        fig.savefig(temp.name, pad_inches=0)
        import base64
        with open(temp.name, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read())
        temp.close()
        return encoded_string, [0, y_lim], label


def get_legend(trials_type, legend_group):
    if trials_type == 'left':
        color = 'green'
    elif trials_type == 'right':
        color = 'blue'
    elif trials_type == 'incorrect':
        color = 'red'
    else:
        raise NameError(
            f"""
            Wrong trial type, has to be one of the following: \n
            "left", "right", "incorrect"
            """
        )
    if legend_group == 'spike':
        marker = 'markers'
    else:
        marker = 'lines'

    return go.Scatter(
        x=[5],
        y=[10],
        mode=marker,
        marker=dict(
            size=6,
            color=color,
            opacity=0.5
        ),
        name='{} time on<br>{} trials'.format(legend_group, trials_type),
        legendgroup=legend_group
    )
