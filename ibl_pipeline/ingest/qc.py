import json

import datajoint as dj
from tqdm import tqdm

from ibl_pipeline import acquisition as acquisition_real
from ibl_pipeline import ephys as ephys_real
from ibl_pipeline import qc as qc_real
from ibl_pipeline.ingest import acquisition, action, alyxraw, ephys
from ibl_pipeline.ingest import get_raw_field as grf
from ibl_pipeline.ingest import reference, subject
from ibl_pipeline.utils import str_to_dict

schema = dj.schema(dj.config["database.prefix"] + "ibl_ingest_qc")


# This function automatically get qc types from alyx
def get_extended_qc_fields_from_alyx(level="session"):
    if level == "session":
        key_source = dj.U("uuid") & (
            alyxraw.AlyxRaw.Field
            & (alyxraw.AlyxRaw & 'model="actions.session"')
            & 'fname="extended_qc"'
            & 'fvalue!="None"'
        )

        fname = "extended_qc"

    elif level == "probe":

        key_source = dj.U("uuid") & (
            alyxraw.AlyxRaw.Field
            & (alyxraw.AlyxRaw & 'model="experiments.probeinsertion"')
            & 'fname="json"'
            & 'fvalue like "%extended_qc%"'
        )
        fname = "json"
    else:
        raise ValueError('Incorrect level argument, has to be "session" or "probe"')

    eqc_fields = []

    for key in tqdm(key_source):
        qc_extended = str_to_dict(grf(key, fname))

        if qc_extended != "None":
            if level == "probe" and "extended_qc" in qc_extended:
                qc_extended = qc_extended["extended_qc"]

            eqc_fields += list(qc_extended.keys())

    return set(eqc_fields)


qc_choices = qc_real.QCChoice.fetch(format="frame")


@schema
class SessionQCIngest(dj.Computed):
    definition = """
    -> alyxraw.AlyxRaw.proj(session_uuid='uuid')
    """

    key_source = dj.U("session_uuid") & (
        alyxraw.AlyxRaw.Field
        & (alyxraw.AlyxRaw & 'model="actions.session"')
        & 'fname="qc"'
        & 'fvalue in ("10", "30", "40", "50")'
    ).proj(session_uuid="uuid")

    def make(self, key):
        """
        For a SessionQC-related entry in alyxraw.AlyxRaw, fetch and insert into the real tables:
        + SessionQC
        + SessionExtendedQC
        + SessionExtendedQC.Field
        """

        self.insert1(key)

        key["uuid"] = key["session_uuid"]
        qc_alyx = grf(key, "qc")
        qc_extended_alyx = str_to_dict(grf(key, "extended_qc"))

        if len(acquisition_real.Session & key) == 1:
            session_key = (acquisition_real.Session & key).fetch1("KEY")
        else:
            return

        qc_real.SessionQC.insert1(
            dict(**session_key, session_qc=int(qc_alyx)), skip_duplicates=True
        )
        qc_types = (qc_real.QCType & 'qc_level="session"').fetch("qc_type")

        # loop through all qc types on the session level and check whether it's in the current entry
        for qc_type in qc_types:
            if qc_type in qc_extended_alyx:

                # get the entry for SessionExtendedQC
                extended_qc_label = qc_extended_alyx[qc_type]

                # for behavior, the field is 0 for "NOT SET", 1 for PASS
                if extended_qc_label == 0:
                    continue
                elif extended_qc_label == 1 and qc_type == "behavior":
                    extended_qc = 10
                else:
                    extended_qc = qc_choices[
                        qc_choices["qc_label"] == extended_qc_label
                    ].index[0]
                qc_real.SessionExtendedQC.insert1(
                    dict(
                        **session_key, qc_type=qc_type, session_extended_qc=extended_qc
                    ),
                    skip_duplicates=True,
                )

                # get the entries for the part table SessionExtendedQC.Field
                for k, v in qc_extended_alyx.items():
                    # for the session qc field, it has the format of '_{qc_type}', e.g. '_task_trial_length'
                    if f"_{qc_type}" in k:
                        qc_field = dict(
                            **session_key, qc_type=qc_type, session_qc_fname=k
                        )
                        if type(v) == float:
                            qc_fvalue_name = "session_qc_fvalue_float"
                        elif v == "None":
                            continue
                        elif type(v) == str:
                            qc_fvalue_name = "session_qc_fvalue_varchar"
                        else:
                            qc_fvalue_name = "session_qc_fvalue_blob"

                        qc_real.SessionExtendedQC.Field.insert1(
                            {**qc_field, qc_fvalue_name: v}, skip_duplicates=True
                        )


