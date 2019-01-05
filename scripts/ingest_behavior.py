'''
This script ingest behavioral data into tables in the ibl_behavior schema
'''

from ibl_pipeline import subject, acquisition, data, behavior

behavior.CompleteWheelMoveSession.populate()
behavior.WheelMoveSet.populate(display_progress=True, suppress_errors=True)
behavior.CompleteTrialSession.populate()
behavior.TrialSet.populate(display_progress=True, suppress_errors=True)
