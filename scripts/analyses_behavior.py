from ibl_pipeline.analyses import behavior

kwargs = dict(display_progress=True, suppress_errors=True)

behavior.PsychResults.populate(**kwargs)
behavior.PsychResultsBlock.populate(**kwargs)
behavior.ReactionTime.populate(**kwargs)
behavior.ReactionTimeContrastBlock.populate(**kwargs)
behavior.SessionTrainingStatus.populate(**kwargs)
behavior.BehavioralSummaryByDate.populate(**kwargs)
