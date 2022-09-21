import actions
import experiments
import misc
import subjects

from ibl_pipeline import acquisition, ephys, qc
from ibl_pipeline.ingest import alyxraw
from ibl_pipeline.ingest import qc as qc_ingest
from ibl_pipeline.process import ingest_alyx_raw_postgres, update_utils
from ibl_pipeline.utils import get_logger

logger = get_logger(__name__)


QC_MODELS_TO_UPDATE = {
    "actions.session": {
        "alyx_model": actions.models.Session,
        "ref_table": acquisition.Session,
        "alyx_fields": ["qc", "extended_qc"],
        "uuid_name": "session_uuid",
        "ingestion_tables": [qc_ingest.SessionQCIngest],
        "real_tables": [
            qc.SessionExtendedQC.Field,
            qc.SessionExtendedQC,
            qc.SessionQC,
        ],  # in the order of delete_quick()
    },
    "experiments.probeinsertion": {
        "alyx_model": experiments.models.ProbeInsertion,
        "ref_table": ephys.ProbeInsertion,
        "alyx_fields": ["json"],
        "uuid_name": "probe_insertion_uuid",
        "ingestion_tables": [qc_ingest.ProbeInsertionQCIngest],
        "real_tables": [
            qc.ProbeInsertionExtendedQC.Field,
            qc.ProbeInsertionExtendedQC,
            qc.ProbeInsertionQC,
        ],  # in the order of delete_quick()
    },
}


def delete_qc_entries(alyx_model_name):
    """
    Deleting updated/deleted entries so they can be reingest, from:
    + AlyxRaw.Field
    + Ingestion tables (shadow tables)
    + Real tables
    """
    model_info = QC_MODELS_TO_UPDATE[alyx_model_name]

    qc_keys = update_utils.get_deleted_keys(
        alyx_model_name
    ) + update_utils.get_updated_keys(alyx_model_name, fields=["qc", "extended_qc"])

    logger.log(
        25, f"Deleting updated entries for {alyx_model_name} from alyxraw fields..."
    )
    (
        alyxraw.AlyxRaw.Field
        & [dict(fname=f) for f in model_info["alyx_fields"]]
        & qc_keys
    ).delete_quick()

    logger.log(
        25,
        f"Deleting updated qc and extended_qc for {alyx_model_name} from shadow tables...",
    )
    uuids_dict_list = [{model_info["uuid_name"]: k["uuid"]} for k in qc_keys]
    for ingestion_table in model_info["ingestion_tables"]:
        (ingestion_table & uuids_dict_list).delete_quick()

    logger.log(
        25,
        f"Deleting updated qc and extended_qc for {alyx_model_name} from real tables...",
    )
    q_real = model_info["ref_table"] & uuids_dict_list
    for real_table in model_info["real_tables"]:
        (real_table & q_real).delete_quick()


def main():
    alyx_model_names = list(QC_MODELS_TO_UPDATE.keys())
    alyx_models = [v["alyx_model"] for v in QC_MODELS_TO_UPDATE.values()]

    logger.info("QC - Ingesting into UpdateAlyxRaw...")
    ingest_alyx_raw_postgres.insert_to_update_alyxraw_postgres(
        alyx_models=alyx_models,
        delete_UpdateAlyxRaw_first=True,
        skip_existing_alyxraw=True,
    )

    logger.info("QC - Deleting updated/deleted entries...")
    for alyx_model_name in alyx_model_names:
        delete_qc_entries(alyx_model_name)

    logger.info("QC - Ingesting from Postgres Alyx to AlyxRaw...")
    for alyx_model in alyx_models:
        ingest_alyx_raw_postgres.insert_alyx_entries_model(
            alyx_model, skip_existing_alyxraw=False
        )

    logger.info("QC - Calling the populate on the QC-ingestion table...")
    for alyx_model_name in alyx_model_names:
        for ingestion_table in QC_MODELS_TO_UPDATE[alyx_model_name]["ingestion_tables"]:
            ingestion_table.populate(display_progress=True, suppress_errors=True)


if __name__ == "__main__":
    main()
