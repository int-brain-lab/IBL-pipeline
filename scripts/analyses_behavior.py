from ibl_pipeline.analyses import behavior

behavior.PsychResults.populate(suppress_errors=True)
behavior.ReactionTime.populate(suppress_errors=True)
behavior.SessionTrainingStatus.populate(suppress_errors=True)

behavior.BehavioralSummaryByDate.populate(suppress_errors=True)
