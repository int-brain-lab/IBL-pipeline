'''
This script inserts membership tuples into the membership shadow tables, \
which cannot be inserted with auto-population.
'''
import datajoint as dj
import json
import uuid
from ibl_pipeline.ingest import alyxraw, reference, subject, action, acquisition, data
from ibl_pipeline.ingest import get_raw_field as grf
from ibl_pipeline import public


subject_uuids = public.PublicSubjectUuid.fetch('subject_uuid')
subjects = [dict(fname='subject', fvalue=str(uuid))
            for uuid in subject_uuids]

# reference.ProjectLabMember
print('Ingesting reference.ProjectLabMember...')
projects = alyxraw.AlyxRaw & 'model="subjects.project"'
users = alyxraw.AlyxRaw.Field & projects & 'fname="users"' & 'fvalue!="None"'
keys = (alyxraw.AlyxRaw & users).proj(project_uuid='uuid')

for key in keys:
    key_p = dict()
    key_p['project_name'] = (reference.Project & key).fetch1('project_name')

    user_uuids = grf(key, 'users', multiple_entries=True,
                     model='subjects.project')

    if len(user_uuids):
        for user_uuid in user_uuids:
            if user_uuid == 'None':
                continue
            key_pl = key_p.copy()
            key_pl['user_name'] = \
                (reference.LabMember &
                    dict(user_uuid=uuid.UUID(user_uuid))).fetch1(
                        'user_name')

            reference.ProjectLabMember.insert1(key_pl, skip_duplicates=True)

# subject.AlleleSequence
print('Ingesting subject.AlleleSequence...')
keys = (alyxraw.AlyxRaw & 'model="subjects.allele"').proj(allele_uuid='uuid')
for key in keys:
    key_a = dict()
    key_a['allele_name'] = (subject.Allele & key).fetch1('allele_name')
    key['uuid'] = key['allele_uuid']
    sequences = grf(key, 'sequences', multiple_entries=True,
                    model="subjects.allele")

    for sequence in sequences:
        if sequence != 'None':
            key_as = key_a.copy()
            key_as['sequence_name'] = \
                (subject.Sequence &
                    dict(sequence_uuid=uuid.UUID(sequence))).fetch1(
                        'sequence_name')
            subject.AlleleSequence.insert1(key_as, skip_duplicates=True)

# subject.LineAllele
print('Ingesting subject.LineAllele...')
keys = (alyxraw.AlyxRaw & 'model="subjects.line"').proj(line_uuid='uuid')
for key in keys:
    key_l = dict()
    key_l['line_name'] = (subject.Line & key).fetch1('line_name')
    key['uuid'] = key['line_uuid']
    alleles = grf(key, 'alleles', multiple_entries=True, model='subjects.line')

    for allele in alleles:
        if allele != 'None':
            key_la = key_l.copy()
            key_la['allele_name'] = \
                (subject.Allele &
                    dict(allele_uuid=uuid.UUID(allele))).fetch1('allele_name')
            subject.LineAllele.insert1(key_la, skip_duplicates=True)


# action.SurgeryUser
print('Ingesting action.SurgeryUser...')
surgeries = alyxraw.AlyxRaw & 'model = "actions.surgery"'
surgeries_with_users = alyxraw.AlyxRaw.Field & surgeries & \
    'fname="users"' & 'fvalue!="None"'
keys = (surgeries & surgeries_with_users & restr_subjects).proj(
    surgery_uuid='uuid')

for key in keys:
    key['uuid'] = key['surgery_uuid']
    if not len(action.Surgery & key):
        print('Surgery {} not in the table action.Surgery'.format(
            key['surgery_uuid']))
        continue

    key_s = dict()
    key_s['subject_uuid'], key_s['surgery_start_time'] = \
        (action.Surgery & key).fetch1(
            'subject_uuid', 'surgery_start_time')

    users = grf(key, 'users', multiple_entries=True)

    for user in users:
        key_su = key_s.copy()
        key_su['user_name'] = \
            (reference.LabMember &
             dict(user_uuid=uuid.UUID(user))).fetch1('user_name')
        action.SurgeryUser.insert1(key_su, skip_duplicates=True)


# action.SurgeryProcedure
print('Ingesting action.SurgeryProcedure...')
surgeries = alyxraw.AlyxRaw & 'model = "actions.surgery"'
surgeries_with_procedures = alyxraw.AlyxRaw.Field & surgeries & \
    'fname="procedures"' & 'fvalue!="None"'

keys = (surgeries & surgeries_with_procedures & restr_subjects).proj(
    surgery_uuid='uuid')

for key in keys:
    key_s = dict()
    key['uuid'] = key['surgery_uuid']
    if not len(action.Surgery & key):
        print('Surgery {} not in the table action.Surgery'.format(
            key['suggery_uuid']))
        continue

    key_s = dict()
    key_s['subject_uuid'], key_s['surgery_start_time'] = \
        (action.Surgery & key).fetch1(
            'subject_uuid', 'surgery_start_time')
    procedures = grf(key, 'procedures', multiple_entries=True)

    for procedure in procedures:
        key_sp = key_s.copy()
        key_sp['procedure_type_name'] = \
            (action.ProcedureType &
             dict(procedure_type_uuid=uuid.UUID(procedure))).fetch1(
                 'procedure_type_name')
        action.SurgeryProcedure.insert1(key_sp, skip_duplicates=True)


