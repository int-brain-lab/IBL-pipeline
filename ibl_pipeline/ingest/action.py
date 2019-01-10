import datajoint as dj
from . import alyxraw, reference, subject
from . import get_raw_field as grf


schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_ingest_action')

@schema
class ProcedureType(dj.Computed):
    definition = """
    (procedure_type_uuid) -> alyxraw.AlyxRaw
    ---
    procedure_type_name:                varchar(255)
    procedure_type_description=null:    varchar(1024)
    """
    
    key_source = (alyxraw.AlyxRaw & 'model="actions.proceduretype"').proj(procedure_type_uuid='uuid')

    def make(self, key):
        key_pt = key.copy()
        key['uuid'] = key['procedure_type_uuid']

        key_pt['procedure_type_name'] = grf(key, 'name')

        description = grf(key, 'description')
        if description != 'None':
            key_pt['procedure_type_description'] = description

        self.insert1(key_pt)


@schema
class Weighing(dj.Computed):
    # <class 'actions.models.Weighing'>
    definition = """
    (weigh_uuid) -> alyxraw.AlyxRaw
    ---
    lab_name:           varchar(255)
    subject_nickname:   varchar(255)     # inherited from Subject
    weighing_time:		datetime		# date time
    weight:	            float			# weight in grams
    weighing_user=null: varchar(255)
    """
    key_source = (alyxraw.AlyxRaw & 'model="actions.weighing"').proj(weigh_uuid='uuid')

    def make(self, key):
        key_weigh = key.copy()
        key['uuid'] = key['weigh_uuid']
        
        subject_uuid = grf(key, 'subject')
        key_weigh['lab_name'], key_weigh['subject_nickname'] = (subject.Subject & 'subject_uuid="{}"'.format(subject_uuid)).fetch1('lab_name', 'subject_nickname')
        key_weigh['weighing_time'] = grf(key, 'date_time')

        weight = grf(key, 'weight')
        if weight != 'None':
            key_weigh['weight'] = float(weight)

        user_uuid = grf(key, 'user')
        if user_uuid != 'None':
            key_weigh['weighing_user'] = (reference.LabMember & 'user_uuid="{}"'.format(user_uuid)).fetch1('user_name')

        self.insert1(key_weigh)


@schema
class WaterType(dj.Computed):
    definition = """
    (watertype_uuid) -> alyxraw.AlyxRaw
    ---
    watertype_name:     varchar(255)
    """
    key_source = (alyxraw.AlyxRaw & 'model = "actions.watertype"').proj(watertype_uuid='uuid')

    def make(self, key):
        key_type = key.copy()
        key['uuid'] = key['watertype_uuid']

        key_type['watertype_name'] = grf(key, 'name')
        self.insert1(key_type)


@schema
class WaterAdministration(dj.Computed):
    # <class 'actions.models.WaterAdministration'>
    definition = """
    (wateradmin_uuid) -> alyxraw.AlyxRaw
    ---
    lab_name:                       varchar(255)
    subject_nickname:               varchar(255)
    administration_user=null:       varchar(255)
    administration_time:	        datetime		# date time
    water_administered=null:		float			# water administered
    watertype_name:		            varchar(255)    # type of water
    adlib:                          boolean
    """
    key_source = (alyxraw.AlyxRaw & 'model = "actions.wateradministration"').proj(wateradmin_uuid='uuid')

    def make(self, key):
        key_wa = key.copy()
        key['uuid'] = key['wateradmin_uuid']

        subject_uuid = grf(key, 'subject')
        try:
            key_wa['lab_name'], key_wa['subject_nickname'] = (subject.Subject & 'subject_uuid="{}"'.format(subject_uuid)).fetch1('lab_name', 'subject_nickname')
        except:
            return
        key_wa['administration_time'] = grf(key, 'date_time')
        wa = grf(key, 'water_administered')
        if wa != 'None':
            key_wa['water_administered'] = wa

        water_type = grf(key, 'water_type')
        key_wa['watertype_name'] = (WaterType & 'watertype_uuid="{}"'.format(water_type)).fetch1('watertype_name')

        user_uuid = grf(key, 'user')
        if user_uuid != 'None':
            key_wa['administration_user'] = (reference.LabMember & 'user_uuid="{}"'.format(user_uuid)).fetch1('user_name')

        key_wa['adlib'] = grf(key, 'adlib')=='True'

        self.insert1(key_wa)


@schema
class WaterRestriction(dj.Computed):
    # <class 'actions.models.WaterRestriction'>
    definition = """
    (restriction_uuid) -> alyxraw.AlyxRaw
    ---
    lab_name:                   varchar(255)
    subject_nickname:           varchar(255)
    restriction_start_time:     datetime	# start time
    restriction_end_time=null:  datetime	# end time
    restriction_narrative=null: varchar(1024)
    reference_weight:           float
    restriction_lab=null:       varchar(255)
    restriction_location=null:  varchar(255)
    """
    key_source = (alyxraw.AlyxRaw & 'model = "actions.waterrestriction"').proj(restriction_uuid='uuid')

    def make(self, key):
        key_res = key.copy()
        key['uuid'] = key['restriction_uuid']

        subject_uuid = grf(key, 'subject')
        key_res['lab_name'], key_res['subject_nickname'] = (subject.Subject & 'subject_uuid="{}"'.format(subject_uuid)).fetch1('lab_name', 'subject_nickname')
        key_res['restriction_start_time'] = grf(key, 'start_time')

        end_time = grf(key, 'end_time')
        if end_time != 'None':
            key_res['restriction_end_time'] = end_time

        narrative = grf(key, 'narrative')
        if narrative != 'None':
            key_res['restriction_narrative'] = narrative

        location_uuid = grf(key, 'location')
        if location_uuid != 'None':
            key_res['restriction_lab'], key_res['restriction_location'] = \
                (reference.LabLocation & key & 'location_uuid="{}"'.format(location_uuid)).fetch1('lab_name', 'slocation_name')

        key_res['reference_weight'] = grf(key, 'reference_weight')

        self.insert1(key_res)

