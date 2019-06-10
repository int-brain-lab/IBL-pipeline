import datajoint as dj
from .. import subject, action, acquisition, behavior
from ..utils import psychofit as psy
from . import analysis_utils as utils
from datetime import datetime
import numpy as np

schema = dj.schema(dj.config.get('database.prefix', '') +
                   'ibl_analyses_behavior')


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

        if task_protocol and ('biased' in task_protocol):
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
         'stim_on_times_status = "Complete"')

    def make(self, key):
        trials = behavior.TrialSet.Trial & key
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
         'stim_on_times_status = "Complete"')

    def make(self, key):
        task_protocol = (acquisition.Session & key).fetch1(
            'task_protocol')

        trials = behavior.TrialSet.Trial & key

        if task_protocol and ('biased' in task_protocol):
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

        self.insert1(master_entry)

        complete = (behavior.CompleteTrialSession & trial_sets_keys).fetch(
            'stim_on_times_status'
        )

        # compute reaction time for all trials
        if 'Complete' in complete:
            trials_with_stim_on_time = trials & 'trial_stim_on_time is not NULL'

            if len(trials_with_stim_on_time):
                rts = trials_with_stim_on_time.proj(
                    rt='trial_response_time-trial_stim_on_time').fetch('rt')
                rt_overall['median_reaction_time'] = np.median(rts)
                self.ReactionTimeByDate.insert1(rt_overall)

        # compute psych results for all trials

        task_protocols = (acquisition.Session & trial_sets_keys).fetch(
            'task_protocol')
        task_protocols = [protocol for protocol in task_protocols if protocol]

        if any('biased' in task_protocol
               for task_protocol in task_protocols):
            trials_biased = trials & (acquisition.Session &
                                      trial_sets_keys &
                                      'task_protocol LIKE "%biased%"')
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
                if 'Complete' in complete:
                    trials_sub = trials_sub & 'trial_stim_on_time is not NULL'
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
            if 'Complete' in complete:
                trials = trials & 'trial_stim_on_time is not NULL'
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
    contents = zip(['over40days',
                    'training in progress',
                    'trained',
                    'ready for ephys',
                    'wrong session type run'])


