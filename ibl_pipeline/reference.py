import datajoint as dj
import os

mode = os.environ.get('MODE')

if mode == 'update':
    schema = dj.schema('ibl_reference')
else:
    schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_reference')


@schema
class Lab(dj.Lookup):
    # <class 'misc.models.Lab'>
    definition = """
    lab_name:                   varchar(255)  # name of lab
    ---
    lab_uuid:                   uuid
    institution:                varchar(255)
    address:                    varchar(255)
    time_zone:                  varchar(255)
    reference_weight_pct:       float
    zscore_weight_pct:          float
    lab_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class LabMember(dj.Manual):
    # <class 'misc.models.LabMember'>
    # <class 'django.contrib.auth.models.User'>
    definition = """
    user_name:		                varchar(255)	# username
    ---
    user_uuid:                      uuid
    password:		                varchar(255)	# password
    email=null:		                varchar(255)	# email address
    last_login=null:	            datetime	    # last login
    first_name=null:                varchar(255)	# first name
    last_name=null:		            varchar(255)	# last name
    date_joined:	                datetime	    # date joined
    is_active:		                boolean		    # active
    is_staff:		                boolean		    # staff status
    is_superuser:	                boolean		    # superuser status
    is_stock_manager:               boolean         # stock manager status
    groups=null:                    blob            #
    user_permissions=null:          blob            #
    labmember_ts=CURRENT_TIMESTAMP: timestamp
    """


@schema
class LabMembership(dj.Manual):
    definition = """
    -> Lab
    -> LabMember
    ---
    lab_membership_uuid:                uuid
    role=null:                          varchar(255)
    mem_start_date=null:                date
    mem_end_date=null:                  date
    labmembership_ts=CURRENT_TIMESTAMP: timestamp
    """


@schema
class LabLocation(dj.Manual):
    # <class 'misc.models.LabLocation'>
    definition = """
    # The physical location at which an session is performed or appliances are located.
    # This could be a room, a bench, a rig, etc.
    -> Lab
    location_name:      varchar(255)    # name of the location
    ---
    location_uuid:      uuid
    lablocation_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class Project(dj.Lookup):
    definition = """
    project_name:                   varchar(255)
    ---
    project_uuid:                   uuid
    project_description=null:       varchar(1024)
    project_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class ProjectLabMember(dj.Manual):
    definition = """
    -> Project
    -> LabMember
    ---
    projectlabmember_ts=CURRENT_TIMESTAMP:   timestamp
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
class CoordindateSystem(dj.Lookup):
    definition = """
    coordinate_system_name: varchar(64)
    ---
    coordinate_system_uuid:  uuid
    coordinate_system_description=null: varchar(2048)
    """


@schema
class Atlas(dj.Lookup):
    definition = """
    atlas:      varchar(64)
    """
    contents = zip(['allen_ccf'])


@schema
class BrainLocationAcronym(dj.Lookup):
    definition = """
    acronym:  varchar(32) # acronym of a brain location
    ---
    full_name = null: varchar(128) # full name of the brain location
    """
    contents = [
        ['ACA', 'Anterior cingulate area'],
        ['ACB', 'Nucleus accumbens'],
        ['IC', 'Inferior colliculus '],
        ['MOs', 'Secondary motor area'],
        ['MRN', 'Midbrain reticular nucleus'],
        ['root', ''],
        ['RSP', 'Retrosplenial area'],
        ['SCsg', 'Superficial gray layer '],
        ['VISp', 'Primary visual area']
    ]
