'''
This script ingest behavioral data into tables in the ibl_behavior schema
'''

import datajoint as dj
from ibl_pipeline import subject, acquisition, data, behavior
from oneibl.one import ONE


behavior.Wheel.populate()
# behavior.WheelMoveSet.populate()
behavior.TrialSet.populate()