@schema
class WaterRestrictionUser(dj.Manual):
    definition = """
    lab_name:               varchar(255)
    subject_nickname:       varchar(255)
    restriction_start_time: varchar(255)   
    user_name:              varchar(255)
    """

@schema
class WaterRestrictionProcedure(dj.Manual):
    definition = """
    lab_name:               varchar(255)
    subject_nickname:       varchar(255)
    restriction_start_time: varchar(255)   
    procedure_type_name:    varchar(255)
    """

@schema
class Surgery(dj.Computed):
    # <class 'actions.models.Surgery'>
    definition = """
    (surgery_uuid) -> alyxraw.AlyxRaw
    ---
    lab_name:                   varchar(255)    # inherited from Subject
    subject_nickname:           varchar(255)    # inherited from Subject
    surgery_lab=null:           varchar(255)    # lab for sugery
    surgery_location=null:      varchar(255)    # foreign key inherited from reference.LabLocation
    surgery_start_time:	        datetime        # surgery start time
    surgery_end_time=null:	    datetime        # surgery end time
    surgery_outcome_type:		enum('None', 'a', 'n', 'r')	    # outcome type
    surgery_narrative=null:     varchar(2048)    	# narrative
    """
    key_source = (alyxraw.AlyxRaw & 'model = "actions.surgery"').proj(surgery_uuid='uuid')

    def make(self, key):
        key_surgery = key.copy()
        key['uuid'] = key['surgery_uuid']

        subject_uuid = grf(key, 'subject')
        if len(subject.Subject & 'subject_uuid="{}"'.format(subject_uuid)) == 0:
            return
        key_surgery['lab_name'], key_surgery['subject_nickname'] = (subject.Subject & 'subject_uuid="{}"'.format(subject_uuid)).fetch1('lab_name', 'subject_nickname')

        start_time = grf(key, 'start_time')
        if start_time != 'None':
            key_surgery['surgery_start_time'] = start_time

        end_time = grf(key, 'end_time')
        if end_time != 'None':
            key_surgery['surgery_end_time'] = end_time

        key_surgery['surgery_outcome_type'] = grf(key, 'outcome_type')

        narrative = grf(key, 'narrative')
        if narrative != 'None':
            key_surgery['surgery_narrative'] = narrative

        location_uuid = grf(key, 'location')
        if location_uuid != 'None':
            key_surgery['surgery_lab'], key_surgery['surgery_location'] = \
                (reference.LabLocation & 'location_uuid="{}"'.format(location_uuid)).fetch1('lab_name', 'location_name')

        self.insert1(key_surgery)


@schema
class SurgeryUser(dj.Manual):
    definition = """
    lab_name:           varchar(255)
    subject_nickname:   varchar(255)
    surgery_start_time: datetime
    user_name:          varchar(255)
    """


@schema
class SurgeryProcedure(dj.Manual):
    definition = """
    lab_name:               varchar(255)
    subject_nickname:       varchar(255)
    surgery_start_time:     datetime
    procedure_type_name:    varchar(255)
    """


@schema
class VirusInjection(dj.Computed):
    # <class 'actions.models.VirusInjection'>
    definition = """
    (virus_injection_uuid) -> alyxraw.AlyxRaw
    lab_name:               varchar(255)        # inherited from Subject
    subject_nickname:       varchar(255)        # inherited from Subject
    injection_time:		    datetime        	# injection time
    injection_volume:		float   		    # injection volume
    rate_of_injection:		float               # rate of injection
    injection_type:		    varchar(255)    	# injection type
    """
    key_source = alyxraw.AlyxRaw & 'model = "actions.virusinjection"'
    # data missing


@schema
class OtherAction(dj.Computed):
    # <class 'actions.models.OtherAction'>
    definition = """
    (other_action_uuid) -> alyxraw.AlyxRaw
    ---
    lab_name:                   varchar(255)
    subject_nickname:           varchar(255)
    other_action_start_time:    datetime	    # start time
    other_action_end_time=null: datetime	    # end time
    other_action_lab=null:      varchar(255)
    other_action_location=null: varchar(255)    # refer to reference.Location
    procedure_name=null:        varchar(255)    # refer to action.Procedure
    """
    key_source = (alyxraw.AlyxRaw & 'model = "actions.otheraction"').proj(other_action_uuid='uuid')

    def make(self, key):
        key_other = key.copy()
        key['uuid'] = key['other_action_uuid']
        subject_uuid = grf(key, 'subject')
        key_other['lab_name'], key_other['subject_nickname'] =\
            (subject.Subject & 'subject_uuid="{}"'.format(subject_uuid)).fetch1('lab_name', 'subject_nickname')
        key_other['other_action_start_time'] = grf(key, 'start_time')

        end_time = grf(key, 'end_time')
        if end_time != 'None':
            key_other['other_action_end_time'] = end_time

        location_uuid = grf(key, 'location')
        if location_uuid != 'None':
            key_other['other_action_lab'], key_other['other_action_location'] =\
                (reference.LabLocation & 'location_uuid="{}"'.format(location_uuid)).fetch1('lab_name', 'location_name')

        procedure_uuid = grf(key, 'procedures')
        if procedure_uuid != 'None':
            key_other['procedure_name'] = (ProcedureType & 'procedure_type_uuid = "{}"'.format(procedure_uuid)).fetch1('procedure_type_name')

        self.insert1(key_other)
