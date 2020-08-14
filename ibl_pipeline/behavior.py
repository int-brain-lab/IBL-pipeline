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
    one = ONE()
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
class Eye(dj.Imported):
    definition = """
    # eye recording
    -> acquisition.Session
    ---
    eye_sample_ids:     longblob        # Sample ids corresponding to the timestamps
    eye_timestamps:     longblob        # Timestamps for pupil tracking timeseries (seconds)
    eye_raw_dir=null:   varchar(256)    # directory of the raw datafile
    eye_area:           longblob        # Area of pupil (pixels^2)
    eye_x_pos:          longblob        # x position of pupil (pixels)
    eye_y_pos:          longblob        # y position of pupil (pixels)
    eye_blink:          longblob        # Boolean array saying whether eye was blinking in each frame
    eye_fps:            float           # Frames per second
    eye_start_time:     float           # (seconds)
    eye_end_time:       float           # (seconds)
    """

    key_source = acquisition.Session & (data.FileRecord & {'exists': 1} & 'dataset_name in \
                    ("eye.area.npy", "eye.blink.npy", \
                     "eye.xyPos.npy", "eye.timestamps.npy")')

    def make(self, key):

        eID = str((acquisition.Session & key).fetch1('session_uuid'))
        eye_area, eye_blink, eye_xypos, eye_timestamps = \
            one.load(eID, dataset_types=['eye.area',
                                         'eye.blink',
                                         'eye.xypos',
                                         'eye.timestamps'])

        eye_sample_ids = eye_timestamps[:, 0]
        eye_timestamps = eye_timestamps[:, 1]

        assert len(np.unique(np.array([len(eye_xypos),
                                       len(eye_blink),
                                       len(eye_area)]))) == 1, \
            'Loaded eye files do not have the same length'

        key['eye_sample_ids'] = eye_sample_ids
        key['eye_timestamps'] = eye_timestamps
        key['eye_area'] = eye_area
        key['eye_x_pos'] = eye_xypos[:, 0]
        key['eye_y_pos'] = eye_xypos[:, 1]
        key['eye_blink'] = eye_blink
        key['eye_fps'] = 1 / np.median(np.diff(eye_timestamps))
        key['eye_start_time'] = eye_timestamps[0]
        key['eye_end_time'] = eye_timestamps[-1]

        self.insert1(key)
        logger.info('Populated an Eye tuple for subject {subject_uuid} \
            on session started at {session_start_time}'.format(
            **key))


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
class WheelMoveType(dj.Lookup):
    definition = """
    wheel_move_type:   varchar(64)   # movement type
    """
    contents = [['CW'], ['CCW'], ['Flinch'], ['Other']]


@schema
class CompleteWheelMoveSession(dj.Computed):
    definition = """
    # sessions that are complete with wheel related information and thus may be ingested
    -> acquisition.Session
    """

    required_datasets = ["_ibl_wheelMoves.intervals.npy",
                         "_ibl_wheelMoves.type.csv"]

    def make(self, key):
        datasets = (data.FileRecord & key & {'exists': 1}).fetch(
            'dataset_name')
        if bool(np.all([req_ds in datasets
                for req_ds in self.required_datasets])):
            self.insert1(key)


@schema
class WheelMoveSet(dj.Imported):
    definition = """
    # detected wheel movements
    -> acquisition.Session
    ---
    wheel_move_number : int     # total number of movements in this set
    """
    key_source = CompleteWheelMoveSession()

    def make(self, key):
        wheel_move_key = key.copy()

        eID = str((acquisition.Session & key).fetch1('session_uuid'))
        wheel_moves_intervals, wheel_moves_types = \
            one.load(eID, dataset_types=['wheelMoves.intervals',
                                         'wheelMoves.type'])

        wheel_moves_types = wheel_moves_types.columns

        assert len(np.unique(np.array([len(wheel_moves_intervals),
                                       len(wheel_moves_types)]))) == 1, \
            'Loaded wheel move files do not have the same length'

        key['wheel_move_number'] = len(wheel_moves_types)
        self.insert1(key)

        for idx_move in range(len(wheel_moves_types)):
            wheel_move_key['wheel_move_id'] = idx_move + 1
            wheel_move_key['wheel_move_start_time'] = \
                wheel_moves_intervals[idx_move, 0]
            wheel_move_key['wheel_move_end_time'] = \
                wheel_moves_intervals[idx_move, 1]

            wheel_move_type = wheel_moves_types[idx_move]
            if 'CCW' in wheel_move_type:
                wheel_move_key['wheel_move_type'] = 'CCW'
            elif 'flinch' in wheel_move_type:
                wheel_move_key['wheel_move_type'] = 'flinch'
            else:
                wheel_move_key['wheel_move_type'] = 'CW'

            self.WheelMove().insert1(wheel_move_key)

        logger.info('Populated a WheelMoveSet and all WheelMove tuples for \
            subject {subject_uuid} in session started at \
            {session_start_time}'.format(**key))

    class WheelMove(dj.Part):
        definition = """
        -> master
        wheel_move_id:          int     # identifier of a wheel movement
        ---
        wheel_move_start_time:  float   # onset time of the detected wheel movement (seconds)
        wheel_move_end_time:    float   # offset time of the detected wheel movement (seconds)
        -> WheelMoveType
        """


