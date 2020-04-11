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

logging.basicConfig(
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler("ephys_ingestion.log"),
        logging.StreamHandler()],
    level=30)

logger = logging.getLogger(__name__)

kargs = dict(display_progress=True, suppress_errors=True)

start_time = time.time()

logger.log(30, 'Ingesting CompleteClusterSession...')
ephys.CompleteClusterSession.populate(**kargs)

complete_cluster_time = time.time()
logger.log(30, 'Ingestion time of CompleteCluster {}'.format(
    complete_cluster_time-start_time))

logger.log(30, 'Ingesting ChannelGroup...')
ephys.ChannelGroup.populate(**kargs)
channel_group_time = time.time()
logger.log(30, 'Ingestion time of ChannelGroup {}'.format(
    channel_group_time-complete_cluster_time))

logger.log(30, 'Ingesting Cluster...')
ephys.DefaultCluster.populate(**kargs)
cluster_time = time.time()
logger.log(30, 'Ingestion time of Cluster {}'.format(
    cluster_time-channel_group_time))

ephys.GoodCluster.populate(**kargs)

logger.log(30, 'Ingesting TrialSpikes...')
ephys.AlignedTrialSpikes.populate(**kargs)
trial_spikes_time = time.time()
logger.log(30, 'Ingestion time of TrialSpikes {}'.format(
    trial_spikes_time-cluster_time))

logger.log(30, 'Ingesting plotting psth...')
ephys_plotting.Psth.populate(
    **kargs)
psth_plotting_time = time.time()
logger.log(30, 'Ingestion time of PSTH {}'.format(
    psth_plotting_time-trial_spikes_time))

logger.log(30, 'Ingesting plotting Raster...')
ephys_plotting.Raster.populate(**kargs)
raster_plotting_time = time.time()
logger.log(30, 'Ingestion time of Raster {}'.format(
    raster_plotting_time-psth_plotting_time))

end_time = time.time()
logger.log(30, 'Total ingestion time {}'.format(
    end_time-start_time
))
