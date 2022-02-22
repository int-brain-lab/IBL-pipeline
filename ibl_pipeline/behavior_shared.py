import datajoint as dj
import numpy as np
import pandas as pd
from os import path, environ
import datetime
import logging
import warnings
from . import reference, subject, acquisition, data

try:
    from oneibl.one import ONE
    import alf.io
    one = ONE(silent=True)
except ImportError:
    warnings.warn('ONE not installed, cannot use populate')
    pass

logger = logging.getLogger(__name__)
mode = environ.get('MODE')

if mode == 'update':
    schema = dj.schema('ibl_behavior')
else:
    schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_behavior')


@schema
class CompleteWheelSession(dj.Computed):
    definition = """
    # sessions that are complete with wheel related information and thus may be ingested
    -> acquisition.Session
    ---
    wheel_velocity_status:     enum('Missing', 'Complete')
    """

    flatiron = 'repo_name like "%flatiron%"'
    key_source = acquisition.Session & \
        (data.FileRecord & flatiron & 'dataset_name="_ibl_wheel.position.npy"') & \
        (data.FileRecord & flatiron & 'dataset_name="_ibl_wheel.timestamps.npy"')

    def make(self, key):
        datasets = (data.FileRecord & key & 'repo_name LIKE "flatiron_%"' &
                    {'exists': 1}).fetch('dataset_name')

        if '_ibl_wheel.velocity.npy' in datasets:
            key['wheel_velocity_status'] = 'Complete'
        else:
            key['wheel_velocity_status'] = 'Missing'

        self.insert1(key)


@schema
class Wheel(dj.Imported):
    definition = """
    # raw wheel recording
    -> acquisition.Session
    ---
    wheel_start_time:       float     # Start time of wheel recording (seconds)
    wheel_end_time:         float     # End time of wheel recording (seconds)
    wheel_duration:         float     # Duration time of wheel recording (seconds)
    wheel_sampling_rate:    float     # Samples per second
    """

    key_source = CompleteWheelSession()

    def make(self, key):

        eID = str((acquisition.Session & key).fetch1('session_uuid'))
        wheel_position, wheel_velocity, wheel_timestamps = \
            one.load(eID, dataset_types=['wheel.position',
                                         'wheel.velocity',
                                         'wheel.timestamps'])

        wheel_sampling_rate = 1 / np.median(np.diff(wheel_timestamps))

        if np.ndim(wheel_timestamps) == 2:
            wheel_timestamps = wheel_timestamps[:, 1]

        key['wheel_start_time'] = wheel_timestamps[0]
        key['wheel_end_time'] = wheel_timestamps[-1]
        key['wheel_duration'] = wheel_timestamps[-1] - wheel_timestamps[0]
        key['wheel_sampling_rate'] = wheel_sampling_rate

        self.insert1(key)
        logger.info('Populated a Wheel tuple for subject {subject_uuid} \
            in session on {session_start_time}'.format(**key))


