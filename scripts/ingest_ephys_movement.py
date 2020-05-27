
from ibl_pipeline import ephys
from ibl_pipeline.analyses import ephys as ephys_analyses
from ibl_pipeline.plotting import ephys as ephys_plotting

kargs = dict(display_progress=True, suppress_errors=True)

print('Populating AlignedTrialSpikes...')
ephys.AlignedTrialSpikes.populate(**kargs)

print('Populating Raster...')
ephys_plotting.Raster.populate(**kargs)

print('Populating Psth...')
ephys_plotting.Psth.populate(**kargs)

print('Populating DepthPeth analyses...')
ephys_analyses.DepthPeth.populate(**kargs)

print('Populating NormedDepthPeth analyses...')
ephys_analyses.NormedDepthPeth.populate(**kargs)

print('Populating NormedDepthPeth plotting...')
ephys_plotting.DepthPeth.populate(**kargs)

print('Populating DepthRasterExampleTrial...')
ephys_plotting.DepthRasterExampleTrial.populate(**kargs)
