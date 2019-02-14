import datajoint as dj
from .. import subject, action, acquisition, behavior
import numpy as np
import psychofit as psy

schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_analyses_behavior')


@schema
class PsychResults(dj.Computed):
    definition = """
    -> behavior.TrialSet
    ---
    performance:        float   # percentage correct in this session
    contrasts:          blob    # contrasts used in this session
    prob_choose_right:  blob    # probability of choosing right, same size as contrasts
    rt:                 blob    # reaction time, in secs
    threshold:          float
    bias:               float
    lapse_low:          float
    lapse_high:         float
    """
    def make(self, key):
        
        key_psy = key.copy()

        n_trials, n_correct_trials = (behavior.TrialSet & key).fetch1('n_trials', 'n_correct_trials')
        key_psy['performance'] = n_correct_trials/n_trials

        trials = behavior.TrialSet.Trial & key
        trials_rt = trials.proj(rt='trial_response_time-trial_stim_on_time')
        contrasts_left = np.unique(trials.fetch('trial_stim_contrast_left'))[1:] # discard contrast 0
        contrasts_right = np.unique(trials.fetch('trial_stim_contrast_right'))[1:] # discard contrast 0
        trials_no_contrast = trials & 'trial_stim_contrast_right=0' & 'trial_stim_contrast_left=0'
        

        n_right_trials_stim_left = [len(trials & 'trial_stim_contrast_left={}'.format(contrast) & 'trial_response_choice="CCW"') \
                                    for contrast in contrasts_left]
        n_trials_stim_left = [len(trials & 'trial_stim_contrast_left={}'.format(contrast)) \
                                    for contrast in contrasts_left]
        n_right_trials_stim_right = [len(trials & 'trial_stim_contrast_right={}'.format(contrast) & 'trial_response_choice="CCW"') \
                                    for contrast in contrasts_right]
        n_trials_stim_right = [len(trials & 'trial_stim_contrast_right={}'.format(contrast)) \
                                    for contrast in contrasts_right]

        p_right_stim_left = np.divide(n_right_trials_stim_left, n_trials_stim_left)
        p_right_stim_right = np.divide(n_right_trials_stim_right, n_trials_stim_right)

        rt_stim_left = [(trials_rt & (trials & 'trial_stim_contrast_left={}'.format(contrast))).fetch('rt').mean() \
                        for contrast in contrasts_left]
        rt_stim_right = [(trials_rt & (trials & 'trial_stim_contrast_right={}'.format(contrast))).fetch('rt').mean() \
                        for contrast in contrasts_right]
        
        trials_no_contrast = trials & 'trial_stim_contrast_right=0' & 'trial_stim_contrast_left=0'
        if trials_no_contrast:
            key_psy['contrasts'] = np.hstack([np.negative(contrasts_left[::-1]), 0,  contrasts_right])*100
            
            p_right_no_contrast = len(trials_no_contrast & 'trial_response_choice="CCW"')/len(trials_no_contrast)            
            key_psy['prob_choose_right'] = np.hstack([p_right_stim_left[::-1], p_right_no_contrast, p_right_stim_right])
            n_total_trials = np.hstack([n_trials_stim_left, len(trials_no_contrast), n_trials_stim_right])
            rt_no_contrast = (trials_rt & trials_no_contrast).fetch('rt').mean()
            key_psy['rt'] = np.hstack([rt_stim_left, rt_no_contrast, rt_stim_right])
        else:
            key_psy['contrasts'] = np.hstack([np.negative(contrasts_left[::-1]),  contrasts_right])*100
            key_psy['prob_choose_right'] = np.hstack([(p_right_stim_left[::-1]), p_right_stim_right])
            n_total_trials = np.hstack([n_trials_stim_left, n_trials_stim_right])
            key_psy['rt'] = np.hstack([rt_stim_left, rt_stim_right])

        pars, L = psy.mle_fit_psycho(np.vstack([key_psy['contrasts'], n_total_trials, key_psy['prob_choose_right']]), \
                P_model='erf_psycho_2gammas', \
                parstart=np.array([key_psy['contrasts'].mean(), 20., 0.05, 0.05]), \
                parmin=np.array([key_psy['contrasts'].mean(), 0., 0., 0.]), \
                parmax=np.array([key_psy['contrasts'].mean(), 100., 1, 1]))
        print(pars)
        key_psy['bias'] = pars[0]
        key_psy['threshold'] = pars[1] 
        key_psy['lapse_low'] = pars[2]
        key_psy['lapse_high'] = pars[3]

        self.insert1(key_psy)
        