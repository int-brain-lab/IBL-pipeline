import datajoint as dj
from tqdm import tqdm
from ibl_pipeline.process import ingest_alyx_raw

alyxraw = dj.create_virtual_module(
    'alyxraw', dj.config.get('database.prefix', '') + 'ibl_alyxraw')
alyxraw_update = dj.create_virtual_module(
    'alyxraw', 'update_ibl_alyxraw', create_schema=True)


def insert_to_update_alyxraw(
        filename=None, delete_tables=False, models=None):

    with dj.config(safemode=False):
        if not models:
            raise ValueError('Argument models is required, \
                str of an alyx model or a list of alyx models')

        if delete_tables:

            print('Deleting alyxraw update...')
            alyxraw_update.AlyxRaw.Field.delete_quick()
            alyxraw_update.AlyxRaw.delete_quick()

        ingest_alyx_raw.insert_to_alyxraw(
            ingest_alyx_raw.get_alyx_entries(
                filename=filename,
                models=models),
            alyxraw_module=alyxraw_update
        )


def get_deleted_keys(model):
    return ((alyxraw.AlyxRaw - alyxraw_update.AlyxRaw.proj()) &
            f'model="{model}"').fetch('KEY')


def get_updated_keys(model, fields=None):

    fields = alyxraw.AlyxRaw.Field & (alyxraw.AlyxRaw & f'model="{model}"')
    fields_update = alyxraw_update.AlyxRaw.Field & \
        (alyxraw_update.AlyxRaw & f'model="{model}"')

    if fields:
        fields_restr = {}
    else:
        fields_restr = [{'fname': f} for f in fields]

    return (alyxraw.AlyxRaw &
            (fields_update.proj(fvalue_new='fvalue') * fields &
            'fvalue_new != fvalue' & 'fname not in ("json")' & fields_restr)).fetch('KEY')


def delete_from_alyxraw(keys):

    with dj.config(safemode=False):

        if len(keys) < 50:
            (alyxraw.AlyxRaw.Field & keys).delete_quick()
            (alyxraw.AlyxRaw & keys).delete()
        else:
            for key in tqdm(keys, position=0):
                (alyxraw.AlyxRaw.Field & key).delete_quick()
                (alyxraw.AlyxRaw & key).delete()


if __name__ == '__main__':
    insert_to_update_alyxraw(
        filename='/data/alyxfull_20201013_2222.json',
        models=['experiments.trajectoryestimate', 'experiments.channel'])
