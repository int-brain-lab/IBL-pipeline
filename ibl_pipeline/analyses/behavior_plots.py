# -*- coding: utf-8 -*-
"""
Created on Tue Sep 11 18:39:52 2018

@author: Miles
"""

#import psychofit as psy
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import scipy as sp
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
#from matplotlib.dates import MONDAY
from ibl_pipeline.analyses import psychofit as psy # https://github.com/cortex-lab/psychofit
import seaborn as sns
import pandas as pd
from IPython import embed as shell

def plot_psychometric(df, ax=None, color="black"):
    """
    Plots psychometric data for a given DataFrame of behavioural trials

    If the data contains more than six different contrasts (or > three per side)
    the data are fit with an erf function.  The x-axis is percent contrast and
    the y-axis is the proportion of 'rightward choices', i.e. trials where the
    subject turned the wheel clockwise to threshold.

    Example:
        df = alf.load_behaviour('2018-09-11_1_Mouse1', r'\\server\SubjectData')
        plot_psychometric(df)

    Args:
        df (DataFrame): DataFrame constructed from an ALF trials object.
        ax (Axes): Axes to plot to.  If None, a new figure is created.

    Returns:
        ax (Axes): The plot axes

    TODO Process three response types
    TODO Better titling of figure
    TODO Return fit pars if available
    TODO May as well reuse perf_per_contrast?
    TODO: Change plot_psychometric to split by side prob
    """

    contrastSet = np.sort(df['signedContrast'].unique())
    #choiceSet = np.array(set(df['choice']))
    nn = np.array([sum((df['signedContrast']==c) & (df['included']==True)) for c in contrastSet])
    pp = np.array([sum((df['signedContrast']==c) & (df['included']==True) & (df['choice']==1)) for c in contrastSet])/nn
    # ci = 1.96*np.sqrt(pp*(1-pp)/nn) # TODO: this is not the binomial CI

    def binom_interval(success, total, confint=0.95):
        quantile = (1 - confint) / 2
        lower = sp.stats.beta.ppf(quantile, success, total - success + 1)
        upper = sp.stats.beta.ppf(1 - quantile, success + 1, total - success)
        return (lower, upper)

    lowerci, upperci = binom_interval(pp*nn, nn)

    # graphics
    if ax is None:
        plt.figure()
        ax = plt.gca()
        # ax.cla()

    if contrastSet.size > 4:
        pars, L = psy.mle_fit_psycho(np.vstack((contrastSet,nn,pp)),
                                     P_model='erf_psycho_2gammas',
                                     parstart=np.array([np.mean(contrastSet), 3., 0.05, 0.05]),
                                     parmin=np.array([np.min(contrastSet), 10., 0., 0.]),
                                     parmax=np.array([np.max(contrastSet), 30., .4, .4]))


        ax.plot(np.arange(-100,100), psy.erf_psycho_2gammas( pars, np.arange(-100,100)) , color=color)

    # when there are not enough contrasts, still fit the same errorbar
    ax.errorbar(contrastSet, pp, pp-lowerci, upperci-pp, fmt='o', ecolor=color, mfc=color, mec="white")

    # Reduce the clutter
    ax.set_xticks([-100, -50, -25, -12.5, -6, 0, 6, 12.5, 25, 50, 100])
    ax.set_xticklabels(['-100', '', '', '', '', '0', '', '', '', '', '100'])
    ax.set_yticks([0, .5, 1])
    # Set the limits
    ax.set_xlim([-110, 110])
    ax.set_ylim([-0.03, 1.03])
    ax.set_xlabel('Contrast (%)')

    return ax

