
from ibl_pipeline import subject, acquisition
from ibl_pipeline.job import patch
import datetime

sessions = acquisition.Session & {'session_uuid': 'f8d5c8b0-b931-4151-b86c-c471e2e80e5d'}

for session in sessions.fetch('KEY'):
    entry = (acquisition.Session*subject.Subject & session).fetch(
        'subject_uuid', 'session_start_time',
        'session_uuid', 'subject_nickname', as_dict=True)
    patch.Session.insert1(
        dict(**entry, job_date=datetime.date(2020, 7, 10)),
        skip_duplicates=True)

patch.Run.populate(display_progress=True)
