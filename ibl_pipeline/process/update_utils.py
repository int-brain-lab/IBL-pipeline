import datajoint as dj
from tqdm import tqdm


alyxraw = dj.create_virtual_module(
    'alyxraw', dj.config.get('database.prefix', '') + 'ibl_alyxraw')
alyxraw_update = dj.create_virtual_module(
    'alyxraw', dj.config.get('database.prefix', '') + 'update_ibl_alyxraw',
    create_schema=True)


def get_created_keys(model):
    """compare entries of a given alyx model between update_ibl_alyxraw schema and current ibl_alyxraw schema,
    get keys that exist in update_ibl_alyxraw but not ibl_alyxraw

    Args:
        model [str]: alyx model name in table alyxraw.AlyxRaw, e.g. subjects.subject

    Returns:
        created_pks [list]: list of created uuids, existing in update_ibl_alyxraw but not ibl_alyxraw
    """
    return ((alyxraw_update.AlyxRaw - alyxraw.AlyxRaw.proj()) &
            f'model="{model}"').fetch('uuid')


def get_deleted_keys(model):
    """compare entries of a given alyx model between update_ibl_alyxraw schema and current ibl_alyxraw schema,
    get keys that exist in the current ibl_alyxraw but not in update_ibl_alyxraw

    Args:
        model [str]: alyx model name in table alyxraw.AlyxRaw

    Returns:
        deleted_pks [list]: list of deleted uuids, existing in the current ibl_alyxraw but not update_ibl_alyxraw
    """
    return ((alyxraw.AlyxRaw - alyxraw_update.AlyxRaw.proj()) &
            f'model="{model}"').fetch('uuid')


def get_updated_keys(model, fields=None):
    """compare entries of a given alyx model between update_ibl_alyxraw schema and current ibl_alyxraw schema,
    get keys whose field values have changed.

    Args:
        model [str]: alyx model name in table alyxraw.AlyxRaw, e.g. 'actions.session'
        fields [list of strs]: alyx model field names that updates need to be detected

    Returns:
        modified_pks [list]: list of deleted uuids, existing in the current ibl_alyxraw but not update_ibl_alyxraw
    """
    fields_original = alyxraw.AlyxRaw.Field & (alyxraw.AlyxRaw & f'model="{model}"')
    fields_update = alyxraw_update.AlyxRaw.Field & \
        (alyxraw_update.AlyxRaw & f'model="{model}"')

    if not fields:
        fields_restr = {}
    else:
        fields_restr = [{'fname': f} for f in fields]

    return (alyxraw.AlyxRaw &
            (fields_update.proj(fvalue_new='fvalue') * fields_original &
             'fvalue_new != fvalue' & 'fname not in ("json")' & fields_restr)).fetch('uuid')


def delete_from_alyxraw(keys):

    with dj.config(safemode=False):

        if len(keys) < 50:
            (alyxraw.AlyxRaw.Field & keys).delete_quick()
            (alyxraw.AlyxRaw & keys).delete()
        else:
            for key in tqdm(keys, position=0):
                (alyxraw.AlyxRaw.Field & key).delete_quick()
                (alyxraw.AlyxRaw & key).delete()
