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
import boto3
import io
import ibl_pipeline


def get_sort_and_marker(align_event, sorting_var):

    '''
    Based on align_event and sorting variables, get the expression for query.

    Parameters
    -----------
    align_event: the event name that trials need to align to
    sorting_var: the variable to sort with for the raster plot

    Returns
    --------
    sorting_query: sorting variable used in the query,
                   e.g. 'trial_response_time - trial_stim_on_time'
    mark: marking variable used in the query.
          e.g. for sorting with 'response - stim on'
          If aligned to stim on time, mark response_time - stim_on_time (positive)
          If alighed to response time, mark stim_on_time - response_time (negative)
    label: label of the marker event, e.g. if aligned to stim on, mark response
    '''

    if sorting_var == 'response - stim on':
        sorting_query = 'trial_response_time - trial_stim_on_time'
        if align_event == 'stim on':
            mark = sorting_query
            label = 'response'
        elif align_event == 'response':
            mark = 'trial_stim_on_time - trial_response_time'
            label = 'stim on'
        else:
            raise NameError(
                f"""
                Wrong combination of alignment and sorting:\n
                {sorting_var}, {align_event}
                """
            )
    elif sorting_var == 'feedback - stim on':
        sorting_query = 'trial_feedback_time - trial_stim_on_time'
        if align_event == 'stim on':
            mark = sorting_query
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
        sorting_query = 'trial_feedback_time - trial_response_time'
        if align_event == 'response':
            mark = sorting_query
            label = 'feedback'
        elif align_event == 'feedback':
            mark = 'trial_response_time - trial_feedback_time'
            label = 'response'
        else:
            raise NameError(
                f"""
                Wrong combination of alignment and sorting:\n
                {sorting_var}, {align_event}
                """
            )
    elif sorting_var == 'trial_id':
        sorting_query = 'trial_id'
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
    return sorting_query, mark, label


def create_raster_plot(trials, align_event,
                       sorting_var='trial_id', x_lim=[-1, 1],
                       show_plot=False):

    sorting_query, mark, label = get_sort_and_marker(
        align_event, sorting_var)

    if sorting_var != 'trial_id':
        trials = (trials & 'event="{}"'.format(align_event)).proj(
            'trial_id', 'trial_spike_times', sorting_query=sorting_query, mark=mark)
        spk_times, marking_points = trials.fetch(
            'trial_spike_times', 'mark', order_by='sorting_query')
    else:
        trials = (trials & 'event="{}"'.format(align_event)).proj(
            'trial_id', 'trial_spike_times', sorting_query=sorting_query)
        spk_times = trials.fetch(
            'trial_spike_times', order_by='sorting_query')

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


def compute_psth(trials, trial_type, align_event, nbins,
                 window_size, x_lim=[-1, 1], as_dict=True):

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
    if as_dict:
        return data
    else:
        return list(time_bins), list(psth)


def get_spike_times(trials, sorting_var, align_event,
                    sorting_query=None,
                    mark=None):
    '''
    get spike times as a vector and values of marking points

    Parameters:
    -----------
    trials: query of behavior.TrialSet.Trial * ephys.TrialSpikes,
            for suitable conditions
    sorting_var: the variable to sort with for the raster plot
    align_event: the event name that the spike times aligns to
    sorting_query: sorting variable used in the query,
                   e.g. 'trial_response_time - trial_stim_on_time'
    mark: marking variable used in the query.
          e.g. for sorting with 'response - stim on'
          If aligned to stim on time, mark response_time - stim_on_time (positive)
          If alighed to response time, mark stim_on_time - response_time (negative)

    Returns:
    -----------
    spk_times: trial spike times as an array of spike times per trial,
               including the trials without spikes.
    marking_points: values of marking points,
                    e.g. normalized reponse time for sorting
                    'reponse_time - stim_on_time'
    '''

    if sorting_var != 'trial_id':
        trials = (trials & 'event="{}"'.format(align_event)).proj(
            'trial_id', 'trial_spike_times',
            sorting_query=sorting_query, mark=mark)
        spk_times, marking_points = trials.fetch(
            'trial_spike_times', 'mark', order_by='sorting_query')
    else:
        trials = (trials & 'event="{}"'.format(align_event)).fetch(
            'trial_spike_times', order_by='trial_id')
        marking_points = None

    return spk_times, marking_points


