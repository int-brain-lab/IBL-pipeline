import inspect
import logging
import os
import pathlib

import actions
import data
import datajoint as dj
import experiments

# alyx models
import misc
import subjects
from tqdm import tqdm

from ibl_pipeline.common import *
from ibl_pipeline.ingest import QueryBuffer, populate_batch
from ibl_pipeline.ingest.common import *
from ibl_pipeline.process import (
    ingest_alyx_raw,
    ingest_alyx_raw_postgres,
    ingest_real,
    update_utils,
)

log_file = pathlib.Path(__file__).parent / "logs/process_histology.log"
log_file.parent.mkdir(parents=True, exist_ok=True)
log_file.touch(exist_ok=True)

logging.basicConfig(
    format="%(asctime)s - %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    level=25,
)

logger = logging.getLogger(__name__)


from ibl_pipeline import mode

ALYX_HISTOLOGY_MODELS = [
    experiments.models.CoordinateSystem,
    experiments.models.TrajectoryEstimate,
    experiments.models.Channel,
]

HISTOLOGY_SHADOW_TABLES = [
    reference_ingest.Lab,
    reference_ingest.LabMember,
    reference_ingest.LabMembership,
    reference_ingest.LabLocation,
    reference_ingest.Project,
    reference_ingest.CoordinateSystem,
    subject_ingest.Species,
    subject_ingest.Source,
    subject_ingest.Strain,
    subject_ingest.Sequence,
    subject_ingest.Allele,
    subject_ingest.Line,
    subject_ingest.Subject,
    subject_ingest.SubjectProject,
    subject_ingest.SubjectUser,
    subject_ingest.SubjectLab,
    subject_ingest.UserHistory,
    action_ingest.ProcedureType,
    acquisition_ingest.Session,
    ephys_ingest.ProbeModel,
    ephys_ingest.ProbeInsertion,
]

HISTOLOGY_TABLES_FOR_POPULATE = [
    histology.ProbeTrajectory,
    histology.ChannelBrainLocation,
    histology.ClusterBrainRegion,
    histology_plotting.SubjectSpinningBrain,
    histology_plotting.ProbeTrajectoryCoronal,
]

HISTOLOGY_TABLES_FOR_DELETE = []


if mode != "public":
    HISTOLOGY_SHADOW_TABLES.extend(
        [
            histology_ingest.ProbeTrajectoryTemp,
            histology_ingest.ChannelBrainLocationTemp,
        ]
    )

    HISTOLOGY_TABLES_FOR_DELETE.extend(
        [
            histology.ProbeBrainRegionTemp,
            histology.ClusterBrainRegionTemp,
            histology.ChannelBrainLocationTemp,
            histology.ProbeTrajectoryTemp,
        ]
    )

    HISTOLOGY_TABLES_FOR_POPULATE.extend(
        [
            histology.ClusterBrainRegionTemp,
            histology.ProbeBrainRegionTemp,
            histology.DepthBrainRegionTemp,
        ]
    )


def populate_shadow_tables():
    kwargs = dict(display_progress=True, suppress_errors=True)
    for t in HISTOLOGY_SHADOW_TABLES:
        print(f"Populating {t.__name__}...")
        if t.__name__ == "ChannelBrainLocationTemp":
            populate_batch(t)
        else:
            t.populate(**kwargs)


