import datajoint as dj
import json

from . import alyxraw, reference, subject, action
from . import get_raw_field as grf

schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_ingest_acquisition')


@schema
class Session(dj.Computed):
    definition = """
    (session_uuid) -> alyxraw.AlyxRaw
    ---
    session_number=null:        int
    lab_name:                   varchar(255)
    subject_nickname:           varchar(255)
    project_name=null:          varchar(255)
    session_start_time:         datetime
    session_end_time=null:      datetime
    session_lab=null:           varchar(255)
    session_location=null:      varchar(255)
    session_type=null:          varchar(255)
    session_narrative=null:     varchar(1024)
    task_protocol=null:         int
    """
    key_source = (alyxraw.AlyxRaw & 'model="actions.session"').proj(session_uuid='uuid')

    def make(self, key):
        key_session = key.copy()
        key['uuid'] = key['session_uuid']

        subject_uuid = grf(key, 'subject')
        try:
            key_session['lab_name'], key_session['subject_nickname'] = (subject.Subject & 'subject_uuid="{}"'.format(subject_uuid)).fetch1('lab_name', 'subject_nickname')
        except:
            return

        session_number = grf(key, 'number')
        if session_number != 'None':
            key_session['session_number'] = session_number

        proj_uuid = grf(key, 'project')
        if proj_uuid != 'None':
            key_session['project_name'] = (reference.Project & 'project_uuid="{}"'.format(proj_uuid)).fetch1('project_name')

        key_session['session_start_time'] = grf(key, 'start_time')

        end_time = grf(key, 'end_time')
        if end_time != 'None':
            key_session['session_end_time'] = end_time

        location_uuid = grf(key, 'location')
        if location_uuid != 'None':
            key_session['session_lab'], key_session['session_location'] = \
                (reference.LabLocation & 'location_uuid="{}"'.format(location_uuid)).fetch1('lab_name', 'location_name')

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
    lab_name:                   varchar(255)      
    subject_nickname:           varchar(255)
    session_start_time:         datetime
    ---
    parent_session_start_time:  datetime
    """


@schema
class SessionUser(dj.Manual):
    definition = """
    lab_name:               varchar(255)          
    subject_nickname:       varchar(255)
    session_start_time:     datetime
    user_name:              varchar(255)
    """


@schema
class SessionProcedure(dj.Manual):  
    definition = """
    lab_name:               varchar(255)          
    subject_nickname:       varchar(255)
    session_start_time:     datetime
    procedure_type_name:    varchar(255)
    """

@schema
class WaterAdministrationSession(dj.Manual):
    definition = """
    lab_name:               varchar(255)
    subject_nickname:       varchar(255)
    administration_time:    datetime
    ---
    session_start_time:     datetime
    """
    