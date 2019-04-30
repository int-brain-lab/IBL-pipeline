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
from ibl_pipeline.analyses import behavior as behavior_analysis
from ibl_pipeline.utils import psychofit as psy

# loading and plotting functions
from behavior_plots import *
from load_mouse_data_datajoint import * # this has all plotting functions

# folder to save plots, from DataJoint
path = '/Figures_DataJoint_shortcuts/'
datapath = '/Data_shortcut/'

# ============================================= #
# START BIG OVERVIEW PLOT
# ============================================= #

# all mice that are alive, without those with undefined sex (i.e. example mice)
# restrict to animals that have trial data, weights and water logged
allsubjects = pd.DataFrame.from_dict(
    ((subject.Subject - subject.Death) * subject.SubjectLab & 'sex!="U"' &
     action.Weighing & action.WaterAdministration).fetch(
         as_dict=True, order_by=['lab_name', 'subject_nickname']))

if allsubjects.empty:
    raise ValueError('DataJoint seems to be down, please try again later')

users = allsubjects['lab_name'].unique()
print(users)

for lidx, lab in enumerate(users):

    # take mice from this lab only
    subjects = allsubjects[allsubjects['lab_name'].str.contains(lab)].reset_index()

    for i, mouse in enumerate(subjects['subject_nickname']):

        # get all this mouse's data
        print(mouse)
        weight_water, baseline = get_water_weight(mouse, lab)

        # ============================================= #
        # GENERAL METADATA, use DJ variable names
        # ============================================= #

        # MAKE THE FIGURE, divide subplots using gridspec
        fig, axes = plt.subplots(ncols=5, nrows=4,
                                 gridspec_kw=dict(width_ratios=[2, 2, 1, 1, 1], height_ratios=[1, 1, 1, 1]),
                                 figsize=(13.69, 8.27))
        sns.set_palette("colorblind")  # palette for water types

        fig.suptitle('Mouse %s (%s), born %s, %s, %s' %(subjects['subject_nickname'][i],
         subjects['sex'][i], subjects['subject_birth_date'][i], subjects['lab_name'][i],
         subjects['subject_description'][i]))

        # ============================================= #
        # WEIGHT CURVE AND WATER INTAKE
        # ============================================= #

        # determine x limits
        xlims = [weight_water.date.min()-timedelta(days=2), weight_water.date.max()+timedelta(days=2)]
        plot_water_weight_curve(weight_water, baseline, axes[0,0], xlims)

        # ============================================= #
        # check whether the subject is trained based the the lastest session
        # ============================================= #

        subj = subject.Subject & 'subject_nickname="{}"'.format(mouse) & \
            (subject.SubjectLab & 'lab_name="{}"'.format(lab))
        subj_sessions = behavior.TrialSet & subj
        if not len(subj_sessions):
            continue

        last_session = subj.aggr(
            behavior.TrialSet, session_start_time='max(session_start_time)')
        if not len(last_session):
            traing_status = 'training in progress'
        else:
            training_status = \
                (behavior_analysis.SessionTrainingStatus & last_session).fetch1(
                    'training_status')
        if training_status in ['trained', 'ready for ephys']:
            first_trained_session = subj.aggr(
                behavior_analysis.SessionTrainingStatus &
                'training_status="trained"',
                first_trained='min(session_start_time)')
            first_trained_session_time = first_trained_session.fetch1(
                'first_trained')
            # convert to timestamp
            trained_date = pd.DatetimeIndex([first_trained_session_time])[0]

            if training_status == 'ready for ephys':
                first_biased_session = subj.aggr(
                    behavior_analysis.SessionTrainingStatus &
                    'training_status="ready for ephys"',
                    first_biased='min(session_start_time)')
                first_biased_session_time = first_biased_session.fetch1(
                    'first_biased')
                biased_date = pd.DatetimeIndex([first_biased_session_time])[0]

        # ============================================= #
        # TRIAL COUNTS AND SESSION DURATION
        # ============================================= #

        plot_trialcounts_sessionlength(mouse, lab, axes[1, 0], xlims)
        if training_status == 'trained':
            # indicate date at which the animal is 'trained'
            axes[1, 0].axvline(trained_date, color="orange")
        elif training_status == 'ready for ephys':
            # indicate date at which the animal is 'ready for ephys'
            axes[1, 0].axvline(trained_date, color="orange")
            axes[1, 0].axvline(biased_date, color="forestgreen")

        # ============================================= #
        # PERFORMANCE AND MEDIAN RT
        # ==== ========================================= #

        plot_performance_rt(mouse, lab, axes[2, 0], xlims)
        if training_status == 'trained':
            # indicate date at which the animal is 'trained'
            axes[2, 0].axvline(trained_date, color="orange")
        elif training_status == 'ready for ephys':
            # indicate date at which the animal is 'ready for ephys'
            axes[2, 0].axvline(trained_date, color="orange")
            axes[2, 0].axvline(biased_date, color="forestgreen")

        # ============================================= #
        # CONTRAST/CHOICE HEATMAP
        # ============================================= #

        plot_contrast_heatmap(mouse, lab, axes[3,0], xlims)

        # ============================================= #
        # PSYCHOMETRIC FUNCTION FITS OVER TIME
        # ============================================= #

        # grab values from precomputed
        pars = pd.DataFrame((behavior_analysis.BehavioralSummaryByDate.PsychResults * subject.Subject * subject.SubjectLab &
                'subject_nickname="%s"'%mouse & 'lab_name="%s"'%lab).fetch(as_dict=True))

        # link to their descriptions
        ylabels = {'threshold': r'Threshold $(\sigma)$', 'bias': r'Bias $(\mu)$',
            'lapse_low': r'Lapse low $(\gamma)$', 'lapse_high': r'Lapse high $(\lambda)$'}
        ylims = [[-5, 105], [-105, 105], [-0.05, 1.05], [-0.05, 1.05]]
        yticks = [[0, 19, 100], [-100, -16, 0, 16, 100], [-0, 0.2, 0.5, 1], [-0, 0.2, 0.5, 1]]

        # pick a good-looking diverging colormap with black in the middle
        cmap = sns.diverging_palette(20, 220, n=3, center="dark")
        left_blocks = pars['prob_left_block'].unique()
        if len(left_blocks) == 1:
            cmap = "gist_gray"

        sns.set_palette(cmap)

        # plot the fitted parameters
        for pidx, (var, labelname) in enumerate(ylabels.items()):
            ax = axes[pidx,1]

            sns.lineplot(x="session_date", y=var, marker='o', hue="prob_left_block",
                hue_order=[1, 0, 2], linestyle='', lw=0,
                palette=cmap, data=pars, legend=None, ax=ax)
            ax.set(xlabel='', ylabel=labelname, ylim=ylims[pidx],
                yticks=yticks[pidx],
                xlim=[pars.session_date.min()-timedelta(days=1), pars.session_date.max()+timedelta(days=1)])

            fix_date_axis(ax)
            if pidx == 0:
                ax.set(title=r'$\gamma + (1 -\gamma-\lambda)  (erf(\frac{x-\mu}{\sigma} + 1)/2$')

            if training_status == 'trained':
                # indicate date at which the animal is 'trained'
                ax.axvline(trained_date, color="orange")
            elif training_status == 'ready for ephys':
                # indicate date at which the animal is 'ready for ephys'
                ax.axvline(trained_date, color="orange")
                ax.axvline(biased_date, color="forestgreen")

        # ============================================= #
        # LAST THREE SESSIONS
        # ============================================= #

        behav = get_behavior(mouse, lab)

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
            cmap = sns.diverging_palette(20, 220, n=3, center="dark")
            if len(dat['probabilityLeft_block'].unique()) == 1:
                cmap = [np.array([0,0,0,1])]

            # PSYCHOMETRIC FUNCTION
            ax = axes[0, didx]
            for ix, probLeft in enumerate(dat['probabilityLeft_block'].sort_values().unique()):
                plot_psychometric(dat.loc[dat['probabilityLeft_block'] == probLeft, :], ax=ax, color=cmap[ix])
            ax.set(xlabel="Contrast (%)", ylabel="Choose right (%)")
            ax.set(title=pd.to_datetime(dat['start_time'].unique()[0]).strftime('%b-%d, %A'))

            # CHRONOMETRIC FUNCTION
            ax = axes[1, didx]
            for ix, probLeft in enumerate(dat['probabilityLeft_block'].sort_values().unique()):
                plot_chronometric(dat.loc[dat['probabilityLeft_block'] == probLeft, :], ax, cmap[ix])
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

        # get most recent session_date for the naming of the plot
        subj_with_last_session = subj.aggr(
            behavior.TrialSet, last_behavior='max(session_start_time)'
        )

        last_behavior_time = subj_with_last_session.fetch('last_behavior')
        subj_with_last_weighing_water = subj.aggr(
            action.Weighing * action.WaterAdministration,
            last_weighing='max(weighing_time)',
            last_water='max(administration_time)'
        )
        last_weighing_time, last_water_time = \
            subj_with_last_weighing_water.fetch1(
                'last_weighing', 'last_water')

        if last_behavior_time.size:
            last_time = last_behavior_time[0]
        else:
            last_time = max([last_weighing_time, last_water_time])

        last_date = last_time.date().strftime("%Y-%m-%d")


        fig.savefig(os.path.join(path + '%s_%s_mouse_%s_snapshot.pdf' % (last_date,
                                                                   subjects.loc[subjects['subject_nickname'] == mouse]['lab_name'].item(),
                                                                   mouse)))

        fig.savefig(os.path.join(path + '%s_%s_mouse_%s_snapshot.png' % (last_date,
                                                                         subjects.loc[
                                                                             subjects['subject_nickname'] == mouse][
                                                                             'lab_name'].item(),
                                                                         mouse)))
        plt.close(fig)
