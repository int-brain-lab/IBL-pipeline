from oneibl.one import ONE
import pandas as pd
import numpy as np
from os import listdir, getcwd
from os.path import isfile, join
import re
from IPython import embed as shell

one = ONE() # initialize

def load_behavior(ref, rootDir=None):
    """
    Load the trials for a given experiment reference

    Example:
        df = load_behaviour('2018-09-11_1_MOUSE', rootDir = r'\\server1\Subjects')
        df.head()

    Args:
        subject (str): The subject name
        rootDir (str): The root directory, i.e. where the subject data are stored.
                       If rootDir is None, the current working directory is used.

    Returns:
        df (DataFrame): DataFrame constructed from the trials object of the ALF
                        files located in the experiment directory

    TODO: return multi-level data frame

    @author: Miles
    """


    if rootDir is None:
        rootDir = getcwd()
    path = dat.exp_path(ref, rootDir)
    alfs = [f for f in listdir(path) if (isfile(join(path, f))) & (is_alf(f))]
    parts = [alf_parts(alf) for alf in alfs]
    # List of 'trials' attributes
    attr = [parts[i]['typ'] for i in range(len(parts)) if parts[i]['obj'] == 'trials']
    attr.extend(['trialStart', 'trialEnd'])
    # Pull paths of trials ALFs
    trials = [join(path,f) for f in alfs if 'trials' in f]
    if not trials:
        print('{}: Nothing to process'.format(ref))
        return
    # Load arrays into dictionary
    trialsDict = dict.fromkeys(attr)
    for p,name in zip(trials, attr):
        trialsDict[name] = np.load(p).squeeze()
    # Check all arrays the same length
    lengths = [len(val) for val in [trialsDict.values()]]
    assert len(set(lengths))==1,'Not all arrays in trials the same length'
    # Deal with intervals
    trialsDict['trialStart'] = trialsDict['intervals'][:,0]
    trialsDict['trialEnd'] = trialsDict['intervals'][:,1]
    trialsDict.pop('intervals', None)
    # Create data from from trials dict
    df = pd.DataFrame(trialsDict)
    df['contrast'] = (df['contrastRight']-df['contrastLeft'])*100
    df.name = ref
    return df


def get_weight_records(subjects, ai):
    """
    Determine whether the mouse has met the criteria for having learned

    Example:
        baseURL = 'https://alyx.internationalbrainlab.org/'
        ai = AlyxClient(username='miles', password=pwd, base_url=baseURL)
        records, info = get_weight_records(['ALK081', 'LEW010'], ai)

    Args:
        subjects (list): List of subjects.
        ai (AlyxClient): An instance of the AlyxClient

    Returns:
        records (Data Frame): Data frame of weight and water records
        info (Data Frame): Data frame of subject information

    """
    s = ai.get('subjects?stock=False')
    rmKeys = ['actions_sessions','water_administrations','weighings','genotype']
    subject_info = []
    records = []
    weight_info = []
    for s in subjects:
        subj = ai.get('subjects/{}'.format(s))
        subject_info.append({key: subj[key] for key in subj if key not in rmKeys})
        endpoint = ('water-requirement/{}?start_date=2016-01-01&end_date={}'
                    .format(s, datetime.datetime.now().strftime('%Y-%m-%d')))
        wr = ai.get(endpoint)
        if wr['implant_weight']:
            iw = wr['implant_weight']
        else:
            iw = 0
        #TODO MultiIndex without None
        if not wr['records']:
            records.append(None)
        else:
            df = pd.DataFrame(wr['records'])
            df = (df.set_index(pd.DatetimeIndex(df['date']))
                  .drop('date', axis=1)
                  .assign(pct_weight = lambda x:
                          (x['weight_measured']-iw) /
                          (x['weight_expected']-iw)
                          if 'weight_measured' in x.columns.values
                          else np.nan))
            records.append(df)
            wr.pop('records', None)
        weight_info.append(wr)


    info = (pd.DataFrame(weight_info)
            .merge(pd.DataFrame(subject_info), left_on='subject', right_on='nickname')
           .set_index('subject'))
    records = pd.concat(records, keys=subjects, names=['name', 'date'])
    return records, info
    return records

# ==================== #
# ONE/ALYX
# ==================== #


def get_metadata(mousename):

    metadata = {'date_birth': one._alyxClient.get('/weighings?nickname=%s' %mousename),
        'cage': one._alyxClient.get('/cage?nickname=%s' %mousename)}

    return metadata

def get_weights(mousename):

    wei = one._alyxClient.get('/weighings?nickname=%s' %mousename)
    wei = pd.DataFrame(wei)
    wei['date_time'] = pd.to_datetime(wei.date_time)
    wei.sort_values('date_time', inplace=True)
    wei.reset_index(drop=True, inplace=True)
    wei['date'] = wei['date_time'].dt.floor('D')
    wei['days'] = wei.date - wei.date[0]
    wei['days'] = wei.days.dt.days # convert to number of days from start of the experiment

    return wei

