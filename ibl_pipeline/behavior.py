import datajoint as dj
import numpy as np
import pandas as pd
from os import path
import logging
from . import reference, subject, acquisition, data
from .ingest import get_raw_field as grf
try:
    from oneibl.one import ONE
except:
    # TODO: consider issuing a warning about not being able to perform ingestion without ONE access
    pass

logger = logging.getLogger(__name__)
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

    key_source = acquisition.Session & (data.FileRecord & 'repo_name LIKE "flatiron_%"' & 'dataset_name in \
                    ("_ibl_eye.area.npy", "_ibl_eye.blink.npy", "_ibl_eye.xyPos.npy", "_ibl_eye.timestamps.npy")')

    def make(self, key):

        eID = (acquisition.Session & key).fetch1('session_uuid')
        eye_area, eye_blink, eye_xypos, eye_timestamps = \
            ONE().load(eID, dataset_types=['_ibl_eye.area', '_ibl_eye.blink', '_ibl_eye.xypos', '_ibl_eye.timestamps'])

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
        logger.info('Populated an Eye tuple for subject {subject_nickname} on {session_start_time}'.format(**key))


@schema
class CompleteWheelSession(dj.Computed):
    definition = """
    # sessions that are complete with wheel related information and thus may be ingested
    -> acquisition.Session
    ---
    wheel_session_complete: bool              # whether the session is complete
    """

    required_datasets =  ["_ibl_wheel.position.npy", "_ibl_wheel.velocity.npy", "_ibl_wheel.timestamps.npy"]

    def make(self, key):
        datasets = (data.FileRecord & key & 'repo_name LIKE "flatiron_%"' & {'exists': 1}).fetch('dataset_name')
        key['wheel_session_complete'] = bool(np.all([req_ds in datasets for req_ds in self.required_datasets]))
        self.insert1(key)


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

    key_source = CompleteWheelSession & 'wheel_session_complete = 1'

    def make(self, key):

        eID = (acquisition.Session & key).fetch1('session_uuid')
        wheel_position, wheel_velocity, wheel_timestamps = \
            ONE().load(eID, dataset_types=['_ibl_wheel.position', '_ibl_wheel.velocity', '_ibl_wheel.timestamps'])

        wheel_sample_ids = wheel_timestamps[:, 0]
        wheel_timestamps = wheel_timestamps[:, 1]
        wheel_sampling_rate = 1 / np.median(np.diff(wheel_timestamps))

        key['wheel_position'] = wheel_position
        key['wheel_velocity'] = wheel_velocity
        key['wheel_sample_ids'] = wheel_sample_ids
        key['wheel_timestamps'] = wheel_timestamps
        key['wheel_start_time'] = wheel_timestamps[0]
        key['wheel_end_time'] = wheel_timestamps[-1]
        key['wheel_duration'] = wheel_timestamps[-1] - wheel_timestamps[0]
        key['wheel_sampling_rate'] = wheel_sampling_rate

        self.insert1(key)
        logger.info('Populated a Wheel tuple for subject {subject_nickname} in session started at {session_start_time}'.format(**key))


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
    ---
    wheelmove_session_complete: bool              # whether the session is complete
    """

    required_datasets = ["_ibl_wheelMoves.intervals.npy", "_ibl_wheelMoves.type.csv"]

    def make(self, key):
        datasets = (data.FileRecord & key & 'repo_name LIKE "flatiron_%"' & {'exists': 1}).fetch('dataset_name')
        key['wheelmove_session_complete'] = bool(np.all([req_ds in datasets for req_ds in self.required_datasets]))
        self.insert1(key)


@schema
class WheelMoveSet(dj.Imported):
    definition = """
    # detected wheel movements
    -> acquisition.Session
    ---
    wheel_move_number : int     # total number of movements in this set
    """
    key_source = CompleteWheelMoveSession & 'wheelmove_session_complete = 1'

    def make(self, key):
        wheel_move_key = key.copy()

        eID = (acquisition.Session & key).fetch1('session_uuid')
        wheel_moves_intervals, wheel_moves_types = \
            ONE().load(eID, dataset_types=['_ibl_wheelMoves.intervals', '_ibl_wheelMoves.type'])

        wheel_moves_types = wheel_moves_types.columns

        assert len(np.unique(np.array([len(wheel_moves_intervals), len(wheel_moves_types)]))) == 1, 'Loaded wheel move files do not have the same length'

        key['wheel_move_number'] = len(wheel_moves_types)
        self.insert1(key)

        for idx_move in range(len(wheel_moves_types)):
            wheel_move_key['wheel_move_id'] = idx_move + 1
            wheel_move_key['wheel_move_start_time'] = wheel_moves_intervals[idx_move, 0]
            wheel_move_key['wheel_move_end_time'] = wheel_moves_intervals[idx_move, 1]

            wheel_move_type = wheel_moves_types[idx_move]
            if 'CCW' in wheel_move_type:
                wheel_move_key['wheel_move_type'] = 'CCW'
            elif 'flinch' in wheel_move_type:
                wheel_move_key['wheel_move_type'] = 'flinch'
            else:
                wheel_move_key['wheel_move_type'] = 'CW'

            self.WheelMove().insert1(wheel_move_key)

        logger.info('Populated a WheelMoveSet and all WheelMove tuples for subject {subject_nickname} in session started at {session_start_time}'.format(**key))

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

    key_source = acquisition.Session & (data.FileRecord & 'repo_name LIKE "flatiron_%"' & {'exists': 1} & 'dataset_name in \
                    ("_ibl_sparseNoise.positions.npy", "_ibl_sparseNoise.times.npy")')

    def make(self, key):

        eID = (acquisition.Session & key).fetch1('session_uuid')

        sparse_noise_positions, sparse_noise_times = \
            ONE().load(eID, dataset_types=['_ibl_sparseNoise.positions', '_ns_sparseNoise.times'])

        assert len(np.unique(np.array([len(sparse_noise_positions), len(sparse_noise_times)]))) == 1, 'Loaded sparse noise files do not have the same length'

        key['sparse_noise_x_pos'] = sparse_noise_positions[:, 0],
        key['sparse_noise_y_pos'] = sparse_noise_positions[:, 1],
        key['sparse_noise_times'] = sparse_noise_times
        self.insert1(key)
        logger.info('Populated a SparseNoise tuple for subject {subject_nickname} in session started at {session_start_time}'.format(**key))


@schema
class ExtraRewards(dj.Imported):
    definition = """
    # information about extra rewards given manually by the experimenter
    -> acquisition.Session
    ---
    extra_rewards_times: longblob 			# times of extra rewards (seconds)
    """

    key_source = acquisition.Session & (data.FileRecord & 'repo_name LIKE "flatiron_%"' & {'exists': 1} & 'dataset_name in \
                    ("_ibl_extraRewards.times.npy")')

    def make(self, key):

        eID = (acquisition.Session & key).fetch1('session_uuid')

        extra_rewards_times = \
            ONE().load(eID, dataset_types=['_ibl_extraRewards.times'])

        key['extra_rewards_times'] = extra_rewards_times

        self.insert1(key)

        logger.info('Populated an ExtraRewards tuple for subject {subject_nickname} in session started at {session_start_time}'.format(**key))


@schema
class SpontaneousTimeSet(dj.Imported):
    definition = """
    # times when no other protocol was going on for at least 30 sec or so
    -> acquisition.Session
    ---
    spontaneous_time_total_num:   int   # total number of the spontaneous time periods
    """

    key_source = acquisition.Session & (data.FileRecord & 'repo_name LIKE "flatiron_%"' & {'exists': 1} & 'dataset_name in \
                    ("_ibl_spontaneous.intervals.npy")')

    def make(self, key):
        spon_time_key = key.copy()

        eID = (acquisition.Session & key).fetch1('session_uuid')

        spontaneous_intervals = \
            ONE().load(eID, dataset_types=['_ibl_spontaneous.intervals'])

        key['spontaneous_time_total_num'] = len(spontaneous_intervals)
        self.insert1(key)

        for idx_spon in range(len(spontaneous_intervals)):
            spon_time_key['spontaneous_time_id'] = idx_spon + 1
            spon_time_key['spontaneous_start_time'] = spontaneous_intervals[idx_spon, 0]
            spon_time_key['spontaneous_end_time'] = spontaneous_intervals[idx_spon, 1]
            spon_time_key['spontaneous_time_duration'] = float(np.diff(spontaneous_intervals[idx_spon, :]))
            self.SpontaneousTime().insert1(spon_time_key)

        logger.info('Populated a SpontaneousTimeSet tuple and all Spontaneoustime tuples for subject {subject_nickname} in session started at {session_start_time}'.format(**key))

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

    key_source = acquisition.Session & (data.FileRecord & 'repo_name LIKE "flatiron_%"' & {'exists': 1} & 'dataset_name in \
                    ("_ibl_licks.times.npy", "_ibl_lickPiezo.raw.npy", "_ibl_lickPiezo.timestamps.npy")')

    def make(self, key):

        eID = (acquisition.Session & key).fetch1('session_uuid')

        lick_times, lick_piezo_raw, lick_piezo_timestamps = \
            ONE().load(eID, dataset_types=['_ibl_licks.times', '_ibl_lickPiezo.raw', '_ibl_lickPiezo.timestamps'])

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

        logger.info('Populated a Lick tuple for subject {subject_nickname} in session started at {session_start_time}'.format(**key))


@schema
class CompleteTrialSession(dj.Computed):
    definition = """
    # sessions that are complete with trial information and thus may be ingested
    -> acquisition.Session
    ---
    trial_session_complete: tinyint # whether the session is complete, 1: complete 2: partial stimOn_times 3: missing stimOn_times
    """

    required_datasets =  ["_ibl_trials.feedback_times.npy", "_ibl_trials.feedbackType.npy", \
                            "_ibl_trials.intervals.npy", "_ibl_trials.repNum.npy", \
                            "_ibl_trials.choice.npy", "_ibl_trials.response_times.npy", \
                            "_ibl_trials.contrastLeft.npy", "_ibl_trials.contrastRight.npy", \
                            "_ibl_trials.included.npy", "_ibl_trials.probabilityLeft.npy"]

    def make(self, key):
        datasets = (data.FileRecord & key & 'repo_name LIKE "flatiron_%"' & {'exists': 1}).fetch('dataset_name')
        is_complete = bool(np.all([req_ds in datasets for req_ds in self.required_datasets]))
        if is_complete is True:
            if '_ibl_trials.stimOn_times.npy' not in datasets:
                key['trial_session_complete'] = 3
            else:
                eID = (acquisition.Session & key).fetch1('session_uuid')
                if key['lab_name'] == 'wittenlab':
                    stimOn_times = np.squeeze(ONE().load(eID, dataset_types='_ibl_trials.stimOn_times', clobber=True))
                else:        
                    stimOn_times = ONE().load(eID, dataset_types='_ibl_trials.stimOn_times')
                
                if np.all(np.isnan(stimOn_times)):
                    key['trial_session_complete'] = 3
                elif np.any(np.isnan(stimOn_times)):
                    key['trial_session_complete'] = 2
                else:
                    key['trial_session_complete'] = 1

            self.insert1(key)


@schema
class TrialSet(dj.Imported):
    definition = """
    # information about behavioral trials
    -> acquisition.Session
    ---
    n_trials:                int              # total trial numbers in this set
    n_correct_trials=null:   int              # number of the correct trials
    trials_start_time:       float            # start time of the trial set (seconds)
    trials_end_time:         float            # end time of the trial set (seconds)
    """

    # Knowledge based hack to be formalized better later
    key_source = CompleteTrialSession

    def make(self, key):
        trial_key = key.copy()
        # excluded_trial_key = key.copy()      
        eID = (acquisition.Session & key).fetch1('session_uuid')

        trials_feedback_times, trials_feedback_types, trials_intervals, \
            trials_rep_num, trials_response_choice, trials_response_times, \
            trials_contrast_left, trials_contrast_right, \
            trials_included, trials_p_left = \
            ONE().load(eID, dataset_types=['_ibl_trials.feedback_times', '_ibl_trials.feedbackType',
                                           '_ibl_trials.intervals', '_ibl_trials.repNum',
                                           '_ibl_trials.choice', '_ibl_trials.response_times',
                                           '_ibl_trials.contrastLeft', '_ibl_trials.contrastRight',
                                           '_ibl_trials.included', '_ibl_trials.probabilityLeft'])
        if key['lab_name'] == 'wittenlab':
            trials_visual_stim_times = np.squeeze(ONE().load(eID, dataset_types='_ibl_trials.stimOn_times', clobber=True))
        else:
            trials_visual_stim_times = ONE().load(eID, dataset_types='_ibl_trials.stimOn_times')

        if len(trials_visual_stim_times) == 1:
            trials_visual_stim_times = np.squeeze(trials_visual_stim_times)
        
        # for debugging purpose
        # print(key['session_start_time'])
        # print(len(trials_feedback_times), len(trials_feedback_types), len(trials_intervals), \
        #     len(trials_rep_num), len(trials_response_choice), len(trials_response_times), len(trials_contrast_left), \
        #     len(trials_contrast_right), len(trials_visual_stim_times), len(trials_included), len(trials_p_left))
        assert len(np.unique(np.array([len(trials_feedback_times),
                                       len(trials_feedback_types),
                                       len(trials_intervals),
                                       len(trials_rep_num),
                                       len(trials_response_choice),
                                       len(trials_response_times),
                                       len(trials_contrast_left),
                                       len(trials_contrast_right),
                                       len(trials_visual_stim_times),
                                       len(trials_included),
                                       len(trials_p_left)
                                       ]))) == 1, 'Loaded trial files do not have the same length'
        
        key['n_trials'] = len(trials_response_choice)

        key_session = dict()
        key_session['model'] = 'actions.session'
        key_session['uuid'] = (acquisition.Session & key).fetch1('session_uuid')
        
        n_correct_trials = grf(key_session, 'n_correct_trials')
        if n_correct_trials != 'None':
            key['n_correct_trials'] = n_correct_trials
        else:
            key['n_correct_trials'] = sum((np.squeeze(trials_response_choice)==1) & (np.squeeze(trials_contrast_left)>0)) \
                + sum((np.squeeze(trials_response_choice)==-1) & (np.squeeze(trials_contrast_right)>0))

        key['trials_start_time'] = trials_intervals[0, 0]
        key['trials_end_time'] = trials_intervals[-1, 1]

       
        self.insert1(key)

        for idx_trial in range(len(trials_response_choice)):

            if np.isnan(trials_contrast_left[idx_trial]):
                trial_stim_contrast_left = 0
            else:
                trial_stim_contrast_left = trials_contrast_left[idx_trial]

            if np.isnan(trials_contrast_right[idx_trial]):
                trial_stim_contrast_right = 0
            else:
                trial_stim_contrast_right = trials_contrast_right[idx_trial]

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
            trial_key['trial_end_time'] = trials_intervals[idx_trial, 1]
            trial_key['trial_response_time'] = float(trials_response_times[idx_trial])
            trial_key['trial_response_choice'] = trial_response_choice
            trials_visual_stim_times = np.squeeze(trials_visual_stim_times)
            trial_key['trial_stim_on_time'] = trials_visual_stim_times[idx_trial]
            trial_key['trial_stim_contrast_left'] = float(trial_stim_contrast_left)
            trial_key['trial_stim_contrast_right'] = float(trial_stim_contrast_right)
            trial_key['trial_feedback_time'] = float(trials_feedback_times[idx_trial])
            trial_key['trial_feedback_type'] = int(trials_feedback_types[idx_trial])
            trial_key['trial_rep_num'] = int(trials_rep_num[idx_trial])
            trial_key['trial_stim_prob_left'] = float(trials_p_left[idx_trial])
            trial_key['trial_included'] = bool(trials_included[idx_trial])

            self.Trial().insert1(trial_key)
            #
            # if trials_included[idx_trial] is False:
            #     excluded_trial_key['trial_id'] = idx_trial + 1
            #     self.ExcludedTrial().insert1(excluded_trial_key)

        logger.info('Populated a TrialSet tuple, all Trial tuples and Excluded Trial tuples for subject {subject_nickname} in session started at {session_start_time}'.format(**key))

    class Trial(dj.Part):
        # all times are in absolute seconds, rather than relative to trial onset
        definition = """
        -> master
        trial_id:               int           # trial identification number
        ---
        trial_start_time:           double         # beginning of quiescent period time (seconds)
        trial_end_time:             double         # end of iti (seconds)
        trial_response_time:        double         # Time of "response" in choiceworld (seconds). This is when one of the three possible choices is registered in software, will not be the same as when the mouse's movement to generate that response begins.
        trial_response_choice:      enum("CCW", "CW", "No Go")       # which choice was made in choiceworld
        trial_stim_on_time=null:    double         # Time of stimulus in choiceworld (seconds)
        trial_stim_contrast_left:   float	      # contrast of the stimulus on the left
        trial_stim_contrast_right:  float         # contrast of the stimulus on the right
        trial_feedback_time:        double         # Time of feedback delivery (reward or not) in choiceworld
        trial_feedback_type:        tinyint       # whether feedback is positive or negative in choiceworld (-1 for negative, +1 for positive)
        trial_rep_num:              int     	  # the repetition number of the trial, i.e. how many trials have been repeated on this side (counting from 1)
        trial_stim_prob_left:       float         # probability of the stimulus being present on left
        trial_included:             bool          # whether the trial should be included
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

    key_source = acquisition.Session & (data.FileRecord & 'repo_name LIKE "flatiron_%"' & {'exists': 1} & 'dataset_name in \
                    ("_ibl_passiveVisual.contrastLeft.npy", "_ibl_passiveVisual.contrastRight.npy", "_ibl_lickPiezo.timestamps.npy")')

    def make(self, key):

        passive_trial_key = key.copy()
        eID = (acquisition.Session & key).fetch1('session_uuid')

        passive_visual_stim_contrast_left, passive_visual_stim_contrast_right = \
            ONE().load(eID, dataset_types=['_ibl_passiveVisual.contrastLeft',
                                           '_ibl_passiveVisual.contrastRight',
                                           '_ibl_passiveVisual.times'])

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

        logger.info('Populated a PassiveTrialSet tuple, all Trial tuples and Excluded Trial tuples for subject {subject_nickname} in session started at {session_start_time}'.format(**key))

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

    key_source = acquisition.Session & (data.FileRecord & 'repo_name LIKE "flatiron_%"' & {'exists': 1} & 'dataset_name in \
                    ("_ibl_passiveBeeps.times.npy", "_ibl_passiveValveClick.times.npy", "_ibl_passiveWhiteNoise.times.npy")')

    def make(self, key):

        eID = (acquisition.Session & key).fetch1('session_uuid')

        key['passive_beep_times'], key['passive_valve_click_times'], key['passive_white_noise_times'] = \
            ONE().load(eID, dataset_types=['_ibl_passiveBeeps.times',
                                           '_ibl_passiveValveClick.times',
                                           '_ibl_passiveWhiteNoise.times'])

        self.insert1(key)
