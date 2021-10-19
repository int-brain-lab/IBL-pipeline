import logging
from logging.handlers import RotatingFileHandler

import datajoint as dj
from ibl_pipeline import acquisition, behavior, mode
import numpy as np
import pathlib

import brainbox.behavior.wheel as wh
from ibllib.io.extractors.training_wheel import extract_wheel_moves, extract_first_movement_times, infer_wheel_units

from .. import one


log_path = pathlib.Path(__file__).parent / 'logs'
log_path.mkdir(parents=True, exist_ok=True)
log_file = log_path / f'process_wheel{"_public" if mode == "public" else ""}.log'
log_file.touch(exist_ok=True)

logging.basicConfig(
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()],
    level=25)

logger = logging.getLogger(__name__)

schema = dj.schema('group_shared_wheel')  # group_shared_wheel


@schema
class WheelMoveSet(dj.Imported):
    definition = """
    # Wheel movements occurring within a session
    -> acquisition.Session
    ---
    n_movements:            int # total number of movements within the session
    total_displacement:     float # total displacement of the wheel during session in radians
    total_distance:         float # total movement of the wheel in radians
    n_direction_changes:    int # total number of direction changes within a session
    """

    class Move(dj.Part):
        # all times are in absolute seconds relative to session
        definition = """
        -> master
        move_id:                int # wheel movement id
        ---
        movement_onset:         float # time of movement onset in seconds from session start
        movement_offset:        float # time of movement offset in seconds from session start
        max_velocity:           float # time of movement's peak velocity
        movement_amplitude:     float # the absolute peak amplitude relative to onset position
        """

    class DirectionChange(dj.Part):
        # all times are in absolute seconds relative to session
        definition = """
        -> master.Move
        change_id:              int # direction change id
        ---
        change_time:            float # time of direction change
        """

    key_source = behavior.CompleteWheelSession

    def make(self, key, one=None):
        # Load the wheel for this session
        move_key = key.copy()
        change_key = move_key.copy()
        one = one or ONE()
        eid, ver = (acquisition.Session & key).fetch1('session_uuid', 'task_protocol')
        logger.info('WheelMoves for session %s, %s', str(eid), ver)

        try:  # Should be able to remove this
            wheel = one.load_object(str(eid), 'wheel')
            all_loaded = \
                all([isinstance(wheel[lab], np.ndarray) for lab in wheel]) and \
                all(k in wheel for k in ('timestamps', 'position'))
            assert all_loaded, 'wheel data missing'

            # If times and timestamps present, drop times
            if {'times', 'timestamps'}.issubset(wheel):
                wheel.pop('times')
            wheel_moves = extract_wheel_moves(wheel.timestamps, wheel.position)
        except ValueError:
            logger.exception('Failed to find movements')
            raise
        except AssertionError as ex:
            logger.exception(str(ex))
            raise
        except Exception as ex:
            logger.exception(str(ex))
            raise

        # Build list of table entries
        keys = ('move_id', 'movement_onset', 'movement_offset', 'max_velocity', 'movement_amplitude')
        on_off, amp, vel_t = wheel_moves.values()  # Unpack into short vars
        moves = [dict(zip(keys, (i, on, off, vel_t[i], amp[i])), **move_key)
                 for i, (on, off) in enumerate(on_off)]

        # Calculate direction changes
        Fs = 1000
        re_ts, re_pos = wheel.timestamps, wheel.position
        if len(re_ts.shape) != 1:
            logger.info('2D wheel timestamps')
            if len(re_pos.shape) > 1:  # Ensure 1D array of positions
                re_pos = re_pos.flatten()
            # Linearly interpolate the times
            x = np.arange(re_pos.size)
            re_ts = np.interp(x, re_ts[:, 0], re_ts[:, 1])

        pos, ts = wh.interpolate_position(re_pos, re_ts, freq=Fs)
        vel, _ = wh.velocity_smoothed(pos, Fs)
        change_mask = np.insert(np.diff(np.sign(vel)) != 0, 0, 0)

        changes = []
        for i, (on, off) in enumerate(on_off.reshape(-1, 2)):
            mask = np.logical_and(ts > on, ts < off)
            ind = np.logical_and(mask, change_mask)
            changes.extend(
                dict(change_key, move_id=i, change_id=j, change_time=t) for j, t in enumerate(ts[ind])
            )

        # Get the units of the position data
        units, *_ = infer_wheel_units(wheel.position)
        key['n_movements'] = wheel_moves['intervals'].shape[0]  # total number of movements within the session
        key['total_displacement'] = float(np.diff(wheel.position[[0, -1]]))  # total displacement of the wheel during session
        key['total_distance'] = float(np.abs(np.diff(wheel.position)).sum())  # total movement of the wheel
        key['n_direction_changes'] = sum(change_mask)  # total number of direction changes
        if units == 'cm':  # convert to radians
            key['total_displacement'] = wh.cm_to_rad(key['total_displacement'])
            key['total_distance'] = wh.cm_to_rad(key['total_distance'])
            wheel_moves['peakAmplitude'] = wh.cm_to_rad(wheel_moves['peakAmplitude'])

        # Insert the keys in order
        self.insert1(key)
        self.Move.insert(moves)
        self.DirectionChange.insert(changes)