@schema
class ProbeInsertionQCIngest(dj.Computed):
    definition = """
    -> alyxraw.AlyxRaw.proj(probe_insertion_uuid='uuid')
    ---
    subject_uuid        : uuid
    session_start_time  : datetime
    probe_idx           : tinyint
    """

    key_source = dj.U("probe_insertion_uuid") & (
        alyxraw.AlyxRaw.Field
        & (alyxraw.AlyxRaw & 'model="experiments.probeinsertion"')
        & 'fname="json"'
        & 'fvalue like "%qc%"'
    ).proj(probe_insertion_uuid="uuid")

    def make(self, key):
        """
        For a ProbeInsertionQC-related entry in alyxraw.AlyxRaw, fetch and insert into the real tables:
        + ProbeInsertionQC
        + ProbeInsertionExtendedQC
        + ProbeInsertionExtendedQC.Field
        """

        key["uuid"] = key["probe_insertion_uuid"]
        json_field = str_to_dict(grf(key, "json"))

        if len(ephys_real.ProbeInsertion & key) == 1:
            probe_insertion_key = (ephys_real.ProbeInsertion & key).fetch1("KEY")
        else:
            return

        if "qc" in json_field:
            qc = (qc_real.QCChoice & {"qc_label": json_field["qc"]}).fetch1("qc")
            # skip ingestion if qc is "NOT SET"
            # turn on skip_duplicates because there are chances to delete this table and reingest everything
            if qc != 0:
                qc_real.ProbeInsertionQC.insert1(
                    dict(**probe_insertion_key, insertion_qc=qc), skip_duplicates=True
                )

        qc_types = (qc_real.QCType & 'qc_level="probe_insertion"').fetch("qc_type")

        # example extended_qc field in alyx:
        # "extended_qc": {
        #     "experimenter": "PASS",
        #     "tracing_exists": true,
        #     "alignment_count": 1,
        #     "alignment_stored": "2020-09-28T12:00:12_guido",
        #     "alignment_resolved": false
        # }

        if "extended_qc" in json_field:
            extended_qc_alyx = json_field["extended_qc"]

            for qc_type in qc_types:

                if qc_type in extended_qc_alyx:
                    # Only ingest when tracing tracing exists
                    if qc_type == "tracing_exists" and extended_qc_alyx[qc_type]:
                        # if tracing exists, then set insertion_extended_qc to 10 (PASS)
                        qc_real.ProbeInsertionExtendedQC.insert1(
                            dict(
                                **probe_insertion_key,
                                qc_type=qc_type,
                                insertion_extended_qc=10,
                            ),
                            skip_duplicates=True,
                        )
                    # Only ingest when alignment is resolved
                    if qc_type == "alignment_resolved" and extended_qc_alyx[qc_type]:

                        # only ingest into current table if alignment is resolved
                        self.insert1(
                            dict(
                                **probe_insertion_key, probe_insertion_uuid=key["uuid"]
                            )
                        )
                        qc_real.ProbeInsertionExtendedQC.insert1(
                            dict(
                                **probe_insertion_key,
                                qc_type=qc_type,
                                insertion_extended_qc=10,
                            ),
                            skip_duplicates=True,
                        )

                        # check for alignment field
                        for k, v in json_field["extended_qc"].items():
                            if "alignment" in k and k != "alignment_resolved":
                                if type(v) == float:
                                    qc_fvalue_name = "insertion_qc_fvalue_float"
                                elif v == "None":
                                    pass
                                elif type(v) == str:
                                    qc_fvalue_name = "insertion_qc_fvalue_str"
                                else:
                                    qc_fvalue_name = "insertion_qc_fvalue_blob"

                                qc_real.ProbeInsertionExtendedQC.Field.insert1(
                                    {
                                        **probe_insertion_key,
                                        "qc_type": qc_type,
                                        "insertion_qc_fname": k,
                                        qc_fvalue_name: v,
                                    },
                                    skip_duplicates=True,
                                )
