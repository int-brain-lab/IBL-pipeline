import datajoint as dj
from . import reference
from . import alyxraw

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

        key_pt['procedure_type_name'] = (alyxraw.AlyxRaw.Field & key & 'fname="name"').fetch1('fvalue')

        description = (alyxraw.AlyxRaw.Field & key & 'fname="description"').fetch1('fvalue')
        if description != 'None':
            key_pt['procedure_type_description'] = description
        
        self.insert1(key_pt, skip_duplicates=True)

@schema
class Weighing(dj.Computed):
    # <class 'actions.models.Weighing'>
    definition = """
    (weigh_uuid) -> alyxraw.AlyxRaw
    ---
    subject_uuid:       varchar(36)     # inherited from Subject
    weighing_time:		datetime		# date time
    weight=null:	    float			# weight in grams
    """
    key_source = (alyxraw.AlyxRaw & 'model="actions.weighing"').proj(weigh_uuid='uuid')

    def make(self, key):
        key_weigh = key.copy()
        key['uuid'] = key['weigh_uuid']
        
        key_weigh['subject_uuid'] = (alyxraw.AlyxRaw.Field & key & 'fname="subject"').fetch1('fvalue')
        key_weigh['weighing_time'] = (alyxraw.AlyxRaw.Field & key & 'fname="date_time"').fetch1('fvalue')

        weight = (alyxraw.AlyxRaw.Field & key & 'fname="weight"').fetch1('fvalue')
        if weight != 'None':
            key_weigh['weight'] = float(weight)
        
        self.insert1(key_weigh, skip_duplicates=True)

@schema
class WaterAdministration(dj.Computed):
    # <class 'actions.models.WaterAdministration'>
    definition = """
    (wateradmin_uuid) -> alyxraw.AlyxRaw
    ---
    subject_uuid:           varchar(36)
    administration_time:	datetime		# date time
    water_administered:		float			# water administered
    hydrogel=null:		    boolean         # hydrogel, to be changed in future release of alyx
    """
    key_source = (alyxraw.AlyxRaw & 'model = "actions.wateradministration"').proj(wateradmin_uuid='uuid')
    
    def make(self, key):
        key_wa = key.copy()
        key['uuid'] = key['wateradmin_uuid']
        
        key_wa['subject_uuid'] = (alyxraw.AlyxRaw.Field & key & 'fname="subject"').fetch1('fvalue')
        key_wa['administration_time'] = (alyxraw.AlyxRaw.Field & key & 'fname="date_time"').fetch1('fvalue')
        key_wa['water_administered'] = (alyxraw.AlyxRaw.Field & key & 'fname="water_administered"').fetch1('fvalue')
        hydrogel = (alyxraw.AlyxRaw.Field & key & 'fname="hydrogel"').fetch1('fvalue')
        if hydrogel != 'None':
            key_wa['hydrogel'] = True if hydrogel == "True" else False
        self.insert1(key_wa, skip_duplicates=True)

@schema
class WaterRestriction(dj.Computed):
    # <class 'actions.models.WaterRestriction'>
    definition = """
    (restriction_uuid) -> alyxraw.AlyxRaw
    ---
    subject_uuid:               varchar(36)
    restriction_start_time:     datetime	# start time
    restriction_end_time=null:  datetime	# end time
    restriction_narrative=null: varchar(256)
    procedure_type_uuid=null:   varchar(36)
    location_name=null:         varchar(256)   
    """
    key_source = (alyxraw.AlyxRaw & 'model = "actions.waterrestriction"').proj(restriction_uuid='uuid')
    
    def make(self, key):
        key_res = key.copy()
        key['uuid'] = key['restriction_uuid']
        
        key_res['subject_uuid'] = (alyxraw.AlyxRaw.Field & key & 'fname="subject"').fetch1('fvalue')
        key_res['restriction_start_time'] = (alyxraw.AlyxRaw.Field & key & 'fname="start_time"').fetch1('fvalue')
        
        end_time = (alyxraw.AlyxRaw.Field & key & 'fname="end_time"').fetch1('fvalue')
        if end_time != 'None':
            key_res['restriction_end_time'] = end_time
        
        procedure_type_uuid = (alyxraw.AlyxRaw.Field & key & 'fname="procedures"').fetch1('fvalue')
        if procedure_type_uuid != 'None':
            key_res['procedure_type_uuid'] = procedure_type_uuid
        
        narrative = (alyxraw.AlyxRaw.Field & key & 'fname="narrative"').fetch1('fvalue')
        if narrative != 'None':
            key_res['restriction_narrative'] = narrative

        location_uuid = (alyxraw.AlyxRaw.Field & key & 'fname="location"').fetch1('fvalue')
        if location_uuid != 'None':
            key_res['location_name'] = (reference.Location & key & 'location_uuid="{}"'.format(location_uuid)).fetch1('location_name')

        self.insert1(key_res, skip_duplicates=True)

