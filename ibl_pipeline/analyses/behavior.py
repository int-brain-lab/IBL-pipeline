import datajoint as dj
from .. import subject, action, acquisition, behavior
from . import psychofit as psy
import numpy as np


schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_analyses_behavior')


@schema
class Contrasts(dj.Computed):
    definition = """
    -> behavior.TrialSet
    ---
    contrasts:                      blob    # contrasts used in this session, negative when on the left
    has_no_contrast:                bool    # have trials with no contrast
    has_left:                       bool    # have trials with contrast on the left
    has_right:                      bool    # have trials with contrast on the right
    contrasts_left=null:            blob    # contrasts shown on the left
    contrasts_right=null:           blob    # contrasts shown on the right
    n_trials_stim:                  blob    # number of trials for each contrast
    n_trials_stim_left=null:        blob    # number of trials when the stimulus is shown on the left
    n_trials_stim_right=null:       blob    # number of trials when the stimulus is shown on the right
    n_trials_stim_no_contrast=null: int     # number of trials when no stimulus is shown 
    """

    def make(self, key):

        key_con = key.copy()
        trials = behavior.TrialSet.Trial & key
        contrasts_left = np.unique(trials.fetch('trial_stim_contrast_left'))
        contrasts_right = np.unique(trials.fetch('trial_stim_contrast_right'))

        # discard contrast 0
        if contrasts_left[0] == 0:
            contrasts_left = contrasts_left[1:]

        if contrasts_right[0] == 0:
            contrasts_right = contrasts_right[1:]
        
        trials_no_contrast = trials & 'trial_stim_contrast_right=0' & 'trial_stim_contrast_left=0'

        key_con['has_left'] = False
        key_con['has_right'] = False
        key_con['has_no_contrast'] = False
        
        if contrasts_left.size != 0:
            key_con['has_left'] = True
            key_con['contrasts_left'] = contrasts_left
            n_trials_stim_left = [len(trials & 'ABS(trial_stim_contrast_left-{})<1e-6'.format(contrast)) \
                                    for contrast in contrasts_left]
            key_con['n_trials_stim_left'] = n_trials_stim_left
        else:
            n_trials_stim_left = []
            
        if contrasts_right.size != 0:
            key_con['has_right'] = True
            key_con['contrasts_right'] = contrasts_right
            n_trials_stim_right = [len(trials & 'ABS(trial_stim_contrast_right-{})<1e-6'.format(contrast)) \
                                    for contrast in contrasts_right]
            key_con['n_trials_stim_right'] = n_trials_stim_right
        else:
            n_trials_stim_right = []
        
        if len(trials_no_contrast) > 0:
            key_con['has_no_contrast'] = True
            no_contrast = 0
            n_trials_stim_no_contrast = len(trials_no_contrast)
            key_con['n_trials_stim_no_contrast'] = n_trials_stim_no_contrast
        else:
            no_contrast = []
            n_trials_stim_no_contrast = [] 
            
        key_con['contrasts'] = np.hstack([np.negative(contrasts_left), no_contrast, contrasts_right])
        key_con['n_trials_stim'] = np.hstack([n_trials_stim_left, n_trials_stim_no_contrast, n_trials_stim_right])

        self.insert1(key_con)



