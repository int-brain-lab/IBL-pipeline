'''
This script inserts membership tuples into the membership shadow tables, \
which cannot be inserted with auto-population.
'''
import datajoint as dj
import json
import uuid
from ibl_pipeline.ingest import (
    alyxraw, reference, subject, action,
    acquisition, data, QueryBuffer)
from ibl_pipeline.ingest import get_raw_field as grf
from tqdm import tqdm

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
keys = (surgeries & surgeries_with_users).proj(
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

keys = (surgeries & surgeries_with_procedures).proj(
    surgery_uuid='uuid')

for key in keys:
    key_s = dict()
    key['uuid'] = key['surgery_uuid']
    if not len(action.Surgery & key):
        print('Surgery {} not in the table action.Surgery'.format(
            key['surgery_uuid']))
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
sessions = alyxraw.AlyxRaw & 'model="actions.session"'
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
sessions = alyxraw.AlyxRaw & 'model="actions.session"'
sessions_with_users = alyxraw.AlyxRaw.Field & sessions & \
    'fname="users"' & 'fvalue!="None"'
keys = (alyxraw.AlyxRaw & sessions_with_users).proj(
    session_uuid='uuid')

session_user = QueryBuffer(acquisition.SessionUser)

for key in tqdm(keys, position=0):

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

        session_user.add_to_queue1(key_su)
        if session_user.flush_insert(
                skip_duplicates=True, chunksz=1000):
            print('Inserted 1000 session user tuples')

if session_user.flush_insert(skip_duplicates=True):
    print('Inserted all remaining session user tuples')


# acquisition.SessionProcedure
print('Ingesting acquisition.SessionProcedure...')
sessions = alyxraw.AlyxRaw & 'model="actions.session"'
sessions_with_procedures = alyxraw.AlyxRaw.Field & sessions & \
    'fname="procedures"' & 'fvalue!="None"'
keys = (alyxraw.AlyxRaw & sessions_with_procedures).proj(
    session_uuid='uuid')

session_procedure = QueryBuffer(acquisition.SessionProcedure)

for key in tqdm(keys, position=0):
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
        session_procedure.add_to_queue1(key_sp)
        if session_procedure.flush_insert(
                skip_duplicates=True, chunksz=1000):
            print('Inserted 1000 session procedure tuples')

if session_procedure.flush_insert(skip_duplicates=True):
    print('Inserted all remaining session procedure tuples')

# acquisition.SessionProject
print('Ingesting acquisition.SessionProject...')
sessions = alyxraw.AlyxRaw & 'model="actions.session"'
sessions_with_projects = alyxraw.AlyxRaw.Field & sessions & \
    'fname="project"' & 'fvalue!="None"'
keys = (alyxraw.AlyxRaw & sessions_with_projects).proj(
    session_uuid='uuid')

session_project = QueryBuffer(acquisition.SessionProject)

for key in tqdm(keys, position=0):
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

    session_project.add_to_queue1(key_sp)

    if session_project.flush_insert(
            skip_duplicates=True, chunksz=1000):
        print('Inserted 1000 session procedure tuples')

if session_project.flush_insert(skip_duplicates=True):
    print('Inserted all remaining session procedure tuples')


# data.ProjectRepository
print('Ingesting data.ProjectRespository...')
projects = alyxraw.AlyxRaw & 'model="subjects.project"'
projects_with_repos = alyxraw.AlyxRaw.Field & projects & \
    'fname="repositories"' & 'fvalue!="None"'
keys = (alyxraw.AlyxRaw & projects_with_repos).proj(project_uuid='uuid')
for key in keys:
    key_p = dict()
    key_p['project_name'] = (reference.Project & key).fetch1('project_name')
    key['uuid'] = key['project_uuid']

    repos = grf(key, 'repositories', multiple_entries=True)

    for repo in repos:
        key_pr = key_p.copy()
        key_pr['repo_name'] = \
            (data.DataRepository &
                dict(repo_uuid=uuid.UUID(repo))).fetch1(
                    'repo_name')
        data.ProjectRepository.insert1(key_pr, skip_duplicates=True)
