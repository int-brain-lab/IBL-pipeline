import datajoint as dj

from ibl_pipeline import mode

if mode == "update":
    schema = dj.schema("ibl_action")
else:
    schema = dj.schema(dj.config.get("database.prefix", "") + "ibl_action")


@schema
class ProcedureType(dj.Manual):
    definition = """
    procedure_type_name:                varchar(255)
    ---
    procedure_type_uuid:                uuid
    procedure_type_description=null:    varchar(1024)
    proceduretype_ts=CURRENT_TIMESTAMP: timestamp
    """
