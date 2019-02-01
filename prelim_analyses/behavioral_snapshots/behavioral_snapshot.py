# Anne Urai, CSHL, 2018
# see https://github.com/int-brain-lab/ibllib/tree/master/python/oneibl/examples

import time, re, datetime, os, glob
from datetime import timedelta
import seaborn as sns

## INITIALIZE A FEW THINGS
sns.set_style("darkgrid", {'xtick.bottom': True,'ytick.left': True, 'lines.markeredgewidth':0})
sns.set_context(context="paper")

import matplotlib as mpl
import matplotlib.pyplot as plt

import numpy as np
import pandas as pd
from IPython import embed as shell

## CONNECT TO datajoint
import datajoint as dj
from ibl_pipeline import reference, subject, action, acquisition, data, behavior

# loading and plotting functions
from define_paths import fig_path
from behavior_plots import *
from load_mouse_data_datajoint import * # this has all plotting functions
import psychofit as psy # https://github.com/cortex-lab/psychofit

# folder to save plots, from DataJoint
path = '/Figures_DataJoint_shortcuts/'

# ============================================= #
# START BIG OVERVIEW PLOT
# ============================================= #

# all mice that are alive, without those with undefined sex (i.e. example mice)
# restrict to animals that have trial data, weights and water logged
# subjects = pd.DataFrame.from_dict(((subject.Subject() - subject.Death() & 'sex!="U"')
#                                    & action.Weighing() & action.WaterAdministration() & behavior.TrialSet()
#                                    ).fetch(as_dict=True, order_by=['lab_name', 'subject_nickname']))
# print(subjects['subject_nickname'].unique())

allsubjects = pd.DataFrame.from_dict(((subject.Subject() - subject.Death()) & 'sex!="U"'
                                   & action.Weighing() & action.WaterAdministration() & behavior.TrialSet()
                                   ).fetch(as_dict=True, order_by=['lab_name', 'subject_nickname']))
users = allsubjects['lab_name'].unique()
print(users)

