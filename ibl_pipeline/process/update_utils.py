import datajoint as dj
from tqdm import tqdm

from ibl_pipeline.ingest import alyxraw


def get_created_keys(model):
    """compare entries of a given alyx model between update_ibl_alyxraw schema and current ibl_alyxraw schema,
    get keys that exist in update_ibl_alyxraw but not ibl_alyxraw

    Args:
        model [str]: alyx model name in table alyxraw.AlyxRaw, e.g. subjects.subject

    Returns:
        created_pks [list]: list of created uuids, existing in update_ibl_alyxraw but not ibl_alyxraw
    """
    return (
        (alyxraw.UpdateAlyxRaw - alyxraw.AlyxRaw.proj()) & f'model="{model}"'
    ).fetch("KEY")


def get_deleted_keys(model):
    """compare entries of a given alyx model between UpdateAlyxRaw and AlyxRaw tables,
    get keys that exist in the current AlyxRaw but not in UpdateAlyxRaw

    Args:
        model [str]: alyx model name in table alyxraw.AlyxRaw

    Returns:
        deleted_pks [list]: list of deleted uuids, existing in the current ibl_alyxraw but not update_ibl_alyxraw
    """
    return (
        (alyxraw.AlyxRaw - alyxraw.UpdateAlyxRaw.proj()) & f'model="{model}"'
    ).fetch("KEY")


def get_updated_keys(model, fields=None):
    """compare entries of a given alyx model between UpdateAlyxRaw and AlyxRaw tables,
    get keys whose field values have changed.

    Args:
        model [str]: alyx model name in table alyxraw.AlyxRaw, e.g. 'actions.session'
        fields [list of strs]: alyx model field names that updates need to be detected

    Returns:
        modified_pks [list]: list of deleted uuids, existing in the AlyxRaw but not UpdateAlyxRaw
    """
    fields_original = alyxraw.AlyxRaw.Field & (alyxraw.AlyxRaw & f'model="{model}"')
    fields_update = alyxraw.UpdateAlyxRaw.Field & (
        alyxraw.UpdateAlyxRaw & f'model="{model}"'
    )

    fields_restr = [{"fname": f} for f in fields] if fields else {}

    return (
        alyxraw.AlyxRaw
        & (
            fields_update.proj(fvalue_new="fvalue") * fields_original
            & "fvalue_new != fvalue"
            & 'fname not in ("json")'
            & fields_restr
        )
    ).fetch("KEY")


def delete_from_alyxraw(keys):
    with dj.config(safemode=False):
        if len(keys) < 50:
            (alyxraw.AlyxRaw.Field & keys).delete_quick()
            (alyxraw.AlyxRaw & keys).delete()
        else:
            for key in tqdm(keys, position=0):
                (alyxraw.AlyxRaw.Field & key).delete_quick()
                (alyxraw.AlyxRaw & key).delete()