@schema
class CompleteTrialSession(dj.Computed):
    definition = """
    # sessions that are complete with trial information and thus may be ingested
    -> acquisition.Session
    ---
    stim_on_times_status:           enum('Complete', 'Partial', 'Missing')
    rep_num_status:                 enum('Complete', 'Missing')
    included_status:                enum('Complete', 'Missing')
    ambient_sensor_data_status:     enum('Complete', 'Missing')
    go_cue_times_status:            enum('Complete', 'Missing')
    go_cue_trigger_times_status:    enum('Complete', 'Missing')
    reward_volume_status:           enum('Complete', 'Missing')
    iti_duration_status:            enum('Complete', 'Missing')
    """

    required_datasets = ["_ibl_trials.feedback_times.npy",
                         "_ibl_trials.feedbackType.npy",
                         "_ibl_trials.intervals.npy", "_ibl_trials.choice.npy",
                         "_ibl_trials.response_times.npy",
                         "_ibl_trials.contrastLeft.npy",
                         "_ibl_trials.contrastRight.npy",
                         "_ibl_trials.probabilityLeft.npy"]
    other_datasets = ["_ibl_trials.stimOn_times.npy",
                      "_ibl_trials.repNum.npy",
                      "_ibl_trials.repNum.npy",
                      "_ibl_trials.included.npy",
                      "_iblrig_ambientSensorData.raw.jsonable",
                      "_ibl_trials.goCue_times.npy",
                      "_ibl_trials.goCueTrigger_times.npy",
                      "_ibl_trials.rewardVolume.npy",
                      "_ibl_trials.itiDuration.npy"
                      ]

    def make(self, key):
        datasets = (data.FileRecord & key & 'repo_name LIKE "flatiron_%"' &
                    {'exists': 1}).fetch('dataset_name')
        is_complete = bool(np.all([req_ds in datasets
                                   for req_ds in self.required_datasets]))
        if is_complete is True:
            if '_ibl_trials.stimOn_times.npy' not in datasets:
                key['stim_on_times_status'] = 'Missing'
            else:
                eID = str((acquisition.Session & key).fetch1('session_uuid'))
                lab_name = (subject.SubjectLab & key).fetch1('lab_name')
                if lab_name == 'wittenlab':
                    stimOn_times = np.squeeze(one.load(
                            eID, dataset_types='trials.stimOn_times',
                            clobber=True))
                else:
                    stimOn_times = one.load(
                        eID, dataset_types='trials.stimOn_times',
                        clobber=True)

                if stimOn_times is not None and len(stimOn_times):
                    if (len(stimOn_times)==1 and stimOn_times[0] is None) or \
                            np.all(np.isnan(np.array(stimOn_times))):
                        key['stim_on_times_status'] = 'Missing'
                    elif np.any(np.isnan(np.array(stimOn_times))):
                        key['stim_on_times_status'] = 'Partial'
                    else:
                        key['stim_on_times_status'] = 'Complete'
                else:
                    key['stim_on_times_status'] = 'Missing'

            if '_ibl_trials.repNum.npy' not in datasets:
                key['rep_num_status'] = 'Missing'
            else:
                key['rep_num_status'] = 'Complete'

            if '_ibl_trials.included.npy' not in datasets:
                key['included_status'] = 'Missing'
            else:
                key['included_status'] = 'Complete'

            if '_iblrig_ambientSensorData.raw.jsonable' not in datasets:
                key['ambient_sensor_data_status'] = 'Missing'
            else:
                key['ambient_sensor_data_status'] = 'Complete'

            if '_ibl_trials.goCue_times.npy' not in datasets:
                key['go_cue_times_status'] = 'Missing'
            else:
                key['go_cue_times_status'] = 'Complete'

            if '_ibl_trials.goCueTrigger_times.npy' not in datasets:
                key['go_cue_trigger_times_status'] = 'Missing'
            else:
                key['go_cue_trigger_times_status'] = 'Complete'

            if '_ibl_trials.rewardVolume.npy' not in datasets:
                key['reward_volume_status'] = 'Missing'
            else:
                key['reward_volume_status'] = 'Complete'

            if '_ibl_trials.itiDuration.npy' not in datasets:
                key['iti_duration_status'] = 'Missing'
            else:
                key['iti_duration_status'] = 'Complete'

            self.insert1(key)


