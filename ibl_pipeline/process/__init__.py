from ibl_pipeline.ingest import alyxraw, QueryBuffer
from ibl_pipeline.utils import is_valid_uuid
import datetime
from tqdm import tqdm


def get_timezone(t=datetime.datetime.now().time()):
    if t < datetime.time(8, 30):
        timezone = 'European'
    elif t > datetime.time(8, 30) and t < datetime.time(10, 30):
        timezone = 'EST'
    elif t > datetime.time(10, 30) and t < datetime.time(16, 30):
        timezone = 'PST'
    else:
        timezone = 'other'
    return timezone


def get_important_pks(pks, return_original_dict=False):
    '''
    Filter out modified keys that belongs to data.filerecord and jobs.task
    :params modified_keys: list of pks
    :params optional return original_dict: boolean, if True, return the list of dictionaries with uuids to be the key
    :returns pks_important: list of filtered pks
    :returns pks_dict: list of dictionary with uuid as the key
    '''

    pks = [pk for pk in pks if is_valid_uuid(pk)]
    pks_dict = [{'uuid': pk} for pk in pks]

    models_ignored = '"data.dataset", "data.filerecord", "jobs.task", "actions.wateradministration", "experiments.trajectoryestimate", "experiments.channel"'

    if len(pks) < 1000:
        pks_unimportant = [
            str(pk['uuid'])
            for pk in (alyxraw.AlyxRaw &
                       f'model in ({models_ignored})' &
                       pks_dict).fetch('KEY')]
    else:
        buffer = QueryBuffer(
            alyxraw.AlyxRaw & f'model in ({models_ignored})')
        for pk in tqdm(pks_dict):
            buffer.add_to_queue1(pk)
            buffer.flush_fetch('KEY', chunksz=200)

        buffer.flush_fetch('KEY')
        pks_unimportant = [str(pk['uuid']) for pk in buffer.fetched_results]

    pks_important = list(set(pks) - set(pks_unimportant))

    if return_original_dict:
        return pks_important, pks_dict
    else:
        return pks_important
