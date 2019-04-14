from ibl_pipeline.analyses import behavior

behavior.PsychResults.populate(diplay_progress=True, suppress_errors=True)
behavior.ReactionTime.populate(display_progress=True, suppress_errors=True)
behavior.SessionTrainingStatus.populate(diplay_progress=True,
                                        suppress_errors=True)
behavior.BehavioralSummaryByDate.populate(display_prgress=True,
                                          suppress_errors=True)