@schema
class TrialSet(dj.Imported):
    definition = """
    # information about behavioral trials
    -> acquisition.Session
    ---
    n_trials:                int      # total trial numbers in this set
    n_correct_trials=null:   int      # number of the correct trials
    trials_start_time:       float    # start time of the trial set (seconds)
    trials_end_time:         float    # end time of the trial set (seconds)
    """

    # Knowledge based hack to be formalized better later
    key_source = acquisition.Session & CompleteTrialSession

    def make(self, key):

        trial_key = key.copy()
        eID = str((acquisition.Session & key).fetch1('session_uuid'))
        dtypes = [
            'trials.feedback_times',
            'trials.feedbackType',
            'trials.intervals',
            'trials.choice',
            'trials.response_times',
            'trials.contrastLeft',
            'trials.contrastRight',
            'trials.probabilityLeft',
            'trials.stimOn_times',
            'trials.repNum',
            'trials.included',
            'trials.goCue_times',
            'trials.goCueTrigger_times',
            'trials.rewardVolume',
            'trials.itiDuration'
            ]

        files = one.load(
            eID, dataset_types=dtypes, download_only=True, clobber=True)
        ses_path = alf.io.get_session_path(files[0])
        trials = alf.io.load_object(
            ses_path.joinpath('alf'), 'trials')

        status = (CompleteTrialSession & key).fetch1()

        lab_name = (subject.SubjectLab & key).fetch1('lab_name')
        if status['stim_on_times_status'] != 'Missing':
            if len(trials['stimOn_times']) == 1:
                trials['stimOn_times'] = np.squeeze(trials['stimOn_times'])

        assert len(np.unique(np.array([len(trials['feedback_times']),
                                       len(trials['feedbackType']),
                                       len(trials['intervals']),
                                       len(trials['choice']),
                                       len(trials['response_times']),
                                       len(trials['contrastLeft']),
                                       len(trials['contrastRight']),
                                       len(trials['probabilityLeft'])
                                       ]))) == 1
        'Loaded trial files do not have the same length'

        key['n_trials'] = len(trials['choice'])
        key['n_correct_trials'] = \
            sum((np.squeeze(trials['choice']) == 1) &
                (np.squeeze(trials['contrastLeft']) > 0)) \
            + sum((np.squeeze(trials['choice']) == -1) &
                  (np.squeeze(trials['contrastRight']) > 0))

        key['trials_start_time'] = trials['intervals'][0, 0]
        key['trials_end_time'] = trials['intervals'][-1, 1]

        self.insert1(key)

        trial_entries = []
        for idx_trial in range(len(trials['choice'])):

            if np.any(np.isnan([trials['intervals'][idx_trial, 1],
                                trials['choice'][idx_trial],
                                trials['probabilityLeft'][idx_trial]])):
                continue

            trial = trial_key.copy()
            c_left = trials['contrastLeft'][idx_trial]
            c_right = trials['contrastRight'][idx_trial]
            trial.update(
                trial_id=idx_trial+1,
                trial_start_time=float(trials['intervals'][idx_trial, 0]),
                trial_end_time=float(trials['intervals'][idx_trial, 1]),
                trial_response_time=float(trials['response_times'][idx_trial]),
                trial_stim_contrast_left=0 if np.isnan(c_left) else float(c_left),
                trial_stim_contrast_right=0 if np.isnan(c_right) else float(c_right),
                trial_feedback_time=float(trials['feedback_times'][idx_trial]),
                trial_feedback_type=int(trials['feedbackType'][idx_trial]),
                trial_stim_prob_left=float(trials['probabilityLeft'][idx_trial]),
                trial_stim_on_time=float(trials['stimOn_times'][idx_trial])
                if status['stim_on_times_status'] != 'Missing' else None,
                trial_rep_num=int(trials['repNum'][idx_trial])
                if status['rep_num_status'] != 'Missing' else None,
                trial_included=bool(trials['included'][idx_trial])
                if status['included_status'] != 'Missing' else None,
                trial_go_cue_time=float(trials['goCue_times'][idx_trial])
                if status['go_cue_times_status'] != 'Missing' else None,
                trial_go_cue_trigger_time=float(
                    trials['goCueTrigger_times'][idx_trial])
                if status['go_cue_trigger_times_status'] != 'Missing' else None,
                trial_reward_volume=float(trials['rewardVolume'][idx_trial])
                if status['reward_volume_status'] != 'Missing' else None,
                trial_iti_duration=float(trials['itiDuration'][idx_trial])
                if status['iti_duration_status'] != 'Missing' else None
            )

            if trials['choice'][idx_trial] == -1:
                trial['trial_response_choice'] = "CCW"
            elif trials['choice'][idx_trial] == 0:
                trial['trial_response_choice'] = "No Go"
            elif trials['choice'][idx_trial] == 1:
                trial['trial_response_choice'] = "CW"
            else:
                raise ValueError('Invalid reponse choice.')

            trial_entries.append(trial)

        self.Trial.insert(trial_entries)

        logger.info('Populated a TrialSet tuple, \
            all Trial tuples and Excluded Trial tuples for \
            subject {subject_uuid} in session started at \
            {session_start_time}'.format(**trial_key))

    class Trial(dj.Part):
        # all times are in absolute seconds, rather than relative to trial onset
        definition = """
        -> master
        trial_id:               int           # trial identification number
        ---
        trial_start_time:           double        # beginning of quiescent period time (seconds)
        trial_end_time:             double        # end of iti (seconds)
        trial_response_time=null:   double        # Time of "response" in choiceworld (seconds). This is when one of the three possible choices is registered in software, will not be the same as when the mouse's movement to generate that response begins.
        trial_response_choice:      enum("CCW", "CW", "No Go")       # which choice was made in choiceworld
        trial_stim_on_time=null:    double        # Time of stimulus in choiceworld (seconds)
        trial_stim_contrast_left:   float	      # contrast of the stimulus on the left
        trial_stim_contrast_right:  float         # contrast of the stimulus on the right
        trial_feedback_time=null:   double        # Time of feedback delivery (reward or not) in choiceworld
        trial_feedback_type=null:   tinyint       # whether feedback is positive or negative in choiceworld (-1 for negative, +1 for positive)
        trial_rep_num=null:         int     	  # the repetition number of the trial, i.e. how many trials have been repeated on this side (counting from 1)
        trial_go_cue_time=null:     float
        trial_go_cue_trigger_time=null:  float
        trial_stim_prob_left:       float         # probability of the stimulus being present on left
        trial_reward_volume=null:   float         # reward volume of each trial
        trial_iti_duration=null:    float         # inter-trial interval
        trial_included=null:        bool          # whether the trial should be included
        """

    class ExcludedTrial(dj.Part):
        definition = """
        -> master
        -> TrialSet.Trial
        """


