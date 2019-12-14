'''
This script tests the ingestion of ephys pipeline.

Shan Shen, 2019-11-20
'''

from ibl_pipeline import subject, acquisition, behavior, ephys
from ibl_pipeline.plotting import ephys as ephys_plotting

import time

kargs = dict(d**kargs)

start_time = time.time()

print('Testing ingestion of ProbeInsertion...')
ephys.ProbeInsertion.populate(display_progress=True, limit=1)

probe_insertion_time = time.time()
print('Ingestion time of ProbeInsertion {}'.format(
    probe_insertion_time-start_time))

print('Testing ingestion of ChannelGroup...')
ephys.ChannelGroup.populate(**kargs)
channel_group_time = time.time()
print('Ingestion time of ChannelGroup {}'.format(
    channel_group_time-probe_insertion_time))

print('Testing ingestion of Cluster...')
ephys.Cluster.populate(**kargs)
cluster_time = time.time()
print('Ingestion time of Cluster {}'.format(
    cluster_time-channel_group_time))

print('Testing ingestion of TrialSpikes...')
ephys.TrialSpikes.populate(d**kargs)
trial_spikes_time = time.time()
print('Ingestion time of TrialSpikes {}'.format(
    trial_spikes_time-channel_group_time))

print('Testing ingestion of plotting raster...')
ephys_plotting.RasterLinkS3.populate(
    **kargs)
raster_plotting_time = time.time()
print('Ingestion time of RasterLinkS3 {}'.format(
    raster_plotting_time-trial_spikes_time))

print('Testing ingestion of plotting psth...')
ephys_plotting.PsthDataVarchar.populate(
    **kargs)
psth_plotting_time = time.time()
print('Ingestion time of TrialSpikes {}'.format(
    psth_plotting_time-raster_plotting_time))

end_time = time.time()
print('Total ingestion time {}'.format(
    end_time-start_time
))
