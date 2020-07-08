import datajoint as dj
from ibl_pipeline import acquisition, behavior
from oneibl.one import ONE
import numpy as np
import brainbox.behavior.wheel as wh
import logging
from logging.handlers import RotatingFileHandler
import alf.io
import os

log_dir = '/tmp/ibllib/logs'
os.chmod(log_dir, 0o0777)

logger = logging.getLogger(__name__)
fh = RotatingFileHandler(log_dir + '/Movements.log', maxBytes=(1048576*5))
logger.addHandler(fh)
logger.setLevel(logging.DEBUG)

mode = os.environ.get('MODE')

if mode == 'update':
    schema = dj.schema('group_shared_wheel')
else:
    schema = dj.schema(dj.config.get('database.prefix', '') + 'group_shared_wheel')


@schema
class WheelMoveSet(dj.Imported):
    definition = """
    # Wheel movements occurring within a session
    -> acquisition.Session
    ---
    n_movements:            int # total number of movements within the session
    total_displacement:     float # total displacement of the wheel during session in radians
    total_distance:         float # total movement of the wheel in radians
    """

    class Move(dj.Part):
        # all times are in absolute seconds relative to session
        definition = """
        -> master
        move_id:                int # movement id
        ---
        movement_onset:         float # time of movement onset in seconds from session start
        movement_offset:        float # time of movement offset in seconds from session start
        max_velocity:           float # time of movement's peak velocity
        movement_amplitude:     float # the absolute peak amplitude relative to onset position
        """

    key_source = behavior.CompleteWheelSession

    # key_source = behavior.CompleteWheelSession & \
    #     (acquisition.Session & 'task_protocol LIKE "%_iblrig_tasks_ephys%"')

    def make(self, key):
        # Load the wheel for this session
        move_key = key.copy()
        one = ONE()
        eid, ver = (acquisition.Session & key).fetch1('session_uuid', 'task_protocol')
        logger.info('WheelMoves for session %s, %s', str(eid), ver)

        try:  # Should be able to remove this
            wheel = one.load_object(str(eid), 'wheel')
            all_loaded = \
                all([isinstance(wheel[lab], np.ndarray) for lab in wheel]) and \
                all(k in wheel for k in ('timestamps', 'position'))
            assert all_loaded, 'wheel data missing'
            alf.io.check_dimensions(wheel)
            if len(wheel['timestamps'].shape) == 1:
                assert wheel['timestamps'].size == wheel['position'].size, 'wheel data dimension mismatch'
                assert np.all(np.diff(wheel['timestamps']) > 0), 'wheel timestamps not monotonically increasing'
            else:
                logger.debug('2D timestamps')
            # Check the values and units of wheel position
            res = np.array([wh.ENC_RES, wh.ENC_RES/2, wh.ENC_RES/4])
            min_change_rad = 2 * np.pi / res
            min_change_cm = wh.WHEEL_DIAMETER * np.pi / res
            pos_diff = np.abs(np.ediff1d(wheel['position']))
            if pos_diff.min() < min_change_cm.min():
                # Assume values are in radians
                units = 'rad'
                encoding = np.argmin(np.abs(min_change_rad - pos_diff.min()))
                min_change = min_change_rad[encoding]
            else:
                units = 'cm'
                encoding = np.argmin(np.abs(min_change_cm - pos_diff.min()))
                min_change = min_change_cm[encoding]
            enc_names = {0: '4X', 1: '2X', 2: '1X'}
            logger.info('Wheel in %s units using %s encoding', units, enc_names[int(encoding)])
            if '_iblrig_tasks_ephys' in ver:
                assert np.allclose(pos_diff, min_change, rtol=1e-05), 'wheel position skips'
        except ValueError:
            logger.exception('Inconsistent wheel data')
            raise
        except AssertionError as ex:
            logger.exception(str(ex))
            raise
        except Exception as ex:
            logger.exception(str(ex))
            raise

        try:
            # Convert the pos threshold defaults from samples to correct unit
            thresholds = wh.samples_to_cm(np.array([8, 1.5]), resolution=res[encoding])
            if units == 'rad':
                thresholds = wh.cm_to_rad(thresholds)
            kwargs = {'pos_thresh': thresholds[0], 'pos_thresh_onset': thresholds[1]}
            #  kwargs = {'make_plots': True, **kwargs}
            # Interpolate and get onsets
            pos, t = wh.interpolate_position(wheel['timestamps'], wheel['position'], freq=1000)
            on, off, amp, peak_vel = wh.movements(t, pos, freq=1000, **kwargs)
            assert on.size == off.size, 'onset/offset number mismatch'
            assert np.all(np.diff(on) > 0) and np.all(np.diff(off) > 0), 'onsets/offsets not monotonically increasing'
            assert np.all((off - on) > 0), 'not all offsets occur after onset'
        except ValueError:
            logger.exception('Failed to find movements')
            raise
        except AssertionError as ex:
            logger.exception('Wheel integrity check failed: ' + str(ex))
            raise

        key['n_movements'] = on.size  # total number of movements within the session
        key['total_displacement'] = float(np.diff(pos[[0, -1]]))  # total displacement of the wheel during session
        key['total_distance'] = float(np.abs(np.diff(pos)).sum())  # total movement of the wheel
        if units is 'cm':  # convert to radians
            key['total_displacement'] = wh.cm_to_rad(key['total_displacement'])
            key['total_distance'] = wh.cm_to_rad(key['total_distance'])
            amp = wh.cm_to_rad(amp)

        self.insert1(key)

        keys = ('move_id', 'movement_onset', 'movement_offset', 'max_velocity', 'movement_amplitude')
        moves = [dict(zip(keys, (i, on[i], off[i], amp[i], peak_vel[i]))) for i in np.arange(on.size)]
        [x.update(move_key) for x in moves]

        self.Move.insert(moves)


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

    def make(self, key):
        THRESH = .1  # peak amp should be at least .1 rad; ~1/3rd of the threshold
        eid, ver = (acquisition.Session & key).fetch1('session_uuid', 'task_protocol')  # For logging purposes
        logger.info('MovementTimes for session %s, %s', str(eid), ver)
        query = (WheelMoveSet.Move & key).proj(
            'move_id',
            'movement_onset',
            'movement_offset',
            'movement_amplitude')
        wheel_move_data = query.fetch(order_by='move_id')

        query = (behavior.TrialSet.Trial & key).proj(
            'trial_response_choice',
            'trial_response_time',
            'trial_stim_on_time',
            'trial_go_cue_time',
            'trial_feedback_time',
            'trial_start_time')
        trial_data = query.fetch(order_by='trial_id')

        if trial_data.size == 0 or wheel_move_data.size == 0:
            logger.warning('Missing DJ trial or move data')
            return

        all_move_onsets = wheel_move_data['movement_onset']
        peak_amp = wheel_move_data['movement_amplitude']
        flinch = abs(peak_amp) < THRESH
        go_trial = trial_data['trial_response_choice'] != 'No Go'
        feedback_times = trial_data['trial_feedback_time']
        cue_times = trial_data['trial_go_cue_time']

        # Check integrity of feedback and start times
        try:
            # Log presence of nans in feedback times (common)
            nan_trial = np.isnan(feedback_times)
            if nan_trial.any():
                n_feedback_nans = np.count_nonzero(nan_trial)
                logger.warning('%i feedback_times nan', np.count_nonzero(nan_trial))
                response_times = trial_data['trial_response_time']
                if n_feedback_nans > np.count_nonzero(np.isnan(response_times)):
                    logger.warning('using response times instead of feedback times')
                    feedback_times = response_times
                    nan_trial = np.isnan(feedback_times)

            # Assert all feedback times are monotonically increasing
            assert np.all(np.diff(feedback_times[~nan_trial]) > 0), 'feedback times not monotonically increasing'
            # Log presence of nans in go cue times times (common)
            if np.isnan(cue_times).any():
                # If all nan, use stim on
                if np.isnan(cue_times).all():
                    logger.warning('trial_go_cue_time is all nan, using trial_stim_on_time')
                    cue_times = trial_data['trial_stim_on_time']
                    if np.isnan(cue_times).any():
                        n_nan = 'all' if np.isnan(cue_times).all() else str(np.count_nonzero(np.isnan(cue_times)))
                        logger.warning('trial_stim_on_time nan for %s trials', n_nan)
                else:
                    logger.warning('trial_go_cue_time is nan for %i trials', np.count_nonzero(np.isnan(cue_times)))
            # Assert all cue times are montonically increasing
            assert np.all(np.diff(cue_times[~np.isnan(cue_times)]) > 0), 'cue times not monotonically increasing'
            # Assert all start times occur before feedback times
            # assert np.all((feedback_times[~nan_trial] - start_times) > 0), 'feedback occurs before start time'
        except AssertionError as ex:
            logger.exception('Movement integrity check failed: ' + str(ex))
            raise

        # Get minimum quiescent period for session
        try:
            one = ONE()
            task_params = one.load_object(str(eid), '_iblrig_taskSettings.raw')
            min_qt = task_params['raw']['QUIESCENT_PERIOD']
            if len(min_qt) > len(cue_times):
                min_qt = np.array(min_qt[0:cue_times.size])
        except BaseException:
            logger.warning('failed to load min quiescent time')
            min_qt = 0.2

        # Find first significant movement for each trial.  To be counted, the movement must
        # occur between go cue / stim on and before feedback / response time.  The movement
        # onset is sometimes just before the cue (occurring in the gap between quiescence end and
        # cue start, or during the quiescence period but sub-threshold).  The movement is
        # sufficiently large if it is greater than or equal to THRESH

        # Initialize as nans
        onsets = np.full(trial_data['trial_id'].shape, np.nan)
        ids = np.full(trial_data['trial_id'].shape, int(-1))
        final_movement = np.zeros(trial_data['trial_id'].shape, bool)
        # Iterate over trials, extracting onsets approx. within closed-loop period
        for i, (t1, t2) in enumerate(zip(cue_times - min_qt, feedback_times)):
            if ~np.isnan(t2 - t1):  # If both timestamps defined
                mask = (all_move_onsets > t1) & (all_move_onsets < t2)
                if np.any(mask):  # If any onsets for this trial
                    trial_onset_ids, = np.where(mask)
                    if np.any(~flinch[mask]):  # If any trial moves were sufficiently large
                        ids[i] = trial_onset_ids[~flinch[mask]][0]  # Find first large move id
                        onsets[i] = all_move_onsets[ids[i]]  # Save first large move onset
                        final_movement[i] = ids[i] == trial_onset_ids[-1]  # Final move of trial
                else:  # Check if trial was no-go
                    if ~go_trial[i]:  # Report if not no-go
                        logger.warning('failed to find any onsets for trial id %i', i+1)
            else:  # Log missing timestamps
                logger.warning('no reliable times for trial id %i', i + 1)

        # Create matrix of values for insertion into table
        movement_data = np.c_[
            trial_data['trial_id'],  # trial_id
            ids,  # wheel_move_id
            onsets - cue_times,  # reaction_time
            final_movement,  # final_movement
            feedback_times - onsets,  # movement_time
            feedback_times - cue_times,  # response_time
            onsets  # movement_onset
        ]
        data = []
        for row in movement_data:
            if np.isnan(row).any():  # don't insert; leave as null
                logger.warning('nan found for trial %i', row[0])
            else:  # insert row
                data.append(tuple([*key.values(), *list(row)]))
        self.insert(data)
