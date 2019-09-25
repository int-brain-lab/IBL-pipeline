
from ibl_pipeline.plotting import behavior

kargs = dict(
    suppress_errors=True, display_progress=True
)
print('------ Populating plotting.DailyLabSummary ------')
behavior.DailyLabSummary.populate(**kargs)
