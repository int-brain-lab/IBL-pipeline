'''
This script tests the modification on using go_cue_trigger_time
for RT computation with stim_on_time is not available

Shan Shen, Dec, 2019
'''

from ibl_pipeline import subject, acquisition, behavior
from ibl_pipeline.analyses import behavior as behavior_analyses
from ibl_pipeline.plotting import behavior as behavior_plotting

subj = subject.Subject & 'subject_nickname="SWC_018"'

print('Testing ReactionTime...')
behavior_analyses.ReactionTime.populate(subj, display_progress=True)

print('Testing ReactionTimeContrastBlock...')
behavior_analyses.ReactionTimeContrastBlock.populate(
    subj, display_progress=True)
print('Testing plotting functions for \
    SessionReactionTimeContrast and SessionReactionTimeTrialNumber')
behavior_plotting.SessionReactionTimeContrast.populate(
    subj, display_progress=True)
