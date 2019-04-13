import datajoint as dj
from . import reference, subject

schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_action')


@schema
class ProcedureType(dj.Manual):
    definition = """
    procedure_type_name:                varchar(255)
    ---
    procedure_type_uuid:                uuid
    procedure_type_description=null:    varchar(1024)
    """


@schema
class Weighing(dj.Manual):
    # <class 'actions.models.Weighing'>
    definition = """
    -> subject.Subject
    weighing_time:		datetime		# date time
    ---
    weigh_uuid:        uuid
    weight:			    float			# weight
    -> [nullable] reference.LabMember.proj(weighing_user="user_name")
    """


@schema
class WaterType(dj.Lookup):
    definition = """
    watertype_name:     varchar(255)
    ---
    watertype_uuid:     uuid
    """


@schema
class WaterAdministration(dj.Manual):
    # <class 'actions.models.WaterAdministration'>
    definition = """
    -> subject.Subject
    administration_time:	    datetime		# date time
    ---
    wateradmin_uuid:            uuid
    water_administered=null:    float			# water administered
    adlib:                      boolean
    -> WaterType
    -> [nullable] reference.LabMember.proj(administration_user="user_name")
    """


@schema
class WaterRestriction(dj.Manual):
    # <class 'actions.models.WaterRestriction'>
    definition = """
    -> subject.Subject
    restriction_start_time:     datetime	# start time
    ---
    restriction_uuid:           uuid
    restriction_end_time=null:  datetime	# end time
    reference_weight:           float
    restriction_narrative=null: varchar(1024)
    -> [nullable] reference.LabLocation.proj(restriction_lab='lab_name', restriction_location='location_name')
    """


@schema
class WaterRestrictionUser(dj.Manual):
    definition = """
    -> WaterRestriction
    -> reference.LabMember
    """


@schema
class WaterRestrictionProcedure(dj.Manual):
    definition = """
    -> WaterRestriction
    -> ProcedureType
    """


@schema
class Surgery(dj.Manual):
    # <class 'actions.models.Surgery'>
    definition = """
    -> subject.Subject
    surgery_start_time:		datetime        # surgery start time
    ---
    surgery_uuid:           uuid
    surgery_end_time=null:  datetime        # surgery end time
    -> [nullable] reference.LabLocation.proj(surgery_lab='lab_name', surgery_location='location_name')
    surgery_outcome_type:   enum('None', 'a', 'n', 'r')	    # outcome type
    surgery_narrative=null: varchar(2048)	# narrative
    """


@schema
class SurgeryUser(dj.Manual):
    definition = """
    -> Surgery
    -> reference.LabMember
    """


@schema
class SurgeryProcedure(dj.Manual):
    definition = """
    -> Surgery
    -> ProcedureType
    """


@schema
class VirusInjection(dj.Manual):
    # <class 'actions.models.VirusInjection'>
    # XXX: user was m2m field in django
    definition = """
    -> subject.Subject
    injection_time:		    datetime        # injection time
    ---
    injection_uuid:         uuid
    injection_volume:		float   		# injection volume
    rate_of_injection:		float           # rate of injection
    injection_type:		    varchar(255)    # injection type
    """


@schema
class OtherAction(dj.Manual):
    # <class 'actions.models.OtherAction'>
    definition = """
    -> subject.Subject
    other_action_start_time:    datetime	# start time
    ---
    other_action_uuid:          uuid
    other_action_end_time=null: datetime	# end time
    description=null:           varchar(1024)    # description
    -> [nullable] reference.LabLocation.proj(other_action_lab='lab_name', other_action_location='location_name')
    """


@schema
class OtherActionUser(dj.Manual):
    # <class 'actions.models.OtherAction'>
    definition = """
    -> subject.Subject
    other_action_start_time:    datetime	# start time
    ---
    user_name:          varchar(255)
    """


@schema
class OtherActionProcedure(dj.Manual):
    # <class 'actions.models.OtherAction'>
    definition = """
    -> subject.Subject
    other_action_start_time:    datetime	# start time
    ---
    procedure_type_name:        varchar(255)
    """
