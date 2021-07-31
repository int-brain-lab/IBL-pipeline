from ibl_pipeline.ingest import alyxraw, QueryBuffer
from ibl_pipeline.utils import is_valid_uuid
import datetime
import pathlib
from tqdm import tqdm


def get_file_timestamp(filepath=None, filetype='json'):
    if not filepath:
        if filetype == 'json':
            filepath = pathlib.Path('/data/alyxfull.json')
        elif filetype == 'sql':
            filepath = pathlib.Path('/tmp/dump.sql.gz')
        else:
            raise ValueError('Unknown filetype, has to be either json or sql')
    else:
        filepath = pathlib.Path(filepath)

    return datetime.datetime.fromtimestamp(filepath.stat().st_mtime)


def get_timezone(t=None, filetype='json'):
    if not t:
        if not filetype:
            raise ValueError('filetype is required if t is not specified')
        else:
            t = get_file_timestamp(filetype=filetype).time()

    if t < datetime.time(8, 30):
        timezone = 'European'
    elif t > datetime.time(8, 30) and t < datetime.time(10, 30):
        timezone = 'EST'
    elif t > datetime.time(10, 30) and t < datetime.time(16, 30):
        timezone = 'PST'
    else:
        timezone = 'other'
    return timezone


def get_file_date(filepath=None, filetype='json'):
    return get_file_timestamp(filepath, filetype).date()


def get_file_timezone(filepath=None, filetype='json'):
    return get_timezone(get_file_timestamp(filepath, filetype).time())


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
