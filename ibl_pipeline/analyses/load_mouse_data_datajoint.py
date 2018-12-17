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

    mouse = (subject.Subject() & 'subject_nickname = "%s"'%mousename )

    wei = {}
    wei['date_time'], wei['weight'] = (action.Weighing() & mouse).fetch('weighing_time', 
        'weight', order_by='weighing_time')

    # now organize in a pandas dataframe
    wei = pd.DataFrame.from_dict(wei)
    wei['date_time'] = pd.to_datetime(wei.date_time)
    wei.sort_values('date_time', inplace=True)
    wei.reset_index(drop=True, inplace=True)
    wei['date'] = wei['date_time'].dt.floor('D')  
    wei['days'] = wei.date - wei.date[0]
    wei['days'] = wei.days.dt.days # convert to number of days from start of the experiment

    return wei

def get_water(mousename):

    mouse = (subject.Subject() & 'subject_nickname = "%s"'%mousename )
    wei = (action.WaterAdministration() & mouse).fetch(as_dict=True)

    wei = pd.DataFrame(wei)
    wei.rename(columns={'administration_time':'date_time', 'watertype_name':'water_type'}, inplace=True)

    wei['date_time'] = pd.to_datetime(wei.date_time)
    wei.sort_values('date_time', inplace=True)
    wei.reset_index(drop=True, inplace=True)
    wei['date'] = wei['date_time'].dt.floor('D')  

    wei['days'] = wei.date - wei.date[0]
    wei['days'] = wei.days.dt.days # convert to number of days from start of the experiment

    return wei

def get_water_weight(mousename):

    wei = get_weights(mousename)
    wa = get_water(mousename)
    wa.reset_index(inplace=True)

    # also grab the info about water restriction
    # TODO: is this possible in DataJoint?

    # make sure that NaNs are entered for days with only water or weight but not both
    combined = pd.merge(wei, wa, on="date", how='outer')   
    combined = combined[['date', 'weight', 'water_administered', 'water_type']]

    # # only if the mouse is on water restriction, add its baseline weight
    # if restr['last_water_restriction']:
        
    #     # remove those weights below current water restriction start
    #     if restr['responsible_user'] == 'valeria':
    #         combined = combined[combined.date >= pd.to_datetime(restr['last_water_restriction'])]

    #     baseline = pd.DataFrame.from_dict({'date': pd.to_datetime(restr['last_water_restriction']), 
    #         'weight': restr['reference_weight'], 'index':[0]})
    # else:

    baseline = pd.DataFrame.from_dict({'date': None, 'weight': combined.weight[0], 'index':[0]})

    combined = combined.sort_values(by='date')
    combined['date'] = combined['date'].dt.floor("D") # round the time of the baseline weight down to the day

    combined = combined.reset_index()
    combined = combined.drop(columns='index')

    # also indicate all the dates as days from the start of water restriction (for easier plotting)
    combined['days'] = combined.date - combined.date[0]
    combined['days'] = combined.days.dt.days # convert to number of days from start of the experiment

    return combined, baseline

def get_behavior(mousename, **kwargs):

    # b = (behavior.TrialSet.Trial * acquisition.Session.session_end_time.proj(ac_lab='lab_name') 
    #     * subject.Subject) & 'subject_nickname = "%s"'%mousename

    b = (behavior.TrialSet.Trial * subject.Subject) & 'subject_nickname = "%s"'%mousename
    behav = pd.DataFrame(b.fetch(order_by='session_start_time, trial_id'))

    # TODO: harmonize the datajoint attribute names to Alf?
    # https://github.com/shenshan/IBL-pipeline/blob/master/notebooks/Behavioral%20overview%20snapshot.ipynb
    behav['start_time']         = pd.to_datetime(behav['session_start_time'])

    # DJ doesn't return session_end_time
    try:
        behav['end_time']       = pd.to_datetime(behav['session_end_time'])
    except: # will set the end_time to be the same as start_time, 0 minute session
        behav['end_time']       = pd.to_datetime(behav['session_start_time'])

    behav['trial']              = behav['trial_id'] - 1
    behav['date']               = behav['session_start_time'].dt.floor("D")

    behav['days']               = behav.date - behav.date[0]
    behav['days']               = behav.days.dt.days

    behav['signedContrast']     = (behav['trial_stim_contrast_left'] - behav['trial_stim_contrast_right']) * 100
    behav['signedContrast']     = behav.signedContrast.astype(int)

    val_map                     = {'CCW': -1, 'No Go': 0, 'CW': 1}
    behav['choice']             = behav['trial_choice'].map(val_map)
    behav['correct']            = np.where(np.sign(behav['signedContrast']) == behav['choice'], 1, 0)
    behav.loc[behav['signedContrast'] == 0, 'correct'] = np.NaN

    behav['choice2']            = behav.choice.replace([-1, 0, 1], [0, np.nan, 1]) # code as 0, 100 for percentages
    behav['correct_easy']       = behav.correct
    behav.loc[np.abs(behav['signedContrast']) < 50, 'correct_easy'] = np.NaN
    behav.rename(columns={'trial_stim_prob_left':'probabilityLeft'}, inplace=True)

    behav['rt']                 = behav['trial_response_time'] - behav['trial_stim_on_time']
    behav['included']           = behav['trial_included']

    return behav
 