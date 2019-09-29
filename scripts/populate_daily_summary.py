
from ibl_pipeline.plotting import behavior
from ibl_pipeline import reference

dj.config['safemode'] = False

kargs = dict(
    suppress_errors=True, display_progress=True
)
print('------ Populating plotting.DailyLabSummary ------')
(behavior.DailyLabSummary & reference.Lab.aggr(
    behavior.DailyLabSummary,
    last_session_time='max(last_session_time)')).delete()
behavior.DailyLabSummary.populate(**kargs)
