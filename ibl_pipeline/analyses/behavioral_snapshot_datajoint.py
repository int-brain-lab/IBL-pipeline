# Anne Urai, CSHL, 2018
# see https://github.com/int-brain-lab/ibllib/tree/master/python/oneibl/examples

import time, re, datetime, os, glob
from datetime import timedelta
import seaborn as sns
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import scipy as sp
import pandas as pd
from IPython import embed as shell

## CONNECT TO ONE, to avoid having these prompts
from oneibl.one import ONE
one = ONE() # initialize

## CONNECT TO datajoint
import datajoint as dj
from ibl_pipeline import reference, subject, action, acquisition, data, behavior

# loading and plotting functions
from define_paths import fig_path
from behavior_plots import *
from load_mouse_data_datajoint import * # this has all plotting functions
import psychofit as psy # https://github.com/cortex-lab/psychofit

# folder to save plots, from DataJoint
path = '/Snapshot_DataJoint'

# ============================================= #
# START BIG OVERVIEW PLOT
# ============================================= #

## INITIALIZE A FEW THINGS
sns.set_style("darkgrid", {'xtick.bottom': True,'ytick.left': True, 'lines.markeredgewidth':0 } )
sns.set_context(context="paper")

# get a list of all mice that are currently training
subjects = pd.DataFrame.from_dict(subject.Subject().fetch(as_dict=True)) 

# all mice that are alive and on water restriction
subjects = pd.DataFrame.from_dict(((subject.Subject() - subject.Death()) & 
	action.WaterRestriction().proj()).fetch(as_dict=True, order_by='lab_name'))
print(subjects['subject_nickname'].unique())

