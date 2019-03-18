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
from behavior_plots import *
from load_mouse_data_datajoint import * # this has all plotting functions
import psychofit as psy # https://github.com/cortex-lab/psychofit

# folder to save plots, from DataJoint
path = '/Figures_DataJoint_shortcuts/'

# ============================================= #
# START BIG OVERVIEW PLOT
# ============================================= #

allsubjects = pd.DataFrame.from_dict(((subject.Subject() - subject.Death()) & 'sex!="U"'
                                   & action.Weighing() & action.WaterAdministration()
                                   ).fetch(as_dict=True, order_by=['lab_name', 'subject_nickname']))
users = allsubjects['lab_name'].unique()
print(users)

# from guido: make sure max 5 mice are plotted on a single figure
sub_batch_size = 5


for lidx, lab in enumerate(users):

	# take mice from this lab only
	subjects = pd.DataFrame.from_dict(((subject.Subject() - subject.Death()) & 'sex!="U"' & 'lab_name="%s"'%lab
                                   & action.Weighing() & action.WaterAdministration()
                                   ).fetch(as_dict=True, order_by=['subject_nickname']))

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

				try:
					# TRIAL COUNTS AND SESSION DURATION
					behav 	= get_behavior(mouse, lab)

					ax = plt.subplot2grid((4, sub_batch_size), (1, i))
					plot_trialcounts_sessionlength(behav, ax, xlims)
					fix_date_axis(ax)
					axes.append(ax)

					# PERFORMANCE AND MEDIAN RT
					ax = plt.subplot2grid((4, sub_batch_size), (2, i))
					plot_performance_rt(behav, ax, xlims)
					fix_date_axis(ax)
					axes.append(ax)

					# CONTRAST/CHOICE HEATMAP
					ax = plt.subplot2grid((4, sub_batch_size), (3, i))
					plot_contrast_heatmap(behav, ax, xlims)

				except:
					pass

				elapsed = time.time() - t
				print( "Elapsed time: %f seconds.\n" %elapsed)
					
				# add an xlabel with the mouse's name and sex
				ax.set_xlabel('Mouse %s (%s)'%(mouse,
					subjects.loc[subjects['subject_nickname'] == mouse]['sex'].item()), fontweight="bold")

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
			last_behavior = mice_sub.aggr(behavior.TrialSet, \
				last_behavior = 'max(session_start_time)').fetch('last_behavior')
			
			if last_behavior.size > 0:
				last_date = max(last_behavior).date().strftime("%Y-%m-%d")
			else:
				last_weighing = mice_sub.aggr(action.Weighing, \
					last_weighing = 'max(weighing_time)').fetch('last_weighing')
				last_water = mice_sub.aggr(action.WaterAdministration, \
					last_water = 'max(administration_time)').fetch('last_water')
				last_date = max(np.hstack([last_weighing, last_water])).date().strftime("%Y-%m-%d")

			fig.savefig(os.path.join(path + '%s_%s_batch_%s_%s.pdf'%(last_date, lab, birth_date, str(int(sub_batch/sub_batch_size)+1))))
			fig.savefig(os.path.join(path + '%s_%s_batch_%s_%s.png'%(last_date, lab, birth_date, str(int(sub_batch/sub_batch_size)+1))))
			plt.close(fig)
