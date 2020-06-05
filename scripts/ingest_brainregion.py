import datajoint as dj
import json
import os.path as path
import sys
from ibl_pipeline.ingest import reference, InsertBuffer
from ingest_alyx_raw import get_alyx_entries
from tqdm import tqdm

keys = get_alyx_entries(models='experiments.brainregion')
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
