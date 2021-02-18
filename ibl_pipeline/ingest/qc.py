import datajoint as dj
import json

from . import alyxraw, reference, subject, action, acquisition, ephys
from .. import acquisition as acquisition_real
from .. import ephys as ephys_real
from .. import qc
from . import get_raw_field as grf
from tqdm import tqdm

schema = dj.schema(dj.config.get('database.prefix', '') +
                   'ibl_ingest_qc')

json_replace_map = {
    "\'": "\"",
    'None': '\"None\"',
    'True': 'true',
    'False': 'false'
}


# This function automatically get qc types from alyx
def get_extended_qc_fields_from_alyx(level='session'):
    if level == 'session':
        key_source = dj.U('uuid') & \
            (alyxraw.AlyxRaw.Field &
             (alyxraw.AlyxRaw & 'model="actions.session"') &
             'fname="extended_qc"' &
             'fvalue!="None"')

        fname = 'extended_qc'

    elif level == 'probe':

        key_source = dj.U('uuid') & \
            (alyxraw.AlyxRaw.Field &
             (alyxraw.AlyxRaw & 'model="experiments.probeinsertion"') &
             'fname="json"' &
             'fvalue like "%extended_qc%"')
        fname = 'json'
    else:
        raise ValueError('Incorrect level argument, has to be "session" or "probe"')

    eqc_fields = []

    for key in tqdm(key_source):
        qc_extended = grf(key, fname)

        try:
            qc_extended = json.loads(qc_extended)
        except json.decoder.JSONDecodeError:
            for k, v in json_replace_map.items():
                qc_extended = qc_extended.replace(k, v)
            qc_extended = json.loads(qc_extended)

        if qc_extended != 'None':
            if level == 'probe' and 'extended_qc' in qc_extended:
                qc_extended = qc_extended['extended_qc']

            eqc_fields += list(qc_extended.keys())

    return set(eqc_fields)


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
    subject_uuid        : uuid
    session_start_time  : datetime
    ---
    session_qc                  : tinyint unsigned
    session_qc_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class SessionExtendedQC(dj.Manual):
    definition = """
    subject_uuid             : uuid
    session_start_time       : datetime
    qc_type                  : varchar(16)
    ---
    session_extended_qc              : tinyint unsigned
    session_extended_qc_ts=CURRENT_TIMESTAMP:   timestamp
    """

    class Field(dj.Part):
        definition = """
        -> master
        session_qc_fname               : varchar(32)
        ---
        session_qc_fvalue_bool=null    : bool
        session_qc_fvalue_float=null   : float
        session_qc_fvalue_str=null     : varchar(32)
        session_qc_fvalue_blob=null    : blob
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
            dict(**session_key, session_qc=int(qc))
        )

        for qc_type in qc_types:
            if qc_type in qc_extended:
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
                            qc_fvalue_name = 'session_qc_fvalue_float'
                        elif v == "None":
                            pass
                        elif type(v) == str:
                            qc_fvalue_name = 'session_qc_fvalue_varchar'
                        else:
                            qc_fvalue_name = 'session_qc_fvalue_blob'

                        SessionExtendedQC.Field.insert1(
                                {**qc_field,
                                 qc_fvalue_name: v})


@schema
class ProbeInsertionQC(dj.Manual):
    definition = """
    subject_uuid         : uuid
    session_start_time   : datetime
    probe_idx            : int
    ---
    insertion_qc         : tinyint
    """


@schema
class ProbeInsertionExtendedQC(dj.Manual):
    definition = """
    subject_uuid         : uuid
    session_start_time   : datetime
    probe_idx            : int
    qc_type              : varchar(16)
    ---
    insertion_extended_qc : tinyint
    insertion_extended_qc_ts=CURRENT_TIMESTAMP:   timestamp
    """

    class Field(dj.Part):
        definition = """
        insertion_qc_fname   : varchar(64)
        ---
        insertion_qc_fvalue_float=null     : float
        insertion_qc_fvalue_bool=null      : bool
        insertion_qc_fvalue_str=null       : varchar(32)
        insertion_qc_fvalue_blob=null      : blob
        """


@schema
class ProbeInsertionQCIngest(dj.Computed):
    definition = """
    -> alyxraw.AlyxRaw.proj(probe_insertion_uuid='uuid')
    """
    key_source = dj.U('probe_insertion_uuid') & \
        (alyxraw.AlyxRaw.Field &
         (alyxraw.AlyxRaw & 'model="experiments.probeinsertion"') &
         'fname="json"' &
         'fvalue like "%qc%"').proj(probe_insertion_uuid='uuid')

    def make(self, key):

        self.insert1(key)

        key['uuid'] = key['probe_insertion_uuid']
        json_field = grf(key, 'json')

        try:
            json_field = json.loads(json_field)
        except json.decoder.JSONDecodeError:
            # fix the json field before decording.
            for k, v in json_replace_map.items():
                json_field = json_field.replace(k, v)
            json_field = json.loads(json_field)

        if len(ephys_real.ProbeInsertion & key) == 1:
            probe_insertion_key = (ephys_real.ProbeInsertion & key).fetch1('KEY')
        else:
            probe_insertion_key = (ephys.ProbeInsertion & key).fetch1('KEY')

        if 'qc' in json_field:
            qc = (QCChoice & {'qc_label': json_field['qc']}).fetch1('qc')

            ProbeInsertionQC.insert1(
                dict(**probe_insertion_key, insertion_qc=qc))

        if 'extended_qc' in json_field:
            extended_qc = json_field['extended_qc']

            for qc_type in qc_types:

                for k, v in json_field['extended_qc'].items():
                    if type(v) == float:
                        qc_fvalue_name = 'insertion_qc_fvalue_float'
                    elif v == "None":
                        pass
                    elif type(v) == str:
                        qc_fvalue_name = 'insertion_qc_fvalue_str'
                    else:
                        qc_fvalue_name = 'insertion_qc_fvalue_blob'

                    ProbeInsertionExtendedQC.insert1(
                        {**probe_insertion_key,
                         'insertion_qc_fname': k,
                         qc_fvalue_name: v})
