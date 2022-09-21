"""
This module delete the entries from alyxraw, shadow membership_tables and update real membership_tables
"""
import datetime
from uuid import UUID

import datajoint as dj
from tqdm import tqdm

# isort: split
import actions
import subjects
from ibl_pipeline import update
from ibl_pipeline.common import *
from ibl_pipeline.ingest import QueryBuffer, alyxraw
from ibl_pipeline.ingest.common import *
from ibl_pipeline.process.ingest_membership import MEMBERSHIP_TABLES
from ibl_pipeline.utils import get_logger, is_valid_uuid

logger = get_logger(__name__)


def get_important_pks(pks, return_original_dict=False):
    """
    Filter out modified keys that belongs to data.filerecord and jobs.task
    :params modified_keys: list of pks
    :params optional return original_dict: boolean, if True, return the list of dictionaries with uuids to be the key
    :returns pks_important: list of filtered pks
    :returns pks_dict: list of dictionary with uuid as the key
    """

    pks = [pk for pk in pks if is_valid_uuid(pk)]
    pks_dict = [{"uuid": pk} for pk in pks]

    models_ignored = '"data.dataset", "data.filerecord", "jobs.task", "actions.wateradministration", "experiments.trajectoryestimate", "experiments.channel"'

    if len(pks) < 1000:
        pks_unimportant = [
            str(pk["uuid"])
            for pk in (
                alyxraw.AlyxRaw & f"model in ({models_ignored})" & pks_dict
            ).fetch("KEY")
        ]
    else:
        buffer = QueryBuffer(alyxraw.AlyxRaw & f"model in ({models_ignored})")
        for pk in tqdm(pks_dict):
            buffer.add_to_queue1(pk)
            buffer.flush_fetch("KEY", chunksz=200)

        buffer.flush_fetch("KEY")
        pks_unimportant = [str(pk["uuid"]) for pk in buffer.fetched_results]

    pks_important = list(set(pks) - set(pks_unimportant))

    if return_original_dict:
        return pks_important, pks_dict
    else:
        return pks_important


# ====================================== functions for deletion ==================================


def delete_entries_from_alyxraw(file_record_keys=[], alyxraw_keys=[]):
    """
    Delete entries from alyxraw and shadow tables, excluding the membership table.
    Args:
        file_record_keys: a list of the AlyxRaw keys where the entries in AlyxRaw.Field
         of type FileRecord are to be deleted
        alyxraw_keys: a list of the AlyxRaw keys where the entries in AlyxRaw
         are to be deleted, except for entries related to the Session table (actions.session)
    Returns:
    """

    if file_record_keys:
        logger.info("Deleting alyxraw entries corresponding to file records...")

        if len(file_record_keys) > 5000:
            file_record_fields = alyxraw.AlyxRaw.Field & {
                "fname": "exists",
                "fvalue": "false",
            }
        else:
            file_record_fields = (
                alyxraw.AlyxRaw.Field
                & {"fname": "exists", "fvalue": "false"}
                & file_record_keys
            )

        for key in tqdm(file_record_fields):
            (alyxraw.AlyxRaw.Field & key).delete_quick()

    if alyxraw_keys:
        logger.info("Deleting modified entries...")

        pk_list = [k for k in alyxraw_keys if is_valid_uuid(k["uuid"])]

        # Delete from alyxraw.AlyxRaw (except for entries related to the Session table)
        alyxraw_buffer = QueryBuffer(alyxraw.AlyxRaw & 'model != "actions.session"')
        for pk in tqdm(pk_list):
            alyxraw_buffer.add_to_queue1(pk)
            alyxraw_buffer.flush_delete(chunksz=50, quick=False)
        alyxraw_buffer.flush_delete(quick=False)

        # Special handling to the AlyxRaw corresponding to the Session table
        #   i.e. the case where uuid is not changed but start time changed for 1 sec
        #   delete only entries in the AlyxRaw.Field, except for the "start time" field.

        alyxraw_field_buffer = QueryBuffer(
            alyxraw.AlyxRaw.Field
            & 'fname!="start_time"'
            & (alyxraw.AlyxRaw & 'model="actions.session"')
        )

        for pk in tqdm(pk_list):
            alyxraw_field_buffer.add_to_queue1(pk)
            alyxraw_field_buffer.flush_delete(chunksz=50, quick=True)
        alyxraw_field_buffer.flush_delete(quick=True)


