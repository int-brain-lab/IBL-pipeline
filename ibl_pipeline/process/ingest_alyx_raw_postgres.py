"""
This script loads the data from alyx postgres database and insert the entries into the alyxraw table.
"""
import datetime
import json
import math
import os
import re

import datajoint as dj
import numpy as np

from ibl_pipeline.ingest import QueryBuffer, alyxraw
from ibl_pipeline.process import (
    alyx_models,
    get_django_field_names,
    get_django_many_to_many_field_names,
    get_django_model_name,
)
from ibl_pipeline.utils import get_logger

# isort: split
import data

logger = get_logger(__name__)

_backtrack_days = int(os.getenv("BACKTRACK_DAYS", 0))

ALYX_MODELS = alyx_models()


def get_models_with_auto_datetime(models=None):
    models = ALYX_MODELS if models is None else models
    mf = tuple((m, get_django_field_names(m)) for m in models)
    return [m for m, f in mf if "auto_datetime" in f]


AUTO_DATETIME_MODELS = get_models_with_auto_datetime()


def insert_alyx_entries_model(
    alyx_model,
    AlyxRawTable=None,
    backtrack_days=None,
    skip_existing_alyxraw=False,
):
    """Insert alyx entries into alyxraw tables for a particular alyx model

    Args:
        alyx_model (django.model object): alyx model
        AlyxRawTable (datajoint module): datajoint module containing AlyxRaw tables, either alyxraw or alyxraw update
        backtrack_days (int, optional): number of days the data are within to backtrack and ingest,
            just applicable to tables with auto_datetime field
        skip_existing_alyxraw: if True, skip over the entries already existed in the AlyxRaw table,
            else, load and insert everything again (but still with `skip_duplicates=True`)
    """
    raw_table = AlyxRawTable or alyxraw.AlyxRaw
    model_name = get_django_model_name(alyx_model)
    field_names = get_django_field_names(alyx_model)
    many_to_many_field_names = get_django_many_to_many_field_names(alyx_model)

    logger.info(f"Loading '{model_name}' data from alyx postgres database...")

    if backtrack_days:
        # filtering the alyx table - get more recent entries within the backtrack_days
        # only applicable to alyx models having "auto_datetime" and FileRecord alyx model
        date_cutoff = (
            datetime.datetime.now().date() - datetime.timedelta(days=backtrack_days)
        ).strftime("%Y-%m-%d")

        if alyx_model in AUTO_DATETIME_MODELS:
            # actions.models.Session, data.models.Dataset, experiments.models.ProbeInsertion
            entries = alyx_model.objects.filter(auto_datetime__date__gte=date_cutoff)
        elif alyx_model == data.models.FileRecord:
            entries = alyx_model.objects.filter(
                dataset__auto_datetime__date__gte=date_cutoff, exists=True
            )
        else:
            entries = alyx_model.objects.all()
    elif alyx_model == data.models.FileRecord:
        # for FileRecord alyx model, restrict to only the entries where the file does exist
        entries = alyx_model.objects.filter(exists=True)
    else:
        entries = alyx_model.objects.all()

    # Ingest into main table
    if skip_existing_alyxraw:
        existing_uuids = (raw_table & {"model": model_name}).fetch("uuid")
        new_uuids = np.setxor1d(
            list(entries.values_list("id", flat=True)),
            existing_uuids,
            assume_unique=True,
        )
    else:
        new_uuids = entries.values_list("id", flat=True)

    # convert to dict to make use of indexing for speed
    new_uuids = {eid: None for eid in new_uuids}

    if not new_uuids:
        logger.info(f"No new entries for '{model_name}'")
        return

    logger.info(f"Inserting {len(new_uuids)} new entries for '{model_name}'")

    # using QueryBuffer, ingest into table AlyxRaw
    alyxraw_buffer = QueryBuffer(raw_table & {"model": model_name}, verbose=False)
    # using QueryBuffer, ingest into part table AlyxRaw.Field
    alyxraw_field_buffer = QueryBuffer(raw_table.Field, verbose=True)
    # cancel on-going transaction, if any
    raw_table.connection.cancel_transaction()

    # ingest fields and single foreign key references in alyxraw.AlyxRaw.Field
    for r in entries:
        if r.id not in new_uuids:
            continue

        logger.info(f"Adding uuid '{r.id}' to '{model_name}'")
        alyxraw_buffer.add_to_queue1({"uuid": r.id, "model": model_name})
        # e.g. for table subjects.models.Subject, each r is a subject queryset
        # for one subject
        try:
            field_entries = []
            for field_name in field_names:
                if field_name == "id":
                    continue

                field_entry = {"uuid": r.id, "fname": field_name}
                field_value = getattr(r, field_name)
                logger.debug(f"Loading field '{field_name}' for '{model_name}': {r.id}")
                if field_name == "json" and field_value:
                    # handles the 'json' field - store the json dump
                    field_entry["value_idx"] = 0
                    field_entry["fvalue"] = json.dumps(field_value)
                    if len(field_entry["fvalue"]) >= 10000:
                        logger.warning(
                            "the json dump is too large, storing fvalue as null"
                        )
                        field_entry.pop("fvalue")
                elif field_name == "narrative" and field_value is not None:
                    # handles 'narrative' field with emoji - filter out emoji
                    emoji_pattern = re.compile(
                        "["
                        "\U0001F600-\U0001F64F"  # emoticons
                        "\U0001F300-\U0001F5FF"  # symbols & pictographs
                        "\U0001F680-\U0001F6FF"  # transport & map symbols
                        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
                        "\U00002702-\U000027B0"
                        "\U000024C2-\U0001F251"
                        "]+",
                        flags=re.UNICODE,
                    )

                    field_entry["value_idx"] = 0
                    field_entry["fvalue"] = emoji_pattern.sub(r"", field_value)
                elif (
                    not isinstance(field_value, (float, int)) and not field_value
                ) or (
                    isinstance(field_value, (float, int)) and math.isnan(field_value)
                ):
                    # handle "falsy" field value - store as string 'None'
                    field_entry["value_idx"] = 0
                    field_entry["fvalue"] = "None"
                elif isinstance(field_value, str):
                    field_entry["value_idx"] = 0
                    field_entry["fvalue"] = field_value
                elif isinstance(
                    field_value, (bool, float, int, datetime.datetime, datetime.date)
                ):
                    field_entry["value_idx"] = 0
                    field_entry["fvalue"] = str(field_value)
                elif isinstance(field_value, dict):
                    field_entry["value_idx"] = 0
                    field_entry["fvalue"] = json.dumps(field_value, default=str)
                else:
                    field_entry["value_idx"] = 0
                    fk_id = field_name + "_id"
                    logger.debug(f"special handling for foreign key object {fk_id}")
                    if hasattr(r, fk_id):
                        field_entry["fvalue"] = str(getattr(r, fk_id))

                field_entries.append(field_entry)
            # ingest many to many fields into alyxraw.AlyxRaw.Field
            for field_name in many_to_many_field_names:
                many_to_many_entries = getattr(r, field_name).all()
                if len(many_to_many_entries) > 200:
                    logger.debug(
                        f"many-to-many field {field_name} with "
                        f"{len(many_to_many_entries)} entries - skipping..."
                    )
                    continue
                field_entries.extend(
                    [
                        dict(
                            uuid=r.id,
                            fname=field_name,
                            value_idx=obj_idx,
                            fvalue=str(obj.id),
                        )
                        for obj_idx, obj in enumerate(many_to_many_entries)
                    ]
                )

            alyxraw_field_buffer.add_to_queue(field_entries)
            dj.conn().ping()
            del field_entries  # to be cleaned by garbage collector, improve memory management

        except Exception as e:
            logger.error(
                f"Problematic entry '{r.id}' of model '{model_name}' with error '{e}'"
            )

        if len(alyxraw_field_buffer._queue) >= 7500:
            with raw_table.connection.transaction:
                alyxraw_buffer.flush_insert(skip_duplicates=True)
                alyxraw_field_buffer.flush_insert(skip_duplicates=True, chunksz=7500)

    with raw_table.connection.transaction:
        alyxraw_buffer.flush_insert(skip_duplicates=True)
        alyxraw_field_buffer.flush_insert(skip_duplicates=True)