@schema
class SparseNoise(dj.Imported):
    definition = """
    -> acquisition.Session
    ---
    sparse_noise_x_pos:  longblob	# x coordiate on screen of sparse noise stimulus squares (WHAT UNIT?)
    sparse_noise_y_pos:  longblob	# y coordiate on screen of sparse noise stimulus squares (WHAT UNIT?)
    sparse_noise_times:  longblob	# times of those stimulus squares appeared in universal seconds
    """

    key_source = acquisition.Session & \
        (data.FileRecord & {'exists': 1} &
         'dataset_name in ("_ibl_sparseNoise.positions.npy", \
                           "_ibl_sparseNoise.times.npy")')

    def make(self, key):

        eID = str((acquisition.Session & key).fetch1('session_uuid'))

        sparse_noise_positions, sparse_noise_times = \
            one.load(eID, dataset_types=['sparseNoise.positions',
                                         'sparseNoise.times'])

        assert len(np.unique(np.array([len(sparse_noise_positions),
                                       len(sparse_noise_times)]))) == 1, \
            'Loaded sparse noise files do not have the same length'

        key['sparse_noise_x_pos'] = sparse_noise_positions[:, 0],
        key['sparse_noise_y_pos'] = sparse_noise_positions[:, 1],
        key['sparse_noise_times'] = sparse_noise_times
        self.insert1(key)
        logger.info('Populated a SparseNoise tuple for subject {subject_uuid} \
            in session started at {session_start_time}'.format(**key))


@schema
class ExtraRewards(dj.Imported):
    definition = """
    # information about extra rewards given manually by the experimenter
    -> acquisition.Session
    ---
    extra_rewards_times: longblob 			# times of extra rewards (seconds)
    """

    key_source = acquisition.Session & \
        (data.FileRecord & {'exists': 1} &
            'dataset_name in ("_ibl_extraRewards.times.npy")')

    def make(self, key):

        eID = (acquisition.Session & key).fetch1('session_uuid')

        extra_rewards_times = \
            one.load(eID, dataset_types=['extraRewards.times'])

        key['extra_rewards_times'] = extra_rewards_times

        self.insert1(key)

        logger.info('Populated an ExtraRewards tuple for \
            subject {subject_uuid} in session started at \
            {session_start_time}'.format(**key))


@schema
class SpontaneousTimeSet(dj.Imported):
    definition = """
    # times when no other protocol was going on for at least 30 sec or so
    -> acquisition.Session
    ---
    spontaneous_time_total_num:   int   # total number of the spontaneous time periods
    """

    key_source = acquisition.Session & \
        (data.FileRecord & {'exists': 1} &
         'dataset_name in ("_ibl_spontaneous.intervals.npy")')

    def make(self, key):
        spon_time_key = key.copy()

        eID = str((acquisition.Session & key).fetch1('session_uuid'))

        spontaneous_intervals = \
            one.load(eID, dataset_types=['spontaneous.intervals'])

        key['spontaneous_time_total_num'] = len(spontaneous_intervals)
        self.insert1(key)

        for idx_spon in range(len(spontaneous_intervals)):
            spon_time_key['spontaneous_time_id'] = idx_spon + 1
            spon_time_key['spontaneous_start_time'] = \
                spontaneous_intervals[idx_spon, 0]
            spon_time_key['spontaneous_end_time'] = \
                spontaneous_intervals[idx_spon, 1]
            spon_time_key['spontaneous_time_duration'] = \
                float(np.diff(spontaneous_intervals[idx_spon, :]))
            self.SpontaneousTime().insert1(spon_time_key)

        logger.info('Populated a SpontaneousTimeSet tuple and all \
            Spontaneoustime tuples for subject {subject_uuid} in \
                session started at {session_start_time}'.format(**key))

    class SpontaneousTime(dj.Part):
        definition = """
        -> master
        spontaneous_time_id: int    # index of spontanoeous time
        ---
        spontaneous_start_time:     float    # (seconds)
        spontaneous_end_time:       float    # (seconds)
        spontaneous_time_duration:  float    # (seconds)
        """


