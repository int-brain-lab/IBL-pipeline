import datetime
import logging
import pathlib
from os import path

import datajoint as dj
from tqdm import tqdm

from ibl_pipeline.ingest import job
from ibl_pipeline.process import (
    create_ingest_task,
    delete_update_entries,
    get_file_date,
    get_file_timestamp,
    get_file_timezone,
    get_timezone,
    ingest_alyx_raw,
    ingest_alyx_raw_postgres,
    ingest_membership,
    ingest_real,
    ingest_shadow,
    populate_behavior,
    update_utils,
)

# logger does not work without this somehow
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

log_file = pathlib.Path(__file__).parent / "logs/main_ingest.log"
log_file.parent.mkdir(parents=True, exist_ok=True)
log_file.touch(exist_ok=True)

logging.basicConfig(
    format="%(asctime)s - %(message)s",
    handlers=[
        # write info into both the log file and console
        logging.FileHandler(log_file),
        logging.StreamHandler(),
    ],
    level=25,
)

logger = logging.getLogger(__name__)


def process_new(
    previous_dump=None,
    latest_dump=None,
    job_date=datetime.date.today().strftime("%Y-%m-%d"),
    timezone="other",
    perform_updates=True,
):

    job_key = dict(
        job_date=job_date,
        job_timezone=timezone,
    )

    if previous_dump is None:
        previous_dump = path.join("/", "data", "alyxfull.json.last")

    if latest_dump is None:
        latest_dump = path.join("/", "data", "alyxfull.json")

    if not (job.Job & job_key):
        logger.log(25, "Comparing json dumps ...")
        create_ingest_task.compare_json_dumps(previous_dump, latest_dump)

    created_pks, modified_pks, deleted_pks, modified_pks_important = (
        job.Job & job_key
    ).fetch1("created_pks", "modified_pks", "deleted_pks", "modified_pks_important")

    if perform_updates:
        logger.log(25, "Deleting modified entries from alyxraw and shadow tables...")
        start = datetime.datetime.now()

        delete_update_entries.delete_entries_from_alyxraw(
            modified_pks, modified_pks_important
        )

        job.TaskStatus.insert_task_status(
            job_key, "Delete alyxraw", start, end=datetime.datetime.now()
        )

        logger.log(25, "Deleting modified entries from membership tables...")
        start = datetime.datetime.now()
        delete_update_entries.delete_entries_from_membership(modified_pks_important)
        job.TaskStatus.insert_task_status(
            job_key, "Delete shadow membership", start, end=datetime.datetime.now()
        )

    logger.log(25, "Ingesting into alyxraw...")
    start = datetime.datetime.now()
    ingest_alyx_raw.insert_to_alyxraw(
        ingest_alyx_raw.get_alyx_entries(
            latest_dump, new_pks=created_pks + modified_pks
        )
    )
    job.TaskStatus.insert_task_status(
        job_key, "Ingest alyxraw", start, end=datetime.datetime.now()
    )

    logger.log(25, "Ingesting into shadow tables...")
    start = datetime.datetime.now()
    ingest_shadow.main(modified_sessions_pks=modified_pks_important)
    job.TaskStatus.insert_task_status(
        job_key, "Ingest shadow", start, end=datetime.datetime.now()
    )

    logger.log(25, "Ingesting into shadow membership tables...")
    start = datetime.datetime.now()
    ingest_membership.main(created_pks + modified_pks_important)
    job.TaskStatus.insert_task_status(
        job_key, "Ingest shadow membership", start, end=datetime.datetime.now()
    )

    logger.log(25, "Ingesting alyx real...")
    start = datetime.datetime.now()
    ingest_real.main()
    job.TaskStatus.insert_task_status(
        job_key, "Ingest real", start, end=datetime.datetime.now()
    )

    if perform_updates:
        logger.log(25, "Updating fields...")
        start = datetime.datetime.now()
        delete_update_entries.update_entries_from_real_tables(modified_pks_important)
        job.TaskStatus.insert_task_status(
            job_key, "Update fields", start, end=datetime.datetime.now()
        )

    logger.log(25, "Ingesting behavior...")
    start = datetime.datetime.now()
    populate_behavior.main(backtrack_days=30)
    job.TaskStatus.insert_task_status(
        job_key, "Populate behavior", start, end=datetime.datetime.now()
    )


