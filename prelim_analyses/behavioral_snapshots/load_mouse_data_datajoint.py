# from oneibl.one import ONE
import pandas as pd
import numpy as np
from os import listdir, getcwd
from os.path import isfile, join
import re
from IPython import embed as shell

import datajoint as dj
from ibl_pipeline import reference, subject, action, acquisition, data, behavior


# ==================== #
# DATAJOINT
# ==================== #

def get_weights(mousename, labname):

    wei = {}
    wei['date_time'], wei['weight'] = (action.Weighing() &
                                       'subject_nickname="%s"'%mousename & 'lab_name="%s"'%labname).fetch('weighing_time',
                                                                        'weight', order_by='weighing_time')
    wei = pd.DataFrame.from_dict(wei)

    # ensure that the reference weight is also added
    restrictions = pd.DataFrame.from_dict((action.WaterRestriction &
        'subject_nickname="%s"'%mousename & 'lab_name="%s"'%labname).fetch(as_dict=True))
    restr_summary = restrictions[['restriction_start_time', 'reference_weight']].copy()
    restr_summary = restr_summary.rename(columns = {'restriction_start_time':'date_time', 'reference_weight':'weight'})

    wei = pd.concat([wei, restr_summary], ignore_index=True)

    if not wei.empty:
        # now organize in a pandas dataframe
        wei['date_time'] = pd.to_datetime(wei.date_time)
        wei.sort_values('date_time', inplace=True)
        wei.reset_index(drop=True, inplace=True)
        wei['date'] = wei['date_time'].dt.floor('D')
        wei['days'] = wei.date - wei.date[0]
        wei['days'] = wei.days.dt.days  # convert to number of days from start of the experiment

    return wei


def get_water(mousename, labname):

    wei = (action.WaterAdministration() & 'subject_nickname="%s"'%mousename & 'lab_name="%s"'%labname).fetch(as_dict=True)
    wei = pd.DataFrame(wei)
    if not wei.empty:
        wei.rename(columns={'administration_time': 'date_time', 'watertype_name': 'water_type'}, inplace=True)

        wei['date_time'] = pd.to_datetime(wei.date_time)
        wei.sort_values('date_time', inplace=True)
        wei.reset_index(drop=True, inplace=True)
        wei['date'] = wei['date_time'].dt.floor('D')

        wei['days'] = wei.date - wei.date[0]
        wei['days'] = wei.days.dt.days  # convert to number of days from start of the experiment

    return wei


def get_water_weight(mousename, labname):

    wei = get_weights(mousename, labname)
    wa  = get_water(mousename, labname)

    if not (wei.empty or wa.empty):

        # AVERAGE WEIGHT WITHIN EACH DAY
        wei = wei.groupby(['date']).mean().reset_index()
        wa  = wa.groupby(['date', 'water_type']).mean().reset_index()

        # make sure that NaNs are entered for days with only water or weight but not both
        combined = pd.merge(wei, wa, on="date", how='outer')
        combined = combined[['date', 'weight', 'water_administered', 'water_type', 'adlib']]
        combined['date'] = combined['date'].dt.floor("D")

        # continuous date range - add missing dates to make my life easier later!
        missingdates = np.setdiff1d(pd.date_range(combined.date.min(), combined.date.max()), combined['date'])
        combined     = pd.merge(combined, pd.DataFrame(missingdates, columns=['date']), how='outer')
        combined.sort_values(by='date', inplace=True)
        combined.reset_index(inplace=True)

        # also indicate all the dates as days from the start of water restriction (for easier plotting)
        combined['days'] = combined.date - combined.date[0]
        combined['days'] = combined.days.dt.days  # convert to number of days from start of the experiment

        # ALSO GET INFO ABOUT WATER RESTRICTIONS
        restrictions = pd.DataFrame.from_dict((action.WaterRestriction &
            'subject_nickname="%s"'%mousename & 'lab_name="%s"'%labname).fetch(as_dict=True))

        # ensure that start and end times are pandas datetimes
        restrictions['restriction_start_time'] = pd.to_datetime(restrictions['restriction_start_time'])
        restrictions['restriction_end_time'] = pd.to_datetime(restrictions['restriction_end_time'])

        # round down to the date
        restrictions['date_start'] = restrictions['restriction_start_time'].dt.floor('D')
        restrictions['date_end'] = restrictions['restriction_end_time'].dt.floor('D')

        # fill to the appropriate day
        restrictions['day_start'] = combined['days'].max() * np.ones(restrictions['date_start'].shape)
        restrictions['day_end'] = combined['days'].max() * np.ones(restrictions['date_end'].shape)
        combined['water_restricted'] = np.zeros(combined['days'].shape, dtype=bool)

        # recode dates into days
        datedict = pd.Series(combined.days.values, index=combined.date).to_dict()
        for d in range(len(restrictions)):
            restrictions.loc[d, 'day_start'] = datedict[restrictions.loc[d, 'date_start']]

            # only do this for dates that are not NaT
            try:
                restrictions.loc[d, 'day_end'] = datedict[restrictions.loc[d, 'date_end']]
            except:
                pass

            # for each day, mark if the animal was on WR or not
            combined['water_restricted'] = combined['water_restricted'] | \
                                           combined['days'].between(restrictions['day_start'][d],
                                           restrictions['day_end'][d], inclusive=True)

    else:
        combined     = pd.DataFrame()
        restrictions = pd.DataFrame()

    return combined, restrictions

