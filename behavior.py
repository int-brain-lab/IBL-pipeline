import datajoint as dj
import acquisition

schema = dj.schema(dj.config['names.{}'.format(__name__)])

@schema
class Eye(dj.Imported):
    definition = """
    -> acquisition.Session
    ---
    eye_timestamps:     longblob # Timestamps for pupil tracking timeseries (seconds)
    eye_raw:            longblob # Raw movie data for pupil tracking
    eye_area:           longblob # Area of pupil (pixels^2)
    eye_x_pos:          longblob # x position of pupil (pixels)
    eye_y_pos:          longblob # y position of pupil (pixels)
    eye_blink:          boolean  # Boolean array saying whether eye was blinking in each frame
    eye_fps:            float    # frames per second
    eye_start_time:     float    # (seconds)
    eye_end_time:       float    # (seconds)
    """

@schema
class Wheel(dj.Imported):
    definition = """
    -> acquisition.Session
    ---
    wheel_position:         longblob  # Absolute position of wheel (cm)
    wheel_velocity:         longblob  # Signed velocity of wheel (cm/s) positive = CW
    wheel_timestamps:       longblob  # Timestamps for wheel timeseries (seconds)
    wheel_start_time:       float     # (seconds)
    wheel_end_time:         float     # (seconds)
    wheel_duration:         float     # (seconds)
    wheel_sampling_rate:    float     # samples per second
    """

@schema
class WheelMoveType(dj.Lookup):
    definition = """
    wheel_move_type:   varchar(64)   # movement type
    """
    contents = [['CW'], ['CCW'], ['Flinch'], ['Other']]

@schema
class WheelMoveSet(dj.Imported):
    definition = """
    -> Wheel
    ---
    wheel_move_number : int     # total number of movement in this set
    """
    class WheelMove(dj.Part):
        definition = """
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


@schema
class ExtraRewards(dj.Imported):
    definition = """
    -> acquisition.Session
    ---
    extra_rewards_times: longblob 			# times of extra rewards (seconds)
    """

@schema
class SpontaneousTime(dj.Imported):
    # times when no other protocol was going on for at least 30 sec or so
    definition = """
    -> acquisition.Session
    spontaneous_start_time: float           # (seconds)
    ---
    spontaneous_end_time: float 		    # (seconds)
    spontaneous_duration: float             # (sedonds)
    """

@schema
class Lick(dj.Imported):
    definition = """
    -> acquisition.Session
    ---
    lick_times:             longblob  # Times of licks
    """

# saved for future when we have the corresponding data
#lick_piezo_raw:         longblob  # Raw lick trace (volts)
#lick_sample_id:         longblob  # Sample number of lick
#lick_piezo_timestamps:  longblob  # Timestamps for lick trace timeseries in seconds
#lick_start_times: longblob
#lick_end_times: longblob


@schema
class TrialSet(dj.Imported):
    definition = """
    -> acquisition.Session
    ---
    trials_total_num:   int             # total trial numbers in this set
    trials_start_time: float            # start time of the trial set (seconds)
    trials_end_time:   float            # end time of the trial set (seconds)
    """
    class Trial(dj.Part):
        # all times are in absolute seconds, rather than relative to trial onset
        definition = """
        -> master
        trial_id:               int           # trial identification number
        ---
        trial_start_time:       float         # beginning of quiescent period time (seconds)
        trial_end_time:         float         # end of iti (seconds)
        trial_go_cue_time:      float         # Time of go cue in choiceworld (seconds)
        trial_response_time:    float         # Time of "response" in choiceworld (seconds). This is when one of the three possible choices is registered in software, will not be the same as when the mouse's movement to generate that response begins.
        trial_choice:           enum("CCW", "CW", "No Go")       # which choice was made in choiceworld
        trial_stim_on_time:     float         # Time of stimulus in choiceworld (seconds)
        trial_stim_position:    enum("Left", "Right")	 # position of the stimulus
        trial_stim_contrast:    float         # contrast of the stimulus
        trial_feedback_time:    float         # Time of feedback delivery (reward or not) in choiceworld
        trial_feedback_type:    tinyint       # whether feedback is positive or negative in choiceworld (-1 for negative, +1 for positive)
        trial_rep_num:          int     	  # the repetition number of the trial, i.e. how many trials have been repeated on this side (counting from 1)
        """

@schema
class ExcludedTrial(dj.Imported):
    definition = """
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
    class PassiveTrial(dj.Part):
        definition = """
        -> master
        passive_trial_id:           int         # trial identifier
        ---
        passive_trial_included:         boolean		             # suggesting whether this trial to include in analysis, chosen at experimenter discretion, e.g. by excluding the block of incorrect trials at the end of the session when the mouse has stopped
        passive_trial_stim_on_time:     float	                 # Time of stimuli in choiceworld
        passive_trial_stim_position:    enum("Left", "Right")	 # position of the stimulus
        passive_trial_contrast:         float                    # contrast of the stimulus
        passive_valve_click_time:       float 		             # Time of valve opening during passive trial presentation (seconds)
        passive_beep_time:              float         		     # Time of the beep, equivilent to the go cue during the choice world task (seconds)
        passive_white_noise_time:       float		             # Time of white noise bursts, equivilent to the negative feedback sound during the choice world task (seconds)
        passive_noise_start_time:       float  	                 # passive noise trial's start(i.e. beginning of quiescent period) (seconds)
        passive_noise_end_time:         float                    # passive noise trial's stop (i.e. end of iti) (seconds)
        """