def delete_entries_from_membership(pks_to_be_deleted):
    """
    Delete entries from shadow membership membership_tables
    """
    for t in MEMBERSHIP_TABLES:
        ingest_mod = t["dj_parent_table"].__module__
        table_name = t["dj_parent_table"].__name__

        mem_table_name = t["dj_current_table"].__name__

        real_table = eval(
            ingest_mod.replace("ibl_pipeline.ingest.", "") + "." + table_name
        )

        entries_to_delete = (
            real_table
            & [
                {t["dj_parent_uuid_name"]: pk}
                for pk in pks_to_be_deleted
                if is_valid_uuid(pk)
            ]
        ).fetch("KEY")

        logger.info(
            f"Deleting {len(entries_to_delete)} records from membership table {mem_table_name} ...",
        )

        if entries_to_delete:
            with dj.config(safemode=False):
                (t["dj_current_table"] & entries_to_delete).delete()


# =================================== Tables to be updated ========================


TABLES_TO_UPDATE = [
    {
        "real_schema": reference,
        "shadow_schema": reference_ingest,
        "table_name": "Project",  # datajoint table name
        "members": [],
        "alyx_model": subjects.models.Project,
    },
    {
        "real_schema": subject,
        "shadow_schema": subject_ingest,
        "table_name": "Subject",
        "members": ["SubjectLab", "SubjectUser", "SubjectProject", "Death"],
        "alyx_model": subjects.models.Subject,
    },
    {
        "real_schema": action,
        "shadow_schema": action_ingest,
        "table_name": "Weighing",
        "members": [],
        "alyx_model": actions.models.Weighing,
    },
    {
        "real_schema": action,
        "shadow_schema": action_ingest,
        "table_name": "WaterRestriction",
        "members": [],
        "alyx_model": actions.models.WaterRestriction,
    },
    {
        "real_schema": action,
        "shadow_schema": action_ingest,
        "table_name": "WaterAdministration",
        "members": [],
        "alyx_model": actions.models.WaterAdministration,
    },
    {
        "real_schema": acquisition,
        "shadow_schema": acquisition_ingest,
        "table_name": "Session",
        "members": ["SessionUser", "SessionProject"],
        "alyx_model": actions.models.Session,
    },
]


# =================================== functions for update ==========================================