def insert_to_update_alyxraw_postgres(
    alyx_models=None,
    excluded_models=[],
    delete_UpdateAlyxRaw_first=False,
    skip_existing_alyxraw=False,
):
    """Ingest entries into update_ibl_alyxraw from postgres alyx instance

    Args:
        alyx_models (list of alyx model django objects): list of alyx django models
        delete_UpdateAlyxRaw_first (bool, optional): whether to delete the update module alyx raw tables first. Defaults to False.
    """
    if not alyx_models:
        alyx_models = ALYX_MODELS

    if delete_UpdateAlyxRaw_first:
        with dj.config(safemode=False):
            logger.info("Deleting update ibl alyxraw tables...")
            models_res = [{"model": get_django_model_name(m) for m in alyx_models}]
            (alyxraw.UpdateAlyxRaw.Field & models_res).delete_quick()
            (alyxraw.UpdateAlyxRaw & models_res).delete_quick()

    for alyx_model in alyx_models:
        if alyx_model.__name__ in excluded_models:
            continue
        logger.info(
            "Ingesting alyx table {} into datajoint UpdateAlyxRaw...".format(
                get_django_model_name(alyx_model)
            ),
        )
        insert_alyx_entries_model(
            alyx_model,
            AlyxRawTable=alyxraw.UpdateAlyxRaw,
            skip_existing_alyxraw=skip_existing_alyxraw,
        )


def main(backtrack_days=None, skip_existing_alyxraw=False):
    for alyx_model in ALYX_MODELS:
        logger.info(
            "Ingesting alyx table {} into datajoint alyxraw...".format(
                get_django_model_name(alyx_model)
            ),
        )
        if get_django_model_name(alyx_model) == "actions.session":
            skip_existing_alyxraw = False
        insert_alyx_entries_model(
            alyx_model,
            AlyxRawTable=alyxraw.AlyxRaw,
            backtrack_days=backtrack_days,
            skip_existing_alyxraw=skip_existing_alyxraw,
        )


if __name__ == "__main__":
    main(backtrack_days=_backtrack_days)
