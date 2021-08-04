from ibl_pipeline.process import update_utils, ingest_alyx_raw
from ibl_pipeline.ingest import alyxraw
from ibl_pipeline import acquisition, ephys, qc
from ibl_pipeline.ingest import qc as qc_ingest

import logging

logging.basicConfig(
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler("/src/IBL-pipeline/ibl_pipeline/process/logs/process_qc.log"),
        logging.StreamHandler()],
    level=25)

logger = logging.getLogger(__name__)

qc_update_models = {
    'actions.session':
    {
        'ref_table': acquisition.Session,
        'alyx_fields': ['qc', 'extended_qc'],
        'uuid_name': 'session_uuid',
        'ingest_tables': [qc_ingest.SessionQCIngest],
        'real_tables': [
            qc.SessionExtendedQC.Field,
            qc.SessionExtendedQC,
            qc.SessionQC
        ],  # in the order of delete_quick()
    },
    'experiments.probeinsertion':
    {
        'ref_table': ephys.ProbeInsertion,
        'alyx_fields': ['json'],
        'uuid_name': 'probe_insertion_uuid',
        'ingest_tables': [qc_ingest.ProbeInsertionQCIngest],
        'real_tables': [
            qc.ProbeInsertionExtendedQC.Field,
            qc.ProbeInsertionExtendedQC,
            qc.ProbeInsertionQC
        ]  # in the order of delete_quick()
    }
}


def delete_qc_entries(alyx_model):

    model_info = qc_update_models[alyx_model]

    qc_keys = update_utils.get_deleted_keys(alyx_model) + \
        update_utils.get_updated_keys(alyx_model, fields=['qc', 'extended_qc'])

    logger.log(25, f'Deleting updated entries for {alyx_model} from alyxraw fields...')
    (alyxraw.AlyxRaw.Field &
     [dict(fname=f) for f in model_info['alyx_fields']] & qc_keys).delete_quick()

    logger.log(25, f'Deleting updated qc and extended_qc for {alyx_model} from ingest tables...')
    uuids_dict_list = [{model_info['uuid_name']: k['uuid']} for k in qc_keys]
    q_real = model_info['ref_table'] & uuids_dict_list

    for m in model_info['ingest_tables']:
        (m & uuids_dict_list).delete_quick()

    logger.log(25, f'Deleting updated qc and extended_qc for {alyx_model} from real tables...')
    for m in model_info['real_tables']:
        (m & q_real).delete_quick()


def process_alyxraw_qc(
        filename='/data/alyxfull.json',
        models=['actions.session', 'experiments.probeinsertion']):
    '''
    Ingest all qc entries in a particular alyx dump, regardless of the current status.
    '''

    ingest_alyx_raw.insert_to_alyxraw(
        ingest_alyx_raw.get_alyx_entries(
            filename=filename,
            models=models
        ),
        alyx_type='part'
    )


def ingest_tables(alyx_model):

    for m in qc_update_models[alyx_model]['ingest_tables']:
        m.populate(display_progress=True, suppress_errors=True)


def main(fpath='/data/alyxfull.json'):

    alyx_models = list(qc_update_models.keys())

    logger.log(25, 'Insert to update alyxraw...')
    ingest_alyx_raw.insert_to_update_alyxraw(
        models=alyx_models, filename=fpath, delete_tables=True)

    logger.log(25, 'Deleting updated entries...')

    for alyx_model in alyx_models:
        delete_qc_entries(alyx_model)

    logger.log(25, 'Ingesting Alyxraw for QC...')
    process_alyxraw_qc(models=alyx_models)

    logger.log(25, 'Ingesting QC tables...')
    for alyx_model in alyx_models:
        ingest_tables(alyx_model)


if __name__ == '__main__':

    main()