@schema
class Lick(dj.Imported):
    definition = """
    # detected licks
    -> acquisition.Session
    ---
    lick_times:             longblob  # Times of licks
    lick_piezo_raw = null:  longblob  # Raw lick trace (volts)
    lick_sample_ids:        longblob  # Sample ids corresponding to the timestamps
    lick_piezo_timestamps:  longblob  # Timestamps for lick trace timeseries (seconds)
    lick_start_time:        float     # recording start time (seconds)
    lick_end_time:          float     # recording end time (seconds)]
    lick_sampling_rate:     float     # number of samples per second
    """

    key_source = acquisition.Session & \
        (data.FileRecord & {'exists': 1} &
         'dataset_name in ("_ibl_licks.times.npy", \
                           "_ibl_lickPiezo.raw.npy", \
                           "_ibl_lickPiezo.timestamps.npy")')

    def make(self, key):

        eID = (acquisition.Session & key).fetch1('session_uuid')

        lick_times, lick_piezo_raw, lick_piezo_timestamps = \
            one.load(eID, dataset_types=['licks.times',
                                         'lickPiezo.raw',
                                         'lickPiezo.timestamps'])

        lick_sample_ids = lick_piezo_timestamps[:, 0]
        lick_piezo_timestamps = lick_piezo_timestamps[:, 1]

        key['lick_times'] = lick_times
        key['lick_piezo_raw'] = lick_piezo_raw
        key['lick_sample_ids'] = lick_sample_ids
        key['lick_piezo_timestamps'] = lick_piezo_timestamps
        key['lick_start_time'] = lick_piezo_timestamps[0]
        key['lick_end_time'] = lick_piezo_timestamps[-1]
        key['lick_sampling_rate'] = \
            1 / np.median(np.diff(lick_piezo_timestamps))

        self.insert1(key)

        logger.info('Populated a Lick tuple for \
            subject {subject_uuid} in session started at \
            {session_start_time}'.format(**key))


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

                if np.all(np.isnan(stimOn_times)):
                    key['stim_on_times_status'] = 'Missing'
                elif np.any(np.isnan(stimOn_times)):
                    key['stim_on_times_status'] = 'Partial'
                else:
                    key['stim_on_times_status'] = 'Complete'

            if '_ibl_trials.repNum.npy' not in datasets:
                key['rep_num_status'] = 'Missing'
            else:
                key['rep_num_status'] = 'Complete'

            if 'ibl_trials.included.npy' not in datasets:
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
    if not environ.get('MODE') == 'test':
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
            ses_path.joinpath('alf'), '_ibl_trials')

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
    error_type:    enum("elapsed time not available", "raw task data not available")
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
        data = one.load(str(eID), dataset_types=['_iblrig_taskData.raw'])
        trial_start, trial_end = (TrialSet.Trial & key & 'trial_id=1').fetch1(
            'trial_start_time', 'trial_end_time')
        first_trial_duration = trial_end - trial_start

        if data[0]:
            if 'elapsed_time' in data[0][0].keys():
                elapsed_time = data[0][0]['elapsed_time'].split(':')
                key['session_delay_in_secs'] = float(elapsed_time[1])*60 + \
                    float(elapsed_time[2]) - first_trial_duration
                key['session_delay_in_mins'] = key['session_delay_in_secs']/60
                self.insert1(key)
            else:
                key['error_type'] = 'raw task data not available'
                SessionDelayAvailability.insert1(key, allow_direct_insert=True)
        else:
            key['error_type'] = 'elapsed time not available'
            SessionDelayAvailability.insert1(key, allow_direct_insert=True)


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


