from ibl_pipeline.analyses import behavior
from ibl_pipeline import behavior as behavior_ingest
from ibl_pipeline import subject, action, acquisition, ephys
from ibl_pipeline.utils import psychofit as psy
import ibl_pipeline
from uuid import UUID
import numpy as np
import datajoint as dj
import plotly.graph_objs as go
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import colorlover as cl
import plotly
from plotly import tools
import statsmodels.stats.proportion as smp
from scipy.signal import gaussian, convolve, boxcar
import os
import boto3
import io
import tempfile
import base64
import gc
import datetime


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
        convolve(mean_counts, boxcar(window_size), mode='same'),
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
        fig.clear()
        plt.close(fig)
        gc.collect()

    import base64
    with open(temp.name, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
    temp.close()
    return encoded_string, y_lim


def compute_psth(trials, trial_type, align_event, bin_size=0.025,
                 smoothing=0.025, x_lim=[-1, 1], as_dict=True):

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

    # get rid of boundary effects for smoothing
    n_offset = 5 * int(np.ceil(smoothing / bin_size))
    n_bins_pre = int(np.ceil(np.negative(x_lim[0]) / bin_size)) + n_offset
    n_bins_post = int(np.ceil(x_lim[1] / bin_size)) + n_offset
    n_bins = n_bins_pre + n_bins_post

    spk_times = trials.fetch('trial_spike_times')
    hist = np.histogram(np.hstack(spk_times),
                        range=x_lim,
                        bins=n_bins)

    mean_fr = np.divide(hist[0], len(spk_times)*bin_size)
    time = hist[1]
    time_bins = (time[:-1] + time[1:])/2
    # build gaussian kernel
    if smoothing > 0:
        w = n_bins - 1 if n_bins % 2 == 0 else n_bins
        window = gaussian(w, std=smoothing / bin_size)
        window /= np.sum(window)

    psth = convolve(mean_fr, window, mode='same', method='auto')

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


def compute_psth_with_errorbar(
        trials, trial_type, align_event, bin_size=0.025,
        smoothing=0.025, x_lim=[-1, 1], as_plotly_obj=True):

    if trial_type == 'left':
        color = 'green'
        err_color = 'rgba(0, 255, 0, 0.2)'
    elif trial_type == 'right':
        color = 'blue'
        err_color = 'rgba(0, 0, 255, 0.2)'
    elif trial_type == 'all':
        color = 'black'
        err_color = 'rgba(0, 0, 0, 0.2)'
    elif trial_type == 'incorrect':
        color = 'red'
        err_color = 'rgba(255, 0, 0, 0.2)'
    else:
        raise NameError('Invalid type name')

    # set up bins
    n_offset = 5 * int(np.ceil(smoothing / bin_size))  # get rid of boundary effects for smoothing
    n_bins_pre = int(np.ceil(np.negative(x_lim[0]) / bin_size)) + n_offset
    n_bins_post = int(np.ceil(x_lim[1] / bin_size)) + n_offset
    n_bins = n_bins_pre + n_bins_post

    # this is bin edges
    bins = np.arange(-n_bins_pre, n_bins_post + 1) * bin_size

    # spikes times for all trials
    spk_times = trials.fetch('trial_spike_times')

    # trial_id for each spike, flattened
    trial_ids_flat = np.hstack([[i_trial] * len(spk_time)
                                for i_trial, spk_time in enumerate(spk_times)])
    # flatten spk times
    spk_times_flat = np.hstack(spk_times)

    # filter out spike times that are not in this range
    rel_idxs = np.bitwise_and(spk_times_flat >= bins[0],
                              spk_times_flat <= bins[-1])
    filtered_spike_times_flat = spk_times_flat[rel_idxs]
    filtered_trial_ids_flat = trial_ids_flat[rel_idxs]

    # ----- assign each spike into 2D bins, each trial and each time slot --------

    # bin id of each spike
    bin_id = (np.floor((filtered_spike_times_flat - np.min(bins)) / bin_size)).astype(np.int64)

    # trial id of each spike
    trial_scale, trial_id = np.unique(filtered_trial_ids_flat,
                                      return_inverse=True)

    # assign each spike a 1d index representing a combination of trial and time bin
    bin_num, trial_num = [bins.size, trial_scale.size]
    ind2d = np.ravel_multi_index(np.c_[trial_id, bin_id].T,
                                 dims=[trial_num, bin_num])

    # spike counts of each trial and each bin
    spike_counts = np.bincount(ind2d,
                               minlength=bin_num * trial_num,
                               weights=None).reshape(trial_num, bin_num)

    # get binned spikes as a 2D array n_trials x n_bins
    binned_spikes = spike_counts[:, :-1]

    # smooth with convolution
    if smoothing > 0:
        w = n_bins - 1 if n_bins % 2 == 0 else n_bins
        window = gaussian(w, std=smoothing / bin_size)
        window /= np.sum(window)
        binned_spikes_conv = np.zeros([trial_num, bin_num-1])
        for j in range(binned_spikes.shape[0]):
            binned_spikes_conv[j, :] = convolve(
                binned_spikes[j, :], window, mode='same', method='auto')
        binned_spikes = binned_spikes_conv

    mean_psth = np.mean(binned_spikes, axis=0)
    sem_psth = np.std(binned_spikes, axis=0)/np.sqrt(trial_num)

    mean_psth = mean_psth[n_offset:-n_offset]/bin_size
    sem_psth = sem_psth[n_offset:-n_offset]/bin_size

    upper_psth = mean_psth + sem_psth
    lower_psth = mean_psth - sem_psth

    # return the middle of each bin as the time
    time_bins = (bins[:-1] + bins[1:]) / 2
    time_bins = time_bins[n_offset:-n_offset]

    upper_bound = psth = go.Scatter(
        x=list(time_bins),
        y=list(upper_psth),
        mode='lines',
        marker=dict(color="#444"),
        fillcolor=err_color,
        line=dict(width=0),
        fill='tonexty',
        showlegend=False,
    )
    psth = go.Scatter(
        x=list(time_bins),
        y=list(mean_psth),
        mode='lines',
        marker=dict(
            size=6,
            color=color),
        fill='tonexty',
        fillcolor=err_color,
        name='{} trials, mean +/- s.e.m'.format(trial_type)
    )
    lower_bound = go.Scatter(
        x=list(time_bins),
        y=list(lower_psth),
        mode='lines',
        marker=dict(color="#444"),
        line=dict(width=0),
        showlegend=False,
    )

    if as_plotly_obj:
        return [lower_bound, psth, upper_bound]
    else:
        return list(time_bins), list(mean_psth), list(mean_psth+sem_psth), list(mean_psth-sem_psth)


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


def store_fig_external(fig, store_type, fig_dir):
    if store_type == 'filepath':
        if not os.path.exists(os.path.dirname(fig_dir)):
            try:
                os.makedirs(os.path.dirname(fig_dir))
            except OSError as exc:  # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise
        fig.savefig(fig_dir, pad_inches=0)
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


def convert_fig_to_encoded_string(fig):

    temp = tempfile.NamedTemporaryFile(suffix=".png")
    fig.savefig(temp.name, pad_inches=0)
    fig.clear()
    plt.close(fig)
    gc.collect()
    with open(temp.name, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
    temp.close()
    return encoded_string


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
                'trial_spike_times', 'trial_id', order_by='trial_id')
            spk_trial_ids = np.hstack(
                [[trial_id] * len(spk_time)
                    for trial_id, spk_time in enumerate(spk_times)])
            ax.plot(np.hstack(spk_times), spk_trial_ids, 'k.', alpha=0.5,
                    markeredgewidth=0)
        elif sorting_var == 'contrast':
            spk_times, trial_contrasts = (trials & 'event="{}"'.format(align_event)).fetch(
                'trial_spike_times', 'trial_signed_contrast',
                order_by='trial_signed_contrast, trial_id')
            spk_trial_ids = np.hstack(
                [[trial_id] * len(spk_time)
                    for trial_id, spk_time in enumerate(spk_times)])
            ax.plot(np.hstack(spk_times), spk_trial_ids, 'k.', alpha=0.5,
                    markeredgewidth=0)

            # plot different contrasts as background
            contrasts, u_inds = np.unique(trial_contrasts, return_index=True)
            u_inds = list(u_inds) + [len(trial_contrasts)]

            tick_positions = np.add(u_inds[1:], u_inds[:-1])/2

            puor = cl.scales[str(len(contrasts))]['div']['PuOr']
            puor = np.divide(cl.to_numeric(puor), 255)

            for i, ind in enumerate(u_inds[:-1]):
                ax.fill_between([-1, 1], u_inds[i], u_inds[i+1]-1, color=puor[i], alpha=0.8)
            fig.add_axes(ax)
        elif sorting_var == 'feedback type':
            spk_times, trial_fb_types = (trials & 'event="{}"'.format(align_event)).fetch(
                'trial_spike_times', 'trial_feedback_type',
                order_by='trial_feedback_type, trial_id')
            spk_trial_ids = np.hstack(
                [[trial_id] * len(spk_time)
                    for trial_id, spk_time in enumerate(spk_times)])
            ax.plot(np.hstack(spk_times), spk_trial_ids, 'k.', alpha=0.5,
                    markeredgewidth=0)

            # plot different feedback types as background
            fb_types, u_inds = np.unique(trial_fb_types, return_index=True)
            u_inds = list(u_inds) + [len(trial_fb_types)]

            colors = sns.diverging_palette(10, 240, n=len(fb_types))

            for i, ind in enumerate(u_inds[:-1]):
                ax.fill_between([-1, 1], u_inds[i], u_inds[i+1]-1, color=colors[i], alpha=0.5)
            fig.add_axes(ax)
        else:
            spk_times_left, marking_points_left, \
                spk_times_right, marking_points_right, \
                spk_times_incorrect, marking_points_incorrect = \
                get_spike_times_trials(
                    trials, sorting_var, align_event, sorting_query, mark)

            id_gap = len(trials) * 0

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

            if not len(id_left):
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

            if not len(id_right):
                id_right = [max(id_left)]

    ax.set_axis_off()
    fig.add_axes(ax)

    # hide the axis
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)

    # set the limits
    ax.set_xlim(x_lim[0], x_lim[1])
    if sorting_var in ('trial_id', 'contrast', 'feedback type'):
        if len(spk_trial_ids):
            y_lim = max(spk_trial_ids) * 1.02
        else:
            y_lim = 2
    else:
        y_lim = max(id_right) * 1.02
    ax.set_ylim(-2, y_lim)

    if not show_plot:
        plt.close(fig)

    # save the figure with `pad_inches=0` to remove
    # any padding in the image

    if fig_dir:
        store_fig_external(fig, store_type, fig_dir)
        fig.clear()
        gc.collect()
        if sorting_var == 'contrast':
            return [0, y_lim], label, contrasts, tick_positions
        else:
            return [0, y_lim], label
    else:
        encoded_string = convert_fig_to_encoded_string(fig)
        if sorting_var == 'contrast':
            return encoded_string, [0, y_lim], label, contrasts, tick_positions
        else:
            return encoded_string, [0, y_lim], label


