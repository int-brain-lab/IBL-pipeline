import datajoint as dj
from . import reference, subject
import os

mode = os.environ.get('MODE')

if mode == 'update':
    schema = dj.schema('ibl_action')
else:
    schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_action')


@schema
class ProcedureType(dj.Manual):
    definition = """
    procedure_type_name:                varchar(255)
    ---
    procedure_type_uuid:                uuid
    procedure_type_description=null:    varchar(1024)
    proceduretype_ts=CURRENT_TIMESTAMP: timestamp
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
    surgery_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class SurgeryUser(dj.Manual):
    definition = """
    -> Surgery
    -> reference.LabMember
    ---
    surgeryuser_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class SurgeryProcedure(dj.Manual):
    definition = """
    -> Surgery
    -> ProcedureType
    surgeryprocedure_ts=CURRENT_TIMESTAMP:   timestamp
    """