# TODO: change /data /tmp to use dj.config
def process_updates(pks, current_dump="/data/alyxfull.json"):
    """
    Update the all the fields in givens a set of pks
    :param pks: uuids where an update is needed
    :param current_dump: the latest
    """
    logger.log(25, "Deleting from alyxraw...")
    delete_update_entries.delete_entries_from_alyxraw(alyxraw_keys=pks)
    logger.log(25, "Deleting from shadow membership...")
    delete_update_entries.delete_entries_from_membership(pks)

    logger.log(25, "Ingesting alyxraw...")
    ingest_alyx_raw.insert_to_alyxraw(
        ingest_alyx_raw.get_alyx_entries(current_dump, new_pks=pks)
    )

    logger.log(25, "Ingesting into shadow tables...")
    ingest_shadow.main(excluded_tables=["DataSet", "FileRecord"])

    logger.log(25, "Ingesting into shadow membership tables...")
    ingest_membership.main(pks)

    logger.log(25, "Ingesting alyx real...")
    ingest_real.main(excluded_tables=["DataSet", "FileRecord"])

    logger.log(25, "Updating field...")
    delete_update_entries.update_entries_from_real_tables(pks)

    # ============================== processes based on local alyx postgres instance ===================================

    """
    General flow for daily ingestion with updates
    + create update_ibl_alyxraw from scratch
    + compare f_values for certain alyx models between update_ibl_alyxraw and ibl_alyxraw,
        get the keys that are updated and deleted, ingest or update entries in job.Job
    + delete ibl_alyxraw and shawdow tables entries that are deleted and updated
    + delete shadow membership entries that are deleted and updated
    + ingest entries into ibl_alyxraw, shadow, and shadow membership tables
    + update real tables by comparing with shadow and shadow membership tables
    + populate behavior

    General flow for daily ingestion without updates
    + create job.Job entry without filling modified_pks_important
    + ingest into alyxraw tables with alyx django model classes
    + ingest into shadow tables with populate
    + ingest into shadow tables with ingestion script
    + populate behavior
    """


def get_created_modified_deleted_pks():
    """compare tables AlyxRaw and UpdateAlyxRaw to get
    created_pks, modified_pks and deleted_pks

    Returns:
        created_pks [list]: list of uuids for newly created entries
        modified_pks [list]: list of uuids for modified entries
        delete_pks [list]: list of uuids for deleted entries
    """

    created_pks, modified_pks, deleted_pks = [], [], []

    # all the models
    for alyx_model in ingest_alyx_raw_postgres.ALYX_MODELS_OF_INTEREST:
        model_name = ingest_alyx_raw_postgres.get_alyx_model_name(alyx_model)
        created_pks.extend(update_utils.get_created_keys(model_name))

    # only models that need an update
    for table in delete_update_entries.TABLES_TO_UPDATE:
        model_name = ingest_alyx_raw_postgres.get_alyx_model_name(table["alyx_model"])
        modified_pks.extend(update_utils.get_updated_keys(model_name))
        deleted_pks.extend(update_utils.get_deleted_keys(model_name))

    return created_pks, modified_pks, deleted_pks