for lidx, lab in enumerate(users):

    # take mice from this lab only
    subjects = pd.DataFrame.from_dict(((subject.Subject() - subject.Death() & 'sex!="U"' & 'lab_name="%s"'%lab)
                                   & action.Weighing() & action.WaterAdministration() & behavior.TrialSet()
                                   ).fetch(as_dict=True, order_by=['subject_nickname']))

    for i, mouse in enumerate(subjects['subject_nickname']):

        # get all this mouse's data
        print(mouse)
        weight_water, baseline = get_water_weight(mouse, lab)
        behav = get_behavior(mouse, lab)

        if weight_water.empty or behav.empty:
            continue

        # ============================================= #
        # GENERAL METADATA, use DJ variable names
        # ============================================= #

        # MAKE THE FIGURE, divide subplots using gridspec
        fig, axes = plt.subplots(ncols=5, nrows=4, constrained_layout=False,
                                 gridspec_kw=dict(width_ratios=[2, 2, 1, 1, 1], height_ratios=[1, 1, 1, 1]),
                                 figsize=(11.69, 8.27))
        sns.set_palette("colorblind")  # palette for water types

        fig.suptitle('Mouse %s (%s), born %s, user %s (%s), %s' %(subjects['subject_nickname'][i],
         subjects['sex'][i], subjects['subject_birth_date'][i],
         subjects['responsible_user'][i], subjects['lab_name'][i],
         subjects['subject_description'][i]))

        # ============================================= #
        # WEIGHT CURVE AND WATER INTAKE
        # ============================================= #

        # determine x limits
        xlims = [weight_water.date.min()-timedelta(days=2), weight_water.date.max()+timedelta(days=2)]
        plot_water_weight_curve(weight_water, baseline, axes[0,0], xlims)

        # ============================================= #
        # TRIAL COUNTS AND SESSION DURATION
        # ============================================= #

        if behav.empty:
            continue

        plot_trialcounts_sessionlength(behav, axes[1,0], xlims)

        # ============================================= #
        # PERFORMANCE AND MEDIAN RT
        # ============================================= #

        plot_performance_rt(behav, axes[2,0], xlims)

        # ============================================= #
        # CONTRAST/CHOICE HEATMAP
        # ============================================= #

        plot_contrast_heatmap(behav, axes[3,0])

        # ============================================= #
        # PSYCHOMETRIC FUNCTION FITS OVER TIME
        # ============================================= #

        # fit psychfunc on choice fraction, rather than identity
        pars = behav.groupby(['date', 'probabilityLeft']).apply(fit_psychfunc).reset_index()

        # TODO: HOW TO SAVE THIS IN A DJ TABLE FOR LATER?
        parsdict = {'threshold': r'Threshold $(\sigma)$', 'bias': r'Bias $(\mu)$',
            'lapselow': r'Lapse low $(\gamma)$', 'lapsehigh': r'Lapse high $(\lambda)$'}
        ylims = [[-5, 105], [-105, 105], [-0.05, 1.05], [-0.05, 1.05]]
        yticks = [[0, 19, 100], [-100, -16, 0, 16, 100], [-0, 0.2, 0.5, 1], [-0, 0.2, 0.5, 1]]

        # pick a good-looking diverging colormap with black in the middle
        cmap = sns.diverging_palette(20, 220, n=len(behav['probabilityLeft'].unique()), center="dark")
        if len(behav['probabilityLeft'].unique()) == 1:
            cmap = "gist_gray"
        sns.set_palette(cmap)

        # plot the fitted parameters
        for pidx, (var, labelname) in enumerate(parsdict.items()):
            ax = axes[pidx,1]
            sns.lineplot(x="date", y=var, marker='o', hue="probabilityLeft", linestyle='', lw=0,
                palette=cmap, data=pars, legend=None, ax=ax)
            ax.set(xlabel='', ylabel=labelname, ylim=ylims[pidx],
                yticks=yticks[pidx],
                xlim=[behav.date.min()-timedelta(days=1), behav.date.max()+timedelta(days=1)])

            fix_date_axis(ax)
            if pidx == 0:
                ax.set(title=r'$\gamma + (1 -\gamma-\lambda)  (erf(\frac{x-\mu}{\sigma} + 1)/2$')

        # ============================================= #
        # LAST THREE SESSIONS
        # ============================================= #

        didx = 1
        sorteddays = behav['days'].sort_values(ascending=True).unique()
        for day in behav['days'].unique():

            # use only the last three days
            if len(sorteddays) >= 3:
                if day < sorteddays[-3]:
                    continue

            # grab only that day
            dat = behav.loc[behav['days'] == day, :]
            print(dat['date'].unique())
            didx += 1

            # colormap for the asymmetric blocks
            cmap = sns.diverging_palette(20, 220, n=len(dat['probabilityLeft'].unique()), center="dark")
            if len(dat['probabilityLeft'].unique()) == 1:
                cmap = [np.array([0,0,0,1])]

            # PSYCHOMETRIC FUNCTION
            ax = axes[0, didx]
            for ix, probLeft in enumerate(dat['probabilityLeft'].sort_values().unique()):
                plot_psychometric(dat.loc[dat['probabilityLeft'] == probLeft, :], ax=ax, color=cmap[ix])
            ax.set(xlabel="Contrast (%)", ylabel="Choose right (%)")
            ax.set(title=pd.to_datetime(dat['start_time'].unique()[0]).strftime('%b-%d, %A'))

            # CHRONOMETRIC FUNCTION
            ax = axes[1, didx]
            for ix, probLeft in enumerate(dat['probabilityLeft'].sort_values().unique()):
                plot_chronometric(dat.loc[dat['probabilityLeft'] == probLeft, :], ax, cmap[ix])
            ax.set(ylim=[0.1,1.5], yticks=[0.1, 1.5])
            ax.set_yscale("log")
            ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda y,pos:
                ('{{:.{:1d}f}}'.format(int(np.maximum(-np.log10(y),0)))).format(y)))

            # RTS THROUGHOUT SESSION
            ax = axes[2, didx]
            sns.scatterplot(x='trial', y='rt', style='correct', hue='correct',
                palette={1:"#009E73", 0:"#D55E00"}, # from https://github.com/matplotlib/matplotlib/blob/master/lib/matplotlib/mpl-data/stylelib/seaborn-colorblind.mplstyle
                markers={1:'o', 0:'X'}, s=10, edgecolors='face',
                alpha=.5, data=dat, ax=ax, legend=False)
            # running median overlaid
            sns.lineplot(x='trial', y='rt', color='black', ci=None,
                data=dat[['trial', 'rt']].rolling(10).median(), ax=ax)
            ax.set(xlabel="Trial number", ylabel="RT (s)", ylim=[0.02, 60])
            ax.set_yscale("log")
            ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda y,pos:
                ('{{:.{:1d}f}}'.format(int(np.maximum(-np.log10(y),0)))).format(y)))

            # ============================ #
            # WHEEL ANALYSIS - TODO
            # ============================ #

        # clean up layout
        for j in range(3):
            axes[j,3].set(ylabel='')
            axes[j,4].set(ylabel='')

        # ============================================= #
        # SAVE WHETHER THERE ARE DATA OR NOT!
        # ============================================= #

        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        fig.savefig(os.path.join(path + '%s_%s_mouse_%s_snapshot.pdf' % (datetime.datetime.now().strftime("%Y-%m-%d"),
                                                                   subjects.loc[subjects['subject_nickname'] == mouse]['lab_name'].item(),
                                                                   mouse)))

        fig.savefig(os.path.join(path + '%s_%s_mouse_%s_snapshot.png' % (datetime.datetime.now().strftime("%Y-%m-%d"),
                                                                         subjects.loc[
                                                                             subjects['subject_nickname'] == mouse][
                                                                             'lab_name'].item(),
                                                                         mouse)))
        plt.close(fig)
