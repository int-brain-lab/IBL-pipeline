import time
from ibl_pipeline import subject, acquisition, data, behavior
from ibl_pipeline.analyses import behavior as behavior_analyses

kwargs = dict(display_progress=True,
              suppress_errors=True,
              reserve_jobs=True)
start = time.time()

print('------ Populating CompleteTrialSession ---------')
behavior.CompleteTrialSession.populate(**kwargs)
print('------------- Populating TrialSet --------------')
behavior.TrialSet.populate(**kwargs)
print('----------- Populating PsychResults ------------')
behavior.PsychResults.populate(**kwargs)
print('--------- Populating PsychResultsBlock ---------')
behavior.PsychResultsBlock.populate(**kwargs)
print('----------- Populating ReactionTime ------------')
behavior.ReactionTime.populate(**kwargs)
print('----- Populating ReactionTimeContrastBlock -----')
behavior.ReactionTimeContrastBlock.populate(**kwargs)
print('------- Populating SessionTrainingStatus -------')
behavior.SessionTrainingStatus.populate(**kwargs)
print('------ Populating BehavioralSummaryByDate ------')
behavior.BehavioralSummaryByDate.populate(**kwargs)

end = time.time()
print(end-start)
