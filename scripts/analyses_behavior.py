from ibl_pipeline.analyses import behavior

kwargs = dict(display_progress=True, suppress_errors=True)

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
