from ibl_pipeline import subject, acquisition, data, behavior

behavior.CompleteTrialSession.populate(suppress_errors=True)
behavior.TrialSet.populate(display_progress=True, suppress_errors=True)
