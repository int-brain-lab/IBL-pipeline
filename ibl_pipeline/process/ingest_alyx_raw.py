'''
This script load the json dump and insert the tuples into the alyxraw table.
'''

import datajoint as dj
import json
import logging
import math
import collections
import os.path as path
from ibl_pipeline.ingest import alyxraw, QueryBuffer
import sys
import uuid
import re
from tqdm import tqdm
import numpy as np


logger = logging.getLogger(__name__)


def get_alyx_entries(filename=None, models=None,
                     exclude=None, new_pks=None):

    exclude_list = {'auth.group', 'sessions.session',
                    'authtoken.token',
                    'experiments.brainregion',
                    'misc.note',
                    'jobs.task',
                    'actions.notificationrule',
                    'actions.notification'
                   }
    if exclude:
        exclude_list = exclude_list.union(set(exclude))

    if not filename:
        filename = path.join('/', 'data', 'alyxfull.json')

    with open(filename, 'r') as fid:
        keys_all = json.load(fid)

    print('Creating entries to insert into alyxraw...')
    if not models:
        if new_pks:
            return [key for key in tqdm(keys_all) if key['model'] not in exclude_list and key['pk'] in new_pks]
        else:
            return [key for key in keys_all if key['model'] not in exclude_list]
    elif isinstance(models, str):
        if new_pks:
            return [key for key in keys_all if key['model'] == models and key['pk'] in new_pks]
        else:
            return [key for key in keys_all if key['model'] == models]
    elif isinstance(models, list):
        if new_pks:
            return [key for key in keys_all if key['model'] in models and key['pk'] in new_pks]
        else:
            return [key for key in keys_all if key['model'] in models]
    else:
        raise ValueError('models should be a str, list or numpy array')


def insert_to_alyxraw(
        keys, alyxraw_module=alyxraw,
        alyx_type='all'):

    # use insert buffer to speed up the insertion process
    if alyx_type in ('all', 'main'):

        ib_main = QueryBuffer(alyxraw_module.AlyxRaw)
        # insert into AlyxRaw table
        for key in tqdm(keys, position=0):
            try:
                pk = uuid.UUID(key['pk'])
            except Exception:
                print('Error for key: {}'.format(key))
                continue

            ib_main.add_to_queue1(dict(uuid=pk, model=key['model']))
            if ib_main.flush_insert(skip_duplicates=True, chunksz=10000):
                logger.debug('Inserted 10000 raw tuples.')

        if ib_main.flush_insert(skip_duplicates=True):
            logger.debug('Inserted remaining raw tuples')
            ib_main = QueryBuffer(alyxraw_module.AlyxRaw)

    if alyx_type in ('all', 'part'):
        ib_part = QueryBuffer(alyxraw_module.AlyxRaw.Field)
        # insert into the part table AlyxRaw.Field
        for ikey, key in tqdm(enumerate(keys), position=0):
            try:
                try:
                    pk = uuid.UUID(key['pk'])
                except ValueError:
                    print('Error for key: {}'.format(key))
                    continue

                key_field = dict(uuid=uuid.UUID(key['pk']))
                for field_name, field_value in key['fields'].items():
                    key_field = dict(key_field, fname=field_name)

                    if field_name == 'json' and field_value is not None:

                        key_field['value_idx'] = 0
                        key_field['fvalue'] = json.dumps(field_value)
                        if len(key_field['fvalue']) < 10000:
                            ib_part.add_to_queue1(key_field)
                        else:
                            continue
                    if field_name == 'narrative' and field_value is not None:
                        # filter out emoji
                        emoji_pattern = re.compile(
                            "["
                            u"\U0001F600-\U0001F64F"  # emoticons
                            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                            u"\U0001F680-\U0001F6FF"  # transport & map symbols
                            u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                            u"\U00002702-\U000027B0"
                            u"\U000024C2-\U0001F251"
                            "]+", flags=re.UNICODE)

                        key_field['value_idx'] = 0
                        key_field['fvalue'] = emoji_pattern.sub(r'', field_value)

                    elif field_value is None or field_value == '' or field_value == [] or \
                            (isinstance(field_value, float) and math.isnan(field_value)):
                        key_field['value_idx'] = 0
                        key_field['fvalue'] = 'None'
                        ib_part.add_to_queue1(key_field)

                    elif type(field_value) is list and \
                            (type(field_value[0]) is dict or type(field_value[0]) is str):
                        for value_idx, value in enumerate(field_value):
                            key_field['value_idx'] = value_idx
                            key_field['fvalue'] = str(value)
                            ib_part.add_to_queue1(key_field)
                    else:
                        key_field['value_idx'] = 0
                        key_field['fvalue'] = str(field_value)
                        ib_part.add_to_queue1(key_field)

                    if ib_part.flush_insert(skip_duplicates=True, chunksz=10000):
                        logger.debug('Inserted 10000 raw field tuples')

            except Exception:
                print('Problematic entry:{}'.format(ikey))
                raise

        if ib_part.flush_insert(skip_duplicates=True):
            logger.debug('Inserted all remaining raw field tuples')


def insert_to_update_alyxraw(
        models, filename=None, delete_tables=False):
    """Ingest data to alyxraw datajoint tables, json dump based

    Args:
        models (str or list of str): alyx model names, str or a list of str.
        filename (str, optional): filename of alyx json dump. Defaults to None.
        delete_tables (bool, optional): whether to delete the update module alyx raw tables first. Defaults to False.
    """

    alyxraw_update = dj.create_virtual_module(
        'alyxraw', dj.config.get('database.prefix', '') + 'update_ibl_alyxraw',
        create_schema=True)

    with dj.config(safemode=False):

        if delete_tables:

            print('Deleting alyxraw update...')
            alyxraw_update.AlyxRaw.Field.delete_quick()
            alyxraw_update.AlyxRaw.delete_quick()

    insert_to_alyxraw(
        get_alyx_entries(
            filename=filename,
            models=models),
        alyxraw_module=alyxraw_update
    )


if __name__ == '__main__':

    if len(sys.argv) < 2:  # no arguments given
        # if no argument given, assume a canonical file location and name
        filename = path.join('/', 'data', 'alyxfull.json')
    else:
        filename = path.join(dir_name, sys.argv[1])

    new_pks_file = path.join('/', 'data', 'created_pks.json')

    with open(new_pks_file, 'r') as fid:
        new_pks = json.load(fid)

    insert_to_alyxraw(get_alyx_entries(filename, new_pks=new_pks))
