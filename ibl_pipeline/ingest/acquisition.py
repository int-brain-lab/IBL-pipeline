import datajoint as dj
import json

from . import alyxraw, reference, acquisition
from . import get_raw_field as grf

schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_ingest_acquisition')


@schema
class Session(dj.Computed):
    definition = """
    (session_uuid) -> alyxraw.AlyxRaw
    ---
    session_number=null:        int
    subject_uuid:               varchar(64)
    project_name=null:          varchar(255)
    session_start_time:         datetime
    session_end_time=null:      datetime
    lab_name=null:              varchar(255)
    location_name=null:         varchar(255)
    session_type=null:          varchar(255)
    session_narrative=null:     varchar(1024)
    task_protocol=null:         int
    """
    key_source = (alyxraw.AlyxRaw & 'model="actions.session"').proj(session_uuid='uuid')

    def make(self, key):
        key_session = key.copy()
        key['uuid'] = key['session_uuid']

        session_number = grf(key, 'number')
        if session_number != 'None':
            key_session['session_number'] = session_number

        key_session['subject_uuid'] = grf(key, 'subject')

        proj_uuid = grf(key, 'project')
        if proj_uuid != 'None':
            key_session['project_name'] = (reference.Project & 'project_uuid="{}"'.format(proj_uuid)).fetch1('project_name')

        key_session['session_start_time'] = grf(key, 'start_time')

        end_time = grf(key, 'end_time')
        if end_time != 'None':
            key_session['session_end_time'] = end_time

        lab_uuid = grf(key, 'lab')
        if lab_uuid != 'None':
            key_session['lab_name'] = (reference.Lab & 'lab_uuid="{}"'.format(lab_uuid)).fetch1('lab_name')

        location_uuid = grf(key, 'location')
        if location_uuid != 'None':
            key_session['location_name'] = (reference.LabLocation & 'location_uuid="{}"'.format(location_uuid)).fetch1('location_name')

        session_type = grf(key, 'type')
        if session_type != 'None':
            key_session['session_type'] = session_type

        narrative = grf(key, 'narrative')
        if narrative != 'None' and narrative != "":
            key_session['session_narrative'] = narrative

        protocol = grf(key, 'task_protocol')
        if protocol != 'None':
            key_session['task_protocol'] = protocol

        self.insert1(key_session)


@schema
class ChildSession(dj.Manual):
    definition = """
    subject_uuid:               varchar(64)
    session_start_time:         datetime
    ---
    parent_session_start_time:  datetime
    """


@schema
class SessionLabMember(dj.Manual):
    definition = """
    subject_uuid:           varchar(64)
    session_start_time:     datetime
    user_name:              varchar(255)
    """


@schema
class SessionProcedureType(dj.Manual):  
    definition = """
    subject_uuid:           varchar(64)
    session_start_time:     datetime
    procedure_type_name:    varchar(255)
    """
