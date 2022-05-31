#!/usr/bin/python3

"""
Ingestion routine of ephys pipeline.
Shan Shen, 2019-11-20

Added a number of plotting tables.
Shan Shen, 2020-08-15

Added histology tables populate
Thinh Nguyen, 2021-10-15
"""

import logging
import pathlib
import time

from ibl_pipeline import ephys, histology, mode
from ibl_pipeline.analyses import ephys as ephys_analyses
from ibl_pipeline.plotting import ephys as ephys_plotting
from ibl_pipeline.plotting import histology as histology_plotting

log_path = pathlib.Path(__file__).parent / "logs"
log_path.mkdir(parents=True, exist_ok=True)
log_file = log_path / f'ephys_ingestion{"_public" if mode == "public" else ""}.log'
log_file.touch(exist_ok=True)

logging.basicConfig(
    format="%(asctime)s - %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    level=30,
)

logger = logging.getLogger(__name__)

EPHYS_TABLES = [
    ephys.CompleteClusterSession,
    ephys.DefaultCluster,
    ephys.AlignedTrialSpikes,
    ephys.GoodCluster,
    ephys.ChannelGroup,
    ephys_analyses.DepthPeth,
    ephys_analyses.NormedDepthPeth,
    # ephys_plotting.DepthRaster,
    ephys_plotting.DepthPeth,
    ephys_plotting.Raster,
    ephys_plotting.Psth,
    ephys_plotting.SpikeAmpTime,
    ephys_plotting.AutoCorrelogram,
    ephys_plotting.Waveform,
    ephys_plotting.DepthRasterExampleTrial,
]

HISTOLOGY_TABLES = [
    histology.ProbeTrajectory,
    histology.ChannelBrainLocation,
    histology.ClusterBrainRegion,
    histology_plotting.SubjectSpinningBrain,
    histology_plotting.ProbeTrajectoryCoronal,
]


if mode != "public":
    HISTOLOGY_TABLES.extend(
        [
            histology.ClusterBrainRegionTemp,
            histology.ProbeBrainRegionTemp,
            histology.DepthBrainRegionTemp,
        ]
    )


gkwargs = dict(display_progress=True, suppress_errors=True)


def main(exclude_plottings=False, run_duration=3600 * 3, sleep_duration=60, **kwargs):

    start_time = time.time()
    while (
        (time.time() - start_time < run_duration)
        or (run_duration is None)
        or (run_duration < 0)
    ):

        tstart = time.time()

        logger.log(30, "Ephys populate")

        for table in EPHYS_TABLES:
            table_start_time = time.time()
            if exclude_plottings and table.__module__ == "ibl_pipeline.plotting.ephys":
                continue
            logger.log(30, "Ingesting {}...".format(table.__name__))
            table.populate(**gkwargs)
            logger.log(
                30,
                "Ingestion time of {} is {}".format(
                    table.__name__, time.time() - table_start_time
                ),
            )

        logger.log(30, "Total ingestion time {}".format(time.time() - tstart))

        logger.log(30, "Histology populate")
        for table in HISTOLOGY_TABLES:
            logger.log(30, f"Populating {table.__name__}...")
            table.populate(**gkwargs)

        time.sleep(sleep_duration)


if __name__ == "__main__":
    main()
