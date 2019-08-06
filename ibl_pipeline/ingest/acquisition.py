import datajoint as dj
import json
import uuid

from . import alyxraw, reference, subject, action
from . import get_raw_field as grf

schema = dj.schema(dj.config.get('database.prefix', '') +
                   'ibl_ingest_acquisition')


@schema
class Session(dj.Computed):
    definition = """
    (session_uuid) -> alyxraw.AlyxRaw
    ---
    session_number=null:        int
    subject_uuid:               uuid
    session_start_time:         datetime
    session_end_time=null:      datetime
    session_lab=null:           varchar(255)
    session_location=null:      varchar(255)
    session_type=null:          varchar(255)
    session_narrative=null:     varchar(2048)
    task_protocol=null:         varchar(255)
    session_ts=CURRENT_TIMESTAMP:   timestamp
    """
    key_source = (alyxraw.AlyxRaw & 'model="actions.session"').proj(
        session_uuid='uuid')

    def make(self, key):
        key_session = key.copy()
        key['uuid'] = key['session_uuid']
        key_session['subject_uuid'] = uuid.UUID(grf(key, 'subject'))

        if not len(subject.Subject & key_session):
            print('Subject {} is not in the table subject.Subject'.format(
                key_session['subject_uuid']))
            return

        session_number = grf(key, 'number')
        if session_number != 'None':
            key_session['session_number'] = session_number

        key_session['session_start_time'] = grf(key, 'start_time')

        end_time = grf(key, 'end_time')
        if end_time != 'None':
            key_session['session_end_time'] = end_time

        location_uuid = grf(key, 'location')
        if location_uuid != 'None':
            key_session['session_lab'], key_session['session_location'] = \
                (reference.LabLocation &
                 dict(location_uuid=uuid.UUID(location_uuid))).fetch1(
                     'lab_name', 'location_name')

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
    subject_uuid:               uuid
    session_start_time:         datetime
    ---
    parent_session_start_time:  datetime
    childsession_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class SessionUser(dj.Manual):
    definition = """
    subject_uuid:           uuid
    session_start_time:     datetime
    user_name:              varchar(255)
    ---
    sessionuser_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class SessionProcedure(dj.Manual):
    definition = """
    subject_uuid:           uuid
    session_start_time:     datetime
    procedure_type_name:    varchar(255)
    ---
    sessionprocedure_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class SessionProject(dj.Manual):
    definition = """
    subject_uuid:         uuid
    session_start_time:   datetime
    ---
    session_project:      varchar(255)
    sessionproject_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class WaterAdministrationSession(dj.Manual):
    definition = """
    subject_uuid:           uuid
    administration_time:    datetime
    ---
    session_start_time:     datetime
    wateradministrationsession_ts=CURRENT_TIMESTAMP:   timestamp
    """
