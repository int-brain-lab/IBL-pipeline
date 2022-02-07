import datajoint as dj
import datetime
from tqdm import tqdm
import uuid

from . import reference, subject, action
from . import mode, one


alyxraw = dj.create_virtual_module('alyxraw', dj.config.get('database.prefix', '') + 'ibl_alyxraw')


# Map to the correct schema based on mode.
if mode == 'update':
    schema = dj.schema('ibl_acquisition')
else:
    schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_acquisition')


@schema
class Session(dj.Manual):
    # <class 'actions.models.Session'>
    definition = """
    -> subject.Subject
    session_start_time:         datetime	# start time
    ---
    session_uuid:               uuid
    session_number=null:        int     	# number
    session_end_time=null:      datetime	# end time
    -> [nullable] reference.LabLocation.proj(session_lab='lab_name', session_location='location_name')
    task_protocol=null:         varchar(255)
    session_type=null:		    varchar(255)	# type
    session_narrative=null:     varchar(2048)
    session_ts=CURRENT_TIMESTAMP:   timestamp
    """

    @classmethod
    def insert_with_alyx_rest(cls, backtrack_days=1):
        """Helper function that inserts new sessions by query alyx with rest api
        Args:
            backtrack_days (int): the number of days back to search for new sessions
        """
        date_cutoff = datetime.datetime.now() - datetime.timedelta(days=backtrack_days)

        alyx_sessions = one.alyx.rest('sessions', 'list', django=f'start_time__gte,{date_cutoff}')

        for alyx_session in tqdm(alyx_sessions):
            sess_key = {
                'subject_uuid': (subject.Subject & {'subject_nickname': alyx_session['subject']}).fetch1('subject_uuid'),
                'session_start_time': datetime.datetime.strptime(alyx_session["start_time"], '%Y-%m-%dT%H:%M:%S.%f'),
                }

            sess_uuid = alyx_session['url'].split('/')[-1]

            if (cls & sess_key) or (alyxraw.AlyxRaw & {'uuid': sess_uuid}):
                # If this session is already in AlyxRaw, skip, as it will get inserted into Session in this ingestion cycle
                continue

            cls.insert1({**sess_key,
                         'session_uuid': uuid.UUID(sess_uuid),
                         'session_number': alyx_session['number'],
                         'session_end_time': None,
                         'session_lab': alyx_session['lab'],
                         'session_location': None,
                         'task_protocol': alyx_session['task_protocol'],
                         'session_type': None,
                         'session_narrative': None})


@schema
class ChildSession(dj.Manual):
    definition = """
    -> Session
    ---
    (parent_session_start_time) -> Session(session_start_time)
    childsession_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class SessionUser(dj.Manual):
    definition = """
    -> Session
    -> reference.LabMember
    ---
    sessionuser_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class SessionProcedure(dj.Manual):
    definition = """
    -> Session
    -> action.ProcedureType
    ---
    sessionprocedure_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class SessionProject(dj.Manual):
    definition = """
    -> Session
    ---
    -> reference.Project.proj(session_project='project_name')
    sessionproject_ts=CURRENT_TIMESTAMP:   timestamp
    """