@schema
class SessionDelayAvailability(dj.Imported):
    definition = """
    -> acquisition.Session
    ---
    error_type:    enum("elapsed time not available", "raw task data not available", "delay not available")
    """


@schema
class SessionDelay(dj.Imported):
    definition = """
    -> acquisition.Session
    ---
    session_delay_in_secs:      float       # session delay in seconds
    session_delay_in_mins:      float       # session delay in minutes
    """

    # only check missing data within 5 days
    date = datetime.datetime.today() - datetime.timedelta(days=5)
    key_source = TrialSet() - \
        (SessionDelayAvailability() & 'session_start_time < "{}"'.format(
            date.strftime('%Y-%m-%d')))

    def make(self, key):

        eID = (acquisition.Session & key).fetch1('session_uuid')
        json = one.alyx.get(one.get_details(str(eID))['url'])['json']

        if 'SESSION_START_DELAY_SEC' in json.keys():
            self.insert1(dict(
                **key,
                session_delay_in_secs=json['SESSION_START_DELAY_SEC'],
                session_delay_in_mins=json['SESSION_START_DELAY_SEC'] / 60
            ))
        else:
            key['error_type'] = 'delay not available'
            SessionDelayAvailability.insert1(
                key, allow_direct_insert=True,
                skip_duplicates=True)


@schema
class SettingsAvailability(dj.Imported):
    definition = """
    -> acquisition.Session
    ---
    error_type:     varchar(128)   # error message
    """


