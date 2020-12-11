import datajoint as dj
import os
from ibl_pipeline.ingest import reference

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
class CoordinateSystem(dj.Lookup):
    definition = """
    coordinate_system_name: varchar(64)
    ---
    coordinate_system_uuid:  uuid
    coordinate_system_description='': varchar(2048)
    """


@schema
class Ontology(dj.Lookup):
    definition = """
    ontology    : varchar(32)
    """
    contents = zip(['CCF 2017'])


@schema
class BrainRegion(dj.Lookup):
    definition = """
    -> Ontology
    acronym                 : varchar(32)
    ---
    brain_region_name       : varchar(128)
    parent=null             : int               # pk of the parent
    brain_region_pk         : int
    brain_region_level=null : tinyint
    graph_order=null        : smallint unsigned
    """


@schema
class ParentRegion(dj.Imported):
    definition = """
    -> BrainRegion
    ---
    -> BrainRegion.proj(parent='acronym')
    """
    key_source = BrainRegion & \
        (reference.BrainRegion & 'parent is not NULL').proj()

    def make(self, key):

        parent_pk = (reference.BrainRegion & key).fetch1('parent')
        acronym = (BrainRegion & dict(brain_region_pk=parent_pk)).fetch1(
            'acronym')

        self.insert1(
            dict(**key, parent=acronym))
