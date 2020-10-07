#!/usr/bin/python3

'''
This script tests the ingestion of ephys pipeline.
Shan Shen, 2019-11-20

Added a number of plotting tables.
Shan Shen, 2020-08-15
'''

from ibl_pipeline.common import *
import logging
import time

import datetime
from uuid import UUID

EPHYS_TABLES = [
    ephys.CompleteClusterSession,
    ephys.DefaultCluster,
    ephys.AlignedTrialSpikes,
    ephys.GoodCluster,
    ephys_analyses.DepthPeth,
    ephys_analyses.NormedDepthPeth,
    histology.ClusterBrainRegion,
    histology.SessionBrainRegion,
    ephys_plotting.DepthRaster,
    ephys_plotting.DepthPeth,
    ephys_plotting.Raster,
    ephys_plotting.Psth,
    ephys_plotting.SpikeAmpTime,
    ephys_plotting.AutoCorrelogram,
    ephys_plotting.Waveform,
    ephys_plotting.DepthRasterExampleTrial,
]


def main(exclude_plottings=False):
    logging.basicConfig(
        format='%(asctime)s - %(message)s',
        handlers=[
            logging.FileHandler("ephys_ingestion.log"),
            logging.StreamHandler()],
        level=30)

    logger = logging.getLogger(__name__)

    kwargs = dict(display_progress=True, suppress_errors=True)

    start_time = time.time()

    for table in EPHYS_TABLES:
        table_start_time = time.time()
        if exclude_plottings and table.__module__ == 'ibl_pipeline.plotting.ephys':
            continue
        logger.log(30, 'Ingesting {}...'.format(table.__name__))
        table.populate(**kwargs)
        logger.log(30, 'Ingestion time of {} is {}'.format(
            table.__name__,
            time.time()-table_start_time))

    end_time = time.time()
    logger.log(30, 'Total ingestion time {}'.format(
        end_time-start_time
    ))


if __name__ == '__main__':

    main(exclude_plottings=True)
