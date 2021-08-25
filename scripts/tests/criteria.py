'''
This script tests the new version of criteria for the behavior benchmarks

Shan Shen, 2019-11-02
'''

from ibl_pipeline import subject, acquisition, behavior
from ibl_pipeline.analyses import behavior as behavior_analyses
from ibl_pipeline.plotting import behavior as behavior_plotting

if __name__ == '__main__':
    test_animals = [
        {'subject_nickname': 'ZM_1743'},
        # {'subject_nickname': 'IBL-T4'},
        # {'subject_nickname': 'ibl_witten_07'}
    ]

    subjs = subject.Subject & test_animals
    (behavior_analyses.SessionTrainingStatus & subjs).delete()
    behavior_analyses.SessionTrainingStatus.populate(subjs, display_progress=True)
    # (behavior.CumulativeSummary & subjs).delete()
    # behavior_plotting.CumulativeSummary.populate(subjs)
