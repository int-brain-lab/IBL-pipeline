import datajoint as dj
import json

from . import alyxraw, reference, subject, action, acquisition
from .. import acquisition as acquisition_real
from .. import qc
from . import get_raw_field as grf

schema = dj.schema(dj.config.get('database.prefix', '') +
                   'ibl_ingest_qc')


@schema
class SessionQC(dj.Manual):
    definition = """
    subject_uuid        : uuid
    session_start_time  : datetime
    ---
    qc                  : tinyint unsigned
    sessionqc_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class SessionExtendedQC(dj.Manual):
    definition = """
    subject_uuid             : uuid
    session_start_time       : datetime
    qc_type                  : varchar(16)
    ---
    extended_qc              : tinyint unsigned
    session_extended_qc_ts=CURRENT_TIMESTAMP:   timestamp
    """

    class Field(dj.Part):
        definition = """
        -> master
        qc_fname               : varchar(32)
        ---
        qc_fvalue_float=null   : float
        qc_fvalue_str=null     : varchar(32)
        qc_fvalue_blob=null    : blob
        """


qc_types = qc.QCType.fetch('qc_type')
qc_choices = qc.QCChoice.fetch(format='frame')


@schema
class SessionQCIngest(dj.Computed):
    definition = """
    -> alyxraw.AlyxRaw.proj(session_uuid='uuid')
    """
    key_source = dj.U('session_uuid') & \
        (alyxraw.AlyxRaw.Field &
         (alyxraw.AlyxRaw & 'model="actions.session"') &
         'fname="qc"' &
         'fvalue in ("10", "30", "40", "50")').proj(session_uuid='uuid')

    def make(self, key):

        self.insert1(key)

        key['uuid'] = key['session_uuid']
        qc = grf(key, 'qc')
        qc_extended = grf(key, 'extended_qc')

        try:
            qc_extended = json.loads(qc_extended)
        except json.decoder.JSONDecodeError:
            qc_extended = qc_extended.replace("\'", "\"")
            qc_extended = qc_extended.replace('None', "\"None\"")
            qc_extended = json.loads(qc_extended)

        if len(acquisition.Session & key) == 1:
            session_key = (acquisition_real.Session & key).fetch1('KEY')
        else:
            session_key = (acquisition.Session & key).fetch1('KEY')

        SessionQC.insert1(
            dict(**session_key, qc=int(qc))
        )

        for qc_type in qc_types:
            try:
                session_qc_type = qc_extended[qc_type]
                qc_choice = qc_choices[
                    qc_choices['qc_label'] == session_qc_type].index[0]
                SessionExtendedQC.insert1(
                    dict(**session_key,
                         qc_type=qc_type,
                         extended_qc=qc_choice)
                )
                for k, v in qc_extended.items():
                    if f'_{qc_type}' in k:
                        qc_field = dict(
                            **session_key,
                            qc_type=qc_type,
                            qc_fname=k)
                        if type(v) == float:
                            SessionExtendedQC.Field.insert1(
                                dict(**qc_field,
                                     qc_fvalue_float=v))
                        elif v == "None":
                            pass
                        elif type(v) == str:
                            SessionExtendedQC.Field.insert1(
                                dict(**qc_field,
                                     qc_fvalue_varchar=v))
                        else:
                            SessionExtendedQC.Field.insert1(
                                dict(**qc_field,
                                     qc_fvalue_blob=v))
            except Exception:
                pass
