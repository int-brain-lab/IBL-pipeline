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
from ibl_pipeline.utils import psychofit as psy # https://github.com/cortex-lab/psychofit

# loading and plotting functions
from behavior_plots import *
from load_mouse_data_datajoint import * # this has all plotting functions

# folder to save plots, from DataJoint
path = '/Figures_DataJoint_shortcuts/'

# ============================================= #
# START BIG OVERVIEW PLOT
# ============================================= #

allsubjects = pd.DataFrame.from_dict(
	((subject.Subject - subject.Death) * subject.SubjectLab & 'sex!="U"' &
	 action.Weighing & action.WaterAdministration).fetch(
		as_dict=True, order_by=['lab_name', 'subject_nickname'])
)

if allsubjects.empty:
	raise ValueError('DataJoint seems to be down, please try again later')

users = allsubjects['lab_name'].unique()
print(users)

# from guido: make sure max 5 mice are plotted on a single figure
sub_batch_size = 5

# keep track of when each mouse is trained
training_review = pd.DataFrame([])

for lidx, lab in enumerate(users):

	# take mice from this lab only
	subjects = pd.DataFrame.from_dict(
		((subject.Subject - subject.Death) * subject.SubjectLab & 'sex!="U"' &
		 'lab_name="%s"'%lab & action.Weighing & action.WaterAdministration).fetch(
			 as_dict=True, order_by=['subject_nickname']))

	# group by batches: mice that were born on the same day
	batches = subjects.subject_birth_date.unique()

	for birth_date in batches:

		mice = subjects.loc[subjects['subject_birth_date'] == birth_date]['subject_nickname'].unique()
		print(mice)

		# TODO: need a better way to define batches! litter mates?
		for sub_batch in np.arange(0,len(mice),sub_batch_size):

			fig  = plt.figure(figsize=(13.69, 8.27), constrained_layout=True)
			axes = []
			sns.set_palette("colorblind") # palette for water types

			for i, mouse in enumerate(mice[sub_batch:sub_batch+sub_batch_size]):
				print(mouse)

				# WEIGHT CURVE AND WATER INTAKE
				t = time.time()
				weight_water, baseline = get_water_weight(mouse, lab)

				# determine x limits
				xlims = [weight_water.date.min() - timedelta(days=2), weight_water.date.max() + timedelta(days=2)]
				ax = plt.subplot2grid((4, sub_batch_size), (0, i))
				plot_water_weight_curve(weight_water, baseline, ax, xlims)
				axes.append(ax)

				# check whether the subject is trained based the the lastest session
				subj = subject.Subject & 'subject_nickname="{}"'.format(mouse)
				last_session = subj.aggr(
					behavior.TrialSet, session_start_time='max(session_start_time)')

				if not len(last_session):
					training_status = 'traing in progress'
				else:
					training_status = \
						(behavior_analysis.SessionTrainingStatus & last_session).fetch1(
							'training_status')

				days_intraining = (subj * behavior.TrialSet.proj(session_date='DATE(session_start_time)')).fetch('session_start_time')

				if training_status in ['trained', 'ready for ephys']:
					first_trained_session = subj.aggr(
						behavior_analysis.SessionTrainingStatus &
						'training_status="trained"',
						first_trained='min(session_start_time)')
					first_trained_session_time = first_trained_session.fetch1(
						'first_trained')
					# convert to timestamp
					trained_date = pd.DatetimeIndex([first_trained_session_time])[0]

					# how many days to training?
					days_to_trained = sum(days_intraining < trained_date.to_pydatetime())

					if training_status == 'ready for ephys':
						first_biased_session = subj.aggr(
							behavior_analysis.SessionTrainingStatus &
							'training_status="ready for ephys"',
							first_biased='min(session_start_time)')
						first_biased_session_time = first_biased_session.fetch1(
							'first_biased')
						# convert to timestamp
						biased_date = pd.DatetimeIndex([first_biased_session_time])[0]

						# how many days from trained to biased?
						days_to_biased = sum(
							(days_intraining < biased_date.to_pydatetime()) &
							(days_intraining > trained_date.to_pydatetime())
						)

					else:
						days_to_biased = np.nan
				else:
						days_to_trained = np.nan
						days_to_biased = np.nan

				# keep track
				training_review = training_review.append(
					pd.DataFrame({
						'subject_nickname': mouse,
						'lab_name': lab,
						'training_status': training_status,
						'days_to_trained': days_to_trained,
						'days_to_biased': days_to_biased},
						index=[0]),
					ignore_index=True)

				# MAIN PLOTS
				if len(last_session):
					ax = plt.subplot2grid((4, sub_batch_size), (1, i))
					if training_status == 'trained':
					# indicate date at which the animal is 'trained'
						# shell()
						ax.axvline(trained_date, color="orange")
					elif training_status == 'ready for ephys':
					# indicate date at which the animal is 'ready for ephys'
						ax.axvline(trained_date, color="orange")
						ax.axvline(biased_date, color="forestgreen")

					plot_trialcounts_sessionlength(mouse, lab, ax, xlims)
					fix_date_axis(ax)
					axes.append(ax)

					# PERFORMANCE AND MEDIAN RT
					ax = plt.subplot2grid((4, sub_batch_size), (2, i))
					plot_performance_rt(mouse, lab, ax, xlims)
					if training_status == 'trained':
					# indicate date at which the animal is 'trained'
						# shell()
						ax.axvline(trained_date, color="orange")
					elif training_status == 'ready for ephys':
					# indicate date at which the animal is 'ready for ephys'
						ax.axvline(trained_date, color="orange")
						ax.axvline(biased_date, color="forestgreen")

					fix_date_axis(ax)
					axes.append(ax)

					# CONTRAST/CHOICE HEATMAP
					ax = plt.subplot2grid((4, sub_batch_size), (3, i))
					plot_contrast_heatmap(mouse, lab, ax, xlims)

				elapsed = time.time() - t
				print( "Elapsed time: %f seconds.\n" %elapsed)

				# add an xlabel with the mouse's name and sex
				ax.set_xlabel('Mouse %s (%s)'%(mouse,
					subjects.loc[subjects['subject_nickname'] == mouse]['sex'].item()), fontweight="bold")

				if training_status == 'trained':
					ax.xaxis.label.set_color('orange')
				elif training_status == 'ready for ephys':
					ax.xaxis.label.set_color('forestgreen')
				elif training_status == 'untrainable':
					ax.xaxis.label.set_color('red')

			# FIX: after creating the whole plot, make sure xticklabels are shown
			# https://stackoverflow.com/questions/46824263/x-ticks-disappear-when-plotting-on-subplots-sharing-x-axis
			for i, ax in enumerate(axes):
				[t.set_visible(True) for t in ax.get_xticklabels()]

			# SAVE FIGURE PER BATCH
			fig.suptitle('Mice born on %s, %s' %(birth_date, lab))
			try:
				plt.tight_layout(rect=[0, 0.03, 1, 0.95])
			except:
				pass

			mice_sub = mice[sub_batch:sub_batch+sub_batch_size]
			mice_str = '"' + mice[0] + '"'
			for imouse in mice_sub[1:]:
				mice_str = mice_str + ', "' + imouse + '"'

			mice_sub = subject.Subject & 'subject_nickname in ({})'.format(mice_str)
			last_behavior = mice_sub.aggr(behavior.TrialSet,
				last_behavior = 'max(session_start_time)').fetch('last_behavior')

			# include date of last change in data
			last_weighing = mice_sub.aggr(action.Weighing,
				last_weighing = 'max(weighing_time)').fetch('last_weighing')
			last_water = mice_sub.aggr(action.WaterAdministration,
				last_water = 'max(administration_time)').fetch('last_water')

			if last_behavior.size:
				last_behavior = max(last_behavior)
				last_date = max(np.hstack(
					[last_weighing, last_water, last_behavior])).date().strftime("%Y-%m-%d")
			else:
				last_date = max(np.hstack([last_weighing, last_water])).date().strftime("%Y-%m-%d")

			fig.savefig(os.path.join(path + '%s_%s_batch_%s_%s.pdf'%(last_date, lab, birth_date, str(int(sub_batch/sub_batch_size)+1))))
			fig.savefig(os.path.join(path + '%s_%s_batch_%s_%s.png'%(last_date, lab, birth_date, str(int(sub_batch/sub_batch_size)+1))))
			plt.close(fig)

training_review.to_csv(os.path.join(path + 'training_review.csv'))
