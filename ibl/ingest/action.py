import datajoint as dj
from . import reference
from . import alyxraw

schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_ingest_subject')

@schema
class Weighing(dj.Computed):
    # <class 'actions.models.Weighing'>
    definition = """
    (weigh_uuid) -> alyxraw.AlyxRaw
    ---
    subject_uuid:       varchar(36)     # inherited from Subject
    weighing_time:		datetime		# date time
    weight:			    float			# weight in grams
    """
    key_source = alyxraw.AlyxRaw & 'model="subjects.weighing"'

    def make(self, key):
        key['subject_uuid'] = (alyxraw.AlyxRaw.Field & key & 'fname="subject"').fetch1('fvalue')
        key['weighing_time'] = (alyxraw.AlyxRaw.Field & key & 'fname="date_time"').fetch1('fvalue')
        key['weight'] = (alyxraw.AlyxRaw.Field & key & 'fname="weight"').fetch1('fvalue')
        self.insert1(key, skip_duplicates=True)

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
    key_source = alyxraw.AlyxRaw & 'model = actions.wateradministration'
    
    def make(self, key):
        key['subject_uuid'] = (alyxraw.AlyxRaw.Field & key & 'fname="subject"').fetch1('fvalue')
        key['administration_time'] = (alyxraw.AlyxRaw.Field & key & 'fname="date_time"').fetch1('fvalue')
        key['water_administered'] = (alyxraw.AlyxRaw.Field & key & 'fname="water_administered"').fetch1('fvalue')
        hydrogel = (alyxraw.AlyxRaw.Field & key & 'fname="hydrogel"').fetch1('fvalue')
        key['hydrogel'] = True if hydrogel == "True" else False
        self.insert1(key, skip_duplicates=True)

@schema
class WaterRestriction(dj.Manual):
    # <class 'actions.models.WaterRestriction'>
    definition = """
    (restriction_uuid) -> alyxraw.AlyxRaw
    ---
    subject_uuid:               varchar(36)
    restriction_start_time:     datetime	# start time
    restriction_end_time:       datetime	# end time
    -> reference.Location     
    """

@schema
class Surgery(dj.Computed):
    # <class 'actions.models.Surgery'>
    definition = """
    (surgery_uuid) -> alyxraw.AlyxRaw
    ---
    subject_uuid:           varchar(36)     # inherited from Subject
    lab_name=null:          varchar(255)    # inherited from reference.Lab in the future?
    user_name=null:         varchar(255)    # inherited from reference.LabMember
    location_name=null:     varchar(255)    # foreign key inherited from reference.Location
    surgery_start_time:		datetime        # surgery start time
    surgery_end_time:		datetime        # surgery end time
    outcome_type:		    enum('None', 'a', 'n', 'r')	    # outcome type
    narrative:			    varchar(255)	# narrative
    """
    key_source = alyxraw.AlyxRaw & 'model = "actions.surgery"'

    def make(self, key):
        key['subject_uuid'] = (alyxraw.AlyxRaw.Field & key & 'fname="subject"').fetch1('fvalue')
        key['surgery_start_time'] = (alyxraw.AlyxRaw.Field & key & 'fname="start_time"').fetch1('fvalue')
        key['surgery_end_time'] = (alyxraw.AlyxRaw.Field & key & 'fname="end_time"').fetch1('fvalue')
        key['outcome_type'] = (alyxraw.AlyxRaw.Field & key 'fname="outcome_type"').fetch1('fvalue')
        key['narrative'] = (alyxraw.AlyxRaw.Field & key & 'fname="narrative"').fetch1('fvalue')
        key['lab_name'] = (alyxraw.AlyxRaw.Field & key & 'fname="lab_name"').fetch1('fvalue')
        
        location_uuid = (alyxraw.AlyxRaw.Field & key & 'fname="location"').fetch1('fvalue')
        if location_uuid != "None":
            key['location_name'] = (reference.Location & 'location_uuid="{}"'.format(location_uuid)).fetch1('location_name')
        self.insert1(key, skip_duplicates=True)


    @schema
class Implant(dj.Computed):
     # <class 'subjects.models.Subject'>
    definition = """
    (implant_uuid) -> alyxraw.AlyxRaw
    ---
    subject_uuid:       varchar(36)         # inherited from Subject
    implant_weight:		float			    # implant weight
    protocol_number:	varchar(255)		# protocol number
    description:		varchar(255)		# description
    adverse_effects:	varchar(255)		# adverse effects
    actual_severity:    tinyint             # actual severity, inherited from Severity
    """
    key_source = alyxraw.AlyxRaw & 'model = "subjects.subject"'
    
    def make(self, key):
        key['subject_uuid'] = (alyxraw.AlyxRaw.Field & key & 'fname="uuid"').fetch1('fvalue')
        key['implant_weight'] = (alyxraw.AlyxRaw.Field & key & 'fname="implant_weight"').fetch1('fvalue')
        key['protocol_number'] = (alyxraw.AlyxRaw.Field & key & 'fname="protocol_number"').fetch1('fvalue')
        key['description'] = (alyxraw.AlyxRaw.Field & key & 'fname="description"').fetch1('fvalue')
        key['adverse_effects'] = (alyxraw.AlyxRaw.Field & key & 'fname="adverse_effects"').fetch1('fvalue')
        self.insert1(key, skip_duplicates=True)

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
    subject_uuid:               varchar(36)
    other_action_start_time:    datetime	    # start time
    other_action_end_time:      datetime	    # end time
    location_name:              varchar(255)    # refer to reference.Location
    procedure_name:             varchar(255)    # refer to action.Procedure
    """
    key_source = alyxraw.AlyxRaw & 'model = actions.otheraction'

    def make(self, key):
        key['subject_uuid'] = (alyxraw.AlyxRaw.Field & key & 'fname="subject"').fetch1('fvalue')
        key['other_action_start_time'] = (alyxraw.AlyxRaw.Field & key & 'fname="start_time"').fetch1('fvalue')
        key['other_action_end_time'] = (alyxraw.AlyxRaw.Field & key & 'fname="end_time"').fetch1('fvalue')

        location_uuid = (alyxraw.AlyxRaw.Field & key & 'fname="location"').fetch1('fvalue')
        key['location_name'] = (reference.Location & 'location_uuid="{}"'.format(location_uuid)).fetch1('location_name')
        
        procedure_uuid = (alyxraw.AlyxRaw.Field & key & 'fname="procedures"').fetch1('fvalue')
        key['procedure_name'] = (action.ProcedureType & 'procedure_uuid = "{}"'.format(procedure_uuid)).fetch1('procedure_name')

        self.insert1(key, skip_duplicates=True)

