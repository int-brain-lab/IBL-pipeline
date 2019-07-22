
from ibl_pipeline.plotting import behavior

kargs = dict(
    suppress_errors=True, display_progress=True
)
behavior.DailyLabSummary.populate(**kargs)