def get_water(mousename):
    wei = one._alyxClient.get('/water-administrations?nickname=%s' %mousename)
    wei = pd.DataFrame(wei)
    wei['date_time'] = pd.to_datetime(wei.date_time)

    # for w in wei:
    # wei['date_time'] = isostr2date(wei['date_time'])
    wei.sort_values('date_time', inplace=True)
    wei.reset_index(drop=True, inplace=True)
    wei['date'] = wei['date_time'].dt.floor('D')

    wei['days'] = wei.date - wei.date[0]
    wei['days'] = wei.days.dt.days # convert to number of days from start of the experiment

    # wei = wei.set_index('date')
    # wei.index = pd.to_datetime(wei.index)

    wa_unstacked = wei.pivot_table(index='date',
        columns='water_type', values='water_administered', aggfunc='sum').reset_index()
    # wa_unstacked = wa_unstacked.set_index('date')
    # wa_unstacked.index = pd.to_datetime(wa_unstacked.index)

    wa_unstacked['date'] = pd.to_datetime(wa_unstacked.date)
    wa_unstacked.set_index('date', inplace=True)

    return wa_unstacked, wei


def get_behavior(mousename, **kwargs):

    # find metadata we need
    eid, details = one.search(subjects=mousename, details=True, **kwargs)

    # sort by date so that the sessions are shown in order
    start_times  = [d['start_time'] for d in details]
    eid          = [x for _,x in sorted(zip(start_times, eid))]
    details      = [x for _,x in sorted(zip(start_times, details))]

    # grab only behavioral datatypes, all start with _ibl_trials
    types       = one.list(eid)
    types2      = [item for sublist in types for item in sublist]
    types2      = list(set(types2)) # take unique by converting to a set and back to list
    dataset_types = [s for i, s in enumerate(types2) if '_ibl_trials' in s]

    # load data over sessions
    for ix, eidx in enumerate(eid):
        dat = one.load(eidx, dataset_types=dataset_types, dclass_output=True)

        # skip if no data, or if there are fewer than 10 trials in this session
        if len(dat.data) == 0:
            continue
        else:
            if len(dat.data[0]) < 10:
                continue

        # pull out a dict with variables and their values
        tmpdct = {}
        for vi, var in enumerate(dat.dataset_type):
            k = [item[0] for item in dat.data[vi]]
            tmpdct[re.sub('_ibl_trials.', '', var)] = k

        # add crucial metadata
        tmpdct['subject']       = details[ix]['subject']
        tmpdct['users']         = details[ix]['users'][0]
        tmpdct['lab']           = details[ix]['lab']
        tmpdct['session']       = details[ix]['number']
        tmpdct['start_time']    = details[ix]['start_time']
        tmpdct['end_time']      = details[ix]['end_time']
        tmpdct['trial']         = [i for i in range(len(dat.data[0]))]

        # append all sessions into one dataFrame
        if not 'df' in locals():
            df = pd.DataFrame.from_dict(tmpdct)
        else:
            df = df.append(pd.DataFrame.from_dict(tmpdct), sort=False, ignore_index=True)

    # take care of dates properly
    df['start_time'] = pd.to_datetime(df.start_time)
    df['end_time']   = pd.to_datetime(df.end_time)
    df['date']       = df['start_time'].dt.floor("D")

    # convert to number of days from start of the experiment
    df['days']       = df.date - df.date[0]
    df['days']       = df.days.dt.days

    # add some more handy things
    df['rt']        = df['response_times'] - df['stimOn_times']
    df['signedContrast'] = (df['contrastLeft'] - df['contrastRight']) * 100
    df['signedContrast'] = df.signedContrast.astype(int)

    df['correct']   = np.where(np.sign(df['signedContrast']) == df['choice'], 1, 0)
    df.loc[df['signedContrast'] == 0, 'correct'] = np.NaN

    df['choice2'] = df.choice.replace([-1, 0, 1], [0, np.nan, 1]) # code as 0, 100 for percentages
    df['probabilityLeft'] = df.probabilityLeft.round(decimals=2)

    return df

def get_water_weight(mousename):

    wei = get_weights(mousename)
    wa_unstacked, wa = get_water(mousename)
    wa.reset_index(inplace=True)

    # make sure that NaNs are entered for days with only water or weight but not both
    combined = pd.merge(wei, wa, on="date", how='outer')
    combined = combined[['date', 'weight', 'water_administered', 'water_type']]
    combined['days'] = combined.date - combined.date[0]
    combined['days'] = combined.days.dt.days # convert to number of days from start of the experiment

    return combined
