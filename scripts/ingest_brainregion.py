import datajoint as dj
import json
import os.path as path
import sys
from ibl_pipeline.ingest import reference, InsertBuffer
from ingest_alyx_raw import get_alyx_entries
from tqdm import tqdm
import pandas as pd
import numpy as np

keys = get_alyx_entries(models='experiments.brainregion')
ib_brainregion = InsertBuffer(reference.BrainRegion)

atlas = pd.read_csv('/data/allen_structure_tree.csv')

for key in tqdm(keys):
    fields = key['fields']
    graph_order = atlas[atlas['id'] == key['pk']]['graph_order']

    if np.isnan(graph_order):
        graph_order = None
    else:
        graph_order = int(graph_order)

    ib_brainregion.insert1(
        dict(brain_region_pk=key['pk'],
             acronym=fields['acronym'],
             brain_region_name=fields['name'],
             parent=fields['parent'],
             brain_region_level=fields['level'],
             graph_order=graph_order))
    if ib_brainregion.flush(skip_duplicates=True, chunksz=1000):
        print('Inserted 1000 raw tuples.')

if ib_brainregion.flush(skip_duplicates=True):
    print('Inserted all remaining raw field tuples')