@schema
class PassiveTrialSet(dj.Imported):
    definition = """
    -> acquisition.Session
    ---
    passive_trials_total_num : int
    passive_trials_start_time : float
    passive_trials_end_time : float
    """

    key_source = acquisition.Session & (data.FileRecord & {'exists': 1} &
                                        'dataset_name in \
                                        ("passiveTrials.contrastLeft.npy", \
                                        "passiveTrials.contrastRight.npy", \
                                        "_ibl_lickPiezo.timestamps.npy")')

    def make(self, key):

        passive_trial_key = key.copy()
        eID = str((acquisition.Session & key).fetch1('session_uuid'))

        passive_visual_stim_contrast_left, passive_visual_stim_contrast_right = \
            one.load(eID, dataset_types=['passiveTrials.contrastLeft',
                                         'passiveTrials.contrastRight',
                                         'passiveTrials.times'],
                     clobber=True)

        assert len(np.unique(np.array([len(passive_visual_stim_contrast_left),
                                       len(passive_visual_stim_contrast_right),
                                       len(passive_visual_stim_times)]))) == 1, \
            'Loaded passive visual files do not have the same length'

        key['passive_trials_total_num'] = len(passive_visual_stim_times)
        key['passive_trials_start_time'] = float(passive_visual_stim_times[0])
        key['passive_trials_end_time'] = float(passive_visual_stim_times[-1])

        self.insert1(key)

        for idx_trial in range(len(passive_visual_stim_times)):

            if np.isnan(passive_visual_stim_contrast_left[idx_trial]):
                passive_stim_contrast_left = 0
            else:
                passive_stim_contrast_left = \
                    passive_visual_stim_contrast_left[idx_trial]

            if np.isnan(passive_visual_stim_contrast_right[idx_trial]):
                passive_stim_contrast_right = 0
            else:
                passive_stim_contrast_right = \
                    passive_visual_stim_contrast_right[idx_trial]

            passive_trial_key['passive_trial_id'] = idx_trial + 1
            passive_trial_key['passive_trial_stim_on_time'] = float(
                passive_visual_stim_times[idx_trial])
            passive_trial_key['passive_trial_stim_contrast_left'] = float(
                passive_stim_contrast_left)
            passive_trial_key['passive_trial_stim_contrast_right'] = float(
                passive_stim_contrast_right)

            self.PassiveTrial().insert1(passive_trial_key)

        logger.info('Populated a PassiveTrialSet tuple, all Trial tuples and \
            Excluded Trial tuples for subject {subject_uuid} in \
                session started at {session_start_time}'.format(**key))

    class PassiveTrial(dj.Part):
        definition = """
        -> master
        passive_trial_id:           int         # trial identifier
        ---
        passive_trial_stim_on_time:          float	# Time of stimuli in choiceworld
        passive_trial_stim_contrast_left:    float 	# contrast of the stimulus on the left
        passive_trial_stim_contrast_right:   float   # contrast of the stimulus on the right
        """


@schema
class PassiveRecordings(dj.Imported):
    definition = """
    -> acquisition.Session
    ---
    passive_valve_click_times:      longblob      # Times of valve opening during passive trial presentation (seconds)
    passive_beep_times:             longblob      # Times of the beeps, equivilent to the go cue during the choice world task (seconds)
    passive_white_noise_times:      longblob      # Times of white noise bursts, equivilent to the negative feedback sound during the choice world task (seconds)
    """

    key_source = acquisition.Session & (data.FileRecord & 'repo_name LIKE "flatiron_%"' & {'exists': 1} & 'dataset_name in \
        ("passiveBeeps.times.npy", "passiveValveClicks.times.npy", "passiveWhiteNoise.times.npy")')

    def make(self, key):

        eID = str((acquisition.Session & key).fetch1('session_uuid'))

        key['passive_beep_times'], key['passive_valve_click_times'], \
            key['passive_white_noise_times'] = \
            one.load(eID, dataset_types=['passiveBeeps.times',
                                         'passiveValveClicks.times',
                                         'passiveWhiteNoise.times'],
                     clobber=True)

        self.insert1(key)
