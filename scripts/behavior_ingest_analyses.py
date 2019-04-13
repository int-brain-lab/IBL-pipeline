import time
from ibl_pipeline import subject, acquisition, data, behavior
from ibl_pipeline.analyses import behavior as behavior_analyses

start = time.time()
behavior.CompleteTrialSession.populate(suppress_errors=True)
behavior.TrialSet.populate(display_progress=True, suppress_errors=True)
behavior_analyses.PsychResults.populate(
    display_progress=True, suppress_errors=True)
behavior_analyses.ReactionTime.populate(
    display_progress=True, suppress_errors=True)
behavior_analyses.SessionTrainingStatus.populate(
    display_progress=True, suppress_errors=True)
behavior_analyses.BehavioralSummaryByDate.populate(
    display_progress=True, suppress_errors=True)

end = time.time()

print(end-start)
