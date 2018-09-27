
import datajoint as dj

from . import alyxraw
from . import reference


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
        key_lab_member['username'] = (alyxraw.AlyxRaw.Field & key & 'fname="username"').fetch1('fvalue')
        key_lab_member['password'] = (alyxraw.AlyxRaw.Field & key & 'fname="password"').fetch1('fvalue')
        key_lab_member['email'] = (alyxraw.AlyxRaw.Field & key & 'fname="email"').fetch1('fvalue')
        
        last_login = (alyxraw.AlyxRaw.Field & key & 'fname="last_login"').fetch1('fvalue')
        if last_login != 'None':
            key_lab_member['last_login'] = last_login

        key_lab_member['first_name'] = (alyxraw.AlyxRaw.Field & key & 'fname="first_name"').fetch1('fvalue')
        key_lab_member['last_name'] = (alyxraw.AlyxRaw.Field & key & 'fname="last_name"').fetch1('fvalue')
        key_lab_member['date_joined'] = (alyxraw.AlyxRaw.Field & key & 'fname="date_joined"').fetch1('fvalue')
        
        is_active = (alyxraw.AlyxRaw.Field & key & 'fname="is_active"').fetch1('fvalue')
        key_lab_member['is_active'] = True if is_active == 'True' else False
        
        is_staff = (alyxraw.AlyxRaw.Field & key & 'fname="is_staff"').fetch1('fvalue')
        key_lab_member['is_staff'] = True if is_staff == 'True' else False
        
        is_superuser = (alyxraw.AlyxRaw.Field & key & 'fname="is_superuser"').fetch1('fvalue')
        key_lab_member['is_superuser'] = True if is_superuser == 'True' else False

        self.insert1(key_lab_member, skip_duplicates=True)

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
        key_loc['location_name'] = (alyxraw.AlyxRaw.Field & key & 'fname="name"').fetch1('fvalue')

        #lab_uuid = (alyxraw.AlyxRaw.Field & key & 'fname="lab"').fetch1('fvalue')
        #if lab_uuid != 'None':
        #    key_loc['lab_name'] = (Lab & 'lab_uuid="{}"'.format(lab_uuid)).fetch1('lab_name')

        self.insert1(key_loc, skip_duplicates=True)


@schema
class Note(dj.Computed):
    definition = """
    (note_uuid) -> alyxraw.AlyxRaw
    ---
    user_uuid:      varchar(36)        # refer to LabMember
    date_time:		datetime		    # date time
    text:		    varchar(255)		# text
    object_id:		varchar(36)		    # object id
    content_type:   varchar(8)          # content type
    """
    key_source = (alyxraw.AlyxRaw & 'model = "misc.note"').proj(note_uuid='uuid')

    def make(self, key):
        key_note = key.copy()
        key['uuid'] = key['note_uuid']
        key_note['user_uuid'] = (alyxraw.AlyxRaw.Field & key & 'fname="user"').fetch1('fvalue')
        key_note['date_time'] = (alyxraw.AlyxRaw.Field & key & 'fname="date_time"').fetch1('fvalue')
        key_note['text'] = (alyxraw.AlyxRaw.Field & key & 'fname="text"').fetch1('fvalue')
        key_note['object_id'] = (alyxraw.AlyxRaw.Field & key & 'fname="object_id"').fetch1('fvalue')
        key_note['content_type'] = (alyxraw.AlyxRaw.Field & key & 'fname="content_type"').fetch1('fvalue')

        self.insert1(key_note, skip_duplicates=True)