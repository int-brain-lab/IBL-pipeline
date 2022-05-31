import datajoint as dj
import json
import uuid

from ibl_pipeline.ingest import alyxraw, reference, subject, action, ShadowIngestionError
from ibl_pipeline import acquisition
from ibl_pipeline.ingest import get_raw_field as grf

schema = dj.schema(dj.config.get('database.prefix', '') +
                   'ibl_ingest_acquisition')


@schema
class Session(dj.Computed):
    definition = """
    -> alyxraw.AlyxRaw.proj(session_uuid='uuid')
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
    key_source = (alyxraw.AlyxRaw & alyxraw.AlyxRaw.Field
                  & 'model="actions.session"').proj(session_uuid='uuid')

    @staticmethod
    def create_entry(key):
        if not (alyxraw.AlyxRaw.Field & key):
            raise ShadowIngestionError('No AlyxRaw.Field')

        key_session = key.copy()
        key['uuid'] = key['session_uuid']
        key_session['subject_uuid'] = uuid.UUID(grf(key, 'subject'))

        if not len(subject.Subject & key_session):
            raise ShadowIngestionError(f'Subject not found in the table subject.Subject: {key_session["subject_uuid"]}')

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

        return key_session

    def make(self, key):
        self.insert1(Session.create_entry(key))


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


@schema
class SessionQC(dj.Manual):
    definition = """
    subject_uuid        : uuid
    session_start_time  : datetime
    ---
    qc                  : tinyint unsigned
    sessionqc_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class SessionExtendedQC(dj.Manual):
    definition = """
    subject_uuid             : uuid
    session_start_time       : datetime
    qc_type                  : varchar(16)
    ---
    extended_qc              : tinyint unsigned
    session_extended_qc_ts=CURRENT_TIMESTAMP:   timestamp
    """

    class Field(dj.Part):
        definition = """
        -> master
        qc_fname               : varchar(32)
        ---
        qc_fvalue_float=null   : float
        qc_fvalue_str=null     : varchar(32)
        qc_fvalue_blob=null    : blob
        """
