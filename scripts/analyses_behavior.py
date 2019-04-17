from ibl_pipeline.analyses import behavior

behavior.PsychResults.populate(display_progress=True, suppress_errors=True)
behavior.ReactionTime.populate(display_progress=True, suppress_errors=True)
behavior.SessionTrainingStatus.populate(display_progress=True,
                                        suppress_errors=True)
behavior.BehavioralSummaryByDate.populate(display_progress=True,
                                          suppress_errors=True)
