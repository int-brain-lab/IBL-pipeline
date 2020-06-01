import datajoint as dj
import json
import os.path as path
import sys
from ibl_pipeline.ingest import reference, InsertBuffer

dir_name = path.dirname(__file__)


if len(sys.argv) < 2:  # no arguments given
    # if no argument given, assume a canonical file location and name
    filename = path.join(dir_name, '..', 'data', 'alyxfull.json')
else:
    filename = path.join(dir_name, sys.argv[1])

with open(filename, 'r') as fid:
    keys_all = json.load(fid)

keys = [key for key in keys_all
        if key['model'] == 'experiments.brainregion']

ib_brainregion = InsertBuffer(reference.BrainRegion)

for key in keys:
    fields = key['fields']
    ib_brainregion.insert1(
        dict(brain_region_pk=key['pk'],
             acronym=fields['acronym'],
             brain_region_name=fields['name'],
             parent=fields['parent']))
    if ib_brainregion.flush(skip_duplicates=True, chunksz=1000):
        print('Inserted 1000 raw tuples.')

if ib_brainregion.flush(skip_duplicates=True):
    print('Inserted all remaining raw field tuples')
