import datajoint as dj
import uuid

from . import alyxraw
from . import get_raw_field as grf

import os

if os.environ.get('MODE') == 'public':
    from .. import public

schema = dj.schema(dj.config.get('database.prefix', '') +
                   'ibl_ingest_reference')


@schema
class Lab(dj.Computed):
    # <class 'misc.models.Lab'>
    definition = """
    (lab_uuid) -> alyxraw.AlyxRaw
    ---
    lab_name:               varchar(255)  # name of lab
    institution:            varchar(255)
    address:                varchar(255)
    time_zone:              varchar(255)
    reference_weight_pct:   float
    zscore_weight_pct:      float
    lab_ts=CURRENT_TIMESTAMP:   timestamp
    """
    key_source = (alyxraw.AlyxRaw & 'model = "misc.lab"').proj(lab_uuid='uuid')

    def make(self, key):
        key_lab = key.copy()
        key['uuid'] = key['lab_uuid']
        key_lab['lab_name'] = grf(key, 'name')
        key_lab['institution'] = grf(key, 'institution')
        key_lab['address'] = grf(key, 'address')
        key_lab['time_zone'] = grf(key, 'timezone')
        key_lab['reference_weight_pct'] = grf(key, 'reference_weight_pct')
        key_lab['zscore_weight_pct'] = grf(key, 'zscore_weight_pct')
        self.insert1(key_lab)


@schema
class LabMember(dj.Computed):
    # <class 'misc.models.OrderedUser'>
    # <class 'django.contrib.auth.models.User'>
    # For public database, first name, last name, email, password was dropped.
    definition = """
    (user_uuid) -> alyxraw.AlyxRaw
    ---
    user_name:		        varchar(255)	# username
    password:		        varchar(255)	# password
    email=null:		        varchar(255)	# email address
    last_login=null:	    datetime	    # last login
    first_name=null:        varchar(255)	# first name
    last_name=null:		    varchar(255)	# last name
    date_joined:	        datetime	    # date joined
    is_active:		        boolean		    # active
    is_staff:		        boolean		    # staff status
    is_superuser:	        boolean		    # superuser status
    is_stock_manager:       boolean         # stock manager status
    labmember_ts=CURRENT_TIMESTAMP:   timestamp
    """
    key_source = (alyxraw.AlyxRaw & 'model = "misc.labmember"').proj(
        user_uuid='uuid')

    def make(self, key):
        key_lab_member = key.copy()
        key['uuid'] = key['user_uuid']

        # check the current mode, if public, omit some fields
        user_name = grf(key, 'username')
        if os.environ.get('MODE') != 'public':
            key_lab_member['user_name'] = user_name
            key_lab_member['password'] = grf(key, 'password')
            key_lab_member['email'] = grf(key, 'email')
            first_name = grf(key, 'first_name')
            if first_name != 'None':
                key_lab_member['first_name'] = first_name

            last_name = grf(key, 'last_name')
            if last_name != 'None':
                key_lab_member['last_name'] = last_name
        else:
            key_lab_member['user_name'] = (public.UserMap &
                                           {'user_name': user_name}).fetch1(
                                               'pseudo_name')

        last_login = grf(key, 'last_login')
        if last_login != 'None':
            key_lab_member['last_login'] = last_login

        key_lab_member['date_joined'] = grf(key, 'date_joined')

        is_active = grf(key, 'is_active')
        key_lab_member['is_active'] = is_active == 'True'

        is_staff = grf(key, 'is_staff')
        key_lab_member['is_staff'] = is_staff == 'True'

        is_superuser = grf(key, 'is_superuser')
        key_lab_member['is_superuser'] = is_superuser == 'True'

        is_stock_manager = grf(key, 'is_stock_manager')
        key_lab_member['is_stock_manager'] = is_stock_manager == 'True'

        self.insert1(key_lab_member)