def delete_histology_alyx_shadow(verbose=False):

    CHANNEL_TABLES = [
        histology_ingest.ChannelBrainLocationTemp,
        alyxraw.AlyxRaw.Field,
        alyxraw.AlyxRaw,
    ]

    channel_loc_keys = update_utils.get_deleted_keys("experiments.channel")
    for t in CHANNEL_TABLES:
        print(f"Deleting from table {t.__name__}")
        uuid_name = t.heading.primary_key[0]
        keys = [{uuid_name: k["uuid"]} for k in tqdm(channel_loc_keys)]
        table = QueryBuffer(t)

        for k in tqdm(keys, position=0):
            table.add_to_queue1(k)
            if table.flush_delete(chunksz=1000, quick=True) and verbose:
                print(f"Deleted 1000 entries from {t.__name__}")

        table.flush_delete(quick=True)

    traj_keys = update_utils.get_deleted_keys(
        "experiments.trajectoryestimate"
    ) + update_utils.get_updated_keys("experiments.trajectoryestimate")

    TRAJ_TABLES = [
        histology_ingest.ProbeTrajectoryTemp,
        alyxraw.AlyxRaw.Field,
        alyxraw.AlyxRaw,
    ]

    for t in TRAJ_TABLES:
        uuid_name = t.heading.primary_key[0]
        keys = [{uuid_name: k["uuid"]} for k in traj_keys]
        table = QueryBuffer(t)
        for k in tqdm(keys, position=0):
            table.add_to_queue1(k)
            if table.flush_delete(chunksz=1000, quick=True) and verbose:
                print(f"Deleted 1000 entries from {t.__name__}")
        table.flush_delete(quick=True)


def delete_histology_real():

    traj_uuids = update_utils.get_deleted_keys(
        "experiments.trajectoryestimate"
    ) + update_utils.get_updated_keys("experiments.trajectoryestimate")

    traj_uuids_real = [{"probe_trajectory_uuid": k["uuid"]} for k in traj_uuids]

    traj_keys = (histology.ProbeTrajectoryTemp & traj_uuids_real).fetch("KEY")

    for t in HISTOLOGY_TABLES_FOR_DELETE:
        print(f"Deleting from table {t.__name__}")
        (t & traj_keys).delete_quick()


def copy_to_real_tables():
    for shadow_table in HISTOLOGY_SHADOW_TABLES:
        mod = shadow_table.__module__
        shadow_module = inspect.getmodule(shadow_table)
        real_module = eval(mod.replace("ibl_pipeline.ingest.", ""))
        table_name = shadow_table.__name__
        print(f"Copying table {table_name}...")
        ingest_real.copy_table(
            real_module, shadow_module, table_name, allow_direct_insert=True
        )


def populate_real_tables():
    for t in HISTOLOGY_TABLES_FOR_POPULATE:
        print(f"Populating {t.__name__}...")
        t.populate(suppress_errors=True, display_progress=True)


def main():

    logger.log(25, "Histology - Ingesting from Postgres to UpdateAlyxRaw...")
    ingest_alyx_raw_postgres.insert_to_update_alyxraw_postgres(
        alyx_models=ALYX_HISTOLOGY_MODELS,
        delete_UpdateAlyxRaw_first=True,
        skip_existing_alyxraw=True,
    )

    logger.log(
        25,
        "Histology - Deleting updated/deleted entries from AlyxRaw and shadow tables...",
    )
    delete_histology_alyx_shadow()

    logger.log(25, "Histology - Ingesting from Postgres to AlyxRaw...")
    for alyx_model in ALYX_HISTOLOGY_MODELS:
        ingest_alyx_raw_postgres.insert_alyx_entries_model(
            alyx_model, skip_existing_alyxraw=True
        )

    logger.log(25, "Histology - Ingesting into shadow tables...")
    populate_shadow_tables()

    logger.log(25, "Histology - Deleting updated/deleted entries from real tables...")
    delete_histology_real()

    logger.log(25, "Histology - Ingesting the real tables...")
    copy_to_real_tables()

    logger.log(25, "Histology - Populate the histology tables...")
    populate_real_tables()


def process_public():
    from ibl_pipeline import public

    for alyx_model in ALYX_HISTOLOGY_MODELS:
        ingest_alyx_raw_postgres.insert_alyx_entries_model(
            alyx_model, skip_existing_alyxraw=False
        )

    populate_shadow_tables()
    copy_to_real_tables()
    populate_real_tables()


if __name__ == "__main__":
    main()
