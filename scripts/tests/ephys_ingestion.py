'''
This script tests the ingestion of ephys pipeline.

Shan Shen, 2019-11-20
'''

from ibl_pipeline import subject, acquisition, behavior, ephys

from ibl_pipeline.plotting import ephys as ephys_plotting

# print('Testing ingestion of ProbeInsertion...')
# ephys.ProbeInsertion.populate(display_progress=True)

# print('Testing ingestion of ChannelGroup...')
# ephys.ChannelGroup.populate(display_progress=True, suppress_errors=True)


print('Testing ingestion of Cluster...')
ephys.Cluster.populate(display_progress=True, suppress_errors=True)

# print('Testing ingestion of plotting raster...')
# ephys_plotting.RasterLinkS3.populate(
#     display_progress=True, suppress_errors=True)

print('Testing ingestion of plotting psth')
ephys_plotting.PsthDataVarchar.populate(
    display_progress=True, suppress_errors=True)
