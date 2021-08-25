'''
This script delete the rasters and psth plots from the old ephys sessions, and repopulate,
from most recent to oldest
'''


import datajoint as dj
from ibl_pipeline import ephys
from ibl_pipeline.plotting import ephys as ephys_plotting
from tqdm import tqdm
from uuid import UUID
import datetime

if __name__ == '__main__':

    keys = (ephys.CompleteClusterSession &
            (ephys_plotting.RasterLinkS3 & 'session_start_time < "2019-12-07 16:00:00"')).fetch(
                'KEY', order_by='session_start_time desc')

    # keys = \
    #     [{'subject_uuid': UUID('221b68e7-0014-46ae-b8af-308665d8b478'),
    #      'session_start_time': datetime.datetime(2020, 2, 3, 13, 49, 31)},
    #      {'subject_uuid': UUID('d528fe0e-ac52-4fdc-bfb9-c545e44ded66'),
    #      'session_start_time': datetime.datetime(2020, 2, 3, 12, 31, 9)}]

    with dj.config(safemode=False):
        for key in tqdm(keys, position=0):
            print(key)
            # delete tables
            print('deleting entries from TrialSpikes cluster by cluster...')
            # delete from TrialSpikes cluster by cluster
            clusters = (ephys.Cluster & key).fetch('KEY')

            for cluster in tqdm(clusters, position=0):
                (ephys.TrialSpikes & cluster).delete()

            print('repopulating TrialSpikes...')
            ephys.TrialSpikes.populate(
                key, display_progress=True,
                suppress_errors=True)

            print('deleting entries from Raster...')
            (ephys_plotting.RasterLinkS3 & key).delete()

            print('repopulating Raster...')
            ephys_plotting.RasterLinkS3.populate(
                key, display_progress=True,
                suppress_errors=True)

            print('deleting entries from Psth...')
            (ephys_plotting.PsthDataVarchar & key).delete()

            ephys_plotting.PsthDataVarchar.populate(
                key, display_progress=True,
                suppress_errors=True)
