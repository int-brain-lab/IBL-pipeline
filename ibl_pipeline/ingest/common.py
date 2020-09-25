'''
Pre-import all ingest modules
'''
from ibl_pipeline.ingest import alyxraw
from ibl_pipeline.ingest import reference as reference_ingest
from ibl_pipeline.ingest import subject as subject_ingest
from ibl_pipeline.ingest import action as action_ingest
from ibl_pipeline.ingest import acquisition as acquisition_ingest
from ibl_pipeline.ingest import data as data_ingest

from os import environ

mode = environ.get('MODE')
if mode != 'public':
    from ibl_pipeline.ingest import ephys as ephys_ingest
    from ibl_pipeline.ingest import histology as histology_ingest
