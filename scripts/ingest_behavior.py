'''
This script ingest behavioral data into tables in the ibl_behavior schema
'''

from ibl_pipeline import subject, acquisition, data, behavior

behavior.CompleteWheelSession.populate()
behavior.Wheel.populate()
# behavior.WheelMoveSet.populate()
behavior.CompleteTrialSession.populate()
behavior.TrialSet.populate()