@schema
class Surgery(dj.Computed):
    # <class 'actions.models.Surgery'>
    definition = """
    (surgery_uuid) -> alyxraw.AlyxRaw
    ---
    subject_uuid:               varchar(36)     # inherited from Subject
    lab_name=null:              varchar(255)    # inherited from reference.Lab in the future?
    user_name=null:             varchar(255)    # inherited from reference.LabMember
    location_name=null:         varchar(255)    # foreign key inherited from reference.Location
    surgery_start_time=null:	datetime        # surgery start time
    surgery_end_time=null:	    datetime        # surgery end time
    outcome_type:		        enum('None', 'a', 'n', 'r')	    # outcome type
    surgery_narrative=null:     varchar(2048)    	# narrative
    """
    key_source = (alyxraw.AlyxRaw & 'model = "actions.surgery"').proj(surgery_uuid='uuid')
    
    def make(self, key):
        key_surgery = key.copy()
        key['uuid'] = key['surgery_uuid']

        key_surgery['subject_uuid'] = (alyxraw.AlyxRaw.Field & key & 'fname="subject"').fetch1('fvalue')

        surgery_start_time = (alyxraw.AlyxRaw.Field & key & 'fname="start_time"').fetch1('fvalue')
        if surgery_start_time != 'None':
            key_surgery['surgery_start_time'] = surgery_start_time

        surgery_end_time = (alyxraw.AlyxRaw.Field & key & 'fname="end_time"').fetch1('fvalue')
        if surgery_end_time != 'None':
            key_surgery['surgery_end_time'] = surgery_end_time

        key_surgery['outcome_type'] = (alyxraw.AlyxRaw.Field & key & 'fname="outcome_type"').fetch1('fvalue')

        narrative = (alyxraw.AlyxRaw.Field & key & 'fname="narrative"').fetch1('fvalue')
        if narrative != 'None':
            key_surgery['surgery_narrative'] = narrative

        lab_uuid = (alyxraw.AlyxRaw.Field & key & 'fname="lab"').fetch1('fvalue')
        if lab_uuid != 'None':
            key_surgery['lab_name'] = (reference.Lab & 'lab_uuid="{}"'.format(lab_uuid)).fetch1('location_name')
        
        location_uuid = (alyxraw.AlyxRaw.Field & key & 'fname="location"').fetch1('fvalue')
        if location_uuid != 'None':
            key['location_name'] = (reference.Location & 'location_uuid="{}"'.format(location_uuid)).fetch1('location_name')
        
        self.insert1(key_surgery, skip_duplicates=True)


@schema
class VirusInjection(dj.Computed):
    # <class 'actions.models.VirusInjection'>
    definition = """
    (virus_injection_uuid) -> alyxraw.AlyxRaw
    subject_uuid:           varchar(36)         # inherited from Subject
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
    subject_uuid:               varchar(36)
    other_action_start_time:    datetime	    # start time
    other_action_end_time=null: datetime	    # end time
    location_name=null:         varchar(255)    # refer to reference.Location
    procedure_name=null:        varchar(255)    # refer to action.Procedure
    """
    key_source = (alyxraw.AlyxRaw & 'model = "actions.otheraction"').proj(other_action_uuid='uuid')

    def make(self, key):
        key_other = key.copy()
        key['uuid'] = key['other_action_uuid']
        key_other['subject_uuid'] = (alyxraw.AlyxRaw.Field & key & 'fname="subject"').fetch1('fvalue')
        key_other['other_action_start_time'] = (alyxraw.AlyxRaw.Field & key & 'fname="start_time"').fetch1('fvalue')
        
        end_time = (alyxraw.AlyxRaw.Field & key & 'fname="end_time"').fetch1('fvalue')
        if end_time != 'None':
            key_other['other_action_end_time'] = end_time

        location_uuid = (alyxraw.AlyxRaw.Field & key & 'fname="location"').fetch1('fvalue')
        if location_uuid != 'None':
            key_other['location_name'] = (reference.Location & 'location_uuid="{}"'.format(location_uuid)).fetch1('location_name')
        
        procedure_uuid = (alyxraw.AlyxRaw.Field & key & 'fname="procedures"').fetch1('fvalue')
        if procedure_uuid != 'None':
            key_other['procedure_name'] = (ProcedureType & 'procedure_type_uuid = "{}"'.format(procedure_uuid)).fetch1('procedure_type_name')

        self.insert1(key_other, skip_duplicates=True)

