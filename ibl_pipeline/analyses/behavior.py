import datajoint as dj
from .. import subject, action, acquisition, behavior
from ..utils import psychofit as psy
from . import analysis_utils as utils
from datetime import datetime
import numpy as np
import pandas as pd
from pdb import set_trace as bp

schema = dj.schema(dj.config.get('database.prefix', '') +
                   'ibl_analyses_behavior')


def compute_reaction_time(trials, stim_on_type='stim on'):

    # median reaction time
    if stim_on_type == 'stim on':
        trials_rt = trials.proj(
            signed_contrast='trial_stim_contrast_left- \
                            trial_stim_contrast_right',
            rt='trial_response_time-trial_stim_on_time')
    else:
        trials_rt = trials.proj(
            signed_contrast='trial_stim_contrast_left- \
                            trial_stim_contrast_right',
            rt='trial_response_time-trial_go_cue_trigger_time')

    rt = trials_rt.fetch(as_dict=True)
    rt = pd.DataFrame(rt)
    rt = rt[['signed_contrast', 'rt']]

    try:
        median_rt = rt.groupby('signed_contrast').median().reset_index()
    except:
        median_rt = rt.groupby('signed_contrast').count().reset_index()
        median_rt['rt'] = np.nan

    return median_rt


@schema
class PsychResults(dj.Computed):
    definition = """
    -> behavior.TrialSet
    ---
    performance:            float   # percentage correct in this session
    performance_easy=null:  float   # percentage correct of easy trials in this session
    signed_contrasts:       blob    # contrasts used in this session, negative when on the left
    n_trials_stim:          blob    # number of trials for each contrast
    n_trials_stim_right:    blob    # number of reporting "right" trials for each contrast
    prob_choose_right:      blob    # probability of choosing right, same size as contrasts
    threshold:              float
    bias:                   float
    lapse_low:              float
    lapse_high:             float
    """

    def make(self, key):

        trials = behavior.TrialSet.Trial & key
        psych_results_tmp = utils.compute_psych_pars(trials)
        psych_results = {**key, **psych_results_tmp}

        performance_easy = utils.compute_performance_easy(trials)
        if performance_easy:
            psych_results['performance_easy'] = performance_easy

        n_trials, n_correct_trials = (behavior.TrialSet & key).fetch1(
            'n_trials', 'n_correct_trials')
        psych_results['performance'] = n_correct_trials/n_trials
        self.insert1(psych_results)


@schema
class PsychResultsBlock(dj.Computed):
    definition = """
    -> behavior.TrialSet
    prob_left_block:        int     # block number representing the probability left
    ---
    prob_left:              float   # 0.5 for trainingChoiceWorld, actual value for biasedChoiceWorld
    signed_contrasts:       blob    # contrasts used in this session, negative when on the left
    n_trials_stim:          blob    # number of trials for each contrast
    n_trials_stim_right:    blob    # number of reporting "right" trials for each contrast
    prob_choose_right:      blob    # probability of choosing right, same size as contrasts
    threshold:              float
    bias:                   float
    lapse_low:              float
    lapse_high:             float
    """
    key_source = behavior.TrialSet()

    def make(self, key):

        task_protocol = (acquisition.Session & key).fetch1(
            'task_protocol')

        trials = behavior.TrialSet.Trial & key

        if task_protocol and ('biased' in task_protocol or 'ephys' in task_protocol):
            prob_lefts = dj.U('trial_stim_prob_left') & trials

            for prob_left in prob_lefts:
                p_left = prob_left['trial_stim_prob_left']
                trials_sub = trials & \
                    'ABS(trial_stim_prob_left - {})<1e-6'.format(p_left)

                # compute psych results
                psych_results = utils.compute_psych_pars(trials_sub)
                psych_results = {**key, **psych_results}
                psych_results['prob_left'] = prob_left[
                    'trial_stim_prob_left']
                if abs(p_left - 0.8) < 0.001:
                    psych_results['prob_left_block'] = 80
                elif abs(p_left - 0.2) < 0.001:
                    psych_results['prob_left_block'] = 20
                elif abs(p_left - 0.5) < 0.001:
                    psych_results['prob_left_block'] = 50

                self.insert1(psych_results)

        else:
            psych_results = utils.compute_psych_pars(trials)
            psych_results = {**key, **psych_results}
            psych_results['prob_left'] = 0.5
            psych_results['prob_left_block'] = 50

            self.insert1(psych_results)


