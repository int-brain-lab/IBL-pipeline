'''
This module contains functions that generates plots.
'''

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import cm
from matplotlib.colors import Normalize
from scipy.interpolate import interpn
import colorlover as cl


def driftmap_color(
        clusters_depths, spikes_times,
        spikes_amps, spikes_depths, spikes_clusters,
        ax=None, axesoff=False, return_lims=False):

    '''
    Plots the driftmap of a session or a trial

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
    ax: matplotlib.axes.Axes object (optional)
        The axis object to plot the driftmap on
        (if `None`, a new figure and axis is created)

    Return
    ---
    ax: matplotlib.axes.Axes object
        The axis object with driftmap plotted
    x_lim: list of two elements
        range of x axis
    y_lim: list of two elements
        range of y axis
    '''

    color_bins = sns.color_palette("hls", 500)
    new_color_bins = np.vstack(
        np.transpose(np.reshape(color_bins, [5, 100, 3]), [1, 0, 2]))

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

    args = dict(color=colorvec, edgecolors='none')

    if ax is None:
        fig = plt.Figure(dpi=200, frameon=False, figsize=[10, 10])
        ax = plt.Axes(fig, [0.1, 0.1, 0.9, 0.9])
        ax.set_xlabel('Time (sec)')
        ax.set_ylabel('Distance from the probe tip (µm)')
        savefig = True
        args.update(s=0.1)

    ax.scatter(x, y, **args)
    x_edge = (max(x) - min(x)) * 0.05
    x_lim = [min(x) - x_edge, max(x) + x_edge]
    y_lim = [min(y) - 50, max(y) + 100]
    ax.set_xlim(x_lim[0], x_lim[1])
    ax.set_ylim(y_lim[0], y_lim[1])

    if axesoff:
        ax.axis('off')

    if savefig:
        fig.add_axes(ax)
        fig.savefig('driftmap.png')

    if return_lims:
        return ax, x_lim, y_lim
    else:
        return ax


def depth_peth(peth_df, ax=None, colors=None,
               as_background=False, return_lims=False):

    '''
    Plots the peth of all trials for multi-unit activities across different depths.

    The plot shows the heatmap of peth of each time point and depth.

    Parameters
    -------------
    peth_df: data frame
        values to be peth, with time, depths as rows and columns
    ax: matplotlib.axes.Axes object (optional)
        axis object to plot the depth peth
    colors: n x 3 2D list
        color map to generate the heatmap
    as_background: boolean
        if True, return only the heatmap without layout and colorbar
    return_lims: boolean
        if True, return xlim and ylim

    Return
    ------------
    ax: matplotlib.axes.Axes object
    x_lim: list of two elements
        range of x axis
    y_lim: list of two elements
        range of y axis
    '''

    if colors is None:
        colors = sns.diverging_palette(255, 10, n=100)
        center = 0
    else:
        center = None

    if ax is None:
        fig, ax = plt.subplots(1, 1, dpi=100, frameon=False, figsize=[6, 4])

    if as_background:
        ax.axis('off')
        cbar = None
    else:
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Depth relative to the probe tip (µm)')
        cbar = 'auto'

    ax = sns.heatmap(peth_df,
                     xticklabels=10,
                     yticklabels=5,
                     cmap=colors,
                     center=center,
                     ax=ax, cbar=cbar)
    ax.invert_yaxis()

    if return_lims:
        time = peth_df.columns.to_list()
        depths = peth_df.index.to_list()
        time_bin = np.mean(np.diff(time))
        depth_bin = np.mean(np.diff(depths))
        x_lim = [min(time) - time_bin/2, max(time) + time_bin/2]
        y_lim = [min(depths) - depth_bin/2, max(depths) + depth_bin/2]

        return ax, x_lim, y_lim
    else:
        return ax


def spike_amp_time(spike_times, spike_amps,
                   ax=None, s=3,
                   as_background=False, return_lims=False):

    '''
    Plots spike amps versus the time

    Parameters
    -------------
    spike_times: ndarray
        spike times of a cluster, in s
    spike_amps: ndarray
        amplitude of spikes, in uV
    ax: matplotlib.axes.Axes object (optional)
        axis object to plot on
    s:  scalar,
        size of the scatters
    as_background: boolean
        if True, return only the heatmap without layout and colorbar
    return_lims: boolean
        if True, return xlim and ylim

    Return
    ------------
    ax: matplotlib.axes.Axes object
    x_lim: list of two elements
        range of x axis
    y_lim: list of two elements
        range of y axis
    '''

    if ax is None:
        fig, ax = plt.subplots(1, 1, dpi=100, frameon=False, figsize=[6, 4])

    if as_background:
        ax.axis('off')
    else:
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Spike amplitude (µV)')

    x = spike_times
    y = spike_amps
    data, x_e, y_e = np.histogram2d(
        x, y, bins=[100, 100], density=True)
    z = interpn((0.5*(x_e[1:] + x_e[:-1]), 0.5*(y_e[1:]+y_e[:-1])),
                data, np.vstack([x, y]).T,
                method="splinef2d", bounds_error=False)

    # To be sure to plot all data
    z[np.where(np.isnan(z))] = 0.0

    # Sort the points by density, so that the densest points are plotted last
    idx = z.argsort()
    x, y, z = x[idx], y[idx], z[idx]

    ax.scatter(x, y, c=z, s=s)

    if len(spike_times):
        x_lim = [0, np.max(spike_times) + 10]
        y_lim = [0, np.max(spike_amps) + 10]
    else:
        x_lim = [0, 4000]
        y_lim = [0, 500]

    ax.set_xlim(x_lim)
    ax.set_ylim(y_lim)

    if return_lims:
        return ax, x_lim, y_lim
    else:
        return ax


def template_waveform(waveforms, coords,
                      ax=None, as_background=False, return_lims=False):

    if ax is None:
        fig, ax = plt.subplots(1, 1, dpi=100, frameon=False, figsize=[5.8, 4])

    if as_background:
        ax.axis('off')
    else:
        ax.set_xlabel('Channel position x (µm)')
        ax.set_ylabel('Channel position y (µm)')

    x_max = np.max(coords[:, 0])
    x_min = np.min(coords[:, 0])

    y_max = np.max(coords[:, 1])
    y_min = np.min(coords[:, 1])

    n_channels = np.shape(waveforms)[1]
    time_len = np.shape(waveforms)[0]

    dt = 1/30.  # in ms

    x_scale = (x_max - x_min) / n_channels / 10 / dt
    y_scale = (y_max - y_min) / n_channels * 20

    time = np.arange(time_len)*dt

    for wf, coord in zip(waveforms.T, coords):
        ax.plot(time*x_scale + coord[0],
                wf*y_scale+coord[1], color=[0.2, 0.3, 0.8])

    # plot scale bar
    x_bar = x_scale
    y_bar = y_scale

    x0 = x_min - 8
    y0 = y_min + 25

    ax.text(x0-0.2*x_bar, y0-0.2*y_bar, '1 ms', fontdict=dict(family='serif'))
    ax.text(x0-0.6*x_bar, y0+0.2*y_bar, '100 uV', fontdict=dict(family='serif'), rotation='vertical')

    ax.plot([x0, x0 + x_bar], [y0, y0], color='black')
    ax.plot([x0, x0], [y0, y0 + y_bar], color='black')

    x_lim = [x_min - 3*x_bar, x_max + 15]
    y_lim = [y_min - 0.2*y_bar, y_max + 20]

    ax.set_xlim(x_lim)
    ax.set_ylim(y_lim)

    if return_lims:
        return ax, x_lim, y_lim
    else:
        return ax
