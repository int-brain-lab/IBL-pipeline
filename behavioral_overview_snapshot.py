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

from oneibl.one import ONE
from ibllib.time import isostr2date
from psychofit import psychofit as psy # https://github.com/cortex-lab/psychofit

# loading and plotting functions
from behavior_plots import *
from load_mouse_data import * # this has all plotting functions

def fit_psychfunc(df):
	choicedat = df.groupby('signedContrast').agg({'trial':'max', 'choice2':'mean'}).reset_index()
	pars, L = psy.mle_fit_psycho(choicedat.values.transpose(), P_model='erf_psycho_2gammas', 
		parstart=np.array([choicedat['signedContrast'].mean(), 20., 0.05, 0.05]), 
		parmin=np.array([choicedat['signedContrast'].min(), 0., 0., 0.]), 
		parmax=np.array([choicedat['signedContrast'].max(), 100., 1, 1]))
	df2 = {'bias':pars[0],'threshold':pars[1], 'lapselow':pars[2], 'lapsehigh':pars[3]}
	return pd.DataFrame(df2, index=[0])

# ============================================= #
# START BIG OVERVIEW PLOT
# ============================================= #

## INITIALIZE A FEW THINGS
sns.set_style("darkgrid", {'xtick.bottom': True,'ytick.left': True} )
sns.set_context(context="paper")
current_palette = sns.color_palette()

# set a new palette for biased blocks: black, purple, orange
one = ONE() # initialize

# get a list of all mice that are currently training
subjects 	= pd.DataFrame(one._alyxClient.get('/subjects?water_restricted=True&alive=True'))
subjects 	= pd.DataFrame(one._alyxClient.get('/subjects?nickname=IBL_1'))

print(subjects['nickname'].unique())

