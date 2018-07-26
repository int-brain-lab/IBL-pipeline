import datajoint as dj

schema = dj.schema(dj.config['names.%s' % __name__], locals())


@schema
class User(dj.Manual):
    # <class 'misc.models.OrderedUser'>
    # <class 'django.contrib.auth.models.User'>
    definition = """
    username:		varchar(255)	# username
    ---
    password:		varchar(255)	# password
    email:		varchar(255)	# email address
    last_login:		datetime	# last login
    first_name:		varchar(255)	# first name
    last_name:		varchar(255)	# last name
    date_joined:	datetime	# date joined
    is_active:		boolean		# active
    is_staff:		boolean		# staff status
    is_superuser:	boolean		# superuser status
    """


@schema
class Severity(dj.Lookup):
    definition = """
    severity:			tinyint			# severity
    ---
    severity_desc:		varchar(32)		# severity desc
    """
    contents = (
        (0, ''),
        (1, 'Sub-threshold'),
        (2, 'Mild'),
        (3, 'Moderate'),
        (4, 'Severe'),
        (5, 'Non-recovery'),
    )



@schema
class Note(dj.Manual):
    # <class 'misc.models.Note'>
    # TODO: tagging arbitrary objects..
    definition = """
    -> User
    note_id:		int			# id
    ---
    date_time:		datetime		# date time
    text:		varchar(255)		# text
    object_id:		char(32)		# object id
    """