def get_behavior(mousename, labname, **kwargs):

    b = behavior.TrialSet.Trial * acquisition.Session.proj('session_end_time', 'task_protocol',
            ac_lab='lab_name') & 'subject_nickname = "%s"' % mousename & 'lab_name="%s"'%labname
    behav = pd.DataFrame(b.fetch(order_by='session_start_time, trial_id'))

    if not behav.empty:

        # https://github.com/shenshan/IBL-pipeline/blob/master/notebooks/Behavioral%20overview%20snapshot.ipynb
        behav['start_time'] = pd.to_datetime(behav['session_start_time'])

        # DJ doesn't return session_end_time
        behav['end_time'] = pd.to_datetime(behav['session_end_time'])
        behav['trial'] = behav['trial_id'] - 1
        behav['date'] = behav['session_start_time'].dt.floor("D")

        behav['days'] = behav.date - behav.date[0]
        behav['days'] = behav.days.dt.days

        behav['signedContrast'] = (behav['trial_stim_contrast_right'] - behav['trial_stim_contrast_left']) * 100
        behav['signedContrast'] = behav.signedContrast.astype(int)

        val_map = {'CCW': 1, 'No Go': 0, 'CW': -1}
        behav['choice'] = behav['trial_response_choice'].map(val_map)
        behav['correct'] = np.where(np.sign(behav['signedContrast']) == behav['choice'], 1, 0)
        behav.loc[behav['signedContrast'] == 0, 'correct'] = np.NaN

        behav['choice2'] = behav.choice.replace([-1, 0, 1], [0, np.nan, 1])  # code as 0, 100 for percentages
        behav['correct_easy'] = behav.correct
        behav.loc[np.abs(behav['signedContrast']) < 50, 'correct_easy'] = np.NaN
        behav.rename(columns={'trial_stim_prob_left': 'probabilityLeft'}, inplace=True)

        behav['rt'] = behav['trial_response_time'] - behav['trial_stim_on_time']
        behav['included'] = behav['trial_included']

        # don't count RT if there was no response
        behav.loc[behav.choice == 0, 'rt'] = np.nan

        # for trainingChoiceWorld, make sure all probabilityLeft = 0.5
        behav['probabilityLeft_block'] = behav['probabilityLeft']
        behav.fillna({'task_protocol':'unknown'}, inplace=True)
        behav.loc[behav['task_protocol'].str.contains("trainingChoiceWorld"), 'probabilityLeft_block'] = 0.5

    return behav
