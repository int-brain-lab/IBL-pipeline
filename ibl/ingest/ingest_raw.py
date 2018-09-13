import datajoint as dj
import json
import logging
import math
import os.path as path
from ibl.ingest import alyxraw, InsertBuffer

logger = logging.getLogger(__name__)

dir_name = path.dirname(__file__)
filename = path.join(dir_name, '../../data/alyx_dump/dump.uuid.json')

with open(filename, 'r') as fid:
    keys = json.load(fid)

# use Chris' insert buffer to speed up the insersion process
ib_main = InsertBuffer(alyxraw.AlyxRaw)
ib_part = InsertBuffer(alyxraw.AlyxRaw.Field)

# insert into AlyxRaw table
for key in keys:
    ib_main.insert1(dict(uuid=key['pk'], model=key['model']))
    if ib_main.flush(skip_duplicates=True, chunksz=10000):
        logger.debug('Inserted 10000 raw tuples.')
    
if ib_main.flush(skip_duplicates=True):
    logger.debug('Inserted all raw tuples')

# insert into the part table AlyxRaw.Field
for key in keys:
    key_field = dict(uuid=key['pk'])
    for field_name, field_value in key['fields'].items():
        key_field = dict(key_field, fname=field_name)
        
        if field_name == 'json' and field_value is not None:
            key_field['value_idx'] = 0
            key_field['fvalue'] = json.dumps(field_value)
            ib_part.insert1(key_field)
            continue
            
        if field_value == [] or field_value == '' or (type(field_value)==float and math.isnan(field_value)):
            key_field['value_idx'] = 0
            key_field['fvalue'] = 'None'
            ib_part.insert1(key_field)
        
        elif type(field_value) is not list:
            key_field['value_idx'] = 0
            key_field['fvalue'] = str(field_value)
            ib_part.insert1(key_field)
            
        else:
            for value_idx, value in enumerate(field_value):
                key_field['value_idx'] = value_idx
                key_field['fvalue'] = str(value)
                ib_part.insert1(key_field)
     
            if ib_part.flush(skip_duplicates=True, chunksz=10000):
                logger.debug('Inserted 10000 raw field tuples')

if ib_part.flush(skip_duplicates=True):
    logger.debug('Inserted all raw field tuples')