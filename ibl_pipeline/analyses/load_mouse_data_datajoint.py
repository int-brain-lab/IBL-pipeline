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

def get_weights(mousename):
    mouse = (subject.Subject() & 'subject_nickname = "%s"' % mousename)

    wei = {}
    wei['date_time'], wei['weight'] = (action.Weighing() & mouse).fetch('weighing_time',
                                                                        'weight', order_by='weighing_time')
    wei = pd.DataFrame.from_dict(wei)

    if not wei.empty:
        # now organize in a pandas dataframe
        wei['date_time'] = pd.to_datetime(wei.date_time)
        wei.sort_values('date_time', inplace=True)
        wei.reset_index(drop=True, inplace=True)
        wei['date'] = wei['date_time'].dt.floor('D')
        wei['days'] = wei.date - wei.date[0]
        wei['days'] = wei.days.dt.days  # convert to number of days from start of the experiment

    return wei


def get_water(mousename):
    mouse = (subject.Subject() & 'subject_nickname = "%s"' % mousename)
    wei = (action.WaterAdministration() & mouse).fetch(as_dict=True)

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


def get_water_weight(mousename):

    wei = get_weights(mousename)
    wa = get_water(mousename)

    if not (wei.empty or wa.empty):

        # AVERAGE WEIGHT WITHIN EACH DAY
        wei = wei.groupby(['date']).mean().reset_index()
        wa = wa.groupby(['date', 'water_type']).mean().reset_index()

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

        # only if the mouse is on water restriction, add its baseline weight
        mouse = (subject.Subject() & 'subject_nickname = "%s"' % mousename)
        latest = mouse.aggr(action.WaterRestriction.proj(action_lab="lab_name"),
                            restriction_start_time='max(restriction_start_time)')
        restr = pd.DataFrame((action.WaterRestriction & latest).fetch())

        if restr.empty or not restr['reference_weight'].item() > 0:
            baseline = pd.DataFrame.from_dict({'date': None, 'weight': combined.weight[0], 'day': np.nan, 'index': [0]})
        else:
            baseline = pd.DataFrame.from_dict({'date': pd.to_datetime(restr['restriction_start_time'].dt.floor('D'))[0],
                                               'weight': restr['reference_weight'], 'index': [0]})
            # also show the value that we're using as the baseline with a different marker
            baseline.sort_index(inplace=True)

            # if the restriction is within the range of weight/water values, show it
            if baseline['date'][0] in combined['date']:
                baseline['day'] = combined.loc[combined['date'] == baseline['date'][0], 'days'].item()
            else:
                baseline = pd.DataFrame.from_dict({'date': None, 'weight': combined.weight[0], 'day': np.nan, 'index': [0]})
    else:
        combined = pd.DataFrame()
        baseline = pd.DataFrame()

    return combined, baseline

def get_behavior(mousename, **kwargs):

    b = (behavior.TrialSet.Trial * acquisition.Session.proj('session_end_time',
            ac_lab='lab_name') * subject.Subject) & 'subject_nickname = "%s"' % mousename
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

        behav['signedContrast'] = (behav['trial_stim_contrast_left'] - behav['trial_stim_contrast_right']) * 100
        behav['signedContrast'] = behav.signedContrast.astype(int)

        val_map = {'CCW': -1, 'No Go': 0, 'CW': 1}
        behav['choice'] = behav['trial_response_choice'].map(val_map)
        behav['correct'] = np.where(np.sign(behav['signedContrast']) == behav['choice'], 1, 0)
        behav.loc[behav['signedContrast'] == 0, 'correct'] = np.NaN

        behav['choice2'] = behav.choice.replace([-1, 0, 1], [0, np.nan, 1])  # code as 0, 100 for percentages
        behav['correct_easy'] = behav.correct
        behav.loc[np.abs(behav['signedContrast']) < 50, 'correct_easy'] = np.NaN
        behav.rename(columns={'trial_stim_prob_left': 'probabilityLeft'}, inplace=True)

        behav['rt'] = behav['trial_response_time'] - behav['trial_stim_on_time']
        behav['included'] = behav['trial_included']

    return behav
