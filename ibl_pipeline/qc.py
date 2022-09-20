import datajoint as dj

from ibl_pipeline import acquisition, ephys, mode, one
from ibl_pipeline.utils import str_to_dict

if mode == "update":
    schema = dj.schema("ibl_qc")
else:
    schema = dj.schema(dj.config["database.prefix"] + "ibl_qc")

if mode != "public":
    qc_ingest = dj.create_virtual_module("qc_ingest", "ibl_ingest_qc")
    alyxraw = dj.create_virtual_module("alyxraw", "ibl_alyxraw")


@schema
class QCChoice(dj.Lookup):
    definition = """
    # Available flags to quantify the quality of a session or a specific aspect of a session, lookup table got referred in SessionQC and SessionExtendedQC
    qc          : tinyint unsigned
    ---
    qc_label    : varchar(32)
    """

    contents = [
        (0, "NOT_SET"),
        (10, "PASS"),
        (30, "WARNING"),
        (40, "FAIL"),
        (50, "CRITICAL"),
    ]


@schema
class QCLevel(dj.Lookup):
    definition = """
    qc_level : varchar(32)
    """
    contents = zip(["session", "probe_insertion"])


@schema
class QCType(dj.Lookup):
    definition = """
    # Aspect of a session for quality check. e.g. task, behavior, experimenter…
    qc_type  : varchar(32)
    ---
    -> QCLevel
    qc_type_description=''  : varchar(1000)
    """

    contents = [
        ["experimenter", "session", "Manual labeling of a session by user"],
        ["task", "session", "Quality check when running the task"],
        ["behavior", "session", "Behavior criteria"],
        ["videoBody", "session", "Quality check for video recording of body camera"],
        ["videoLeft", "session", "Quality check for video recording of left camera"],
        ["videoRight", "session", "Quality check for video recording of right camera"],
        ["dlc", "session", "Deep lab cut processing on behavioral video data"],
        ["tracing_exists", "probe_insertion", "Histology tracing"],
        ["alignment_resolved", "probe_insertion", "Ephys alignment with histology"],
    ]


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
        session_qc_fname                 : varchar(64)
        ---
        session_qc_fvalue_bool=null      : bool
        session_qc_fvalue_float=null     : float
        session_qc_fvalue_str=null       : varchar(64)
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
        insertion_qc_fname                 : varchar(64)
        ---
        insertion_qc_fvalue_bool=null      : tinyint
        insertion_qc_fvalue_float=null     : float
        insertion_qc_fvalue_str=null       : varchar(64)
        insertion_qc_fvalue_blob=null      : blob
        """

    @classmethod
    def validate_resolved(cls, deep=False):
        """Compare the datasets in datajoint with datasets in alyx

        Args:
            deep (bool, optional): Check the dependent tables to figure out the problem. Defaults to False.

        Returns:
            (list): list of either the problematic key (deep=False) or problematic key with the debugging message.
        """
        resolved = one.alyx.rest(
            "insertions", "list", django="json__extended_qc__alignment_resolved,True"
        )

        uuids_alyx = [r["id"] for r in resolved]
        uuids = (ephys.ProbeInsertion & (cls & 'qc_type="alignment_resolved"')).fetch(
            "probe_insertion_uuid"
        )
        uuids_dj = [str(uuid) for uuid in uuids]

        missing_uuids = list(set(uuids_alyx) - set(uuids_dj))

        if deep:
            messages = []
            for uuid in missing_uuids:
                if not (alyxraw.AlyxRaw.Field & {"uuid": uuid} & 'fname="json"'):
                    msg = "No json entry in alyxraw"
                else:
                    json = str_to_dict(
                        (
                            alyxraw.AlyxRaw.Field & {"uuid": uuid} & 'fname="json"'
                        ).fetch1("fvalue")
                    )
                    if (
                        "extended_qc" in json
                        and "alignment_resolved" in json["extended_qc"]
                        and json["extended_qc"]["alignment_resolved"]
                    ):

                        if ephys.ProbeInsertion & {"probe_insertion_uuid": uuid}:
                            if qc_ingest.ProbeInsertionQCIngest & {
                                "probe_insertion_uuid": uuid
                            }:
                                msg = "Entries exist in both ProbeInsertion and ProbeInsertionQCIngest"
                            else:
                                msg = "Probe ingest did not run or alyx dump outdated."
                        else:
                            msg = "Missing entry in ephys.ProbeInsertion."
                messages.append((uuid, msg))
            return messages
        else:
            return missing_uuids
