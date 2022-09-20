import datajoint as dj
import numpy as np

from ibl_pipeline import acquisition, data, mode, one, reference, subject
from ibl_pipeline.utils import get_logger

logger = get_logger(__name__)

if mode == "update":
    schema = dj.schema("ibl_behavior")
else:
    schema = dj.schema(dj.config["database.prefix"] + "ibl_behavior")


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

    key_source = acquisition.Session & (
        data.FileRecord
        & {"exists": 1}
        & 'dataset_name in \
                    ("eye.area.npy", "eye.blink.npy", \
                     "eye.xyPos.npy", "eye.timestamps.npy")'
    )

    def make(self, key):

        eID = str((acquisition.Session & key).fetch1("session_uuid"))
        eye_area, eye_blink, eye_xypos, eye_timestamps = one.load(
            eID, dataset_types=["eye.area", "eye.blink", "eye.xypos", "eye.timestamps"]
        )

        eye_sample_ids = eye_timestamps[:, 0]
        eye_timestamps = eye_timestamps[:, 1]

        assert (
            len(np.unique(np.array([len(eye_xypos), len(eye_blink), len(eye_area)])))
            == 1
        ), "Loaded eye files do not have the same length"

        key["eye_sample_ids"] = eye_sample_ids
        key["eye_timestamps"] = eye_timestamps
        key["eye_area"] = eye_area
        key["eye_x_pos"] = eye_xypos[:, 0]
        key["eye_y_pos"] = eye_xypos[:, 1]
        key["eye_blink"] = eye_blink
        key["eye_fps"] = 1 / np.median(np.diff(eye_timestamps))
        key["eye_start_time"] = eye_timestamps[0]
        key["eye_end_time"] = eye_timestamps[-1]

        self.insert1(key)
        logger.info(
            "Populated an Eye tuple for subject {subject_uuid} \
            on session started at {session_start_time}".format(
                **key
            )
        )


@schema
class SparseNoise(dj.Imported):
    definition = """
    -> acquisition.Session
    ---
    sparse_noise_x_pos:  longblob	# x coordiate on screen of sparse noise stimulus squares (WHAT UNIT?)
    sparse_noise_y_pos:  longblob	# y coordiate on screen of sparse noise stimulus squares (WHAT UNIT?)
    sparse_noise_times:  longblob	# times of those stimulus squares appeared in universal seconds
    """

    key_source = acquisition.Session & (
        data.FileRecord
        & {"exists": 1}
        & 'dataset_name in ("_ibl_sparseNoise.positions.npy", \
                           "_ibl_sparseNoise.times.npy")'
    )

    def make(self, key):

        eID = str((acquisition.Session & key).fetch1("session_uuid"))

        sparse_noise_positions, sparse_noise_times = one.load_datasets(
            eID,
            datasets=["_ibl_sparseNoise.positions", "_ibl_sparseNoise.times"],
            clobber=True,
        )

        assert (
            len(
                np.unique(
                    np.array([len(sparse_noise_positions), len(sparse_noise_times)])
                )
            )
            == 1
        ), "Loaded sparse noise files do not have the same length"

        key["sparse_noise_x_pos"] = (sparse_noise_positions[:, 0],)
        key["sparse_noise_y_pos"] = (sparse_noise_positions[:, 1],)
        key["sparse_noise_times"] = sparse_noise_times
        self.insert1(key)
        logger.info(
            "Populated a SparseNoise tuple for subject {subject_uuid} \
            in session started at {session_start_time}".format(
                **key
            )
        )


@schema
class ExtraRewards(dj.Imported):
    definition = """
    # information about extra rewards given manually by the experimenter
    -> acquisition.Session
    ---
    extra_rewards_times: longblob 			# times of extra rewards (seconds)
    """

    key_source = acquisition.Session & (
        data.FileRecord
        & {"exists": 1}
        & 'dataset_name in ("_ibl_extraRewards.times.npy")'
    )

    def make(self, key):

        eID = (acquisition.Session & key).fetch1("session_uuid")

        extra_rewards_times = one.load_dataset(
            eID, dataset="_ibl_extraRewards.times", clobber=True
        )

        key["extra_rewards_times"] = extra_rewards_times

        self.insert1(key)

        logger.info(
            "Populated an ExtraRewards tuple for \
            subject {subject_uuid} in session started at \
            {session_start_time}".format(
                **key
            )
        )