for i, mouse in enumerate(subjects['subject_nickname']):

	try:

		# MAKE THE FIGURE, divide subplots using gridspec
		print(mouse)
		fig, axes = plt.subplots(ncols=5, nrows=4, constrained_layout=False,
	        gridspec_kw=dict(width_ratios=[2,2,1,1,1], height_ratios=[1,1,1,1]), figsize=(11.69, 8.27))
		sns.set_palette("colorblind") # palette for water types

		# ============================================= #
		# GENERAL METADATA, use DJ variable names
		# ============================================= #

		fig.suptitle('Mouse %s (%s), born %s, user %s (%s), %s' %(subjects['subject_nickname'][i],
		 subjects['sex'][i], subjects['subject_birth_date'][i],
		 subjects['responsible_user'][i], subjects['lab_name'][i],
		 subjects['subject_description'][i]))

		# ============================================= #
		# WEIGHT CURVE AND WATER INTAKE
		# ============================================= #

		# get all the weights and water aligned in 1 table
		weight_water, baseline = get_water_weight(mouse)

		# determine x limits
		xlims = [weight_water.date.min()-timedelta(days=2), weight_water.date.max()+timedelta(days=2)]
		plot_water_weight_curve(weight_water, baseline, axes[0,0])

		# ============================================= #
		# TRIAL COUNTS AND SESSION DURATION
		# ============================================= #

		behav 	= get_behavior(mouse)
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
		cmap = sns.diverging_palette(220, 20, n=len(behav['probabilityLeft'].unique()), center="dark")
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
			if day < sorteddays[-3]:
				continue

			# grab only that day
			dat = behav.loc[behav['days'] == day, :]
			print(dat['date'].unique())
			didx += 1

			# colormap for the asymmetric blocks
			cmap = sns.diverging_palette(220, 20, n=len(dat['probabilityLeft'].unique()), center="dark")
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
			# WHEEL ANALYSIS
			# ============================ #

			plotWheel = False
			if plotWheel:
				# FIRST CREATE A PANDAS DATAFRAME WITH THE FULL WHEEL TRACE DURING THE SESSION
				thisdate = dat.loc[dat.index[0], 'date'].strftime('%Y-%m-%d')
				eid = one.search(subjects=mouse, date_range=[thisdate, thisdate])
				t, wheelpos, wheelvel = one.load(eid[0],
					dataset_types=['_ibl_wheel.timestamps', '_ibl_wheel.position', '_ibl_wheel.velocity'])
				wheel = pd.DataFrame.from_dict({'position':wheelpos[0], 'velocity':np.transpose(wheelvel)[0]})
				wheel['time'] = pd.to_timedelta(np.linspace(t[0,0], t[1,1], len(wheelpos[0])), unit='s')
				wheel.set_index(wheel['time'], inplace=True)
				wheel = wheel.resample('10ms', on='time').mean().reset_index() # to do analyses more quickly, RESAMPLE to 10ms

				# ADD A FEW SECONDS WITH NANS AT THE BEGINNING AND END
				wheel = pd.concat([ pd.DataFrame.from_dict({'time': pd.to_timedelta(np.arange(-10, 0, 0.1), 's'), 
					'position': np.full((100,), np.nan), 'velocity':  np.full((100,), np.nan)}),
					 wheel,
					 pd.DataFrame.from_dict({'time': pd.to_timedelta(np.arange(wheel.time.max().total_seconds(), 
					 	wheel.time.max().total_seconds()+10, 0.1), 's'), 
					'position': np.full((100,), np.nan), 'velocity':  np.full((100,), np.nan)})])
				wheel.index = wheel['time']

				# round to have the same sampling rate as wheeltimes
				stimonset_times = pd.to_timedelta(np.round(dat['stimOn_times'], 2), 's') # express in timedelta

				# THEN EPOCH BY LOCKING TO THE STIMULUS ONSET TIMES
				prestim 		= pd.to_timedelta(0.2, 's')
				poststim 		= pd.to_timedelta(dat.rt.median(), 's') + pd.to_timedelta(1, 's')
				
				signal = []; time = []
				for i, stimonset in enumerate(stimonset_times):
					sliceidx = (wheel.index > (stimonset - prestim)) & (wheel.index < (stimonset + poststim))
					signal.append(wheel['position'][sliceidx].values)

					# also append the time axis to alignment in seaborn plot
					if i == 0:
						timeaxis = np.linspace(-prestim.total_seconds(), poststim.total_seconds(), len(wheel['position'][sliceidx].values))
					time.append(timeaxis)

				# also baseline correct at zero
				zeroindex = np.argmin(np.abs(timeaxis))
				signal_blcorr = []
				for i, item in enumerate(signal):
					signal_blcorr.append(item - item[zeroindex])

				# MAKE INTO A PANDAS DATAFRAME AGAIN, append all relevant columns
				wheel = pd.DataFrame.from_dict({'time': np.hstack(time), 'position': np.hstack(signal), 
					'position_blcorr': np.hstack(signal_blcorr), 
					'choice': np.repeat(dat['choice'], len(timeaxis)), 
					'correct': np.repeat(dat['correct'], len(timeaxis)),
					'signedContrast': np.repeat(dat['signedContrast'], len(timeaxis))})
				
				ax = axes[3, didx]
				sns.lineplot(x='time', y='position_blcorr', ci=None, hue='signedContrast', 
					style='correct', data=wheel, ax=ax, legend=None)
				ax.set(xlabel='Time from stim (s)', ylabel='Wheel position (deg)')
			else:
				ax = axes[3, didx]

		# clean up layout
		for i in range(3):
			axes[i,3].set(ylabel='')
			axes[i,4].set(ylabel='')

		plt.tight_layout(rect=[0, 0.03, 1, 0.95])

		# TODO: HOW TO SAVE THIS FROM DATAJOINT AWS INTO SOME GENERAL FOLDER EVERYONE CAN ACCESS?
		fig.savefig(join(path + '%s_overview.pdf'%mouse))
		plt.close(fig)

	except:

		print("%s failed to run" %mouse)
		plt.tight_layout(rect=[0, 0.03, 1, 0.95])
		# fig.savefig(join(path + '%s_overview.pdf'%mouse))
		pass


