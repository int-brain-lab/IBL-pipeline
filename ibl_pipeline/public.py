import datajoint as dj
import pandas as pd
import datetime
import re
from uuid import UUID

from ibl_pipeline.ingest import alyxraw

schema = dj.schema('ibl_public')
dj.config['safemode'] = False


@schema
class UserMap(dj.Lookup):
    definition = """
    # a lookup table between the real user name and the pseudo_name
    user_name:      varchar(64)
    ---
    pseudo_name:    varchar(64)
    """


@schema
class PublicSubject(dj.Manual):
    definition = """
    lab_name            : varchar(32)
    subject_nickname    : varchar(32)
    ---
    session_start_date  : date
    session_end_date    : date
    """


@schema
class PublicSubjectUuid(dj.Computed):
    definition = """
    -> PublicSubject
    ---
    subject_uuid    : uuid
    """

    def make(self, key):

        subject = (alyxraw.AlyxRaw & 'model="subjects.subject"') & \
                  (alyxraw.AlyxRaw.Field & 'fname="nickname"' &
                   'fvalue="{}"'.format(key['subject_nickname']))

        self.insert1(dict(**key, subject_uuid=subject.fetch1('uuid')))


PublicSubject.delete()

subject_lists = pd.read_csv('/data/list_of_subjects.csv')

lab_mapping = {
    'Angelaki': 'angelakilab',
    'Witten': 'wittenlab',
    'Mainen': 'mainenlab',
    'Dan': 'danlab',
    'Mrsic-Flogel': 'mrsicflogellab',
    'Cortexlab': 'cortexlab',
    'Churchland': 'churchlandlab',
    'Zador': 'zadorlab'
}
subjs = []
for i, subject in subject_lists.dropna().iterrows():

    subj = dict(lab_name=lab_mapping[subject['Lab'].replace(' ', '')],
                subject_nickname=subject['Mouse ID'])

    if 'until' in subject['Sessions']:
        text = re.search('til (\d+)/(\d+)/(\d+)', subject['Sessions'])
        year, month, date = text.group(3), text.group(2), text.group(1)

        if len(year) == 2:
            year = '20' + year
        subj.update(session_start_date=datetime.date(2018, 6, 1),
                    session_end_date=datetime.date(int(year),
                                                   int(month),
                                                   int(date)))

    elif '-' in subject['Sessions']:
        text = re.search('(\d+)/(\d+)/(\d+).* (\d+)/(\d+)/(\d+)',
                         '22/05/2019- 15/07/2019 (includes a break)')
        year1, month1, date1, year2, month2, date2 = \
            text.group(3), text.group(2), text.group(1), \
            text.group(6), text.group(5), text.group(4)
        if len(year1) == 2:
            year1 = '20' + year1
        if len(year2) == 2:
            year2 = '20' + year2
        subj.update(session_start_date=datetime.date(int(year1), int(month1), int(date1)),
                    session_end_date=datetime.date(int(year2), int(month2), int(date2)))
    else:
        subj.update(session_start_date=datetime.date(2018, 6, 1),
                    session_end_date=datetime.datetime.now().date())
    subjs.append(subj)

PublicSubject.insert(subjs, skip_duplicates=True)
PublicSubjectUuid.populate(display_progress=True)
