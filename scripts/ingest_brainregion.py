import datajoint as dj
import json
import os.path as path
import sys
from ibl_pipeline.ingest import QueryBuffer
from ibl_pipeline.ingest import reference as reference_ingest
from ibl_pipeline import reference
from ingest_alyx_raw import get_alyx_entries
from tqdm import tqdm
import pandas as pd
import numpy as np


keys = get_alyx_entries(models='experiments.brainregion')
atlas = pd.read_csv('/data/allen_structure_tree.csv')


def ingest_all():

    ib_brainregion = QueryBuffer(reference_ingest.BrainRegion)

    for key in tqdm(keys, position=0):
        fields = key['fields']
        graph_order = atlas[atlas['id'] == key['pk']]['graph_order']

        if np.isnan(graph_order.to_list()[0]):
            graph_order = None
        else:
            graph_order = int(graph_order)

        ib_brainregion.add_to_queue1(
            dict(brain_region_pk=key['pk'],
                 acronym=fields['acronym'],
                 brain_region_name=fields['name'],
                 parent=fields['parent'],
                 brain_region_level=fields['level'],
                 graph_order=graph_order))
        if ib_brainregion.flush_insert(skip_duplicates=True, chunksz=1000):
            print('Inserted 1000 raw tuples.')

    if ib_brainregion.flush_insert(skip_duplicates=True):
        print('Inserted all remaining raw field tuples')


# mapping of name in alyx and DJ tables
mapping = dict(acronym='acronym',
               brain_region_name='name',
               parent='parent',
               brain_region_level='level',
               graph_order='graph_order')


def update_shadow_field(field):

    for key in tqdm(keys, position=0):
        fields = key['fields']
        if mapping[field] == 'graph_order':
            graph_order = atlas[atlas['id'] == key['pk']]['graph_order']

            if np.isnan(graph_order.to_list()[0]):
                field_value = None
            else:
                field_value = int(graph_order)
        else:
            field_value = fields[mapping[field]]

        dj.Table._update(reference_ingest.BrainRegion &
                         dict(brain_region_pk=key['pk']),
                         field, field_value)


def update_real_field(field):

    entries_for_updates = \
        reference.BrainRegion.proj('brain_region_pk', field_real=field) * \
        reference_ingest.BrainRegion.proj(field_shadow=field) & \
        ['field_real != field_shadow',
         'field_real is null and field_shadow is not null',
         'field_real is not null and field_shadow is null']

    for key in tqdm(entries_for_updates.fetch('KEY'), position=0):
        dj.Table._update(
            reference.BrainRegion & key, field,
            (reference_ingest.BrainRegion & key).fetch1(field))


if __name__ == '__main__':

    ingest_all()