def update_fields(
    real_schema, shadow_schema, table_name, pks, log_to_UpdateRecord=False
):
    """
    Given a table and the primary key of real table,
        update the real table all the fields that have discrepancy from the shadow table
    Inputs: real_schema     : real schema module, e.g. reference
            shadow_schema   : shadow schema module, e.g. reference_ingest
            table_name      : string, name of a table, e.g. Subject
            pks             : list of dictionaries, primary keys of real table that contains modification
            log_to_UpdateRecord : boolean, if True, log the update history in the table ibl_update.UpdateRecord
    """

    if "." in table_name:
        # handling part-table
        master_name, part_name = table_name.split(".")
        real_table = getattr(getattr(real_schema, master_name), part_name)
        shadow_table = getattr(getattr(shadow_schema, master_name), part_name)
    else:
        real_table = getattr(real_schema, table_name)
        shadow_table = getattr(shadow_schema, table_name)

    # don't update "_ts" fields
    fields_to_update = [
        f for f in real_table.heading.secondary_attributes if not f.endswith("_ts")
    ]

    try:
        ts_field = next(f for f in real_table.heading.names if "_ts" in f)
    except StopIteration:
        ts_field = None
        log_to_UpdateRecord = False

    # do the updating
    for key in (real_table & pks).fetch("KEY"):
        pk_hash = UUID(dj.hash.key_hash(key))

        if not shadow_table & key:
            real_record = (real_table & key).fetch1()
            if log_to_UpdateRecord:
                update_record = dict(
                    table=real_table.__module__ + "." + real_table.__name__,
                    attribute="unknown",
                    pk_hash=pk_hash,
                    original_ts=real_record[ts_field],
                    update_ts=datetime.datetime.now(),
                    pk_dict=key,
                )
                update.UpdateRecord.insert1(update_record)
                update_record.pop("pk_dict")

                update_error_msg = "Record does not exist in the shadow {}".format(key)
                update_record_error = dict(
                    **update_record,
                    update_action_ts=datetime.datetime.now(),
                    update_error_msg=update_error_msg,
                )
                update.UpdateError.insert1(update_record_error)

            logger.info(f"Error updating entry: {update_error_msg}")
            continue
        # if there are more than 1 record
        elif len(shadow_table & key) > 1:
            # delete the older record
            lastest_record = (
                dj.U().aggr(shadow_table & key, session_ts="max(session_ts)").fetch()
            )

            with dj.config(safemode=False):
                ((shadow_table & key) - lastest_record).delete()

        shadow_record = (shadow_table & key).fetch1()
        real_record = (real_table & key).fetch1()

        for f in fields_to_update:
            if real_record[f] != shadow_record[f]:
                try:
                    (real_table & key)._update(f, shadow_record[f])
                    update_narrative = (
                        f"{table_name}.{f}: {shadow_record[f]} != {real_record[f]}"
                    )
                except BaseException as e:
                    logger.info(f"Error while updating record {key}: {str(e)}")
                else:
                    if log_to_UpdateRecord:
                        update_record = dict(
                            table=real_table.__module__ + "." + real_table.__name__,
                            attribute=f,
                            pk_hash=pk_hash,
                            original_ts=real_record[ts_field],
                            update_ts=shadow_record[ts_field],
                            pk_dict=key,
                            original_value=real_record[f],
                            updated_value=shadow_record[f],
                            update_narrative=update_narrative,
                        )
                        update.UpdateRecord.insert1(update_record)


def update_entries_from_real_tables(modified_pks):
    for table_info in TABLES_TO_UPDATE:

        logger.info("Updating {}...".format(table_info["table_name"]))
        table = getattr(table_info["real_schema"], table_info["table_name"])

        if table_info["table_name"] == "Subject":
            uuid_field = "subject_uuid"
        else:
            uuid_field = next(
                f
                for f in table.heading.secondary_attributes
                if "_uuid" in f and "subject" not in f
            )

        pks_important = get_important_pks(modified_pks)

        query = table & [{uuid_field: pk} for pk in pks_important]

        if query:
            update_fields(
                table_info["real_schema"],
                table_info["shadow_schema"],
                table_info["table_name"],
                pks=query.fetch("KEY"),
                log_to_UpdateRecord=True,
            )

            if table_info["members"]:
                for member_table_name in table_info["members"]:
                    member_table = getattr(table_info["real_schema"], member_table_name)
                    if member_table & query:
                        update_fields(
                            table_info["real_schema"],
                            table_info["shadow_schema"],
                            member_table_name,
                            pks=(member_table & query).fetch("KEY"),
                            log_to_UpdateRecord=True,
                        )


if __name__ == "__main__":
    from ibl_pipeline.ingest import job

    with dj.config(safemode=False):

        deleted_pks, modified_pks, modified_pks_important = (
            job.Job & 'job_date="2021-05-18"' & 'job_timezone="European"'
        ).fetch1("deleted_pks", "modified_pks", "modified_pks_important")

        delete_entries_from_alyxraw(deleted_pks + modified_pks, modified_pks_important)
