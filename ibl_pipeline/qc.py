import datajoint as dj
from . import acquisition, ephys
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
class QCType(dj.Lookup):
    definition = """
    # Aspect of a session for quality check. e.g. task, behavior, experimenter…
    qc_type  : varchar(16)
    ---
    qc_
    qc_type_description=''  : varchar(1000)
    """

    # contents = [
    #     ['experimenter', 'Manual labeling of a session by user'],
    #     ['task', 'Quality check when running the task'],
    #     ['behavior', 'Behavior criteria'],
    #     ['videoBody', 'Quality check for video recording of body camera'],
    #     ['videoLeft', 'Quality check for video recording of left camera'],
    #     ['videoRight', 'Quality check for video recording of right camera'],
    #     ['dlc', 'Deep lab cut on behavioral video data'],
    #     ['tracing_exists', 'Histology tracing'],
    #     ['alignment_resolved', 'Ephys alignment with histology']
    # ]


@schema
class SessionQC(dj.Manual):
    definition = """
    # QCChoice for each session, ingested from alyx field qc in the table actions.session
    -> acquisition.Session
    ---
    -> QCChoice.proj(session_qc='qc')
    sessionqc_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class SessionExtendedQC(dj.Manual):
    definition = """
    #QCChoice (e.g. FAIL) for a QCType (e.g. task) for each session, structured data about SessionQC
    -> acquisition.Session
    -> QCType
    ---
    -> QCChoice.proj(session_extended_qc='qc')
    session_extended_qc_ts=CURRENT_TIMESTAMP:   timestamp
    """

    class Field(dj.Part):
        definition = """
        # Part table of SessionExtendedQC. For each entry of SessionExtendedQC, there may be multiple fields describing each value (e.g. 0.99) of a qc aspect (e.g. _task_stimOn_delays) that belongs to a QCType (e.g. task).
        -> master
        session_qc_fname                 : varchar(32)
        ---
        session_qc_fvalue_bool=null      : bool
        session_qc_fvalue_float=null     : float
        session_qc_fvalue_str=null       : varchar(32)
        session_qc_fvalue_blob=null      : blob
        """


@schema
class ProbeInsertionQC(dj.Manual):
    definition = """
    -> ephys.ProbeInsertion
    ---
    -> QCChoice.proj(insertion_qc='qc')
    """


@schema
class ProbeInsertionExtendedQC(dj.Manual):
    definition = """
    -> ephys.ProbeInsertion
    -> QCType
    ---
    -> QCChoice.proj(insertion_extended_qc='qc')
    insertion_extended_qc_ts=CURRENT_TIMESTAMP:   timestamp
    """

    class Field(dj.Part):
        definition = """
        # Part table of SessionExtendedQC. For each entry of ProbeInsertionExtendedQC.
        -> master
        insertion_qc_fname                 : varchar(32)
        ---
        insertion_qc_fvalue_bool=null      : tinyint
        insertion_qc_fvalue_float=null     : float
        insertion_qc_fvalue_str=null       : varchar(32)
        insertion_qc_fvalue_blob=null      : blob
        """
