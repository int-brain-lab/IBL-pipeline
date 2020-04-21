'''
This module contains functions that generates plots.
'''

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns


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
        ax.set_ylabel('Depth relative to the probe tip (um)')
        cbar = 'auto'

    ax = sns.heatmap(peth_df,
                     xticklabels=10,
                     yticklabels=5,
                     cmap=colors,
                     center=center,
                     ax=ax, cbar=cbar)
    ax.invert_yaxis()

    if return_lims:
        time = peth_df['time']
        depth = peth_df['depths']
        time_bin = np.mean(np.diff(time))
        depth_bin = np.mean(np.diff(depths))
        x_lim = [min(time) - time_bin/2, max(time) + time_bin/2]
        y_lim = [min(depths) - depth_bin/2, max(depths) + depth_bin/2]

        return ax, x_lim, y_lim
    else:
        return ax