def plot_RTs(df, ax=None):
    """
    Scatter plot of responses, given a data frame of trials

    On the x-axis is trial number and on the y-axis, the response time in seconds,
    defined as the time between the go cue and a response being recorded.

    Example:
        df = alf.load_behaviour('2018-09-11_1_Mouse1', r'\\server\SubjectData')
        plot_RTs(df)

    Args:
        df (DataFrame): DataFrame constructed from an ALF trials object.
        ax (Axes): Axes to plot to.  If None, a new figure is created.

    Returns:
        ax (Axes): The plot axes
    """
    response_times = df['response_times']-df['goCue_times']
    if ax is None:
        plt.figure()
        ax = plt.gca()
    ax.cla()
    #print(np.array(df.index[df['choice']==1.].tolist())+1)
    leftWrong = (df['choice']==1) & (df['feedbackType']==-1)
    leftRight = (df['choice']==1) & (df['feedbackType']==1)
    rightWrong = (df['choice']==-1) & (df['feedbackType']==-1)
    rightRight = (df['choice']==-1) & (df['feedbackType']==1)
    ax.scatter(np.where(leftWrong)[0]+1, response_times[leftWrong], marker='<', c='r', alpha=0.5, label='Left incorrect')
    ax.scatter(np.where(leftRight)[0]+1, response_times[leftRight], marker='<', c='k', alpha=0.5, label='Left correct')
    ax.scatter(np.where(rightWrong)[0]+1, response_times[rightWrong], marker='>', c='r', alpha=0.5, label='Right incorrect')
    ax.scatter(np.where(rightRight)[0]+1, response_times[rightRight], marker='>', c='k', alpha=0.5, label='right correct')
    ax.set_yscale('log')

    # Hide the right and top spines
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    # Set bounds of axes lines
    #ax.spines['left'].set_bounds(0, 1)
    ax.spines['bottom'].set_bounds(0, len(df.index))
    # Explode out axes
    ax.spines['left'].set_position(('outward',10))
    ax.spines['bottom'].set_position(('outward',10))
    ax.set_xlabel('Trial')
    # Add second x
    #ax2 = ax.twiny()
    #plt.xlim([0 1])
    # Set the limits
    ax.set_ylim([min(response_times), max(response_times)+1])
    #plt.ylabel('Rightward choices')
    ax.legend(loc=0, frameon=True, fancybox=True)
    #plt.legend(bbox_to_anchor=(-.03, 1.02, 1., .102), loc=3, ncol=2, mode="expand", borderaxespad=0.)
    return ax

def perf_per_contrast(df):
    """
    Returns the proportion of 'rightward chocies', given a dataframe of trials.
    Each value corresponds to a contrast, going from highest contrast on the left
    to highest contrast on the right.

    Example:
        df = alf.load_behaviour('2018-09-11_1_Mouse1', r'\\server\SubjectData')
        pp = perf_per_contrast(df)
        >> [0., 0.2, 0., 0.8, 0.9]

    Args:
        df (DataFrame): DataFrame constructed from an ALF trials object.

    Returns:
        pp (numpy.Array): An array of the size (n,) where n is the number of
                          contrasts.  Each value is the proportion of
                          'rightward choices', i.e. trials where the subject
                          turned the wheel clockwise to threshold

    TODO: Optional contrast set input
    """
    contrastSet = (-100., -50., -25., -12.5, -0.06, 0., 0.06, 12.5, 25., 50., 100.)
    nn = np.array([sum((df['signedContrast']==c) & (df['included']==True)) for c in contrastSet], dtype=float)
    nn[nn == 0] = np.nan
    pp = np.array([sum((df['signedContrast']==c) & (df['included']==True) & (df['choice']==1)) for c in contrastSet])/nn
    return pp


def plot_perf_heatmap(dfs, ax=None):
    """
    Plots a heat-map of performance for each contrast per session.

    The x-axis is the contrast, going from highest contrast on the left to
    highest contrast on the right. The y-axis is the session number, ordered
    from most recent.

    Example:
        refs, date, seq = dat.list_exps('Mouse1', rootDir = r'\\server\Data')
        dfs = [load_behaviour(ref[0]) for ref in refs]
        plot_perf_heatmap(dfs)

    Args:
        dfs (List): List of data frames constructed from an ALF trials object.
        ax (Axes): Axes to plot to.  If None, a new figure is created.

    Returns:
        ax (Axes): The plot axes

    TODO: Optional contrast set input
    """

    if ax is None:
        plt.figure()
        ax = plt.gca()

    import copy; cmap=copy.copy(plt.get_cmap('bwr'))
    cmap.set_bad(color='grey')

    if not isinstance(dfs, (list,)):

        # Anne's version
        pp  = dfs.groupby(['signedContrast', 'days']).agg({'choice2':'mean'}).reset_index()
        pp2 = pp.pivot("signedContrast", "days",  "choice2").sort_values(by='signedContrast', ascending=False)
        sns.heatmap(pp2, linewidths=.5, ax=ax, vmin=0, vmax=1, cmap=cmap, cbar=True,
            cbar_kws={'label': 'Choose right (%)', 'shrink': 0.8, 'ticks': []})
        ax.set(ylabel="Contrast (%)")

        # fix the date axis
        dates  = dfs.date.unique()
        xpos   = np.arange(len(dates)) + 0.5 # the tick locations for each day
        xticks = [i for i, dt in enumerate(dates) if pd.to_datetime(dt).weekday() is 0]
        ax.set_xticks(np.array(xticks) + 0.5)

        xticklabels = [pd.to_datetime(dt).strftime('%b-%d') for i, dt in enumerate(dates) if pd.to_datetime(dt).weekday() is 0]
        ax.set_xticklabels(xticklabels)

        for item in ax.get_xticklabels():
            item.set_rotation(60)

    else:
        # Miles' version
        pp = np.vstack([perf_per_contrast(df) for df in dfs])
        pp = np.ma.array(pp, mask=np.isnan(pp))

        ax.imshow(pp, extent=[0, 1, 0, 1], cmap=cmap, vmin = 0, vmax = 1)
        ax.set_xticks([0.05, .5, 0.95])
        ax.set_xticklabels([-100, 0, 100])
        ax.set_yticks(list(range(0,pp.shape[0],-1)))
        ax.set_yticklabels(list(range(0,pp.shape[0],-1)))
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)

    # Set bounds of axes lines
    #ax.spines['left'].set_bounds(0, 1)
    #ax.spines['bottom'].set_bounds(0, len(df.index))
    # Explode out axes
    #ax.spines['left'].set_position(('outward',10))
    #ax.spines['bottom'].set_position(('outward',10))
    return ax