color_bins = sns.color_palette("hls", 500)
new_color_bins = np.vstack(
    np.transpose(np.reshape(color_bins, [5, 100, 3]), [1, 0, 2]))


def prepare_spikes_data(key):
    clusters = ephys.DefaultCluster & key
    clusters_ids, clusters_spk_times, \
        clusters_spk_amps, clusters_spk_depths, clusters_depths = \
        clusters.fetch('cluster_id',
                       'cluster_spikes_times',
                       'cluster_spikes_amps',
                       'cluster_spikes_depths',
                       'cluster_depth')

    spikes_depths = np.hstack(clusters_spk_depths)
    spikes_times = np.hstack(clusters_spk_times)
    spikes_amps = np.hstack(clusters_spk_amps)
    spikes_clusters = np.hstack(
        [[cluster_id]*len(cluster_spk_depths)
            for (cluster_id, cluster_spk_depths) in
            zip(clusters_ids, clusters_spk_depths)])

    return dict(
        spikes_depths=spikes_depths,
        spikes_times=spikes_times,
        spikes_amps=spikes_amps,
        spikes_clusters=spikes_clusters,
        clusters_depths=clusters_depths)


def driftmap(
        clusters_depths, spikes_times,
        spikes_amps, spikes_depths, spikes_clusters,
        ax=None, axesoff=False, return_lims=False):

    '''
    Plots the driftmap of a session or a trial.

    The plot shows the spike times vs spike depths.
    Each dot is a spike, whose color indicates the cluster
    and opacity indicates the spike amplitude.

    Parameters
    -------------
    clusters_depths: ndarray
        depths of all clusters
    spikes_times: ndarray
        spike times of all clusters
    spikes_amps: ndarray
        amplitude of each spike
    spikes_depths: ndarray
        depth of each spike
    spikes_clusters: ndarray
        cluster idx of each spike
    ax: axessubplot (optional)
        The axis handle to plot the driftmap on
        (if `None`, a new figure and axis is created)

    Return
    ---
    ax: axessubplot
    x_lim: list of two elements
    y_lim: list of two elements

    '''

    # get the sorted idx of each depth, and create colors based on the idx

    sorted_idx = np.argsort(np.argsort(clusters_depths))

    colors = np.vstack(
        [np.repeat(
            new_color_bins[np.mod(idx, 500), :][np.newaxis, ...],
            n_spikes, axis=0)
            for (idx, n_spikes) in
            zip(sorted_idx, np.unique(spikes_clusters,
                                      return_counts=True)[1])])

    max_amp = np.percentile(spikes_amps, 90)
    min_amp = np.percentile(spikes_amps, 10)
    opacity = np.divide(spikes_amps - min_amp, max_amp - min_amp)
    opacity[opacity > 1] = 1
    opacity[opacity < 0] = 0

    colorvec = np.zeros([len(opacity), 4], dtype='float16')
    colorvec[:, 3] = opacity.astype('float16')
    colorvec[:, 0:3] = colors.astype('float16')

    x = spikes_times.astype('float32')
    y = spikes_depths.astype('float32')

    if ax is None:
        fig = plt.Figure(dpi=50, frameon=False, figsize=[90, 90])
        ax = plt.Axes(fig, [0., 0., 1., 1.])

    ax.scatter(x, y, color=colorvec, edgecolors='none')
    x_edge = (max(x) - min(x)) * 0.05
    x_lim = [min(x) - x_edge, max(x) + x_edge]
    y_lim = [min(y) - 50, max(y) + 100]
    ax.set_xlim(x_lim[0], x_lim[1])
    ax.set_ylim(y_lim[0], y_lim[1])

    if axesoff:
        ax.axis('off')

    if return_lims:
        return ax, x_lim, y_lim
    else:
        return ax


# class Figure


def create_driftmap_plot(spike_data, figsize=[90, 90], dpi=50,
                         fig_dir=None, store_type=None):
    fig = plt.Figure(dpi=dpi, frameon=False, figsize=figsize)
    ax = plt.Axes(fig, [0., 0., 1., 1.])
    ax, x_lim, y_lim = driftmap(
        **spike_data, ax=ax, axesoff=True, return_lims=True)
    fig.add_axes(ax)
    if fig_dir:
        store_fig_external(fig, store_type, fig_dir)
        fig.clear()
        plt.close(fig)
        gc.collect()
        return x_lim, y_lim
    else:
        encoded_string = convert_fig_to_encoded_string(fig)
        plt.close(fig)
        gc.collect()
        return encoded_string, x_lim, y_lim


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
