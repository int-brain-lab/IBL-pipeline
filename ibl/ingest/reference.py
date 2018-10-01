
import datajoint as dj

from ibl.ingest import alyxraw
from ibl.ingest import get_raw_field as grf


schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_ingest_reference')

@schema
class Lab(dj.Lookup):
    # <class 'misc.models.Lab'>
    definition = """
    lab_uuid:           varchar(36)
    ---
    lab_name:           varchar(255)  # name of lab
    institution=null:   varchar(255)  
    address=null:       varchar(255)
    time_zone=null:     varchar(255)
    """

@schema
class LabMember(dj.Computed):
    # <class 'misc.models.OrderedUser'>
    # <class 'django.contrib.auth.models.User'>
    definition = """
    (user_uuid) -> alyxraw.AlyxRaw
    ---
    username:		    varchar(255)	# username
    password:		    varchar(255)	# password
    email:		        varchar(255)	# email address
    last_login=null:	datetime	    # last login
    first_name:		    varchar(255)	# first name
    last_name:		    varchar(255)	# last name
    date_joined:	    datetime	    # date joined
    is_active:		    boolean		    # active
    is_staff:		    boolean		    # staff status
    is_superuser:	    boolean		    # superuser status
    """
    key_source = (alyxraw.AlyxRaw & 'model = "misc.LabMember"').proj(user_uuid='uuid')

    def make(self, key):
        key_lab_member = key.copy()
        key['uuid'] = key['user_uuid']
        key_lab_member['username'] = grf(key, 'username')
        key_lab_member['password'] = grf(key, 'password')
        key_lab_member['email'] = grf(key, 'email')
        
        last_login = grf(key, 'last_login')
        if last_login != 'None':
            key_lab_member['last_login'] = last_login

        key_lab_member['first_name'] = grf(key, 'first_name')
        key_lab_member['last_name'] = grf(key, 'last_name')
        key_lab_member['date_joined'] = grf(key, 'date_joined')
        
        is_active = grf(key, 'is_active')
        key_lab_member['is_active'] = is_active == 'True'
        
        is_staff = grf(key, 'is_staff')
        key_lab_member['is_staff'] = is_staff == 'True'
        
        is_superuser = grf(key, 'is_superuser')
        key_lab_member['is_superuser'] = is_superuser == 'True'

        self.insert1(key_lab_member)

@schema
class Location(dj.Computed):
    definition = """
    (location_uuid) -> alyxraw.AlyxRaw
    ---
    location_name:      varchar(255)    # name of the location
    lab_name=null:           varchar(36)
    """
    key_source = (alyxraw.AlyxRaw & 'model = "misc.lablocation"').proj(location_uuid='uuid')

    def make(self, key):
        key_loc = key.copy()
        key['uuid'] = key['location_uuid']
        key_loc['location_name'] = grf(key, 'name')

        #lab_uuid = (alyxraw.AlyxRaw.Field & key & 'fname="lab"').fetch1('fvalue')
        #if lab_uuid != 'None':
        #    key_loc['lab_name'] = (Lab & 'lab_uuid="{}"'.format(lab_uuid)).fetch1('lab_name')

        self.insert1(key_loc)


@schema
class Note(dj.Computed):
    definition = """
    (note_uuid) -> alyxraw.AlyxRaw
    ---
    user_uuid:      varchar(36)        # refer to LabMember
    date_time:		datetime		    # date time
    text:		    varchar(255)		# text
    object_id:		varchar(36)		    # object id
    content_type:   varchar(36)          # content type
    """
    key_source = (alyxraw.AlyxRaw & 'model = "misc.note"').proj(note_uuid='uuid')

    def make(self, key):
        key_note = key.copy()
        key['uuid'] = key['note_uuid']
        key_note['user_uuid'] = grf(key, 'user')
        key_note['date_time'] = grf(key, 'date_time')
        key_note['text'] = grf(key, 'text')
        key_note['object_id'] = grf(key, 'object_id')
        key_note['content_type'] = grf(key, 'content_type')

        self.insert1(key_note)