def process_postgres(sql_dump_path="/tmp/dump.sql.gz", perform_updates=True):
    """function that process daily ingestion routine based on alyx postgres instance set up with sql dump

    Args:
        sql_dump_path (str, optional): file path to the current sql dump. Defaults to '/tmp/dump.sql.gz'
        perform_updates (bool, optional): whether to perform entry updates. Defaults to False.
    """

    # ---- Step 1: new job entry in the job.Job table ----
    job_key = dict(
        job_date=get_file_date(sql_dump_path),
        job_timezone=get_file_timezone(sql_dump_path),
    )
    job_entry = dict(job_key, alyx_current_time_stamp=get_file_timestamp(sql_dump_path))

    # ---- Step 2: from postgres-db with the latest sql-dump, ingest into UpdateAlyxRaw ----
    # this step skips `Dataset` and `FileRecord` models
    logger.log(25, "Ingesting into UpdateAlyxRaw...")
    ingest_alyx_raw_postgres.insert_to_update_alyxraw_postgres(
        excluded_models=["Dataset", "FileRecord"],
        delete_UpdateAlyxRaw_first=True,
        skip_existing_alyxraw=True,
    )

    # ---- Step 3: compare UpdateAlyxRaw vs. AlyxRaw ----
    # compare the same tables between UpdateAlyxRaw and AlyxRaw,
    # get the created, modified, and deleted uuids
    logger.log(25, "Getting created, modified and deleted uuids...")
    start = datetime.datetime.now()
    created_pks, modified_pks, deleted_pks = get_created_modified_deleted_pks()

    job.Job.insert1(
        dict(
            job_entry,
            create_pks=created_pks,
            modified_pks_important=modified_pks,
            deleted_pks=deleted_pks,
        ),
        replace=True,
    )
    job.TaskStatus.insert_task_status(
        job_key, "Get created modified deleted pks", start, end=datetime.datetime.now()
    )
    logger.log(25, "Job entry created!")

    # ---- Step 4: perform updates ----
    #   delete from AlyxRaw, shadow tables and shadow Membership tables
    #   those entries found in "modified_pks" and "deleted_pks" so they can be re-ingested
    if perform_updates:
        logger.log(
            25,
            "Deleting modified and deleted entries from alyxraw and shadow tables ...",
        )
        start = datetime.datetime.now()
        delete_update_entries.delete_entries_from_alyxraw(
            [], modified_pks + deleted_pks
        )
        job.TaskStatus.insert_task_status(
            job_key, "Delete alyxraw", start, end=datetime.datetime.now()
        )

        logger.log(
            25,
            "Deleting modified and deleted entries from shadow membership tables ...",
        )
        start = datetime.datetime.now()
        delete_update_entries.delete_entries_from_membership(modified_pks + deleted_pks)
        job.TaskStatus.insert_task_status(
            job_key, "Delete shadow membership", start, end=datetime.datetime.now()
        )

    # ---- Step 5: ingestion of AlyxRaw, shadow tables and shadow membership tables ----

    logger.log(25, "Ingesting from Postgres Alyx to AlyxRaw...")
    start = datetime.datetime.now()
    ingest_alyx_raw_postgres.main(backtrack_days=3, skip_existing_alyxraw=True)
    job.TaskStatus.insert_task_status(
        job_key, "Ingest alyxraw", start, end=datetime.datetime.now()
    )

    logger.log(25, "Ingesting into shadow tables...")
    start = datetime.datetime.now()
    ingest_shadow.main(modified_sessions_pks=modified_pks)
    job.TaskStatus.insert_task_status(
        job_key, "Ingest shadow", start, end=datetime.datetime.now()
    )

    logger.log(25, "Ingesting into shadow membership tables...")
    start = datetime.datetime.now()
    ingest_membership.main()
    job.TaskStatus.insert_task_status(
        job_key, "Ingest shadow membership", start, end=datetime.datetime.now()
    )

    # ---- Step 6: ingestion of all real tables (copy from shadow tables) ----

    logger.log(25, "Ingesting the real tables...")
    start = datetime.datetime.now()
    ingest_real.main(excluded_tables=["DataSet", "FileRecord"])
    job.TaskStatus.insert_task_status(
        job_key, "Ingest real", start, end=datetime.datetime.now()
    )

    if perform_updates:
        logger.log(25, "Updating field...")
        start = datetime.datetime.now()
        delete_update_entries.update_entries_from_real_tables(modified_pks)
        job.TaskStatus.insert_task_status(
            job_key, "Update fields", start, end=datetime.datetime.now()
        )

    # ---- Step 7: populate behavior tables ----

    logger.log(25, "Populating behavior...")
    start = datetime.datetime.now()
    populate_behavior.main(backtrack_days=30)
    job.TaskStatus.insert_task_status(
        job_key, "Populate behavior", start, end=datetime.datetime.now()
    )

    """ General flow for updates only (similar to procedures in process_histology and process_qc)
    + create UpdateAlyxRaw from scratch
    + compare f_values for certain alyx models between UpdateAlyxRaw and AlyxRaw, get the keys that are deleted and updated
    + delete from AlyxRaw and shadow tables: entries that are deleted and updated
        + for Session table - only delete the AlyxRaw.Field, not AlyxRaw
    + delete from shadow membership tables: entries that are deleted and updated
    + ingest entries again into AlyxRaw, shadow, and shadow membership tables
        + for Session table - update the attributes values for "updated/modified" entries
    + update real tables by comparing with shadow and shadow membership tables
    """


if __name__ == "__main__":
    # TODO: change /data /tmp to use dj.config
    process_new(
        previous_dump="/data/alyxfull_20210617_1200.json",
        latest_dump="/data/alyxfull.json",
        job_date="2021-06-18",
        timezone="PST",
    )