# acquisition.ChildSession
print('Ingesting acquisition.ChildSession...')

# get session restrictor
sessions_list = []
for subj_uuid, subj in zip(subject_uuids, subjects):

    session_start, session_end = (
        public.PublicSubject &
        (public.PublicSubjectUuid & {'subject_uuid': subj_uuid})).fetch1(
        'session_start_date', 'session_end_date')
    session_start = session_start.strftime('%Y-%m-%d')
    session_end = session_end.strftime('%Y-%m-%d')
    session_uuids = (alyxraw.AlyxRaw &
                     {'model': 'actions.session'} &
                     (alyxraw.AlyxRaw.Field & subj) &
                     (alyxraw.AlyxRaw.Field &
                      'fname="start_time"' &
                      'fvalue between "{}" and "{}"'.format(
                        session_start, session_end))).fetch(
                            'uuid')
    sessions_list += [dict(uuid=uuid) for uuid in session_uuids]

sessions = alyxraw.AlyxRaw & 'model="actions.session"' & sessions_list
sessions_with_parents = alyxraw.AlyxRaw.Field & sessions & \
    'fname="parent_session"' & 'fvalue!="None"'

keys = (alyxraw.AlyxRaw & sessions_with_parents).proj(
    session_uuid='uuid')
for key in keys:
    key['uuid'] = key['session_uuid']
    if not len(acquisition.Session & key):
        print('Session {} is not in the table acquisition.Session'.format(
            key['session_uuid']))
        continue
    key_cs = dict()
    key_cs['subject_uuid'], key_cs['session_start_time'] = \
        (acquisition.Session & key).fetch1(
            'subject_uuid', 'session_start_time')
    parent_session = grf(key, 'parent_session')
    if not len(acquisition.Session &
               dict(session_uuid=uuid.UUID(parent_session))):
        print('Parent session {} is not in \
            the table acquisition.Session'.format(
            parent_session))
        continue
    key_cs['parent_session_start_time'] = \
        (acquisition.Session &
            dict(session_uuid=uuid.UUID(parent_session))).fetch1(
                'session_start_time')
    acquisition.ChildSession.insert1(key_cs, skip_duplicates=True)


# acquisition.SessionUser
print('Ingesting acquisition.SessionUser...')
sessions_with_users = alyxraw.AlyxRaw.Field & sessions_list & \
    'fname="users"' & 'fvalue!="None"'
keys = (alyxraw.AlyxRaw & sessions_with_users).proj(
    session_uuid='uuid')

for key in keys:

    key['uuid'] = key['session_uuid']

    if not len(acquisition.Session & key):
        print('Session {} is not in the table acquisition.Session'.format(
            key['session_uuid']))
        continue

    key_s = dict()
    key_s['subject_uuid'], key_s['session_start_time'] = \
        (acquisition.Session & key).fetch1(
            'subject_uuid', 'session_start_time')

    users = grf(key, 'users', multiple_entries=True)

    for user in users:
        key_su = key_s.copy()
        key_su['user_name'] = \
            (reference.LabMember & dict(user_uuid=uuid.UUID(user))).fetch1(
                'user_name')
        acquisition.SessionUser.insert1(key_su, skip_duplicates=True)


# acquisition.SessionProcedure
print('Ingesting acquisition.SessionProcedure...')
sessions_with_procedures = alyxraw.AlyxRaw.Field & sessions_list & \
    'fname="procedures"' & 'fvalue!="None"'
keys = (alyxraw.AlyxRaw & sessions_with_procedures).proj(
    session_uuid='uuid')

for key in keys:
    key['uuid'] = key['session_uuid']
    if not len(acquisition.Session & key):
        print('Session {} is not in the table acquisition.Session'.format(
            key['session_uuid']))
        continue
    key_s = dict()
    key_s['subject_uuid'], key_s['session_start_time'] = \
        (acquisition.Session & key).fetch1(
            'subject_uuid', 'session_start_time')

    procedures = grf(key, 'procedures', multiple_entries=True)

    for procedure in procedures:
        key_sp = key_s.copy()
        key_sp['procedure_type_name'] = \
            (action.ProcedureType &
             dict(procedure_type_uuid=uuid.UUID(procedure))).fetch1(
                 'procedure_type_name')
        acquisition.SessionProcedure.insert1(key_sp, skip_duplicates=True)


# acquisition.SessionProject
print('Ingesting acquisition.SessionProject...')
sessions_with_procedures = alyxraw.AlyxRaw.Field & sessions_list & \
    'fname="project"' & 'fvalue!="None"'
keys = (alyxraw.AlyxRaw & sessions_with_procedures).proj(
    session_uuid='uuid')

for key in keys:
    key['uuid'] = key['session_uuid']
    if not len(acquisition.Session & key):
        print('Session {} is not in the table acquisition.Session'.format(
            key['session_uuid']))
        continue
    key_s = dict()
    key_s['subject_uuid'], key_s['session_start_time'] = \
        (acquisition.Session & key).fetch1(
            'subject_uuid', 'session_start_time')

    project = grf(key, 'project')

    key_sp = key_s.copy()
    key_sp['session_project'] = \
        (reference.Project &
         dict(project_uuid=uuid.UUID(project))).fetch1(
        'project_name')

    acquisition.SessionProject.insert1(key_sp, skip_duplicates=True)
