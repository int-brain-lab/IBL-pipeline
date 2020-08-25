'''
This script ingest behavioral data into tables in the ibl_behavior schema
'''

from ibl_pipeline import subject, acquisition, data, behavior


if __name__ == '__main__':
    kargs = dict(
        suppress_errors=True, display_progress=True
    )

    print('-------- Populating CompleteWheelMoveSession -------')
    behavior.CompleteWheelMoveSession.populate(**kargs)
    # print('-------------- Populating WheelMoveSet -------------')
    # behavior.WheelMoveSet.populate(**kargs)
    print('---------- Populating CompleteTrialSession ---------')
    behavior.CompleteTrialSession.populate(**kargs)
    print('---------------- Populating TrialSet ---------------')
    behavior.TrialSet.populate(**kargs)
    print('------------ Populating AmbientSensorData ----------')
    behavior.AmbientSensorData.populate(**kargs)
    print('---------------- Populating Settings ---------------')
    behavior.Settings.populate(**kargs)
    print('------------- Populating SessionDelay --------------')
    behavior.SessionDelay.populate(**kargs)
