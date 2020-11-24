import datajoint as dj
from . import acquisition
import os


mode = os.environ.get('MODE')
if mode == 'update':
    schema = dj.schema('ibl_qc')
else:
    schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_qc')


@schema
class QCChoice(dj.Lookup):
    definition = """
    qc          : tinyint unsigned
    ---
    qc_label    : varchar(32)
    """

    contents = [
        (0, 'NOT_SET'),
        (10, 'PASS'),
        (20, 'SOMETHING'),
        (30, 'WARNING'),
        (40, 'FAIL'),
        (50, 'CRITICAL'),
    ]


@schema
class SessionQC(dj.Manual):
    definition = """
    -> acquisition.Session
    ---
    -> QCChoice
    sessionqc_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class QCType(dj.Lookup):
    definition = """
    qc_type  : varchar(16)
    ---
    qc_type_description=''  : varchar(1000)
    """

    contents = [
        ['experimenter', 'Manual labeling of a session by user'],
        ['task', 'Quality check when running the task'],
        ['behavior', 'Behavior criteria'],
        ['video', 'Quality check for video recording'],
        ['dlc', '']
    ]


@schema
class SessionExtendedQC(dj.Manual):
    definition = """
    -> acquisition.Session
    -> QCType
    ---
    -> QCChoice.proj(extended_qc='qc')
    session_extended_qc_ts=CURRENT_TIMESTAMP:   timestamp
    """

    class Field(dj.Part):
        definition = """
        -> master
        qc_fname                 : varchar(32)
        ---
        qc_fvalue_float=null     : float
        qc_fvalue_str=null       : varchar(32)
        qc_fvalue_blob=null      : blob
        """
