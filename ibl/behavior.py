import datajoint as dj
import numpy as np
from os import path
import logging
from . import acquisition

logger = logging.getLogger(__name__)
schema = dj.schema('ibl_behavior')

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
    def make(self, key):

        datapath = path.join('data', '{subject_id}-{session_start_time}/'.format(**key))
        eye_area = np.load('{}eye.area.npy'.format(datapath))
        eye_blink = np.load('{}eye.blink.npy'.format(datapath))
        eye_xypos = np.load('{}eye.xyPos.npy'.format(datapath))
        eye_timestamps = np.load('{}eye.timestamps.npy'.format(datapath))
        eye_sample_ids = eye_timestamps[:, 0]
        eye_timestamps = eye_timestamps[:, 1]

        assert len(np.unique(np.array([len(eye_xypos),
                                       len(eye_blink),
                                       len(eye_area)]))) == 1, 'Loaded eye files do not have the same length'

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
        logger.info('Populated an Eye tuple for subject {subject_id} on {session_start_time}'.format(**key))

@schema
class Wheel(dj.Imported):
    definition = """
    # raw wheel recording
    -> acquisition.Session
    ---
    wheel_position:         longblob  # Absolute position of wheel (cm)
    wheel_velocity:         longblob  # Signed velocity of wheel (cm/s) positive = CW
    wheel_sample_ids:       longblob  # Sample ids corresponding to the timestamps
    wheel_timestamps:       longblob  # Timestamps for wheel timeseries (seconds)
    wheel_start_time:       float     # Start time of wheel recording (seconds)
    wheel_end_time:         float     # End time of wheel recording (seconds)
    wheel_duration:         float     # Duration time of wheel recording (seconds)
    wheel_sampling_rate:    float     # Samples per second
    """
    def make(self, key):
        datapath = path.join('data', '{subject_id}-{session_start_time}/'.format(**key))
        wheel_position = np.load('{}_ibl_wheel.position.npy'.format(datapath))
        wheel_timestamps = np.load('{}_ibl_wheel.timestamps.npy'.format(datapath))

        wheel_sample_ids = wheel_timestamps[:, 0]
        wheel_timestamps = wheel_timestamps[:, 1]
        wheel_sampling_rate = 1 / np.median(np.diff(wheel_timestamps))

        key['wheel_position'] = wheel_position
        key['wheel_velocity'] = np.diff(wheel_position)*wheel_sampling_rate
        key['wheel_sample_ids'] = wheel_sample_ids
        key['wheel_timestamps'] = wheel_timestamps
        key['wheel_start_time'] = wheel_timestamps[0]
        key['wheel_end_time'] = wheel_timestamps[-1]
        key['wheel_duration'] = wheel_timestamps[-1] - wheel_timestamps[0]
        key['wheel_sampling_rate'] = wheel_sampling_rate

        self.insert1(key)
        logger.info('Populated a Wheel tuple for subject {subject_id} in session started at {session_start_time}'.format(**key))

@schema
class WheelMoveType(dj.Lookup):
    definition = """
    wheel_move_type:   varchar(64)   # movement type
    """
    contents = [['CW'], ['CCW'], ['Flinch'], ['Other']]

