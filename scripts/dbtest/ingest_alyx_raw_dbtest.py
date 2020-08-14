'''
This script ingest alyxraw for test database, ignoring the data tables.
'''

from ibl_pipeline.ingest.ingest_alyx_raw import (get_alyx_entries,
                                                 insert_to_alyxraw)

exclude_list = ['data.dataformat', 'data.datarepositorytype',
                'data.datasettype', 'data.dataset',
                'data.filerecord']

insert_to_alyxraw(get_alyx_entries(exclude=exclude_list))