@schema
class Settings(dj.Imported):
    definition = """
    -> acquisition.Session
    ---
    pybpod_board:    varchar(64)   # bpod machine that generated the session
    """

    # only check missing data within 5 days
    date = datetime.datetime.today() - datetime.timedelta(days=5)
    key_source = TrialSet() - \
        (SettingsAvailability() & 'session_start_time < "{}"'.format(
            date.strftime('%Y-%m-%d')))

    def make(self, key):
        eID = str((acquisition.Session & key).fetch1('session_uuid'))
        try:
            setting = one.load(eID, dataset_types='_iblrig_taskSettings.raw',
                               clobber=True)
        except Exception as e:
            key['error_type'] = 'settings not available'
            SettingsAvailability.insert1(key, allow_direct_insert=True)
            return

        if setting is None:
            key['error_type'] = 'settings not available'
            SettingsAvailability.insert1(key, allow_direct_insert=True)
            return
        elif not len(setting):
            key['error_type'] = 'settings not available'
            SettingsAvailability.insert1(key, allow_direct_insert=True)
            return
        elif setting[0] is None:
            key['error_type'] = 'settings not available'
            SettingsAvailability.insert1(key, allow_direct_insert=True)
            return
        elif setting[0]['PYBPOD_BOARD'] is None:
            key['error_type'] = 'settings not available'
            SettingsAvailability.insert1(key, allow_direct_insert=True)
            return
        key['pybpod_board'] = setting[0]['PYBPOD_BOARD']
        self.insert1(key)


@schema
class AmbientSensorData(dj.Imported):
    definition = """
    -> TrialSet.Trial
    ---
    temperature_c:           float
    air_pressure_mb:         float
    relative_humidity=null:  float
    """
    key_source = CompleteTrialSession & 'ambient_sensor_data_status="Complete"'

    def make(self, key):
        trial_key = key.copy()
        eID = str((acquisition.Session & key).fetch1('session_uuid'))
        asd = one.load(eID, dataset_types='_iblrig_ambientSensorData.raw',
                       clobber=True)

        if not len(TrialSet.Trial & key) == len(asd[0]):
            print('Size of ambient sensor data does not match the trial number')
            return

        for idx_trial, asd_trial in enumerate(asd[0]):
            trial_key['trial_id'] = idx_trial + 1
            trial_key['temperature_c'] = asd_trial['Temperature_C'][0]
            trial_key['air_pressure_mb'] = asd_trial['AirPressure_mb'][0]
            trial_key['relative_humidity'] = asd_trial['RelativeHumidity'][0]
            self.insert1(trial_key)


# ---- SessionTag ----


@schema
class Tag(dj.Lookup):
    definition = """
    tag: varchar(32)
    ---
    description='': varchar(32)
    """

    contents = [
        ("Repeated-Site-2022", "move-to-public"),
        ("Behavior-2022", "move-to-public"),
    ]


@schema
class SessionTag(dj.Computed):
    definition = """
    -> acquisition.Session
    """

    class Tag(dj.Part):
        definition = """
        -> master
        -> Tag
        """

    key_source = acquisition.Session & CompleteTrialSession

    def make(self, key):
        self.insert1(key, skip_duplicates=True)
        sess_uuid = (acquisition.Session & key).fetch1("session_uuid")

        # code block to auto retrieve from one.alyx.rest()
        all_tags = []
        for d in one.alyx.rest("datasets", "list", session=str(sess_uuid), silent=True):
            all_tags.extend(d["tags"])

        tag_lookup_data = [{"tag": tag, "description": "alyx"} for tag in set(all_tags)]
        if tag_lookup_data:
            Tag.insert(tag_lookup_data, skip_duplicates=True)

        # custom code block to determine additional tags a session may have
        if "Repeated site" in all_tags:
            all_tags.append("Repeated-Site-2022")
        if "Behaviour Paper" in all_tags:
            all_tags.append("Behavior-2022")

        tag_part_data = [{**key, "tag": tag} for tag in set(all_tags)]
        if tag_part_data:
            [print("Tagging: ", tag) for tag in tag_part_data]
            self.Tag.insert(tag_part_data, skip_duplicates=True)