@schema
class MovementTimes(dj.Computed):
    definition = """
    # Trial movements table
    -> behavior.TrialSet.Trial
    ---
    -> WheelMoveSet.Move
    reaction_time:          float # time in seconds from go cue to first sufficiently large movement onset of the trial
    final_movement:         bool # indicates whether movement onset was the one that reached threshold
    movement_time:          float # time in seconds from first movement onset to feedback time
    response_time:          float # time in seconds from go cue to feedback time
    movement_onset:         float # time in seconds when first movement onset occurred
    """

    key_source = behavior.CompleteTrialSession & WheelMoveSet

    def make(self, key, one=None):
        # Log eid and task version
        eid, ver = (acquisition.Session & key).fetch1('session_uuid', 'task_protocol')
        logger.info('MovementTimes for session %s, %s', str(eid), ver)

        # Get required data from wheel moves and trials tables, each as a dict of numpy arrays
        fields = ('move_id', 'movement_onset', 'movement_offset', 'movement_amplitude')
        wheel_move_data = {k: v.values for k, v in (
            (
                (WheelMoveSet.Move & key)
                .proj(*fields)
                .fetch(order_by='move_id', format='frame')
                .reset_index()
                .drop(['subject_uuid', 'session_start_time'], axis=1)
                .rename(columns={'movement_amplitude': 'peakAmplitude'})
                .iteritems()
            )
        )}

        fields = ('trial_response_choice', 'trial_response_time', 'trial_stim_on_time',
                  'trial_go_cue_time', 'trial_feedback_time', 'trial_start_time')
        trial_data = {k: v.values for k, v in (
            (
                (behavior.TrialSet.Trial & key)
                .proj(*fields)
                .fetch(order_by='trial_id', format='frame')
                .reset_index()
                .drop(['subject_uuid', 'session_start_time'], axis=1)
                .iteritems()
            )
        )}

        if trial_data['trial_id'].size == 0 or wheel_move_data['move_id'].size == 0:
            logger.warning('Missing DJ trial or move data')
            return

        # Get minimum quiescent period for session
        try:
            one = one or ONE()
            task_params = one.load_object(str(eid), '_iblrig_taskSettings.raw')
            min_qt = task_params['raw']['QUIESCENT_PERIOD']
        except Exception:
            logger.warning('failed to load min quiescent time')
            min_qt = None

        # Many of the timestamps are missing for sessions, therefore will patch together the approximate
        # closed-loop periods by taking the minimum of go_cue and stim_on, response and feedback.
        start = np.nanmin(np.c_[trial_data['trial_stim_on_time'], trial_data['trial_go_cue_time']], axis=1)
        end = np.nanmin(np.c_[trial_data['trial_response_time'], trial_data['trial_feedback_time']], axis=1)

        # Check we have times for at least some trials
        nan_trial = np.isnan(np.c_[start, end]).any(axis=1)
        assert ~nan_trial.all(), 'no reliable trials times for session'

        assert (((start < end) | nan_trial).all() and
                ((np.diff(start) > 0) | np.isnan(np.diff(start))).all()), 'timestamps not increasing'
        go_trial = trial_data['trial_response_choice'] != 'No Go'

        # Rename data for the firstMovement_times extractor function
        wheel_move_data['intervals'] = np.c_[
            wheel_move_data['movement_onset'], wheel_move_data['movement_offset']
        ]
        trial_data = {'goCue_times': start, 'feedback_times': end, 'trial_id': trial_data['trial_id']}

        # Find first significant movement for each trial.  To be counted, the movement must
        # occur between go cue / stim on and before feedback / response time.  The movement
        # onset is sometimes just before the cue (occurring in the gap between quiescence end and
        # cue start, or during the quiescence period but sub-threshold).  The movement is
        # sufficiently large if it is greater than or equal to THRESH
        onsets, final_movement, ids = extract_first_movement_times(wheel_move_data, trial_data, min_qt)
        move_ids = np.full_like(onsets, np.nan)
        move_ids[~np.isnan(onsets)] = ids

        # Check if any movements failed to be detected
        n_nan = np.count_nonzero(np.isnan(onsets[go_trial]))
        if n_nan > 0:
            logger.warning('failed to detect movement on %i go trials', n_nan)

        # Create matrix of values for insertion into table
        movement_data = np.c_[
            trial_data['trial_id'],  # trial_id
            move_ids,  # wheel_move_id
            onsets - start,  # reaction_time
            final_movement,  # final_movement
            end - onsets,  # movement_time
            end - start,  # response_time
            onsets  # movement_onset
        ]
        data = []
        for row in movement_data:
            if ~np.isnan(row).any():  # insert row
                data.append(tuple([*key.values(), *list(row)]))
        self.insert(data)
