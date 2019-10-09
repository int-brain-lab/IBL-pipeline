import datajoint as dj
from ibl_pipeline.plotting import behavior
from ibl_pipeline import reference

dj.config['safemode'] = False

kargs = dict(
    suppress_errors=True, display_progress=True
)
print('------ Populating plotting.DailyLabSummary ------')
last_sessions = (reference.Lab.aggr(
    behavior.DailyLabSummary,
    last_session_time='max(last_session_time)')).fetch('KEY')
(behavior.DailyLabSummary & last_sessions).delete()
behavior.DailyLabSummary.populate(**kargs)
