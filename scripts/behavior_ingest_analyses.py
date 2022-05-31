import time

from ibl_pipeline import acquisition, behavior, data, subject
from ibl_pipeline.analyses import behavior as behavior_analyses

if __name__ == "__main__":
    kwargs = dict(display_progress=True, suppress_errors=True)
    start = time.time()
    behavior.CompleteTrialSession.populate(**kwargs)
    behavior.TrialSet.populate(**kwargs)
    behavior_analyses.PsychResults.populate(**kwargs)
    behavior_analyses.ReactionTime.populate(**kwargs)
    behavior_analyses.SessionTrainingStatus.populate(**kwargs)
    behavior_analyses.BehavioralSummaryByDate.populate(**kwargs)

    end = time.time()
    print(end - start)