def plot_windowed_perf(df, window=10, ax=None):
    """
    Plots the windowed performance over a session.

    The x-axis is the trial number over which the trial window is centered.  The
    y-axis is the performance calculated across the window.

    Example:
        df = alf.load_behaviour('2018-09-11_1_Mouse1', r'\\server\SubjectData')
        plot_windowed_perf(df)

    Args:
        df (Data Frame): Data frame of trials for a given session
        window (int): Width of sliding window (number of trials)
        ax (Axes): Axes to plot to.  If None, a new figure is created

    Returns:
        ax (Axes): The plot axes

    TODO: Optional contrast set input
    TODO: Worth plotting only the easy contrast trials?
    TODO: Add second x-axis to show time
    TODO: Better description in doc string
    """
    if ax is None:
        plt.figure()
        ax = plt.gca()
    ax.cla()
    performance = df['feedbackType'].rolling(window).apply(lambda x: sum(x==1)/len(x))
    ax.plot(np.arange(0,len(df)), performance, 'k-')
    ax.plot([0,len(df)], [.5,.5], 'k:')
    # Set the limits
    ax.set_yticks([0, .25, .5, .75, 1])
    # Fix this ugly line
    ax.set_xticks([1] + list(range(100, np.around(len(df),-1),100)))
    ax.set_xlim([0, len(df)])
    ax.set_ylim([.4, 1.])
    # Hide the right and top spines
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    # Explode out axes
    ax.spines['left'].set_position(('outward',10))
    ax.spines['bottom'].set_position(('outward',10))
    return ax

def plot_learning(dfs, ax=None):
    """
    Plots the performance across the sessions for a data frame set.

    The x-axis is the session number.  The y-axis is the performance.

    Example:
        refs, date, seq = dat.list_exps('Mouse1', rootDir = r'\\server\Data')
        dfs = [load_behaviour(ref[0]) for ref in refs]
        plot_learning(dfs)

    Args:
        dfs (List): List of data frames constructed from an ALF trials object.
        ax (Axes): Axes to plot to.  If None, a new figure is created.

    Returns:
        ax (Axes): The plot axes
    """
    nn = np.array([sum((df['signedContrast']>=.5) &
                       (df['included']==True))
                   for df in dfs])
    pp = np.array([sum((df['signedContrast']>=.5) &
                       (df['feedbackType']==1) &
                       (df['included']==True))
                   for df in dfs]) / nn
    ci = 1.96*np.sqrt(pp*(1-pp)/nn)
    # graphics
    if ax is None:
        plt.figure()
        ax = plt.gca()
    ax.errorbar(np.arange(1,len(dfs)+1), pp, yerr=ci, capsize=2)
    ax.plot([1, len(dfs)+1], [.5, .5], 'k:')
    # Hide the right and top spines
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    # Reduce the clutter
    ax.set_xticks([1] + [i * 5 for i in range(1,round(len(dfs)/5))])
    ax.set_yticks([0, .25, .5, .75, 1.])
    # Set bounds of axes lines
    ax.spines['left'].set_bounds(.4, 1.)
    ax.spines['bottom'].set_bounds(1, len(dfs)+1)
    # Explode out axes
    #ax.spines['left'].set_position(('outward',10))
    ax.spines['bottom'].set_position(('outward',10))
    # Set the limits
    ax.set_xlim([0, len(dfs)+1])
    ax.set_ylim([.4, 1.])
    plt.xlabel('Session #')
    plt.ylabel('Performance at contrast >= 50%')
    return ax