for i, mouse in enumerate(subjects['nickname']):

	try:

		# MAKE THE FIGURE, divide subplots using gridspec
		print(mouse)
		wei 	= get_weights(mouse)
		behav 	= get_behavior(mouse)

		fig, axes = plt.subplots(ncols=5, nrows=4, constrained_layout=False,
	        gridspec_kw=dict(width_ratios=[2,2,1,1,1], height_ratios=[1,1,1,1]), figsize=(11.69, 8.27))

		# ============================================= #
		# GENERAL METADATA
		# ============================================= #

		fig.suptitle('Mouse %s (%s), DoB %s, user %s (%s), strain %s, cage %s, %s' %(subjects['nickname'][i],
		 subjects['sex'][i], subjects['birth_date'][i], 
		 subjects['responsible_user'][i], subjects['lab'][i],
		 subjects['strain'][i], subjects['litter'][i], subjects['description'][i]))

		# ============================================= #
		# WEIGHT CURVE AND WATER INTAKE
		# ============================================= #

		ax = axes[0,0]
		sns.set_palette("colorblind") # palette for water

		# get all the weights and water aligned in 1 table
		weight_water = get_water_weight(mouse)

		# use pandas plot for a stacked bar - water types
		wa_unstacked = weight_water.pivot_table(index='days',
	    	columns='water_type', values='water_administered', aggfunc='sum').reset_index()
		wa_unstacked.index = wa_unstacked.days
		wa_unstacked.loc[:,['Water','Hydrogel']].plot.bar(stacked=True, ax=ax)
		l = ax.legend(loc='upper left', prop={'size': 'xx-small'})
		l.set_title('')
		ax.set(ylabel="Water intake (mL)", xlabel='')

		# overlay the weight curve
		# shell()
		weight_water = weight_water.drop_duplicates('days').reset_index()
		righty = ax.twinx()
		righty.plot(weight_water.weight, '.k-')
		righty.set(xlabel='', ylabel="Weight (g)", 
			xlim=[weight_water.index.min()-1, weight_water.index.max()+1])
		righty.grid(False)	

		# correct the ticks to show dates, not days
		# also indicate Mondays clearly

		# ax.set_xticklabels([dt.strftime('%b-%d') if dt.weekday() is 0 else "" for dt in pp.date])
  #       #ax.set_xticks([dt for dt in pp.date if dt.weekday() is 0])
  #       for item in ax.get_xticklabels():
  #           item.set_rotation(60)

		# ============================================= #
		# PERFORMANCE AND MEDIAN RT
		# ============================================= #

		# performance on easy trials
		ax = axes[1,0]
		behav['correct_easy'] = behav.correct
		behav.loc[np.abs(behav['signedContrast']) < 50, 'correct_easy'] = np.NaN
		correct_easy = behav.groupby(['date'])['correct_easy'].mean().reset_index()
		
		sns.lineplot(x="date", y="correct_easy", markers=True, color="black", data=correct_easy, ax=ax)
		sns.scatterplot(x="date", y="correct_easy", color="black", data=correct_easy, ax=ax)
		ax.set(xlabel='', ylabel="Performance (easy trials)", 
			xlim=[behav.date.min()-timedelta(days=1), behav.date.max()+timedelta(days=2)],
			yticks=[0.5, 0.75, 1], ylim=[0.4, 1.01])
		ax.yaxis.label.set_color("black")

		# RTs on right y-axis
		trialcounts = behav.groupby(['date'])['rt'].median().reset_index()
		righty = ax.twinx()
		sns.lineplot(x="date", y="rt", markers=True, color="firebrick", data=trialcounts, ax=righty)
		sns.scatterplot(x="date", y="rt", color="firebrick", data=trialcounts, ax=righty)
		righty.yaxis.label.set_color("firebrick")
		righty.tick_params(axis='y', colors='firebrick')
		righty.grid(False)
		fix_date_axis(righty)
		fix_date_axis(ax)
		righty.set(xlabel='', ylabel="RT (s)", ylim=[0.1,10],
			xlim=[behav.date.min()-timedelta(days=1), behav.date.max()+timedelta(days=2)])
		righty.set_yscale("log")
		righty.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda y,pos: ('{{:.{:1d}f}}'.format(int(np.maximum(-np.log10(y),0)))).format(y)))

		# ============================================= #
		# TRIAL COUNTS AND SESSION DURATION
		# ============================================= #

		ax = axes[2,0]
		trialcounts = behav.groupby(['date'])['trial'].max().reset_index()
		sns.lineplot(x="date", y="trial", markers=True, color="black", data=trialcounts, ax=ax)
		sns.scatterplot(x="date", y="trial", color="black", data=trialcounts, ax=ax)
		ax.set(xlabel='', ylabel="Trial count", 
			xlim=[behav.date.min()-timedelta(days=1), behav.date.max()+timedelta(days=2)])

		# compute the length of each session
		behav['sessionlength'] = (behav.end_time - behav.start_time)
		behav['sessionlength'] = behav.sessionlength.dt.total_seconds() / 60
		sessionlength = behav.groupby(['date'])['sessionlength'].mean().reset_index()
		righty = ax.twinx()
		sns.lineplot(x="date", y="sessionlength", markers=True, color="firebrick", data=sessionlength, ax=righty)
		sns.scatterplot(x="date", y="sessionlength", color="firebrick", data=sessionlength, ax=righty)
		righty.yaxis.label.set_color("firebrick")
		righty.tick_params(axis='y', colors='firebrick')
		righty.grid(False)
		fix_date_axis(righty)
		fix_date_axis(ax)
		righty.set(xlabel='', ylabel="Session (min)", ylim=[0,80],
				xlim=[behav.date.min()-timedelta(days=1), behav.date.max()+timedelta(days=2)])
		
		# ============================================= #
		# CONTRAST/CHOICE HEATMAP
		# ============================================= #

		ax = axes[3,0]
		plot_perf_heatmap(behav, ax=ax)
		ax.set(xlabel='')

		# ============================================= #
		# PSYCHOMETRIC FUNCTION FITS OVER TIME
		# ============================================= #

		# fit psychfunc on choice fraction, rather than identity
		pars = behav.groupby(['date', 'probabilityLeft']).apply(fit_psychfunc).reset_index()
		parsdict = {'threshold': r'Threshold $(\sigma)$', 'bias': r'Bias $(\mu)$', 
			'lapselow': r'Lapse low $(\gamma)$', 'lapsehigh': r'Lapse high $(\lambda)$'}
		ylims = [[-5, 105], [-105, 105], [-0.05, 1.05], [-0.05, 1.05]]

		# pick a good-looking diverging colormap with black in the middle
		cmap = sns.diverging_palette(220, 20, n=len(behav['probabilityLeft'].unique()), center="dark")
		if len(behav['probabilityLeft'].unique()) == 1:
			cmap = "gist_gray"
		sns.set_palette(cmap)

		for pidx, (var, labelname) in enumerate(parsdict.items()):
			ax = axes[pidx,1]
			sns.lineplot(x="date", y=var, hue="probabilityLeft", palette=cmap, data=pars, legend=None, ax=ax)
			sns.scatterplot(x="date", y=var, hue="probabilityLeft", palette=cmap, data=pars, legend=None, ax=ax)
			ax.set(xlabel='', ylabel=labelname, ylim=ylims[pidx], xlim=[behav.date.min()-timedelta(days=1), behav.date.max()+timedelta(days=1)])

			fix_date_axis(ax)
			if pidx == 0:
				ax.set(title=r'$\gamma + (1 -\gamma-\lambda)  (erf(\frac{x-\mu}{\sigma} + 1)/2$')
			if pidx < 3:
				ax.set(xticklabels=[])

		# ============================================= #
		# LAST THREE SESSIONS
		# ============================================= #

		didx = 1
		sorteddays = behav['days'].sort_values(ascending=True).unique()
		for day in behav['days'].unique():

			# use only the last three days
			if day < sorteddays[-3]:
				continue

			dat = behav.loc[behav['days'] == day, :]
			# print(dat['date'].unique())
			didx += 1

			# PSYCHOMETRIC FUNCTION
			ax = axes[0, didx]
			cmap = sns.diverging_palette(220, 20, n=len(dat['probabilityLeft'].unique()), center="dark")
			if len(dat['probabilityLeft'].unique()) == 1:
				cmap = [np.array([0,0,0,1])]

			for ix, probLeft in enumerate(dat['probabilityLeft'].sort_values().unique()):
				plot_psychometric(dat.loc[dat['probabilityLeft'] == probLeft, :], ax=ax, color=cmap[ix])

			ax.set(xlabel="Contrast (%)", ylabel="Choose right (%)")
			ax.set(title=pd.to_datetime(dat['start_time'].unique()[0]).strftime('%b-%d, %A'))

			# CHRONOMETRIC FUNCTION
			ax = axes[1, didx]
			for ix, probLeft in enumerate(dat['probabilityLeft'].sort_values().unique()):
				plot_chronometric(dat.loc[dat['probabilityLeft'] == probLeft, :], ax, cmap[ix])
			ax.set(ylim=[0.1,10])
			ax.set_yscale("log")
			ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda y,pos: ('{{:.{:1d}f}}'.format(int(np.maximum(-np.log10(y),0)))).format(y)))

			# RTS THROUGHOUT SESSION
			ax = axes[2, didx]
			sns.scatterplot(x='trial', y='rt', hue='correct', 
				palette={1:"forestgreen", 0:"crimson"},
				alpha=.5, data=dat, ax=ax, legend=False)
			sns.lineplot(x='trial', y='rt', color='black', ci=None, 
				data=dat[['trial', 'rt']].rolling(10).median(), ax=ax) 
			ax.set(xlabel="Trial number", ylabel="RT (s)", ylim=[0.02, 60])
			ax.set_yscale("log")
			ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda y,pos: ('{{:.{:1d}f}}'.format(int(np.maximum(-np.log10(y),0)))).format(y)))

			# # WHEEL ANALYSIS
			# thisdate = dat.loc[dat.index[0], 'date'].strftime('%Y-%m-%d')
			# eid = one.search(subjects=mouse, date_range=[thisdate, thisdate])
			# t, wheelpos, wheelvel = one.load(eid[0], 
			# 	dataset_types=['_ibl_wheel.timestamps', '_ibl_wheel.position', '_ibl_wheel.velocity'])
			# wheeltimes = np.interp(np.arange(0,len(wheelpos)), t[:,0], t[:,1])
		 	#    #times = np.interp(np.arange(0,len(wheelPos)), t[:,0], t[:,1])
			# wheel = pd.DataFrame.from_dict({'position':wheelpos, 'velocity':wheelvel, 'times':wheeltimes})

			# ax = axes[3, didx]
			# sns.lineplot(x=wheeltimes, y=wheelpos, ax=ax)

		for i in range(3):
			axes[i,3].set(ylabel='')
			axes[i,4].set(ylabel='')

		plt.tight_layout(rect=[0, 0.03, 1, 0.95])
		fig.savefig('/Users/urai/Google Drive/Rig building WG/DataFigures/BehaviourData_Weekly/AlyxPlots/%s_overview.pdf' %mouse)

	except:
		print("%s failed to run" %mouse)
		pass

	