@schema
class ReactionTime(dj.Computed):
    definition = """
    -> PsychResults
    ---
    reaction_time:     blob   # median reaction time for each contrasts
    """
    key_source = PsychResults & \
        (behavior.CompleteTrialSession &
         'stim_on_times_status in ("Complete", "Partial") or \
          go_cue_trigger_times_status in ("Complete", "Partial")')

    def make(self, key):
        trials = behavior.TrialSet.Trial & key & \
            'trial_stim_on_time is not NULL or trial_go_cue_trigger_time is not NULL'
        key['reaction_time'] = utils.compute_reaction_time(trials)
        self.insert1(key)


@schema
class ReactionTimeContrastBlock(dj.Computed):
    definition = """
    -> behavior.TrialSet
    prob_left_block:   int   #
    ---
    reaction_time_contrast: blob   # median reaction time for each contrast
    reaction_time_ci_high:  blob   # 68 percent confidence interval upper bound
    reaction_time_ci_low:   blob   # 68 percent confidence interval lower bound
    """

    key_source = behavior.TrialSet & \
        (behavior.CompleteTrialSession &
         'stim_on_times_status in ("Complete", "Partial") or \
          go_cue_trigger_times_status in ("Complete", "Partial")')

    def make(self, key):
        task_protocol = (acquisition.Session & key).fetch1(
            'task_protocol')

        trials = behavior.TrialSet.Trial & key & \
            'trial_stim_on_time is not NULL or trial_go_cue_trigger_time is not NULL'

        if task_protocol and ('biased' in task_protocol or 'ephys' in task_protocol):
            prob_lefts = dj.U('trial_stim_prob_left') & trials

            for prob_left in prob_lefts:
                rt = key.copy()
                p_left = prob_left['trial_stim_prob_left']
                trials_sub = trials & \
                    'ABS(trial_stim_prob_left - {})<1e-6'.format(p_left)

                # compute reaction_time
                rt['reaction_time_contrast'], rt['reaction_time_ci_low'], \
                    rt['reaction_time_ci_high'] = utils.compute_reaction_time(
                        trials_sub, compute_ci=True)

                if abs(p_left - 0.8) < 0.001:
                    rt['prob_left_block'] = 80
                elif abs(p_left - 0.2) < 0.001:
                    rt['prob_left_block'] = 20
                elif abs(p_left - 0.5) < 0.001:
                    rt['prob_left_block'] = 50

                self.insert1(rt)

        else:
            rt = key.copy()
            rt['prob_left_block'] = 50
            rt['reaction_time_contrast'], rt['reaction_time_ci_low'], \
                rt['reaction_time_ci_high'] = utils.compute_reaction_time(
                    trials, compute_ci=True)
            self.insert1(rt)


