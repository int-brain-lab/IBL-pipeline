import datajoint as dj
from . import reference, subject

schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_action')


@schema
class ProcedureType(dj.Manual):
    definition = """
    procedure_type_name:                varchar(255)
    ---
    procedure_type_uuid:                varchar(64)
    procedure_type_description=null:    varchar(1024)
    """


@schema
class Weighing(dj.Manual):
    # <class 'actions.models.Weighing'>
    definition = """
    -> subject.Subject
    weighing_time:		datetime		# date time
    ---
    weigh_uuid:        varchar(64)
    weight:			    float			# weight
    -> [nullable] reference.LabMember
    """


@schema
class WaterType(dj.Computed):
    definition = """
    watertype_name:     varchar(255)
    ---
    watertype_uuid:     varchar(64)
    """


@schema
class WaterAdministration(dj.Manual):
    # <class 'actions.models.WaterAdministration'>
    definition = """
    -> subject.Subject
    administration_time:	datetime		# date time
    ---
    wateradmin_uuid:        varchar(64)
    water_administered:		float			# water administered
    -> WaterType
    -> [nullable] reference.LabMember
    """


@schema
class WaterRestriction(dj.Manual):
    # <class 'actions.models.WaterRestriction'>
    definition = """
    -> subject.Subject
    restriction_start_time:     datetime	# start time
    ---
    restriction_uuid:           varchar(64)
    restriction_end_time=null:  datetime	# end time
    restriction_narrative=null: varchar(1024)
    -> [nullable] ProcedureType
    -> [nullable] reference.LabLocation
    """


@schema
class Surgery(dj.Manual):
    # <class 'actions.models.Surgery'>
    definition = """
    -> subject.Subject
    surgery_start_time:		datetime        # surgery start time
    ---
    surgery_uuid:           varchar(64)
    surgery_end_time=null:  datetime        # surgery end time
    -> [nullable] reference.LabLocation
    surgery_outcome_type:   enum('None', 'a', 'n', 'r')	    # outcome type
    surgery_narrative=null: varchar(2048)	# narrative
    """


@schema
class SurgeryLabMember(dj.Manual):
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
    injection_uuid:         varchar(64)     
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
    other_action_uuid:          varchar(64)
    other_action_end_time:      datetime	# end time
    description:                varchar(255)    # description
    -> reference.LabLocation
    """