@schema
class PsychResults(dj.Computed):
    definition = """
    -> Contrasts
    ---
    performance:        float   # percentage correct in this session
    prob_choose_right:  blob    # probability of choosing right, same size as contrasts
    threshold:          float
    bias:               float
    lapse_low:          float
    lapse_high:         float
    """

    def make(self, key):

        print(key)
        
        key_psy = key.copy()

        n_trials, n_correct_trials = (behavior.TrialSet & key).fetch1(
            'n_trials', 'n_correct_trials')
        key_psy['performance'] = n_correct_trials/n_trials

        trials = behavior.TrialSet.Trial & key

        contrasts, has_left, has_right, has_no_contrast, n_trials_stim = (Contrasts & key).fetch1(
            'contrasts', 'has_left', 'has_right', 'has_no_contrast', 'n_trials_stim')
    
        if has_left:
            contrasts_left, n_trials_stim_left = (Contrasts & key).fetch1(
                'contrasts_left', 'n_trials_stim_left')
            n_right_trials_stim_left = [len(trials & 'ABS(trial_stim_contrast_left-{})<1e-6'.format(contrast) & \
                                            'trial_response_choice="CCW"') \
                                        for contrast in contrasts_left]
            p_right_stim_left = np.divide(n_right_trials_stim_left, n_trials_stim_left)
        else:
            p_right_stim_left = []

        
        if has_right:
            contrasts_right, n_trials_stim_right = (Contrasts & key).fetch1(
                'contrasts_right', 'n_trials_stim_right')
            n_right_trials_stim_right = [len(trials & 'ABS(trial_stim_contrast_right-{})<1e-6'.format(contrast) & \
                                            'trial_response_choice="CCW"') \
                                        for contrast in contrasts_right]
            p_right_stim_right = np.divide(n_right_trials_stim_right, n_trials_stim_right)
        else:
            p_right_stim_right = []
        
        if has_no_contrast:
            n_trials_stim_no_contrast = (Contrasts & key).fetch1(
                'n_trials_stim_no_contrast')
            trials_no_contrast = trials & 'trial_stim_contrast_right=0' & 'trial_stim_contrast_left=0'
            p_right_no_contrast = len(trials_no_contrast & 'trial_response_choice="CCW"')/n_trials_stim_no_contrast        
        else:
            p_right_no_contrast = []
        
        prob_choose_right = np.hstack([p_right_stim_left, p_right_no_contrast, p_right_stim_right])

        pars, L = psy.mle_fit_psycho(np.vstack([contrasts, n_trials_stim, prob_choose_right]), \
                P_model='erf_psycho_2gammas', \
                parstart=np.array([contrasts.mean(), 20., 0.05, 0.05]), \
                parmin=np.array([contrasts.mean(), 0., 0., 0.]), \
                parmax=np.array([contrasts.mean(), 100., 1, 1]))
        
        

        key_psy['prob_choose_right'] = prob_choose_right
        key_psy['bias'] = pars[0]
        key_psy['threshold'] = pars[1] 
        key_psy['lapse_low'] = pars[2]
        key_psy['lapse_high'] = pars[3]

        self.insert1(key_psy)


@schema
class ReactionTime(dj.Computed):
    definition = """
    -> Contrasts
    ---
    reaction_time:     blob   # reaction time for all contrasts
    """

    key_source = behavior.TrialSet & \
        (behavior.CompleteTrialSession & 'stim_on_times_status != "Missing"') & \
        PsychResults

    def make(self, key):
        
        key_rt = key.copy()
        trials = behavior.TrialSet.Trial & key
        contrasts_left = np.unique(trials.fetch('trial_stim_contrast_left'))[1:] # discard contrast 0
        contrasts_right = np.unique(trials.fetch('trial_stim_contrast_right'))[1:] # discard contrast 0
        trials_no_contrast = trials & 'trial_stim_contrast_right=0' & 'trial_stim_contrast_left=0'

        trials_rt = trials.proj(rt='trial_response_time-trial_stim_on_time')

        rt_stim_left = [(trials_rt & (trials & 'ABS(trial_stim_contrast_left-{})<1e-6'.format(contrast))).fetch('rt').mean() \
                        for contrast in contrasts_left]
        rt_stim_right = [(trials_rt & (trials & 'ABS(trial_stim_contrast_right-{})<1e-6'.format(contrast))).fetch('rt').mean() \
                        for contrast in contrasts_right]

        rt_no_contrast = (trials_rt & trials_no_contrast).fetch('rt').mean()
        
        if trials_no_contrast:
        
            rt_no_contrast = (trials_rt & trials_no_contrast).fetch('rt').mean()
            key_rt['reaction_time'] = np.hstack([rt_stim_left, rt_no_contrast, rt_stim_right])
        else:
            key_rt['reaction_time'] = np.hstack([rt_stim_left, rt_stim_right])

        self.insert1(key_rt)
