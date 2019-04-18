# -*- coding: utf-8 -*-
"""
Created on Tue Sep 11 18:39:52 2018

@author: Miles
"""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import scipy as sp
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import timedelta
import seaborn as sns
import pandas as pd
from IPython import embed as shell

# import from same parent folder
import datajoint as dj
from ibl_pipeline import reference, subject, action, acquisition, data, behavior
from ibl_pipeline.utils import psychofit as psy # https://github.com/cortex-lab/psychofit
from ibl_pipeline.analyses import behavior as behavior_analysis
from load_mouse_data_datajoint import * # this has all plotting functions

from mpl_toolkits.axes_grid1.inset_locator import inset_axes

def plot_water_weight_curve(weight_water, baseline, ax, xlims):

    weight_water.loc[weight_water['adlib'] == 1, 'water_administered'] = 1

    # ################################################### #
    # use pandas plot for a stacked bar - water types
    # ################################################### #

    wa_unstacked = weight_water.pivot_table(index='days',
        columns='water_type', values='water_administered', aggfunc='sum').reset_index()

    # shorten names for legend
    wa_unstacked.columns = wa_unstacked.columns.str.replace("Water", "Wa")
    wa_unstacked.columns = wa_unstacked.columns.str.replace("Sucrose", "Sucr")
    wa_unstacked.columns = wa_unstacked.columns.str.replace("Citric Acid", "CA")
    wa_unstacked.columns = wa_unstacked.columns.str.replace("Hydrogel", "Hdrg")

    # only one name for CA - merge
    wa_unstacked.columns = wa_unstacked.columns.str.replace("CA Wa 2%", "Wa 2% CA")

    # if duplicate, merge
    colnames = list(wa_unstacked)
    if colnames.count('Wa 2% CA') > 1:
        tmp = wa_unstacked[['Wa 2% CA']].sum(axis=1).copy()
        wa_unstacked = wa_unstacked.drop('Wa 2% CA', 1)
        wa_unstacked['Wa 2% CA'] = tmp

    # order in a fixed way
    wa_unstacked = wa_unstacked.reindex(columns=['days', 'Wa 10% Sucr',
       'Wa', 'Wa 2% CA', 'Hdrg', 'Wa 15% Sucr'])

    # https://stackoverflow.com/questions/44250445/pandas-bar-plot-with-continuous-x-axis
    plotvar       = wa_unstacked.copy()
    plotvar.index = plotvar.days
    plotvar       = plotvar.reindex(np.arange(weight_water.days.min(), weight_water.days.max()+1))
    plotvar.drop(columns='days', inplace=True)

    # sort the columns by possible water types
    plotvar.plot(kind='bar', style='.', stacked=True, ax=ax, edgecolor="none")
    l = ax.legend(loc='lower left', prop={'size': 'xx-small'},
        bbox_to_anchor=(0., 1.02, 1., .102),
        ncol=2, mode="expand", borderaxespad=0., frameon=False)
    l.set_title('')
    ax.set(ylabel="Water intake (mL)", xlabel='',
        xlim=[weight_water.days.min()-2, weight_water.days.max()+2])
    ax.yaxis.label.set_color("#0072B2")

    # ################################################### #
    # OVERLAY THE WEIGHT CURVE
    # ################################################### #

    righty = ax.twinx()
    weight_water2 = weight_water.groupby('days').mean().reset_index()
    weight_water2 = weight_water2.dropna(subset=['weight'])

    # plot weight curve
    sns.lineplot(x=weight_water2.days, y=weight_water2.weight, ax=righty, color='.15', marker='o')

    # show the start of each water restriction
    sns.scatterplot(x=baseline.day_start, y=baseline.reference_weight, ax=righty, marker='D',
                    facecolor='white', edgecolor='black', s=10, zorder=100, legend=False)

    for d in range(len(baseline)):
        # add a line for 85% of baseline weight
        righty.plot((baseline.day_start[d], baseline.day_end[d]),
                    (baseline.reference_weight[d]*0.85, baseline.reference_weight[d]*0.85), 'k--', linewidth=0.5)
        # another line for 75% baseline weight
        righty.plot((baseline.day_start[d], baseline.day_end[d]),
                    (baseline.reference_weight[d]*0.75, baseline.reference_weight[d]*0.75), 'k-.', linewidth=0.5)

    righty.grid(False)
    righty.set(xlabel='', ylabel="Weight (g)",
        xlim=[weight_water.days.min()-2, weight_water.days.max()+2])

    # correct the ticks to show dates, not days
    # also indicate Mondays by grid lines
    ax.set_xticks([weight_water.days[i] for i, dt in enumerate(weight_water.date) if dt.weekday() is 0])
    ax.set_xticklabels([weight_water.date[i].strftime('%b-%d') for i, dt in enumerate(weight_water.date) if dt.weekday() is 0])
    for item in ax.get_xticklabels():
        item.set_rotation(60)