@schema
class LabMembership(dj.Computed):
    definition = """
    (lab_membership_uuid) -> alyxraw.AlyxRaw
    ---
    lab_name:               varchar(255)
    user_name:              varchar(255)
    role=null:              varchar(255)
    mem_start_date=null:    date
    mem_end_date=null:      date
    labmembership_ts=CURRENT_TIMESTAMP:   timestamp
    """
    key_source = (alyxraw.AlyxRaw & 'model="misc.labmembership"').proj(
        lab_membership_uuid='uuid')

    def make(self, key):
        key_mem = key.copy()
        key['uuid'] = key['lab_membership_uuid']

        lab_uuid = grf(key, 'lab')
        key_mem['lab_name'] = \
            (Lab & dict(lab_uuid=uuid.UUID(lab_uuid))).fetch1('lab_name')

        user_uuid = grf(key, 'user')
        key_mem['user_name'] = \
            (LabMember & dict(user_uuid=uuid.UUID(user_uuid))).fetch1(
                'user_name')

        role = grf(key, 'role')
        if role != 'None':
            key_mem['role'] = role

        start_date = grf(key, 'start_date')
        if start_date != 'None':
            key_mem['mem_start_date'] = start_date

        end_date = grf(key, 'end_date')
        if end_date != 'None':
            key_mem['mem_end_date'] = end_date

        self.insert1(key_mem)


@schema
class LabLocation(dj.Computed):
    definition = """
    (location_uuid) -> alyxraw.AlyxRaw
    ---
    lab_name:           varchar(64)
    location_name:      varchar(255)    # name of the location
    lablocation_ts=CURRENT_TIMESTAMP:   timestamp
    """
    key_source = (alyxraw.AlyxRaw & 'model = "misc.lablocation"').proj(
        location_uuid='uuid')

    def make(self, key):
        key_loc = key.copy()
        key['uuid'] = key['location_uuid']
        key_loc['location_name'] = grf(key, 'name')
        lab_uuid = grf(key, 'lab')
        if lab_uuid == 'None':
            key_loc['lab_name'] = 'cortexlab'
        else:
            key_loc['lab_name'] = \
                (Lab & dict(lab_uuid=uuid.UUID(lab_uuid))).fetch1(
                    'lab_name')

        self.insert1(key_loc)


@schema
class Project(dj.Computed):
    definition = """
    (project_uuid) -> alyxraw.AlyxRaw
    ---
    project_name:                varchar(255)
    project_description=null:    varchar(1024)
    project_ts=CURRENT_TIMESTAMP:   timestamp
    """
    key_source = (alyxraw.AlyxRaw & 'model="subjects.project"').proj(
        project_uuid='uuid')

    def make(self, key):
        key_proj = key.copy()
        key['uuid'] = key['project_uuid']

        key_proj['project_name'] = grf(key, 'name')
        key_proj['project_description'] = grf(key, 'description')
        self.insert1(key_proj)


@schema
class ProjectLabMember(dj.Manual):
    definition = """
    project_name:   varchar(255)
    user_name:      varchar(255)
    projectlabmember_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class CoordinateSystem(dj.Imported):
    definition = """
    (coordinate_system_uuid) -> alyxraw.AlyxRaw
    ---
    coordinate_system_name: varchar(64)
    coordinate_system_description=null: varchar(2048)
    """
    key_source = (alyxraw.AlyxRaw & 'model="experiments.coordinatesystem"').proj(
        coordinate_system_uuid='uuid')

    def make(self, key):
        key_coord = key.copy()
        key['uuid'] = key['coordinate_system_uuid']

        key_coord['coordinate_system_name'] = grf(key, 'name')
        key_coord['coordinate_system_description'] = grf(key, 'description')
        self.insert1(key_coord)


@schema
class BrainRegion(dj.Lookup):
    definition = """
    brain_region_pk     : int               # primary key of brain region consistent with Allen marking
    ---
    acronym             : varchar(32)       # e.g. "Su3",
    brain_region_name   : varchar(128)      # fullname of the brain region
    parent=null         : int               # pk of the parent
    ontology='CCF 2017' : varchar(32)       # ccf version
    brain_region_level=null          : tinyint           # level in the tree, root is 0
    graph_order=null    : smallint unsigned # graph order shown in allen brain atlas
    """