@schema
class SpontaneousTimeSet(dj.Imported):
    definition = """
    # times when no other protocol was going on for at least 30 sec or so
    -> acquisition.Session
    ---
    spontaneous_time_total_num:   int   # total number of the spontaneous time periods
    """

    key_source = acquisition.Session & (
        data.FileRecord
        & {"exists": 1}
        & 'dataset_name in ("_ibl_spontaneous.intervals.npy")'
    )

    def make(self, key):
        spon_time_key = key.copy()

        eID = str((acquisition.Session & key).fetch1("session_uuid"))

        spontaneous_intervals = one.load_dataset(
            eID, dataset="_ibl_spontaneous.intervals", clobber=True
        )

        key["spontaneous_time_total_num"] = len(spontaneous_intervals)
        self.insert1(key)

        for idx_spon in range(len(spontaneous_intervals)):
            spon_time_key["spontaneous_time_id"] = idx_spon + 1
            spon_time_key["spontaneous_start_time"] = spontaneous_intervals[idx_spon, 0]
            spon_time_key["spontaneous_end_time"] = spontaneous_intervals[idx_spon, 1]
            spon_time_key["spontaneous_time_duration"] = float(
                np.diff(spontaneous_intervals[idx_spon, :])
            )
            self.SpontaneousTime().insert1(spon_time_key)

        logger.info(
            "Populated a SpontaneousTimeSet tuple and all \
            Spontaneoustime tuples for subject {subject_uuid} in \
                session started at {session_start_time}".format(
                **key
            )
        )

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

    key_source = acquisition.Session & (
        data.FileRecord
        & {"exists": 1}
        & 'dataset_name in ("_ibl_licks.times.npy", \
                           "_ibl_lickPiezo.raw.npy", \
                           "_ibl_lickPiezo.timestamps.npy")'
    )

    def make(self, key):

        eID = (acquisition.Session & key).fetch1("session_uuid")

        lick_times, lick_piezo_raw, lick_piezo_timestamps = one.load_datasets(
            eID,
            datasets=[
                "_ibl_licks.times",
                "_ibl_lickPiezo.raw",
                "_ibl_lickPiezo.timestamps",
            ],
            clobber=True,
        )

        lick_sample_ids = lick_piezo_timestamps[:, 0]
        lick_piezo_timestamps = lick_piezo_timestamps[:, 1]

        key["lick_times"] = lick_times
        key["lick_piezo_raw"] = lick_piezo_raw
        key["lick_sample_ids"] = lick_sample_ids
        key["lick_piezo_timestamps"] = lick_piezo_timestamps
        key["lick_start_time"] = lick_piezo_timestamps[0]
        key["lick_end_time"] = lick_piezo_timestamps[-1]
        key["lick_sampling_rate"] = 1 / np.median(np.diff(lick_piezo_timestamps))

        self.insert1(key)

        logger.info(
            "Populated a Lick tuple for \
            subject {subject_uuid} in session started at \
            {session_start_time}".format(
                **key
            )
        )


@schema
class PassiveTrialSet(dj.Imported):
    definition = """
    -> acquisition.Session
    ---
    passive_trials_total_num : int
    passive_trials_start_time : float
    passive_trials_end_time : float
    """

    key_source = acquisition.Session & (
        data.FileRecord
        & {"exists": 1}
        & 'dataset_name in \
                                        ("passiveTrials.contrastLeft.npy", \
                                        "passiveTrials.contrastRight.npy", \
                                        "_ibl_lickPiezo.timestamps.npy")'
    )

    def make(self, key):
        passive_trial_key = key.copy()
        eID = str((acquisition.Session & key).fetch1("session_uuid"))

        (
            passive_visual_stim_contrast_left,
            passive_visual_stim_contrast_right,
            passive_visual_stim_times,
        ) = one.load_datasets(
            eID,
            datasets=[
                "passiveTrials.contrastLeft",
                "passiveTrials.contrastRight",
                "passiveTrials.times",
            ],
            clobber=True,
        )

        assert (
            len(
                np.unique(
                    np.array(
                        [
                            len(passive_visual_stim_contrast_left),
                            len(passive_visual_stim_contrast_right),
                            len(passive_visual_stim_times),
                        ]
                    )
                )
            )
            == 1
        ), "Loaded passive visual files do not have the same length"

        key["passive_trials_total_num"] = len(passive_visual_stim_times)
        key["passive_trials_start_time"] = float(passive_visual_stim_times[0])
        key["passive_trials_end_time"] = float(passive_visual_stim_times[-1])

        self.insert1(key)

        for idx_trial in range(len(passive_visual_stim_times)):

            if np.isnan(passive_visual_stim_contrast_left[idx_trial]):
                passive_stim_contrast_left = 0
            else:
                passive_stim_contrast_left = passive_visual_stim_contrast_left[
                    idx_trial
                ]

            if np.isnan(passive_visual_stim_contrast_right[idx_trial]):
                passive_stim_contrast_right = 0
            else:
                passive_stim_contrast_right = passive_visual_stim_contrast_right[
                    idx_trial
                ]

            passive_trial_key["passive_trial_id"] = idx_trial + 1
            passive_trial_key["passive_trial_stim_on_time"] = float(
                passive_visual_stim_times[idx_trial]
            )
            passive_trial_key["passive_trial_stim_contrast_left"] = float(
                passive_stim_contrast_left
            )
            passive_trial_key["passive_trial_stim_contrast_right"] = float(
                passive_stim_contrast_right
            )

            self.PassiveTrial.insert1(passive_trial_key)

        logger.info(
            "Populated a PassiveTrialSet tuple, all Trial tuples and \
            Excluded Trial tuples for subject {subject_uuid} in \
                session started at {session_start_time}".format(
                **key
            )
        )

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

    key_source = acquisition.Session & (
        data.FileRecord
        & 'repo_name LIKE "flatiron_%"'
        & {"exists": 1}
        & 'dataset_name in \
        ("passiveBeeps.times.npy", "passiveValveClicks.times.npy", "passiveWhiteNoise.times.npy")'
    )

    def make(self, key):

        eID = str((acquisition.Session & key).fetch1("session_uuid"))

        (
            key["passive_beep_times"],
            key["passive_valve_click_times"],
            key["passive_white_noise_times"],
        ) = one.load_datasets(
            eID,
            datasets=[
                "passiveBeeps.times",
                "passiveValveClicks.times",
                "passiveWhiteNoise.times",
            ],
            clobber=True,
        )
        self.insert1(key)