@schema
class BehavioralSummaryByDate(dj.Computed):
    definition = """
    -> subject.Subject
    session_date:           date    # date of recording
    ---
    performance:            float   # percentage correct for the day
    performance_easy=null:  float   # percentage correct of the easy trials for the day
    n_trials_date=null:     int     # total number of trials on the date
    training_day=null:      int     # days since training
    training_week=null:     int     # weeks since training
    """

    key_source = dj.U('subject_uuid', 'session_date') \
        & behavior.TrialSet.proj(
            session_date='DATE(session_start_time)')

    def make(self, key):

        master_entry = key.copy()
        rt = key.copy()
        rt_overall = key.copy()

        # get all trial sets and trials from that date
        trial_sets_proj = (behavior.TrialSet.proj(
            session_date='DATE(session_start_time)')) & key

        trial_sets_keys = (behavior.TrialSet * trial_sets_proj).fetch('KEY')

        n_trials, n_correct_trials = \
            (behavior.TrialSet & trial_sets_keys).fetch(
                'n_trials', 'n_correct_trials')

        trials = behavior.TrialSet.Trial & trial_sets_keys

        # compute the performance for easy trials
        performance_easy = utils.compute_performance_easy(trials)
        if performance_easy:
            master_entry['performance_easy'] = performance_easy

        # compute the performance for all trials
        master_entry['performance'] = np.divide(
            np.sum(n_correct_trials), np.sum(n_trials))

        master_entry['n_trials_date'] = len(trials)
        master_entry['training_day'] = len(
            dj.U('session_date') &
            (acquisition.Session.proj(
                'task_protocol',
                session_date='date(session_start_time)') &
             {'subject_uuid': key['subject_uuid']} &
             'task_protocol not like "%habituation%" or task_protocol is null') &
            'session_date<="{}"'.format(
                key['session_date'].strftime('%Y-%m-%d')))
        master_entry['training_week'] = np.floor(
            master_entry['training_day'] / 5)

        self.insert1(master_entry)

        complete_stim_on, complete_go_cue_trigger = (
            behavior.CompleteTrialSession & trial_sets_keys).fetch(
            'stim_on_times_status', 'go_cue_trigger_times_status')
        rt_available = \
            np.any([c in ['Complete', 'Partial'] for c in complete_stim_on]) or \
            np.any([c in ['Complete', 'Partial'] for c in complete_go_cue_trigger])

        # compute reaction time for all trials
        if rt_available:
            trials_for_rt = trials & \
                'trial_stim_on_time is not NULL or trial_go_cue_trigger is not NULL'

            trials_go_cue_only = trials & \
                'trial_stim_on_time is NULL and trial_go_cue_trigger_time is not NULL'
            trials_stim_on = trials & \
                'trial_stim_on_time is not NULL'

            rts = []
            if len(trials_go_cue_only):
                trials_rt_go_cue_only = trials_go_cue_only.proj(
                    signed_contrast='trial_stim_contrast_left- \
                        trial_stim_contrast_right',
                    rt='trial_response_time-trial_go_cue_trigger_time')
                rts += list(
                    (trials_rt_go_cue_only & 'rt is not NULL').fetch('rt'))

            if len(trials_stim_on):
                trials_rt_stim_on = trials.proj(
                    signed_contrast='trial_stim_contrast_left- \
                                    trial_stim_contrast_right',
                    rt='trial_response_time-trial_stim_on_time')
                rts += list((trials_rt_stim_on & 'rt is not NULL').fetch('rt'))

            if len(rts):
                rt_overall['median_reaction_time'] = np.median(rts)
                self.ReactionTimeByDate.insert1(rt_overall)

        # compute psych results for all trials

        task_protocols = (acquisition.Session & trial_sets_keys).fetch(
            'task_protocol')
        task_protocols = [protocol for protocol in task_protocols if protocol]

        if any('biased' in task_protocol or 'ephys' in task_protocol
               for task_protocol in task_protocols):
            trials_biased = trials & (acquisition.Session &
                                      trial_sets_keys &
                                      'task_protocol like "%biased%" or task_protocol like "%ephys%"')
            prob_lefts = dj.U('trial_stim_prob_left') & trials_biased

            for prob_left in prob_lefts:
                p_left = prob_left['trial_stim_prob_left']

                if any('training' in task_protocol
                       for task_protocol in task_protocols):
                    if p_left != 0.5:
                        trials_sub = trials_biased & \
                            'ABS(trial_stim_prob_left - {})<1e-6'.format(
                                p_left)
                    else:
                        trials_training = trials & \
                            (acquisition.Session &
                             trial_sets_keys &
                             'task_protocol LIKE "%training%"')
                        trials_50 = trials_biased & \
                            'ABS(trial_stim_prob_left - {})<1e-6'.format(
                                p_left)
                        trials_sub = behavior.TrialSet.Trial & \
                            [trials_training.fetch('KEY'),
                             trials_50.fetch('KEY')]
                else:
                    trials_sub = trials & \
                        'ABS(trial_stim_prob_left - {})<1e-6'.format(p_left)

                # compute psych results
                psych_results_tmp = utils.compute_psych_pars(trials_sub)
                psych_results = {**key, **psych_results_tmp}
                psych_results['prob_left'] = prob_left[
                    'trial_stim_prob_left']
                if abs(p_left - 0.8) < 0.001:
                    psych_results['prob_left_block'] = 2
                elif abs(p_left - 0.2) < 0.001:
                    psych_results['prob_left_block'] = 1
                elif abs(p_left - 0.5) < 0.001:
                    psych_results['prob_left_block'] = 0

                self.PsychResults.insert1(psych_results)
                # compute reaction time
                if rt_available:

                    trials_sub = trials_sub & \
                        'trial_stim_on_time is not NULL or trial_go_cue_trigger_time is not NULL'

                    if abs(p_left - 0.8) < 0.001:
                        rt['prob_left_block'] = 2
                    elif abs(p_left - 0.2) < 0.001:
                        rt['prob_left_block'] = 1
                    elif abs(p_left - 0.5) < 0.001:
                        rt['prob_left_block'] = 0

                    rt['reaction_time_contrast'], rt['reaction_time_ci_low'], \
                        rt['reaction_time_ci_high'] = \
                        utils.compute_reaction_time(
                            trials_sub, compute_ci=True)
                    self.ReactionTimeContrast.insert1(rt)
        else:
            psych_results_tmp = utils.compute_psych_pars(trials)
            psych_results = {**key, **psych_results_tmp}
            psych_results['prob_left'] = 0.5
            psych_results['prob_left_block'] = 0
            self.PsychResults.insert1(psych_results)

            # compute reaction time
            if rt_available:
                trials = trials & \
                    'trial_stim_on_time is not NULL or trial_go_cue_trigger_time is not NULL'

                rt['prob_left_block'] = 0
                rt['reaction_time_contrast'], rt['reaction_time_ci_low'], \
                    rt['reaction_time_ci_high'] = utils.compute_reaction_time(
                        trials, compute_ci=True)
                self.ReactionTimeContrast.insert1(rt)

    class PsychResults(dj.Part):
        definition = """
        -> master
        prob_left_block:        int     # probability left block number
        ---
        prob_left:              float   # 0.5 for trainingChoiceWorld, actual value for biasedChoiceWorld
        signed_contrasts:       blob    # contrasts used in this session, negative when on the left
        n_trials_stim:          blob    # number of trials for each contrast
        n_trials_stim_right:    blob    # number of reporting "right" trials for each contrast
        prob_choose_right:      blob    # probability of choosing right, same size as contrasts
        threshold:              float
        bias:                   float
        lapse_low:              float
        lapse_high:             float
        """

    class ReactionTimeContrast(dj.Part):
        definition = """
        -> master.PsychResults
        ---
        reaction_time_contrast: blob   # median reaction time for each contrast
        reaction_time_ci_high:  blob   # 68 percent confidence interval upper bound
        reaction_time_ci_low:   blob   # 68 percent confidence interval lower bound
        """

    class ReactionTimeByDate(dj.Part):
        definition = """
        -> master
        ---
        median_reaction_time:    float  # median reaction time of the entire day
        """