def get_spike_times_trials(trials, sorting_var, align_event,
                           sorting_query=None,
                           mark=None):
    '''
    return spike times of different groups of
    trials, right, left, and incorrect

    Parameters:
    -----------
    trials: query of behavior.TrialSet.Trial * ephys.TrialSpikes,
            for suitable conditions
    sorting_var: the variable to sort with for the raster plot
    align_event: the event name that the spike times aligns to
    sorting_query: sorting variable used in the query,
                   e.g. 'trial_response_time - trial_stim_on_time'
    '''

    trials_left = trials & 'trial_response_choice="CW"' & \
        'trial_signed_contrast < 0'
    trials_right = trials & 'trial_response_choice="CCW"' & \
        'trial_signed_contrast > 0'

    trials_incorrect = trials - trials_left.proj() - trials_right.proj()

    kargs = dict(
        sorting_var=sorting_var,
        align_event=align_event,
        sorting_query=sorting_query,
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
                                x_lim=[-1, 1],
                                show_plot=False,
                                fig_dir=None,
                                store_type=None):

    sorting_query, mark, label = get_sort_and_marker(
        align_event, sorting_var)

    fig = plt.figure(dpi=150, frameon=False, figsize=[10, 5])
    ax = plt.Axes(fig, [0., 0., 1., 1.])

    if len(trials):
        if sorting_var == 'trial_id':
            spk_times, trial_ids = (trials & 'event="{}"'.format(align_event)).fetch(
                'trial_spike_time', 'trial_id', order_by='trial_id')
            spk_trial_ids = np.hstack(
                [[trial_id] * len(spk_time)
                    for trial_id, spk_time in zip(trial_ids, spk_times)])
            ax.plot(spk_times, spk_trial_ids, 'k.', alpha=0.5,
                    markeredgewidth=0)
        else:
            spk_times_left, marking_points_left, \
                spk_times_right, marking_points_right, \
                spk_times_incorrect, marking_points_incorrect = \
                get_spike_times_trials(
                    trials, sorting_var, align_event, sorting_query, mark)

            id_gap = len(trials) * 0.02

            if len(spk_times_incorrect):
                spk_times_all_incorrect = np.hstack(spk_times_incorrect)
                id_incorrect = [[i] * len(spike_time)
                                for i, spike_time in
                                enumerate(spk_times_incorrect)]
                id_incorrect = np.hstack(id_incorrect)
                ax.plot(spk_times_all_incorrect, id_incorrect, 'r.',
                        alpha=0.5, markeredgewidth=0, label='incorrect trials')
                ax.plot(marking_points_incorrect,
                        range(len(spk_times_incorrect)), 'r', label=label)
            else:
                id_incorrect = [0]

            if not len(id_incorrect):
                id_incorrect = [0]

            if len(spk_times_left):
                spk_times_all_left = np.hstack(spk_times_left)
                id_left = [[i + max(id_incorrect) + id_gap] * len(spike_time)
                           for i, spike_time in
                           enumerate(spk_times_left)]
                id_left = np.hstack(id_left)
                ax.plot(spk_times_all_left, id_left, 'g.',
                        alpha=0.5, markeredgewidth=0, label='left trials')
                ax.plot(marking_points_left,
                        np.add(range(len(spk_times_left)), max(id_incorrect) + id_gap), 'g')
            else:
                id_left = [max(id_incorrect)]

            if len(spk_times_right):
                spk_times_all_right = np.hstack(spk_times_right)
                id_right = [[i + max(id_left) + id_gap] * len(spike_time)
                            for i, spike_time in enumerate(spk_times_right)]
                id_right = np.hstack(id_right)

                ax.plot(spk_times_all_right, id_right, 'b.',
                        alpha=0.5, markeredgewidth=0, label='right trials')
                ax.plot(marking_points_right,
                        np.add(range(len(spk_times_right)), max(id_left) + id_gap), 'b')
            else:
                id_right = [max(id_left)]

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
        if store_type == 'filepath':
            if not os.path.exists(os.path.dirname(fig_dir)):
                try:
                    os.makedirs(os.path.dirname(fig_dir))
                except OSError as exc:  # Guard against race condition
                    if exc.errno != errno.EEXIST:
                        raise
            fig.savefig(fig_dir, pad_inches=0)
            return [0, y_lim], label

        elif store_type == 's3':
            access, secret = (ibl_pipeline.S3Access & 's3_id=1').fetch1(
                'access_key', 'secret_key')

            s3 = boto3.resource(
                's3',
                aws_access_key_id=access,
                aws_secret_access_key=secret)
            BUCKET_NAME = "ibl-dj-external"
            bucket = s3.Bucket(BUCKET_NAME)

            # upload to s3
            img_data = io.BytesIO()
            fig.savefig(img_data, format='png')
            img_data.seek(0)
            bucket.put_object(Body=img_data,
                              ContentType='image/png',
                              Key=fig_dir)
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