def plot_trialcounts_sessionlength(mouse, lab, ax, xlims):

    # GET THE NUMBER OF TRIALS PER DAY
    n_trials = pd.DataFrame((behavior.TrialSet.proj(session_date='DATE(session_start_time)') * \
        behavior.TrialSet * subject.Subject * subject.SubjectLab & 'subject_nickname="%s"'%mouse & 'lab_name="%s"'%lab).proj('session_date', 'n_trials').fetch(as_dict=True))
    n_trials = n_trials.groupby(['session_date'])['n_trials'].sum().reset_index()

    sns.lineplot(x="session_date", y="n_trials", marker='o', color=".15", data=n_trials, ax=ax)
    ax.set(xlabel='', ylabel="Trial count", xlim=xlims)

    # GET SESSION DURATION PER DAY
    duration = pd.DataFrame((acquisition.Session * subject.Subject * subject.SubjectLab & 'subject_nickname="%s"'%mouse & 'lab_name="%s"'%lab).proj(
        session_duration='TIMEDIFF(session_end_time, session_start_time)', session_date='DATE(session_start_time)').proj('session_date', 'session_duration').fetch())
    duration['session_duration_minutes'] = duration.session_duration.dt.total_seconds() / 60   # convert to minutes                      

    righty = ax.twinx()
    sns.lineplot(x="session_date", y="session_duration_minutes", marker='o', color="firebrick", data=duration, ax=righty)
    righty.yaxis.label.set_color("firebrick")
    righty.tick_params(axis='y', colors='firebrick')
    righty.set(xlabel='', ylabel="Session (min)", ylim=[0,90], xlim=xlims)

    righty.grid(False)
    fix_date_axis(righty)
    fix_date_axis(ax)

def plot_performance_rt(mouse, lab, ax, xlims):

    # performance on easy contrasts
    behav = pd.DataFrame((behavior_analysis.BehavioralSummaryByDate * subject.Subject * subject.SubjectLab &
       'subject_nickname="%s"'%mouse & 'lab_name="%s"'%lab).proj('session_date', 'performance_easy').fetch(as_dict=True, order_by='session_date'))
    sns.lineplot(x="session_date", y="performance_easy", marker='o', color=".15", data=behav, ax=ax)
    ax.set(xlabel='', ylabel="Performance (easy trials)",
        xlim=xlims, yticks=[0.5, 0.75, 1], ylim=[0.4, 1.01])

    # RTs on right y-axis
    rt = pd.DataFrame(((behavior_analysis.BehavioralSummaryByDate.ReactionTime * subject.Subject * subject.SubjectLab &
       'subject_nickname="%s"'%mouse & 'lab_name="%s"'%lab)).proj('session_date', 'reaction_time').fetch(as_dict=True, order_by='session_date'))

    righty = ax.twinx()
    # TODO: add median RT of the session (now only returns per contrast)
    # sns.lineplot(x="session_date", y="reaction_time", marker='o', color="firebrick", data=rt, ax=righty)

    # layout
    righty.yaxis.label.set_color("firebrick")
    righty.tick_params(axis='y', colors='firebrick')
    righty.set(xlabel='', ylabel="RT (s)", ylim=[0.1,10], xlim=xlims)
    righty.set_yscale("log")

    righty.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda y,
        pos: ('{{:.{:1d}f}}'.format(int(np.maximum(-np.log10(y),0)))).format(y)))
    righty.grid(False)
    fix_date_axis(righty)
    fix_date_axis(ax)

