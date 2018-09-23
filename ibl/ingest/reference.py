
import datajoint as dj

from . import alyxraw
from .. import reference as ds_reference



schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_ingest_reference')

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
    key_source = alyxraw.AlyxRaw & 'model = "misc.LabMember"'

    def make(self, key):
        key['username'] = (alyxraw.AlyxRaw & key & 'fname="username"').fetch1('fvalue')
        key['password'] = (alyxraw.AlyxRaw & key & 'fname="password"').fetch1('fvalue')
        key['email'] = (alyxraw.AlyxRaw & key & 'fname="email"').fetch1('fvalue')
        key['last_login'] = (alyxraw.AlyxRaw & key & 'fname="last_login"').fetch1('fvalue')
        key['first_name'] = (alyxraw.AlyxRaw & key & 'fname="first_name"').fetch1('fvalue')
        key['last_name'] = (alyxraw.AlyxRaw & key & 'fname="last_name"').fetch1('fvalue')
        key['date_joined'] = (alyxraw.AlyxRaw & key & 'fname="date_joined"').fetch1('fvalue')
        
        is_active = (alyxraw.AlyxRaw & key & 'fname="is_active"').fetch1('fvalue')
        key['is_active'] = True if is_active == 'True' else False
        
        is_staff = (alyxraw.AlyxRaw & key & 'fname="is_staff"').fetch1('fvalue')
        key['is_staff'] = True if is_staff == 'True' else False
        
        is_superuser = (alyxraw.AlyxRaw & key & 'fname="name"').fetch1('fvalue')
        key['is_superuser'] = True if is_superuser == 'True' else False

        self.insert1(key, skip_duplicates=True)

@schema
class Location(dj.Computed):
    definition = """
    (location_uuid) -> alyxraw.AlyxRaw
    ---
    location_name:      varchar(255)    # name of the location
    -> [nullable] Lab
    """
    key_source = alyxraw.AlyxRaw & 'model = "misc.lablocation"'

    def make(self, key):
        key['location_name'] = (alyxraw.AlyxRaw & key & 'fname="name"').fetch1('fvalue')
        self.insert1(key, skip_duplicates=True)


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
    key_source = alyxraw.AlyxRaw & 'model = "misc.note"'

    def make(self, key):
        key['user_uuid'] = (alyxraw.AlyxRaw & key & 'fname="user"').fetch1('fvalue')
        key['date_time'] = (alyxraw.AlyxRaw & key & 'fname="date_time"').fetch1('fvalue')
        key['text'] = (alyxraw.AlyxRaw & key & 'fname="text"').fetch1('fvalue')
        key['object_id'] = (alyxraw.AlyxRaw & key & 'fname="object_id"').fetch1('fvalue')
        key['content_type'] = (alyxraw.AlyxRaw & key & 'fname="content_type"').fetch1('fvalue')

        self.insert1(key, skip_duplicates=True)