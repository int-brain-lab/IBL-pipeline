import datajoint as dj
import os


# try to access parent schemas with virtual modules, if not created, import from package
try:
    reference = dj.create_virtual_module('reference', 'ibl_reference')
except dj.DataJointError:
    from . import reference

try:
    subject = dj.create_virtual_module('subject', 'ibl_subject')
except dj.DataJointError:
    from . import subject


# Map to the correct schema based on mode.
mode = os.environ.get('MODE')
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
