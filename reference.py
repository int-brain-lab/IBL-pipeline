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
class BrainLocation(dj.Manual):
    # <class 'misc.models.BrainLocation'>
    # <class 'electrophysiology.models.BaseBrainLocation'>
    definition = """
    ccf_ap:			float		# ccf ap
    ccf_dv:			float		# ccf dv
    ccf_lr:			float		# ccf lr
    ---
    brain_location_description: varchar(64)	# description
    allen_location_ontology:    varchar(255)	# allen ontology
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
class CoordinateTransformation(dj.Manual):
    # <class 'misc.models.CoordinateTransformation'>
    definition = """
    transform_id:		int		# id
    ---
    name:    			varchar(255)	# name
    description:		varchar(255)	# description
    allen_location_ontology:	varchar(255)	# allen location ontology
    origin:			longblob	# origin
    transformation_matrix:    	longblob	# transformation matrix
    """


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