@schema
class WheelMoveSet(dj.Imported):
    definition = """
    # detected wheel movements
    -> Wheel
    ---
    wheel_move_number : int     # total number of movements in this set
    """
    def make(self, key):
        wheel_move_key = key.copy()

        datapath = path.join('data', '{subject_id}-{session_start_time}/'.format(**key))
        wheel_moves_intervals = np.load('{}_ns_wheelMoves.intervals.npy'.format(datapath))
        wheel_moves_types = np.load('{}_ns_wheelMoves.type.npy'.format(datapath))

        assert len(np.unique(np.array([len(wheel_moves_intervals), len(wheel_moves_types)]))) == 1, 'Loaded wheel move files do not have the same length'

        wheel_moves_types_str = np.array(["" for x in range(len(wheel_moves_types))], dtype='<U10')
        # mapping between numbers and "CW" etc need to be confirmed
        wheel_moves_types_str[wheel_moves_types.ravel()==0] = "CW"
        wheel_moves_types_str[wheel_moves_types.ravel()==1] = "CCW"
        wheel_moves_types_str[wheel_moves_types.ravel()==2] = "Flinch"

        key['wheel_move_number'] = len(wheel_moves_types)
        self.insert1(key)

        for idx_move in range(len(wheel_moves_types)):
            wheel_move_key['wheel_move_id'] = idx_move + 1
            wheel_move_key['wheel_move_start_time'] = wheel_moves_intervals[idx_move, 0]
            wheel_move_key['wheel_move_end_time'] = wheel_moves_intervals[idx_move, 1]
            wheel_move_key['wheel_move_type'] = wheel_moves_types_str[idx_move]
            self.WheelMove().insert1(wheel_move_key)

        logger.info('Populated a WheelMoveSet and all WheelMove tuples for subject {subject_id} in session started at {session_start_time}'.format(**key))

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
    sparse_noise_x_pos:  longblob				# x coordiate on screen of sparse noise stimulus squares (WHAT UNIT?)
    sparse_noise_y_pos:  longblob				# y coordiate on screen of sparse noise stimulus squares (WHAT UNIT?)
    sparse_noise_times:  longblob				# times of those stimulus squares appeared in universal seconds
    """
    def make(self, key):
        datapath = path.join('data', '{subject_id}-{session_start_time}/'.format(**key))
        sparse_noise_positions = np.load('{}_ns_sparseNoise.positions.npy'.format(datapath))
        sparse_noise_times = np.load('{}_ns_sparseNoise.times.npy'.format(datapath))

        assert len(np.unique(np.array([len(sparse_noise_positions), len(sparse_noise_times)]))) == 1, 'Loaded sparse noise files do not have the same length'

        key['sparse_noise_x_pos'] = sparse_noise_positions[:, 0],
        key['sparse_noise_y_pos'] = sparse_noise_positions[:, 1],
        key['sparse_noise_times'] = sparse_noise_times
        self.insert1(key)
        logger.info('Populated a SparseNoise tuple for subject {subject_id} in session started at {session_start_time}'.format(**key))

@schema
class ExtraRewards(dj.Imported):
    definition = """
    # information about extra rewards given manually by the experimenter
    -> acquisition.Session
    ---
    extra_rewards_times: longblob 			# times of extra rewards (seconds)
    """
    def make(self, key):
        datapath = path.join('data', '{subject_id}-{session_start_time}/'.format(**key))
        extra_rewards_times = np.load('{}_ibl_extraRewards.times.npy'.format(datapath))

        key['extra_rewards_times'] = extra_rewards_times

        self.insert1(key)

        logger.info('Populated an ExtraRewards tuple for subject {subject_id} in session started at {session_start_time}'.format(**key))


@schema
class SpontaneousTimeSet(dj.Imported):
    definition = """
    # times when no other protocol was going on for at least 30 sec or so
    -> acquisition.Session
    ---
    spontaneous_time_total_num:   int   # total number of the spontaneous time periods
    """
    def make(self, key):
        spon_time_key = key.copy()

        datapath = path.join('data', '{subject_id}-{session_start_time}/'.format(**key))
        spontaneous_intervals = np.load('{}spontaneous.intervals.npy'.format(datapath))

        key['spontaneous_time_total_num'] = len(spontaneous_intervals)
        self.insert1(key)

        for idx_spon in range(len(spontaneous_intervals)):
            spon_time_key['spontaneous_time_id'] = idx_spon + 1
            spon_time_key['spontaneous_start_time'] = spontaneous_intervals[idx_spon, 0]
            spon_time_key['spontaneous_end_time'] = spontaneous_intervals[idx_spon, 1]
            spon_time_key['spontaneous_time_duration'] = float(np.diff(spontaneous_intervals[idx_spon, :]))
            self.SpontaneousTime().insert1(spon_time_key)

        logger.info('Populated a SpontaneousTimeSet tuple and all Spontaneoustime tuples for subject {subject_id} in session started at {session_start_time}'.format(**key))

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
    def make(self, key):

        datapath = path.join('data', '{subject_id}-{session_start_time}/'.format(**key))
        lick_times = np.load('{}licks.times.npy'.format(datapath))
        lick_piezo_raw = np.load('{}_ibl_lickPiezo.raw.npy'.format(datapath))
        lick_piezo_timestamps = np.load('{}_ibl_lickPiezo.timestamps.npy'.format(datapath))

        lick_sample_ids = lick_piezo_timestamps[:, 0]
        lick_piezo_timestamps = lick_piezo_timestamps[:, 1]

        key['lick_times'] = lick_times
        key['lick_piezo_raw'] = lick_piezo_raw
        key['lick_sample_ids'] = lick_sample_ids
        key['lick_piezo_timestamps'] = lick_piezo_timestamps
        key['lick_start_time'] = lick_piezo_timestamps[0]
        key['lick_end_time'] = lick_piezo_timestamps[-1]
        key['lick_sampling_rate'] = 1 / np.median(np.diff(lick_piezo_timestamps))

        self.insert1(key)

        logger.info('Populated a Lick tuple for subject {subject_id} in session started at {session_start_time}'.format(**key))


@schema
class TrialSet(dj.Imported):
    definition = """
    # information about behavioral trials
    -> acquisition.Session
    ---
    trials_total_num:   int              # total trial numbers in this set
    trials_start_time:  float            # start time of the trial set (seconds)
    trials_end_time:    float            # end time of the trial set (seconds)
    """
    def make(self, key):
        trial_key = key.copy()
        excluded_trial_key = key.copy()

        datapath = path.join('data', '{subject_id}-{session_start_time}/'.format(**key))
        trials_feedback_times = np.load('{}_ns_trials.feedback_times.npy'.format(datapath))
        trials_feedback_types = np.load('{}_ns_trials.feedbackType.npy'.format(datapath))
        trials_gocue_times = np.load('{}_ns_trials.goCue_times.npy'.format(datapath))
        trials_intervals = np.load('{}_ns_trials.intervals.npy'.format(datapath))
        trials_rep_num = np.load('{}_ns_trials.repNum.npy'.format(datapath))
        trials_response_choice = np.load('{}_ns_trials.response_choice.npy'.format(datapath))
        trials_response_times = np.load('{}_ns_trials.response_times.npy'.format(datapath))
        trials_visual_stim_contrast_left = np.load('{}_ns_trials.visualStim_contrastLeft.npy'.format(datapath))
        trials_visual_stim_contrast_right = np.load('{}_ns_trials.visualStim_contrastRight.npy'.format(datapath))
        trials_visual_stim_times = np.load('{}_ns_trials.visualStim_times.npy'.format(datapath))
        trials_included = np.load('{}_ns_trials.included.npy'.format(datapath))

        assert len(np.unique(np.array([len(trials_feedback_times),
                                       len(trials_feedback_types),
                                       len(trials_gocue_times),
                                       len(trials_intervals),
                                       len(trials_rep_num),
                                       len(trials_response_choice),
                                       len(trials_response_times),
                                       len(trials_visual_stim_contrast_left),
                                       len(trials_visual_stim_contrast_right),
                                       len(trials_visual_stim_times),
                                       len(trials_included)]))) == 1, 'Loaded trial files do not have the same length'

        key['trials_total_num'] = len(trials_response_choice)
        key['trials_start_time'] = trials_intervals[0, 0]
        key['trials_end_time'] = trials_intervals[-1, 1]

        self.insert1(key)

        for idx_trial in range(len(trials_response_choice)):

            if np.isnan(trials_visual_stim_contrast_left[idx_trial]):
                trial_stim_contrast_left = 0
            else:
                trial_stim_contrast_left = trials_visual_stim_contrast_left[idx_trial]

            if np.isnan(trials_visual_stim_contrast_right[idx_trial]):
                trial_stim_contrast_right = 0
            else:
                trial_stim_contrast_right = trials_visual_stim_contrast_right[idx_trial]

            if trials_response_choice[idx_trial] == -1:
                trial_response_choice = "CCW"
            elif trials_response_choice[idx_trial] == 0:
                trial_response_choice = "No Go"
            elif trials_response_choice[idx_trial] == 1:
                trial_response_choice = "CW"
            else:
                raise ValueError('Invalid reponse choice.')

            trial_key['trial_id'] = idx_trial + 1
            trial_key['trial_start_time'] = trials_intervals[idx_trial, 0]
            trial_key['trial_end_time'] = trials_intervals[idx_trial, 0]
            trial_key['trial_go_cue_time'] = float(trials_gocue_times[idx_trial])
            trial_key['trial_response_time'] = float(trials_response_times[idx_trial])
            trial_key['trial_choice'] = trial_response_choice
            trial_key['trial_stim_on_time'] = trials_visual_stim_times[idx_trial, 0]
            trial_key['trial_stim_contrast_left'] = float(trial_stim_contrast_left)
            trial_key['trial_stim_contrast_right'] = float(trial_stim_contrast_right)
            trial_key['trial_feedback_time'] = float(trials_feedback_times[idx_trial])
            trial_key['trial_feedback_type'] = int(trials_feedback_types[idx_trial])
            trial_key['trial_rep_num'] = int(trials_rep_num[idx_trial])

            self.Trial().insert1(trial_key)

            if trials_included[idx_trial] == False:
                excluded_trial_key['trial_id'] = idx_trial + 1
                self.ExcludedTrial().insert1(excluded_trial_key)

        logger.info('Populated a TrialSet tuple, all Trial tuples and Excluded Trial tuples for subject {subject_id} in session started at {session_start_time}'.format(**key))

    class Trial(dj.Part):
        # all times are in absolute seconds, rather than relative to trial onset
        definition = """
        -> master
        trial_id:               int           # trial identification number
        ---
        trial_start_time:           float         # beginning of quiescent period time (seconds)
        trial_end_time:             float         # end of iti (seconds)
        trial_go_cue_time:          float         # Time of go cue in choiceworld (seconds)
        trial_response_time:        float         # Time of "response" in choiceworld (seconds). This is when one of the three possible choices is registered in software, will not be the same as when the mouse's movement to generate that response begins.
        trial_choice:               enum("CCW", "CW", "No Go")       # which choice was made in choiceworld
        trial_stim_on_time:         float         # Time of stimulus in choiceworld (seconds)
        trial_stim_contrast_left:   float	      # contrast of the stimulus on the left
        trial_stim_contrast_right:  float         # contrast of the stimulus on the right
        trial_feedback_time:        float         # Time of feedback delivery (reward or not) in choiceworld
        trial_feedback_type:        tinyint       # whether feedback is positive or negative in choiceworld (-1 for negative, +1 for positive)
        trial_rep_num:              int     	  # the repetition number of the trial, i.e. how many trials have been repeated on this side (counting from 1)
        """

    class ExcludedTrial(dj.Part):
        definition = """
        -> master
        -> TrialSet.Trial
        """

@schema
class PassiveTrialSet(dj.Imported):
    definition = """
    -> acquisition.Session
    ---
    passive_trials_total_num : int
    passive_trials_start_time : float
    passive_trials_end_time : float
    """
    def make(self, key):

        passive_trial_key = key.copy()

        datapath = path.join('data', '{subject_id}-{session_start_time}/'.format(**key))
        passive_visual_stim_contrast_left = np.load('{}_ns_passiveVisual.contrastLeft.npy'.format(datapath))
        passive_visual_stim_contrast_right = np.load('{}_ns_passiveVisual.contrastRight.npy'.format(datapath))
        passive_visual_stim_times = np.load('{}_ns_passiveVisual.times.npy'.format(datapath))

        assert len(np.unique(np.array([len(passive_visual_stim_contrast_left),
                                       len(passive_visual_stim_contrast_right),
                                       len(passive_visual_stim_times)]))) == 1, 'Loaded passive visual files do not have the same length'

        key['passive_trials_total_num'] = len(passive_visual_stim_times)
        key['passive_trials_start_time'] = float(passive_visual_stim_times[0])
        key['passive_trials_end_time'] = float(passive_visual_stim_times[-1])

        self.insert1(key)

        for idx_trial in range(len(passive_visual_stim_times)):

            if np.isnan(passive_visual_stim_contrast_left[idx_trial]):
                passive_stim_contrast_left = 0
            else:
                passive_stim_contrast_left = passive_visual_stim_contrast_left[idx_trial]

            if np.isnan(passive_visual_stim_contrast_right[idx_trial]):
                passive_stim_contrast_right = 0
            else:
                passive_stim_contrast_right = passive_visual_stim_contrast_right[idx_trial]

            passive_trial_key['passive_trial_id'] = idx_trial + 1
            passive_trial_key['passive_trial_stim_on_time'] = float(passive_visual_stim_times[idx_trial])
            passive_trial_key['passive_trial_stim_contrast_left'] = float(passive_stim_contrast_left)
            passive_trial_key['passive_trial_stim_contrast_right'] = float(passive_stim_contrast_right)

            self.PassiveTrial().insert1(passive_trial_key)


    class PassiveTrial(dj.Part):
        definition = """
        -> master
        passive_trial_id:           int         # trial identifier
        ---
        passive_trial_stim_on_time:             float	    # Time of stimuli in choiceworld
        passive_trial_stim_contrast_left:       float 	    # contrast of the stimulus on the left
        passive_trial_stim_contrast_right:      float       # contrast of the stimulus on the right
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
    def make(self, key):
        datapath = path.join('data', '{subject_id}-{session_start_time}/'.format(**key))
        key['passive_beep_times'] = np.load('{}_ns_passiveBeeps.times.npy'.format(datapath))
        key['passive_valve_click_times'] = np.load('{}_ns_passiveValveClick.times.npy'.format(datapath))
        key['passive_white_noise_times'] = np.load('{}_ns_passiveWhiteNoise.times.npy'.format(datapath))

        self.insert1(key)
