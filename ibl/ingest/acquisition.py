
import datajoint as dj
import json

from ibl.ingest import alyxraw, reference, action
from ibl.ingest import get_raw_field as grf

schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_ingest_acquisition')


@schema
class Session(dj.Computed):
    definition = """
    (session_uuid) -> alyxraw.AlyxRaw
    ---
    session_number:             int
    subject_uuid:               varchar(64)
    project_name=null:          varchar(255)
    session_start_time:         datetime
    session_end_time=null:      datetime
    lab_name=null:              varchar(255)
    location_name=null:         varchar(255)
    session_type:               varchar(255)
    session_narrative=null:     varchar(1024)
    """
    key_source = (alyxraw.AlyxRaw & 'model="actions.session"').proj(session_uuid='uuid')

    def make(self, key):
        key_session = key.copy()
        key['uuid'] = key['session_uuid']

        key_session['session_number'] = grf(key, 'number')
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

        key_session['session_type'] = grf(key, 'type')
        
        narrative = grf(key, 'narrative')
        if narrative != 'None':
            key_session['session_narrative'] = grf(key, 'narrative')

        self.insert1(key_session)


@schema
class ChildSession(dj.Computed):
    definition = """
    subject_uuid:               varchar(64)
    session_start_time:         datetime
    ---
    parent_session_start_time:  datetime
    """
    key_source = (alyxraw.AlyxRaw & 'model="actions.session"').proj(session_uuid='uuid')

    def make(self, key):
        key_cs = dict()
        key['uuid'] = key['session_uuid']

        key_cs['subject_uuid'], key_cs['session_number'], key_cs['session_start_time'] = \
            (Session & key).fetch1('subject_uuid', 'session_number', 'session_start_time')
        
        parent_session = grf(key, 'parent_session')
        if parent_session != 'None':
            key_cs['parent_session_number'], key['parent_session_start_time'] = \
                (Session & 'session_uuid="{}"'.format(parent_session)).fetch1('session_number')

        self.insert1(key_cs)

@schema
class SessionLabMember(dj.Computed):
    definition = """
    -> Session
    -> reference.LabMember
    """
    key_source = (alyxraw.AlyxRaw & 'model = "actions.Session"').proj(session_uuid = 'uuid')
    
    def make(self, key):
        key_su_temp = key.copy()
        key['uuid'] = key['session_uuid']

        user_uuids = grf(key, 'users', multiple_entries=True)

        for user_uuid in user_uuids:
            key_su = key_su_temp.copy()
            key_su['user_name'] = (reference.LabMember & 'user_uuid="{}"'.format(user_uuid)).fetch1('user_name')
            self.insert1(key_su)


@schema
class SessionProcedureType(dj.Computed):  
    definition = """
    -> Session
    -> action.ProcedureType
    """
    key_source = (alyxraw.AlyxRaw & 'model = "actions.Session"').proj(session_uuid = 'uuid')

    def make(self, key):
        key_su_temp = key.copy()
        key['uuid'] = key['session_uuid']

        users_uuids = (alyxraw.AlyxRaw.Field & key & 'fname="{}"'.format('users')).fetch('fvalue')

        for user_uuid in users_uuids:
            key_su = key_su_temp.copy()
            key_su['user_name'] = (reference.LabMember & 'user_uuid="{}"'.format(user_uuid)).fetch1('user_name')
            self.insert1(key_su)
   