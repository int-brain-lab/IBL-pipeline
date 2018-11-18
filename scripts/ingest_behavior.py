'''
This script ingest behavioral data into tables in the ibl_behavior schema
'''

from ibl_pipeline import subject, acquisition, data, behavior


behavior.Wheel.populate()
# behavior.WheelMoveSet.populate()
behavior.CompleteSession.populate()
behavior.TrialSet.populate()
