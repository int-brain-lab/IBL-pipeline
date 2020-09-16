from ibl_pipeline.ingest import alyxraw
from ibl_pipeline.utils import is_valid_uuid


def get_important_pks(pks, return_original_dict=False):
    '''
    Filter out modified keys that belongs to data.filerecord and jobs.task
    :params modified_keys: list of pks
    :params optional return original_dict: boolean, if True, return the list of dictionary with uuids to be the key
    :returns pks_important: list of filtered pks
    :returns pks_dict: list of dictionary with uuid as the key
    '''

    pks = [pk for pk in pks if is_valid_uuid(pk)]
    pks_dict = [{'uuid': pk} for pk in pks]
    pks_unimportant = [str(pk['uuid'])
        for pk in (alyxraw.AlyxRaw & 'model in ("data.filerecord", "jobs.task")' & pks_dict).fetch('KEY')]
    pks_important = list(set(pks) - set(pks_unimportant))

    if return_original_dict:
        return pks_important, pks_dict
    else:
        return pks_important
