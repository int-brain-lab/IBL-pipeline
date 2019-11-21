'''
This script tests the ingestion of ephys pipeline.

Shan Shen, 2019-11-20
'''

from ibl_pipeline import subject, acquisition, behavior, ephys

print('Testing ingestion of ProbeInsertion...')
ephys.ProbeInsertion.populate(display_progress=True)
