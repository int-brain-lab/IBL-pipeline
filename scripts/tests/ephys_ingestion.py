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

key = {'subject_uuid': UUID('f6fe3981-8b66-4ff7-828b-1a79bd31f0fe'),
       'session_start_time': datetime.datetime(2020, 2, 13, 10, 58, 33)}

logging.basicConfig(
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler("test_ephys_ingestion.log"),
        logging.StreamHandler()],
    level=30)

logger = logging.getLogger(__name__)

kargs = dict(display_progress=True, suppress_errors=True)

start_time = time.time()

logger.log(30, 'Testing ingestion of CompleteClusterSession...')
ephys.CompleteClusterSession.populate(key, **kargs)

complete_cluster_time = time.time()
logger.log(30, 'Ingestion time of ProbeInsertion {}'.format(
    complete_cluster_time-start_time))

logger.log(30, 'Testing ingestion of ProbeInsertion...')
ephys.ProbeInsertion.populate(key, **kargs)

probe_insertion_time = time.time()
logger.log(30, 'Ingestion time of ProbeInsertion {}'.format(
    probe_insertion_time-complete_cluster_time))


logger.log(30, 'Testing ingestion of ProbeTrajectory...')
ephys.ProbeTrajectory.populate(key, **kargs)

probe_trajectory_time = time.time()
logger.log(30, 'Ingestion time of ProbeTrajectory {}'.format(
    probe_trajectory_time-probe_insertion_time))

logger.log(30, 'Testing ingestion of ChannelGroup...')
ephys.ChannelGroup.populate(key, **kargs)
channel_group_time = time.time()
logger.log(30, 'Ingestion time of ChannelGroup {}'.format(
    channel_group_time-probe_trajectory_time))

logger.log(30, 'Testing ingestion of Cluster...')
ephys.DefaultCluster.populate(key, **kargs)
cluster_time = time.time()
logger.log(30, 'Ingestion time of Cluster {}'.format(
    cluster_time-channel_group_time))

logger.log(30, 'Testing ingestion of TrialSpikes...')
ephys.AlignedTrialSpikes.populate(**kargs)
trial_spikes_time = time.time()
logger.log(30, 'Ingestion time of TrialSpikes {}'.format(
    trial_spikes_time-cluster_time))

logger.log(30, 'Testing ingestion of plotting raster...')
ephys_plotting.Raster.populate(
    **kargs)
raster_plotting_time = time.time()
logger.log(30, 'Ingestion time of Raster {}'.format(
    raster_plotting_time-trial_spikes_time))

logger.log(30, 'Testing ingestion of plotting psth...')
ephys_plotting.Psth.populate(
    **kargs)
psth_plotting_time = time.time()
logger.log(30, 'Ingestion time of TrialSpikes {}'.format(
    psth_plotting_time-raster_plotting_time))

end_time = time.time()
logger.log(30, 'Total ingestion time {}'.format(
    end_time-start_time
))
