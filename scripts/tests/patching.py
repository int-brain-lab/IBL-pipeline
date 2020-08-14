
from ibl_pipeline import subject, acquisition, ephys
from ibl_pipeline.job import patch
import datetime


if __name__ == '__main__':
    sessions = acquisition.Session & ephys.DefaultCluster & 'session_lab not in ("cortexlab", "churchlandlab")'

    for session in sessions.fetch('KEY'):
        entry = (acquisition.Session*subject.Subject & session).fetch(
            'subject_uuid', 'session_start_time',
            'session_uuid', 'subject_nickname', as_dict=True)
        patch.Session.insert1(
            dict(**entry[0], job_date=datetime.date(2020, 7, 10)),
            skip_duplicates=True)

    patch.Run.populate(display_progress=True)
