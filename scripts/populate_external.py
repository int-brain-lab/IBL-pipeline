from ibl_pipeline import ephys
from ibl_pipeline.plotting import ephys as ephys_plotting

kargs = dict(
    display_progress=True,
    suppress_errors=True
)
ephys.Cluster.populate(**kargs)
ephys.TrialSpikes.populate(**kargs)
ephys_plotting.Raster.populate(**kargs)
ephys_plotting.Psth.populate(**kargs)