def plot_contrast_heatmap(mouse, lab, ax, xlims):

    import copy; cmap = copy.copy(plt.get_cmap('vlag'))
    cmap.set_bad(color="w") # remove rectangles without data, should be white

    session_date, signed_contrasts, prob_choose_right, prob_left_block = (behavior_analysis.BehavioralSummaryByDate.PsychResults * subject.Subject * subject.SubjectLab &
       'subject_nickname="%s"'%mouse & 'lab_name="%s"'%lab).proj('signed_contrasts', 'prob_choose_right', 'session_date', 'prob_left_block').fetch(\
       'session_date', 'signed_contrasts', 'prob_choose_right', 'prob_left_block')

    # reshape this to a heatmap format
    prob_left_block2 = signed_contrasts.copy()
    for i, date in enumerate(session_date):
        session_date[i] = np.repeat(date, len(signed_contrasts[i]))
        prob_left_block2[i] = np.repeat(prob_left_block[i], len(signed_contrasts[i]))

    result = pd.DataFrame({'session_date':np.concatenate(session_date), 
        'signed_contrasts':np.concatenate(signed_contrasts), 'prob_choose_right':np.concatenate(prob_choose_right), 
        'prob_left_block':np.concatenate(prob_left_block2)})

    # only use the unbiased block for now
    result = result[result.prob_left_block == 0]

    pp2 = result.pivot("signed_contrasts", "session_date", "prob_choose_right").sort_values(by='signed_contrasts', ascending=False)
    pp2 = pp2.reindex(sorted(np.round_(result.signed_contrasts.unique() * 100, decimals=1)))

    # evenly spaced date axis
    x = pd.date_range(xlims[0], xlims[1]).to_pydatetime()
    pp2 = pp2.reindex(columns=x)

    # inset axes for colorbar, to the right of plot
    axins1 = inset_axes(ax, width="5%", height="90%", loc='right',
    bbox_to_anchor=(0.15, 0., 1, 1), bbox_transform=ax.transAxes, borderpad=0,)

    # now heatmap
    sns.heatmap(pp2, linewidths=0, ax=ax, vmin=0, vmax=1, cmap=cmap, cbar=True,
    cbar_ax=axins1, cbar_kws={'label': 'Choose right (%)', 'shrink': 0.8, 'ticks': []})
    ax.set(ylabel="Contrast (%)", xlabel='')
    fix_date_axis(ax)

def fit_psychfunc(df):
    choicedat = df.groupby('signedContrast').agg({'trial':'count', 'choice2':'mean'}).reset_index()
    pars, L = psy.mle_fit_psycho(choicedat.values.transpose(), P_model='erf_psycho_2gammas',
        parstart=np.array([choicedat['signedContrast'].mean(), 20., 0.05, 0.05]),
        parmin=np.array([choicedat['signedContrast'].min(), 0., 0., 0.]),
        parmax=np.array([choicedat['signedContrast'].max(), 100., 1, 1]))
    df2 = {'bias':pars[0],'threshold':pars[1], 'lapselow':pars[2], 'lapsehigh':pars[3]}

    return pd.DataFrame(df2, index=[0])

def plot_psychometric(df, color='black', ax=None, **kwargs):
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
    """

    if len(df['signedContrast'].unique()) > 4:
        df2 = df.groupby(['signedContrast']).agg({'choice':'count', 'choice2':'mean'}).reset_index()
        df2.rename(columns={"choice2": "fraction", "choice": "ntrials"}, inplace=True)

        pars, L = psy.mle_fit_psycho(df2.transpose().values, # extract the data from the df
                                     P_model='erf_psycho_2gammas',
                                     parstart=np.array([df2['signedContrast'].mean(), 20., 0.05, 0.05]),
                                     parmin=np.array([df2['signedContrast'].min(), 0., 0., 0.]),
                                     parmax=np.array([df2['signedContrast'].max(), 100., 1, 1]))
        sns.lineplot(np.arange(-100,100), psy.erf_psycho_2gammas( pars, np.arange(-100,100)), color=color, ax=ax)

    # plot datapoints on top
    sns.lineplot(x='signedContrast', y='choice2', err_style="bars", linewidth=0, linestyle='None', mew=0.5,
        marker='.', ci=68, data=df, color=color, ax=ax)

    # Reduce the clutter
    ax.set_xticks([-100, -50, 0, 50, 100])
    ax.set_xticklabels(['-100', '-50', '0', '50', '100'])
    ax.set_yticks([0, .5, 1])
    # Set the limits
    ax.set_xlim([-110, 110])
    ax.set_ylim([-0.03, 1.03])
    ax.set_xlabel('Contrast (%)')

    return ax

def plot_chronometric(df, ax, color):

    sns.lineplot(x='signedContrast', y='rt', err_style="bars", mew=0.5,
        estimator=np.median, marker='.', ci=68, data=df, color=color, ax=ax)
    ax.set(xlabel="Contrast (%)", ylabel="RT (s)")
    ax.grid(True)
    ax.set_xticks([-100, -50, 0, 50, 100])
    ax.set_xticklabels(['-100', '-50', '0', '50', '100'])


def fix_date_axis(ax):
    # deal with date axis and make nice looking
    ax.xaxis_date()
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MONDAY))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b-%d'))
    for item in ax.get_xticklabels():
        item.set_rotation(60)
