'''
This script tests the ingestion of ephys pipeline.

Shan Shen, 2019-11-20
'''

from ibl_pipeline import subject, acquisition, behavior, ephys
from ibl_pipeline.plotting import ephys as ephys_plotting
import logging
import time

import datetime
from uuid import UUID

key = {'subject_uuid': UUID('10fd3170-6c52-4cb6-986f-aa73704277c0'),
       'session_start_time': datetime.datetime(2019, 11, 11, 14, 26, 45)}

restriction = 'session_start_time > "2019-11-30"'

logging.basicConfig(
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler("ephys_ingestion.log"),
        logging.StreamHandler()],
    level=logging.DEBUG)

logger = logging.getLogger(__name__)

kargs = dict(display_progress=True, suppress_errors=True)

start_time = time.time()

logger.debug('Testing ingestion of CompleteClusterSession...')
ephys.CompleteClusterSession.populate(key, **kargs)

complete_cluster_time = time.time()
logger.debug('Ingestion time of ProbeInsertion {}'.format(
    complete_cluster_time-start_time))

logger.debug('Testing ingestion of ProbeInsertion...')
ephys.ProbeInsertion.populate(key, **kargs)

probe_insertion_time = time.time()
logger.debug('Ingestion time of ProbeInsertion {}'.format(
    probe_insertion_time-complete_cluster_time))


logger.debug('Testing ingestion of ProbeTrajectory...')
ephys.ProbeTrajectory.populate(key, **kargs)

probe_trajectory_time = time.time()
logger.debug('Ingestion time of ProbeTrajectory {}'.format(
    probe_trajectory_time-probe_insertion_time))

logger.debug('Testing ingestion of ChannelGroup...')
ephys.ChannelGroup.populate(key, **kargs)
channel_group_time = time.time()
logger.debug('Ingestion time of ChannelGroup {}'.format(
    channel_group_time-probe_trajectory_time))

logger.debug('Testing ingestion of Cluster...')
ephys.Cluster.populate(key, **kargs)
cluster_time = time.time()
logger.debug('Ingestion time of Cluster {}'.format(
    cluster_time-channel_group_time))

logger.debug('Testing ingestion of TrialSpikes...')
ephys.TrialSpikes.populate(**kargs)
trial_spikes_time = time.time()
logger.debug('Ingestion time of TrialSpikes {}'.format(
    trial_spikes_time-cluster_time))

logger.debug('Testing ingestion of plotting raster...')
ephys_plotting.RasterLinkS3.populate(
    **kargs)
raster_plotting_time = time.time()
logger.debug('Ingestion time of RasterLinkS3 {}'.format(
    raster_plotting_time-trial_spikes_time))

logger.debug('Testing ingestion of plotting psth...')
ephys_plotting.PsthDataVarchar.populate(
    **kargs)
psth_plotting_time = time.time()
logger.debug('Ingestion time of TrialSpikes {}'.format(
    psth_plotting_time-raster_plotting_time))

end_time = time.time()
logger.debug('Total ingestion time {}'.format(
    end_time-start_time
))