@schema
class TrainingStatus(dj.Lookup):
    definition = """
    training_status: varchar(32)
    """
    contents = zip(['untrainable',
                    'unbiasable',
                    'in_training',
                    'trained_1a',
                    'trained_1b',
                    'ready4ephysrig',
                    'ready4delay',
                    'ready4recording'])


@schema
class SessionTrainingStatus(dj.Computed):
    definition = """
    -> PsychResults
    ---
    -> TrainingStatus
    good_enough_for_brainwide_map=0:     bool    # to be included in the brainwide map
    """

    def make(self, key):

        subject_key = key.copy()
        subject_key.pop('session_start_time')

        # ========================================================= #
        # check for "good enough for brainwide map"
        # ========================================================= #

        # trials for current session
        n_trials_current = (behavior.TrialSet & key).fetch1('n_trials')

        # performance of the current session
        perf_current = (PsychResults & key).fetch1('performance_easy')

        # check protocol
        protocol = (acquisition.Session & key).fetch1('task_protocol')

        if n_trials_current > 400 and perf_current > 0.9 and protocol and 'ephys' in protocol:
            key['good_enough_for_brainwide_map'] = 1

        previous_sessions = SessionTrainingStatus & subject_key & \
            'session_start_time < "{}"'.format(
                key['session_start_time'].strftime('%Y-%m-%d %H:%M:%S')
            )
        status = previous_sessions.fetch('training_status')
        # ========================================================= #
        # is the animal ready to be recorded?
        # ========================================================= #

        # if the previous status was 'ready4recording', keep
        if len(status) and np.any(status == 'ready4recording'):
            key['training_status'] = 'ready4recording'
            self.insert1(key)
            return

        # check whether the session is "ready4recording"
        task_protocol = (acquisition.Session & key).fetch1('task_protocol')

        if task_protocol and (('ephys' in task_protocol) or ('biased' in task_protocol)):

            # Criteria for "ready4recording"
            sessions = (behavior.TrialSet & subject_key &
                        (acquisition.Session & 'task_protocol LIKE "%biased%" or task_protocol LIKE "%ephys%"') &
                        'session_start_time <= "{}"'.format(
                            key['session_start_time'].strftime(
                                '%Y-%m-%d %H:%M:%S')
                            )).fetch('KEY')

            # if more than 3 biased or ephys sessions, see what's up
            if len(sessions) >= 3:

                sessions_rel = sessions[-3:]

                # were these last 3 sessions done on an ephys rig?
                bpod_board = (behavior.Settings & sessions_rel).fetch('pybpod_board')
                ephys_board = [True for i in list(bpod_board) if 'ephys' in i]

                task_protocols = (acquisition.Session & sessions_rel).fetch('task_protocol')
                delays = (behavior.SessionDelay & sessions_rel).fetch('session_delay_in_mins')

                if len(ephys_board) == 3 and np.any(delays > 15):

                    n_trials = (behavior.TrialSet & sessions_rel).fetch('n_trials')
                    performance_easy = (PsychResults & sessions_rel).fetch(
                        'performance_easy')

                    # criterion: 3 sessions with >400 trials, and >90% correct on high contrasts
                    if np.all(n_trials > 400) and np.all(performance_easy > 0.9):

                        trials = behavior.TrialSet.Trial & sessions_rel
                        prob_lefts = (dj.U('trial_stim_prob_left') & trials).fetch(
                            'trial_stim_prob_left')

                        # if no 0.5 of prob_left, keep trained
                        if not np.all(abs(prob_lefts - 0.5) > 0.001):

                            # compute psychometric functions for each of 3 conditions
                            # trials_50 = trials & \
                            #     'ABS(trial_stim_prob_left - 0.5) < 0.001'

                            trials_80 = trials & \
                                'ABS(trial_stim_prob_left - 0.2) < 0.001'

                            trials_20 = trials & \
                                'ABS(trial_stim_prob_left - 0.8) < 0.001'

                            if not (len(trials_80) and len(trials_20)):
                                key['training_status'] = 'trained_1b'
                                self.insert1(key)
                                return

                            # also compute the median reaction time
                            medRT = compute_reaction_time(trials)

                            # psych_unbiased = utils.compute_psych_pars(trials_unbiased)
                            psych_80 = utils.compute_psych_pars(trials_80)
                            psych_20 = utils.compute_psych_pars(trials_20)
                            # psych_50 = utils.compute_psych_pars(trials_50)

                            # repeat the criteria for training_1b
                            # add on criteria for lapses and bias shift in the biased blocks
                            criterion = psych_80['lapse_low'] < 0.1 and \
                                psych_80['lapse_high'] < 0.1 and \
                                psych_20['lapse_low'] < 0.1 and \
                                psych_20['lapse_high'] < 0.1 and \
                                psych_20['bias'] - psych_80['bias'] > 5 and \
                                medRT.loc[medRT['signed_contrast'] == 0, 'rt'].iloc[0] < 2

                            if criterion:
                                # were all 3 sessions done on an ephys rig already?
                                key['training_status'] = 'ready4recording'
                                self.insert1(key)
                                return

        # if the previous status was 'ready4delay', keep
        if len(status) and np.any(status=='ready4delay'):
            key['training_status'] = 'ready4delay'
            self.insert1(key)
            return

        # if not, check for criterion of 'ready4delay'
        if len(status) and np.any(status=='ready4ephysrig'):
            # if the current session is performed on ephys rig, run the biased protocol
            bpod_board = (behavior.Settings & key).fetch1('pybpod_board')
            if 'biased' in task_protocol and 'ephys' in bpod_board:
                n_trials = (behavior.TrialSet & key).fetch1('n_trials')
                performance_easy = (PsychResults & key).fetch1(
                    'performance_easy')
                if n_trials > 400 and performance_easy > 0.9:
                    key['training_status'] = 'ready4delay'
                    self.insert1(key)
                    return

        # ========================================================= #
        # is the animal doing biasedChoiceWorld
        # ========================================================= #

        # if the previous status was 'ready4ephysrig', keep
        if len(status) and np.any(status == 'ready4ephysrig'):
            key['training_status'] = 'ready4ephysrig'
            self.insert1(key)
            return

        # if the protocol for the current session is a biased session,
        # set the status to be "trained" and check up the criteria for
        # "ready4ephysrig"
        task_protocol = (acquisition.Session & key).fetch1('task_protocol')
        if task_protocol and 'biased' in task_protocol:

            # Criteria for "ready4ephysrig" status
            sessions = (behavior.TrialSet & subject_key &
                        (acquisition.Session & 'task_protocol LIKE "%biased%"') &
                        'session_start_time <= "{}"'.format(
                            key['session_start_time'].strftime(
                                '%Y-%m-%d %H:%M:%S')
                            )).fetch('KEY')

            # if there are more than 40 sessions of biasedChoiceWorld, give up on this mouse
            if len(sessions) >= 40:
                key['training_status'] = 'unbiasable'

            # if not more than 3 biased sessions, see what's up
            if len(sessions) >= 3:

                sessions_rel = sessions[-3:]
                n_trials = (behavior.TrialSet & sessions_rel).fetch('n_trials')
                performance_easy = (PsychResults & sessions_rel).fetch(
                    'performance_easy')

                # criterion: 3 sessions with >400 trials, and >90% correct on high contrasts
                if np.all(n_trials > 400) and np.all(performance_easy > 0.9):

                    trials = behavior.TrialSet.Trial & sessions_rel
                    prob_lefts = (dj.U('trial_stim_prob_left') & trials).fetch(
                        'trial_stim_prob_left')

                    # if no 0.5 of prob_left, keep trained
                    if not np.all(abs(prob_lefts - 0.5) > 0.001):

                        # # compute psychometric functions for each of 3 conditions
                        # trials_50 = trials & \
                        #     'ABS(trial_stim_prob_left - 0.5) < 0.001'

                        trials_80 = trials & \
                            'ABS(trial_stim_prob_left - 0.2) < 0.001'

                        trials_20 = trials & \
                            'ABS(trial_stim_prob_left - 0.8) < 0.001'

                        if not (len(trials_80) and len(trials_20)):
                            key['training_status'] = 'trained_1b'
                            self.insert1(key)
                            return

                        # also compute the median reaction time
                        medRT = compute_reaction_time(trials)

                        # psych_unbiased = utils.compute_psych_pars(trials_unbiased)
                        psych_80 = utils.compute_psych_pars(trials_80)
                        psych_20 = utils.compute_psych_pars(trials_20)
                        # psych_50 = utils.compute_psych_pars(trials_50)

                        # repeat the criteria for training_1b
                        # add on criteria for lapses and bias shift in the biased blocks
                        criterion = psych_80['lapse_low'] < 0.1 and \
                            psych_80['lapse_high'] < 0.1 and \
                            psych_20['lapse_low'] < 0.1 and \
                            psych_20['lapse_high'] < 0.1 and \
                            psych_20['bias'] - psych_80['bias'] > 5 and \
                            medRT.loc[medRT['signed_contrast'] == 0, 'rt'].iloc[0] < 2

                        if criterion:
                            key['training_status'] = 'ready4ephysrig'
                            self.insert1(key)
                            return

        # ========================================================= #
        # is the animal doing trainingChoiceWorld?
        # 1B training
        # ========================================================= #

        # if has reached 'trained_1b' before, mark the current session 'trained_1b' as well
        if len(status) and np.any(status == 'trained_1b'):
            key['training_status'] = 'trained_1b'
            self.insert1(key)
            return

        # training in progress if the animals was trained in < 3 sessions
        sessions = (behavior.TrialSet & subject_key &
                    'session_start_time <= "{}"'.format(
                        key['session_start_time'].strftime('%Y-%m-%d %H:%M:%S')
                        )).fetch('KEY')

        if len(sessions) >= 3:

            # training in progress if any of the last three sessions have
            # < 400 trials or performance of easy trials < 0.8
            sessions_rel = sessions[-3:]
            n_trials = (behavior.TrialSet & sessions_rel).fetch('n_trials')
            performance_easy = (PsychResults & sessions_rel).fetch(
                'performance_easy')

            if np.all(n_trials > 400) and np.all(performance_easy > 0.9):
                # training in progress if the current session does not
                # have low contrasts
                contrasts = abs(
                    (PsychResults & key).fetch1('signed_contrasts'))
                if 0 in contrasts and \
                   np.sum((contrasts < 0.065) & (contrasts > 0.001)):
                    # compute psych results of last three sessions
                    trials = behavior.TrialSet.Trial & sessions_rel
                    psych = utils.compute_psych_pars(trials)

                    # also compute the median reaction time
                    medRT = compute_reaction_time(trials)

                    # cum_perform_easy = utils.compute_performance_easy(trials)
                    criterion = abs(psych['bias']) < 10 and \
                        psych['threshold'] < 20 and \
                        psych['lapse_low'] < 0.1 and \
                        psych['lapse_high'] < 0.1 and \
                        medRT.loc[medRT['signed_contrast'] == 0, 'rt'].iloc[0] < 2

                    if criterion:
                        key['training_status'] = 'trained_1b'
                        self.insert1(key)
                        return

        # ========================================================= #
        # is the animal still doing trainingChoiceWorld?
        # 1A training
        # ========================================================= #

        # if has reached 'trained_1a' before, mark the current session 'trained_1a' as well
        if len(status) and np.any(status == 'trained_1a'):
            key['training_status'] = 'trained_1a'
            self.insert1(key)
            return

        # training in progress if the animals was trained in < 3 sessions
        sessions = (behavior.TrialSet & subject_key &
                    'session_start_time <= "{}"'.format(
                        key['session_start_time'].strftime('%Y-%m-%d %H:%M:%S')
                        )).fetch('KEY')
        if len(sessions) >= 3:

            # training in progress if any of the last three sessions have
            # < 400 trials or performance of easy trials < 0.8
            sessions_rel = sessions[-3:]
            n_trials = (behavior.TrialSet & sessions_rel).fetch('n_trials')
            performance_easy = (PsychResults & sessions_rel).fetch(
                'performance_easy')

            if np.all(n_trials > 200) and np.all(performance_easy > 0.8):
                # training in progress if the current session does not
                # have low contrasts
                contrasts = abs(
                    (PsychResults & key).fetch1('signed_contrasts'))
                if 0 in contrasts and \
                   np.sum((contrasts < 0.065) & (contrasts > 0.001)):
                    # compute psych results of last three sessions
                    trials = behavior.TrialSet.Trial & sessions_rel
                    psych = utils.compute_psych_pars(trials)
                    # cum_perform_easy = utils.compute_performance_easy(trials)

                    criterion = abs(psych['bias']) < 16 and \
                        psych['threshold'] < 19 and \
                        psych['lapse_low'] < 0.2 and \
                        psych['lapse_high'] < 0.2

                    if criterion:
                        key['training_status'] = 'trained_1a'
                        self.insert1(key)
                        return

        # ========================================================= #
        # did the animal not get any criterion assigned?
        # ========================================================= #

        # check whether the subject has been trained over 40 days
        if len(sessions) >= 40:
            key['training_status'] = 'untrainable'
            self.insert1(key)
            return

        # ========================================================= #
        # assume a base key of 'in_training' for all mice
        # ========================================================= #

        key['training_status'] = 'in_training'

        self.insert1(key)
