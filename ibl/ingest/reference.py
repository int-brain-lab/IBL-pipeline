
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


@schema
class Severity(dj.Computed):
    definition = ds_reference.Severity.definition


@schema
class Note(dj.Computed):
    definition = ds_reference.Note.definition


@schema
class BrainLocationAcronym(dj.Computed):
    definition = ds_reference.BrainLocationAcronym.definition
