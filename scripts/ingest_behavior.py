'''
This script ingest behavioral data into tables in the ibl_behavior schema
'''

from ibl_pipeline import subject, acquisition, data, behavior

kargs = dict(
    suppress_errors=True, display_progress=True
)

behavior.CompleteWheelMoveSession.populate(**kargs)
behavior.WheelMoveSet.populate(**kargs)
behavior.CompleteTrialSession.populate(**kargs)
behavior.TrialSet.populate(**kargs)
behavior.AmbientSensorData.populate(**kargs)
behavior.Settings.populate(**kargs)
