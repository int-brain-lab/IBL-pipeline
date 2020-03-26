'''
This script load the json dump and insert the tuples into the alyxraw table.
'''

import datajoint as dj
import json
import logging
import math
import collections
import os.path as path
from ibl_pipeline.ingest import alyxraw, InsertBuffer
import sys
import uuid


logger = logging.getLogger(__name__)

dir_name = path.dirname(__file__)


if len(sys.argv) < 2:  # no arguments given
    # if no argument given, assume a canonical file location and name
    filename = path.join(dir_name, '..', 'data', 'alyxfull.json')
else:
    filename = path.join(dir_name, sys.argv[1])

with open(filename, 'r') as fid:
    keys = json.load(fid)

# remove invalid uuid from unused tables
keys = [key for key in keys
        if key['model'] not in
        ['auth.group', 'sessions.session', 'authtoken.token']]

# use insert buffer to speed up the insersion process
ib_main = InsertBuffer(alyxraw.AlyxRaw)
ib_part = InsertBuffer(alyxraw.AlyxRaw.Field)

# insert into AlyxRaw table
for key in keys:
    ib_main.insert1(dict(uuid=uuid.UUID(key['pk']), model=key['model']))
    if ib_main.flush(skip_duplicates=True, chunksz=10000):
        logger.debug('Inserted 10000 raw tuples.')

if ib_main.flush(skip_duplicates=True):
    logger.debug('Inserted remaining raw tuples')

# insert into the part table AlyxRaw.Field
for ikey, key in enumerate(keys):
    try:
        key_field = dict(uuid=uuid.UUID(key['pk']))
        for field_name, field_value in key['fields'].items():
            key_field = dict(key_field, fname=field_name)

            if field_name == 'json' and field_value is not None:

                key_field['value_idx'] = 0
                key_field['fvalue'] = json.dumps(field_value)
                if len(key_field['fvalue']) < 10000:
                    ib_part.insert1(key_field)
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
                ib_part.insert1(key_field)

            elif type(field_value) is list and \
                    (type(field_value[0]) is dict or type(field_value[0]) is str):
                for value_idx, value in enumerate(field_value):
                    key_field['value_idx'] = value_idx
                    key_field['fvalue'] = str(value)
                    ib_part.insert1(key_field)
            # elif isinstance(field_value, collections.Sequence) and \
            #         isinstance(field_value, (collections.Mapping, str)):
            #     ib_part.insert(dict(key_field, value_idx=value_idx,
            #                    fvalue=str(value))
            #                    for value_idx, value in enumerate(field_value))
            else:
                key_field['value_idx'] = 0
                key_field['fvalue'] = str(field_value)
                ib_part.insert1(key_field)

            if ib_part.flush(skip_duplicates=True, chunksz=10000):
                logger.debug('Inserted 10000 raw field tuples')
    except Exception as e:
        print('Problematic entry:{}'.format(ikey))
        raise

if ib_part.flush(skip_duplicates=True):
    logger.debug('Inserted all remaining raw field tuples')