@schema
class SessionTrainingStatus(dj.Computed):
    definition = """
    -> PsychResults
    ---
    -> TrainingStatus
    """

    def make(self, key):
        cum_psych_results = key.copy()
        subject_key = key.copy()
        subject_key.pop('session_start_time')

        previous_sessions = SessionTrainingStatus & subject_key & \
            'session_start_time < "{}"'.format(
                key['session_start_time'].strftime('%Y-%m-%d %H:%M:%S')
            )
        status = previous_sessions.fetch('training_status')

        # ================================= #
        # if the protocol for the current session is a biased session,
        # set the status to be "trained" and check up the criteria for
        # "ready for ephys"
        # ================================= #

        task_protocol = (acquisition.Session & key).fetch1('task_protocol')
        if task_protocol and 'biased' in task_protocol:
            if not(len(status) and np.any(status == 'trained')):
                key['training_status'] = 'wrong session type run'
                self.insert1(key)
                return

            # if the animal previously reached 'ready for ephys', keep
            elif len(status) and np.any(status == 'ready for ephys'):
                key['training_status'] = 'ready for ephys'
                self.insert1(key)
                return

            # key['training_status'] = 'trained'
            # Criteria for "ready for ephys" status
            sessions = (behavior.TrialSet & subject_key &
                        (acquisition.Session & 'task_protocol LIKE "%biased%"') &
                        'session_start_time <= "{}"'.format(
                            key['session_start_time'].strftime(
                                '%Y-%m-%d %H:%M:%S')
                            )).fetch('KEY')

            # if not more than 3 biased sessions, continue 
            if len(sessions) >= 3:
                    # self.insert1(key)
                    # return

                sessions_rel = sessions[-3:]
                n_trials = (behavior.TrialSet & sessions_rel).fetch('n_trials')
                performance_easy = (PsychResults & sessions_rel).fetch(
                    'performance_easy')
                if np.all(n_trials > 200) and np.all(performance_easy > 0.8):
                    trials = behavior.TrialSet.Trial & sessions_rel
                    prob_lefts = (dj.U('trial_stim_prob_left') & trials).fetch(
                        'trial_stim_prob_left')

                    # check if there are biased blocks present in these 3 sessions
                    if not np.all(abs(prob_lefts - 0.5) > 0.001):
                            # self.insert1(key)
                            # return

                        trials_unbiased = trials & \
                            'ABS(trial_stim_prob_left - 0.5) < 0.001'

                        trials_80 = trials & \
                            'ABS(trial_stim_prob_left - 0.2) < 0.001'

                        trials_20 = trials & \
                            'ABS(trial_stim_prob_left - 0.8) < 0.001'

                        psych_unbiased = utils.compute_psych_pars(trials_unbiased)
                        psych_80 = utils.compute_psych_pars(trials_80)
                        psych_20 = utils.compute_psych_pars(trials_20)

                        criterion = abs(psych_unbiased['bias']) < 16 and \
                            psych_unbiased['threshold'] < 19 and \
                            psych_unbiased['lapse_low'] < 0.2 and \
                            psych_unbiased['lapse_high'] < 0.2 and \
                            psych_20['bias'] - psych_80['bias'] > 5

                        # if 'ready for ephys' is met, mark and return
                        if criterion:
                            key['training_status'] = 'ready for ephys'
                            self.insert1(key)
                            return

        # if the current session is not a biased session
        # key['training_status'] = 'training in progress'

        # ================================= #
        # if has reached 'trained' before, mark the current session 'trained' as well
        # ================================= #

        if len(status) and np.any(status == 'trained'):
            key['training_status'] = 'trained'
            self.insert1(key)
            return

        # training in progress if the animals was trained in < 3 sessions
        sessions = (behavior.TrialSet & subject_key &
                    'session_start_time <= "{}"'.format(
                        key['session_start_time'].strftime('%Y-%m-%d %H:%M:%S')
                        )).fetch('KEY')

        # ================================= #
        # if the animal did more than 3 sessions,
        # check if it may be considered 'trained'
        # ================================= #

        if len(sessions) >= 3:
            # self.insert1(key)
            # return

            # training in progress if any of the last three sessions have
            # < 200 trials or performance of easy trials < 0.8
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
                    cum_perform_easy = utils.compute_performance_easy(trials)

                    criterion = abs(psych['bias']) < 16 and \
                        psych['threshold'] < 19 and \
                        psych['lapse_low'] < 0.2 and \
                        psych['lapse_high'] < 0.2

                    if criterion:
                        key['training_status'] = 'trained'
                        self.insert1(key)
                        # insert computed results into the part table
                        n_trials, n_correct_trials = \
                            (behavior.TrialSet & key).fetch(
                                'n_trials', 'n_correct_trials')
                        cum_psych_results.update({
                            'cum_performance': np.divide(
                                np.sum(n_correct_trials),
                                np.sum(n_trials)),
                            'cum_performance_easy': cum_perform_easy,
                            'cum_signed_contrasts': psych['signed_contrasts'],
                            'cum_n_trials_stim': psych['n_trials_stim'],
                            'cum_n_trials_stim_right': psych[
                                'n_trials_stim_right'],
                            'cum_prob_choose_right': psych['prob_choose_right'],
                            'cum_bias': psych['bias'],
                            'cum_threshold': psych['threshold'],
                            'cum_lapse_low': psych['lapse_low'],
                            'cum_lapse_high': psych['lapse_high']
                        })
                        self.CumulativePsychResults.insert1(cum_psych_results)
                        return

        # ================================= #
        # if none of the previous criteria has been met,
        # check whether the subject has been trained over 40 days
        # ================================= #

        if len(sessions) >= 40:
            key['training_status'] = 'over40days'

        self.insert1(key)

    class CumulativePsychResults(dj.Part):
        definition = """
        # cumulative psych results from the last three sessions
        -> master
        ---
        cum_performance:            float   # percentage correct in this session
        cum_performance_easy=null:  float   # percentage correct on easy trials 0.5 and 1
        cum_signed_contrasts:       blob    # contrasts used in this session, negative when on the left
        cum_n_trials_stim:          blob    # number of trials for each contrast
        cum_n_trials_stim_right:    blob    # number of reporting "right" trials for each contrast
        cum_prob_choose_right:      blob    # probability of choosing right, same size as contrasts
        cum_threshold:              float
        cum_bias:                   float
        cum_lapse_low:              float
        cum_lapse_high:             float
        """
