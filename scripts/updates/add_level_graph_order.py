from ibl_pipeline import reference
from ibl_pipeline.ingest import reference as reference_ingest
import datajoint as dj
from tqdm import tqdm

for key in tqdm(reference.BrainRegion.fetch('KEY'), position=0):
    level, graph_order = (reference_ingest.BrainRegion & key).fetch1(
        'brain_region_level', 'graph_order')

    dj.Table._update(reference.BrainRegion & key,
                     'brain_region_level',
                     level)
    dj.Table._update(reference.BrainRegion & key,
                     'graph_order', graph_order)