def plot_repeats(dfs, max_repeats=4, normalize=False, ax=None):
    """
    Plots the number of correct trials for each attempt number (repeatNum) over
    each session.

    The x-axis is the session number.  The y-axis is the number (or proportion)
    of trials.

    Example:
        refs, date, seq = dat.list_exps('Mouse1', rootDir = r'\\server\Data')
        dfs = [load_behaviour(ref[0]) for ref in refs]
        plot_repeats(dfs, max_repeats=3, normalize=True)

    Args:
        dfs (List): List of data frames constructed from an ALF trials object.
        max_repeats (int): The attempt number at which to pool sucessful responses.
        normalize (bool): When true, the y-axis becomes the proportion of trials.
        ax (Axes): Axes to plot to.  If None, a new figure is created.

    Returns:
        ax (Axes): The plot axes
    """
    if ax is None:
        plt.figure()
        ax = plt.gca()
    ax.cla()
    counts = np.array([[sum(df['feedbackType'].where(df['repNum']==val)==1) if val < max_repeats
                        else sum(df['feedbackType'].where(df['repNum'] >= val)==1)
                        for val in range(1,max_repeats+1)]
                       for df in dfs])
    max_trials = max([sum(n) for n in counts])
    if normalize is True:
        counts= np.stack([n / sum(n) for n in counts])

    bar_l = range(1,counts.shape[0]+1)
    bottom = np.zeros_like(bar_l).astype('float')
    for i in range(0,max_repeats):
        if i == max_repeats-1:
            label = '> ' + str(max_repeats)
        else:
            label = str(i+1)
        ax.bar(bar_l, counts[:,i], bottom=bottom, width=1, label=label)
    ax.set_xticks([1] + [i * 5 for i in range(1,round(len(dfs)/5))])
    ax.set_xlim([.5,len(dfs)+.5])
    # Hide the right and top spines
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    if normalize is True:
        ax.set_ylim([0.,1.])
        ax.set_yticks([0, .25, .5, .75, 1.])
    else:
        #ax.set_yticks(range(0,max_trials,[25 if n < 250 else 50 for n in [max_trials]][0]))
        #ax.set_ylim(0,round(max_trials))
        pass
    ax.legend()
    return ax

def plot_choice_by_side(df, ax=None):
# TODO: Make look like fig 1F of Lak et al. 2018
    if ax is None:
        plt.figure()
        ax = plt.gca()
    ax.scatter(df['contrast'][df['choice']==1],
                df.index.values[df['choice']==1]+1,
                s=100, marker='_', c='r')
    ax.scatter(df['contrast'][df['choice']==-1],
                df.index.values[df['choice']==-1]+1,
                s=100, marker='_', c='b')
    return ax

def plot_choice_windowed(df, window=10, ax=None):
# TODO: Make look like fig 1F of Lak et al. 2018
    if ax is None:
        plt.figure()
        ax = plt.gca()
    # May require raw=False arg in older versions
    pctRight = df['choice'].rolling(window).apply(lambda x: sum(x==1)/len(x))
    ax.plot(pctRight, df.index.values+1)
    ax.plot((.5,.5), (1,len(df)), 'k--')
    ax.set_xlim([0,1.])
    return ax


def fix_date_axis(ax):
    # deal with date axis and make nice looking
    ax.xaxis_date()
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MONDAY))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b-%d'))
    for item in ax.get_xticklabels():
        item.set_rotation(60)


def plot_chronometric(df, ax, color):

    contrastSet = np.sort(df['signedContrast'].unique())
    df2 = df.groupby(['signedContrast']).agg({'rt':'median'}).reset_index()

    # get quantiles of the RT distribution
    def q1(x):
        return x.quantile(0.25)

    def q2(x):
        return x.quantile(0.75)
    f = {'rt': [q1,q2]}
    qlow = df.groupby(['signedContrast']).agg(f).reset_index()

    # sns.pointplot(x="signedContrast", y="rt", color=color, estimator=np.median, ci=None, join=True, data=df, ax=ax)
    ax.errorbar(df2['signedContrast'], df2['rt'], df2['rt']-qlow['rt']['q1'],
        qlow['rt']['q2']-df2['rt'], 'o-', color=color, mec="white")
    ax.set(xlabel="Contrast (%)", ylabel="RT (s)")
    ax.grid(True)
    ax.set_xticks([-100, -50, -25, -12.5, -6, 0, 6, 12.5, 25, 50, 100])
    ax.set_xticklabels(['-100', '', '', '', '', '0', '', '', '', '', '100'])
