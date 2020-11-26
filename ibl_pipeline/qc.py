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
    # Available flags to quantify the quality of a session or a specific aspect of a session, lookup table got referred in SessionQC and SessionExtendedQC
    qc          : tinyint unsigned
    ---
    qc_label    : varchar(32)
    """

    contents = [
        (0, 'NOT_SET'),
        (10, 'PASS'),
        (30, 'WARNING'),
        (40, 'FAIL'),
        (50, 'CRITICAL'),
    ]


@schema
class SessionQC(dj.Manual):
    definition = """
    # QCChoice for each session, ingested from alyx field qc in the table actions.session
    -> acquisition.Session
    ---
    -> QCChoice
    sessionqc_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class QCType(dj.Lookup):
    definition = """
    # Aspect of a session for quality check. e.g. task, behavior, experimenter…
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
    #QCChoice (e.g. FAIL) for a QCType (e.g. task) for each session, structured data about SessionQC
    -> acquisition.Session
    -> QCType
    ---
    -> QCChoice.proj(extended_qc='qc')
    session_extended_qc_ts=CURRENT_TIMESTAMP:   timestamp
    """

    class Field(dj.Part):
        definition = """
        # Part table of SessionExtendedQC. For each entry of SessionExtendedQC, there may be multiple fields describing each value (e.g. 0.99) of a qc aspect (e.g. _task_stimOn_delays) that belongs to a QCType (e.g. task).
        -> master
        qc_fname                 : varchar(32)
        ---
        qc_fvalue_float=null     : float
        qc_fvalue_str=null       : varchar(32)
        qc_fvalue_blob=null      : blob
        """
