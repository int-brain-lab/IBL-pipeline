'''
This script inserts membership tuples into the membership shadow tables, \
which cannot be inserted with auto-population.
'''
import datajoint as dj
import json
from ibl_pipeline.ingest import alyxraw, reference, subject, action, acquisition, data
from ibl_pipeline.ingest import get_raw_field as grf

subjects = alyxraw.AlyxRaw.Field & (alyxraw.AlyxRaw & 'model="subjects.subject"') & 'fname="lab"' & 'fvalue!="None"'

# reference.ProjectLabMember
print('Ingesting reference.ProjectLabMember...')
keys = (alyxraw.AlyxRaw & 'model="subjects.project"').proj(project_uuid='uuid')

for key in keys:
    key_p = dict()
    key_p['project_name'] = (reference.Project & key).fetch1('project_name')

    user_uuids = grf(key, 'users', multiple_entries=True)

    for user_uuid in user_uuids:
        key_pl = key_p.copy()
        key_pl['user_name'] = (reference.LabMember & 'user_uuid="{}"'.format(user_uuid)).fetch1('user_name')
        reference.ProjectLabMember.insert1(key_pl, skip_duplicates=True)


# subject.AlleleSequence
print('Ingesting subject.AlleleSequence...')
keys = (alyxraw.AlyxRaw & 'model="subjects.allele"').proj(allele_uuid='uuid')
for key in keys:
    key_a = dict()
    key_a['allele_name'] = (subject.Allele & key).fetch1('allele_name')
    key['uuid'] = key['allele_uuid']
    sequences = grf(key, 'sequences', multiple_entries=True)
    for sequence in sequences:
        if sequence != 'None':
            key_as = key_a.copy()
            key_as['sequence_name'] = (subject.Sequence & 'sequence_uuid="{}"'.format(sequence)).fetch1('sequence_name')
            subject.AlleleSequence.insert1(key_as, skip_duplicates=True)

# subject.LineAllele
print('Ingesting subject.LineAllele...')
keys = (alyxraw.AlyxRaw & 'model="subjects.line"').proj(line_uuid='uuid')
for key in keys:
    key_l = dict()
    key_l['line_name'] = (subject.Line & key).fetch1('line_name')
    key['uuid'] = key['line_uuid']
    alleles = grf(key, 'alleles', multiple_entries=True)

    for allele in alleles:
        if allele != 'None':
            key_la = key_l.copy()
            key_la['allele_name'] = (subject.Allele & 'allele_uuid="{}"'.format(allele)).fetch1('allele_name')
            subject.LineAllele.insert1(key_la, skip_duplicates=True)

# subject.LitterSubject
print('Ingesting subject.LitterSubject...')
subjects_l = alyxraw.AlyxRaw.Field & (alyxraw.AlyxRaw & 'model = "subjects.subject"') & 'fname="litter"' & 'fvalue!="None"'
keys = (alyxraw.AlyxRaw & subjects & subjects_l).proj(subject_uuid='uuid')

for key in keys:
    key['uuid'] = key['subject_uuid']
    lab_uuid = grf(key, 'lab')
    key_ls = dict()
    key_ls['lab_name'] = (reference.Lab & 'lab_uuid="{}"'.format(lab_uuid)).fetch1('lab_name')
    key_ls['subject_nickname'] = grf(key, 'nickname')
    litter = grf(key, 'litter')
    key_ls['litter_name'] = (subject.Litter & 'litter_uuid="{}"'.format(litter)).fetch1('litter_name')
    subject.LitterSubject.insert1(key_ls, skip_duplicates=True)

# subject.SubjectProject
print('Ingesting subject.SubjectProject...')
subjects_p = alyxraw.AlyxRaw.Field & (alyxraw.AlyxRaw & 'model="subjects.subject"') & 'fname="projects"' & 'fvalue!="None"'
keys = (alyxraw.AlyxRaw & subjects & subjects_p).proj(subject_uuid='uuid')
for key in keys:
    key['uuid'] = key['subject_uuid']
    lab_uuid = grf(key, 'lab')
    key_s = dict()
    key_s['lab_name'] = (reference.Lab & 'lab_uuid="{}"'.format(lab_uuid)).fetch1('lab_name')
    key_s['subject_nickname'] = grf(key, 'nickname')
    proj_uuids = grf(key, 'projects', multiple_entries=True)
    
    for proj_uuid in proj_uuids:
        key_sp = key_s.copy()
        key_sp['subject_nickname'] = grf(key, 'nickname')
        key_sp['project_name'] = (reference.Project & 'project_uuid="{}"'.format(proj_uuid)).fetch1('project_name')
        subject.SubjectProject.insert1(key_sp, skip_duplicates=True)

# subject.Caging
print('Ingesting subject.Caging...')
subjects_c = alyxraw.AlyxRaw.Field & (alyxraw.AlyxRaw & 'model="subjects.subject"') & 'fname="cage"' & 'fvalue!="None"'
keys = (alyxraw.AlyxRaw & subjects & subjects_c).proj(subject_uuid='uuid')
for key in keys:
    key['uuid'] = key['subject_uuid']
    lab_uuid = grf(key, 'lab')
    key_cage = dict()
    key_cage['lab_name'] = (reference.Lab & 'lab_uuid="{}"'.format(lab_uuid)).fetch1('lab_name')
    key_cage['subject_nickname'] = grf(key, 'nickname')
    
    key_cage['cage_name'] = grf(key, 'cage')
    json_content = grf(key, 'json')
    if json_content != 'None':
        json_dict = json.loads(json_content)
        history = json_dict['history']
        if 'cage' not in history:
            subject.Caging.insert1(key_cage, skip_duplicates=True)
        else:
            cages = history['cage']
            key_cage_i = key_cage.copy()
            for cage in cages[::-1]:
                cage_time = cage['date_time']
                key_cage_i['caging_time'] = cage_time[:-6]
                subject.Caging.insert1(key_cage_i, skip_duplicates=True)
                if cage['value'] != 'None':
                    key_cage_i['cage_name'] = cage['value']
    else:
        subject.Caging.insert1(key_cage, skip_duplicates=True)

# subject.UserHistory
print('Ingesting subject.UserHistory...')
keys = (alyxraw.AlyxRaw & subjects).proj(subject_uuid='uuid')
for key in keys:
    key['uuid'] = key['subject_uuid']
    lab_uuid = grf(key, 'lab')
    key_user = dict()
    key_user['lab_name'] = (reference.Lab & 'lab_uuid="{}"'.format(lab_uuid)).fetch1('lab_name')
    key_user['subject_nickname'] = grf(key, 'nickname')

    user = grf(key, 'responsible_user')
    key_user['user_name'] = user
    json_content = grf(key, 'json')
    if json_content != 'None':
        json_dict = json.loads(json_content)
        history = json_dict['history']
        if 'reponsible_user' not in history:
            subject.UserHistory.insert1(key_user, skip_duplicates=True)
        else:
            users = history['responsible_user']
            key_user_i = key_user.copy()
            for user in users[::-1]:
                user_change_time = user['date_time']
                key_user_i['user_change_time'] = user_change_time[:-6]
                subject.UserHistory.insert1(key_user_i, skip_duplicates=True)
                if user['value'] != 'None':
                    user_uuid = user['value']
                    key_user_i['user_name'] = (reference.LabMember & 'user_uuid="{}"'.format(user_uuid)).fetch1('user_name')
    else:
        subject.UserHistory.insert1(key_user, skip_duplicates=True)


# subject.Weaning
print('Ingesting subject.Weaning...')
subjects_w = alyxraw.AlyxRaw.Field & (alyxraw.AlyxRaw & 'model="subjects.subject"') & 'fname="wean_date"' & 'fvalue!="None"'
keys = (alyxraw.AlyxRaw & subjects & subjects_w).proj(subject_uuid='uuid')
for key in keys:
    key['uuid'] = key['subject_uuid']
    lab_uuid = grf(key, 'lab')
    key_weaning = dict()
    key_weaning['lab_name'] = (reference.Lab & 'lab_uuid="{}"'.format(lab_uuid)).fetch1('lab_name')
    key_weaning['subject_nickname'] = grf(key, 'nickname')
    wean_date = grf(key, 'wean_date')
    key_weaning['wean_date'] = wean_date
    subject.Weaning.insert1(key_weaning, skip_duplicates=True)

# subject.Death
print('Ingesting subject.Death...')
subjects_d = alyxraw.AlyxRaw.Field & (alyxraw.AlyxRaw & 'model="subjects.subject"') & 'fname="death_date"' & 'fvalue!="None"'
keys = (alyxraw.AlyxRaw & subjects & subjects_d).proj(subject_uuid='uuid')

for key in keys:    
    key['uuid'] = key['subject_uuid']
    lab_uuid = grf(key, 'lab')
    key_death = dict()
    key_death['lab_name'] = (reference.Lab & 'lab_uuid="{}"'.format(lab_uuid)).fetch1('lab_name')
    key_death['subject_nickname'] = grf(key, 'nickname')
    death_date = grf(key, 'death_date')
    key_death['death_date'] = death_date
    subject.Death.insert1(key_death, skip_duplicates=True)

# subject.Implant
print('Ingesting subject.Implant...')
subjects_i = alyxraw.AlyxRaw.Field & (alyxraw.AlyxRaw & 'model="subjects.subject"') & 'fname="implant_weight"' & 'fvalue!="None"'
keys = (alyxraw.AlyxRaw & subjects & subjects_i).proj(subject_uuid='uuid')

for key in keys:
    key['uuid'] = key['subject_uuid']
    lab_uuid = grf(key, 'lab')
    key_implant = dict()
    key_implant['lab_name'] = (reference.Lab & 'lab_uuid="{}"'.format(lab_uuid)).fetch1('lab_name')
    key_implant['subject_nickname'] = grf(key, 'nickname')
    key_implant['implant_weight'] = float(grf(key, 'implant_weight'))

    adverse_effects = grf(key, 'adverse_effects')
    if adverse_effects != 'None':
        key_implant['adverse_effects'] = adverse_effects

    actual_severity = grf(key, 'actual_severity')
    if actual_severity != 'None':
        key_implant['actual_severity'] = int(actual_severity)

    key_implant['protocol_number'] = int(grf(key, 'protocol_number'))

    subject.Implant.insert1(key_implant, skip_duplicates=True)

# action.WaterRestrictionUser
print('Ingesting action.WaterRestrictionUser...')
keys = (alyxraw.AlyxRaw & 'model = "actions.waterrestriction"').proj(restriction_uuid='uuid')
for key in keys:
    key_r = dict()
    key['uuid'] = key['restriction_uuid']
    key_r['lab_name'], key_r['subject_nickname'], key_r['restriction_start_time'] = \
        (action.WaterRestriction & key).fetch1('lab_name', 'subject_nickname', 'restriction_start_time')
    
    user_uuids = grf(key, 'users', multiple_entries=True)

    for user_uuid in user_uuids:
        if user_uuid != 'None':
            key_ru = key_r.copy()
            key_ru['user_name'] = (reference.LabMember & 'user_uuid="{}"'.format(user_uuid)).fetch1('user_name')
            action.WaterRestrictionUser.insert1(key_ru, skip_duplicates=True)

# action.WaterRestrictionProcedure
print('Ingesting action.WaterRestrictionProcedure...')
keys = (alyxraw.AlyxRaw & 'model = "actions.waterrestriction"').proj(restriction_uuid='uuid')
for key in keys:
    key_r = dict()
    key['uuid'] = key['restriction_uuid']
    key_r['lab_name'], key_r['subject_nickname'], key_r['restriction_start_time'] = \
        (action.WaterRestriction & key).fetch1('lab_name', 'subject_nickname', 'restriction_start_time')
    
    procedures = grf(key, 'procedures', multiple_entries=True)

    for procedure in procedures:
        if procedure != 'None':
            key_rp = key_r.copy()
            key_rp['procedure_type_name'] = (action.ProcedureType & 'procedure_type_uuid="{}"'.format(procedure)).fetch1('procedure_type_name')
            action.WaterRestrictionProcedure.insert1(key_rp, skip_duplicates=True)



# action.SurgeryUser
print('Ingesting action.SurgeryUser...')
keys = (alyxraw.AlyxRaw & 'model = "actions.surgery"').proj(surgery_uuid='uuid')
for key in keys:
    key_s = dict()
    key['uuid'] = key['surgery_uuid']
    if len(action.Surgery & key)==0:
        continue
    key_s['lab_name'], key_s['subject_nickname'], key_s['surgery_start_time'] = \
        (action.Surgery & key).fetch1('lab_name', 'subject_nickname', 'surgery_start_time')
    user_uuids = grf(key, 'users', multiple_entries=True)

    for user_uuid in user_uuids:
        if user_uuid != 'None':
            key_sl = key_s.copy()
            key_sl['user_name'] = (reference.LabMember & 'user_uuid="{}"'.format(user_uuid)).fetch1('user_name')
            action.SurgeryUser.insert1(key_sl, skip_duplicates=True)

# action.SurgeryProcedure
print('Ingesting action.SurgeryProcedure...')
keys = (alyxraw.AlyxRaw & 'model = "actions.surgery"').proj(surgery_uuid='uuid')
for key in keys:
    key_s = dict()
    key['uuid'] = key['surgery_uuid']
    if len(action.Surgery & key)==0:
        continue
    key_s['lab_name'], key_s['subject_nickname'], key_s['surgery_start_time'] = \
        (action.Surgery & key).fetch1('lab_name', 'subject_nickname', 'surgery_start_time')
    procedures = grf(key, 'procedures', multiple_entries=True)

    for procedure in procedures:
        if procedure != 'None':
            key_sp = key_s.copy()
            key_sp['procedure_type_name'] = (action.ProcedureType & 'procedure_type_uuid="{}"'.format(procedure)).fetch1('procedure_type_name')
            action.SurgeryProcedure.insert1(key_sp, skip_duplicates=True)

# acquisition.ChildSession
print('Ingesting acquisition.ChildSession...')
sessions = alyxraw.AlyxRaw.Field & (alyxraw.AlyxRaw & 'model="actions.session"') & 'fname="parent_session"' & 'fvalue!="None"'
keys = (alyxraw.AlyxRaw & sessions & 'model="actions.session"').proj(session_uuid='uuid')
for key in keys:
    key_cs = dict()
    key['uuid'] = key['session_uuid']

    key_cs['lab_name'], key_cs['subject_nickname'], key_cs['session_start_time'] = \
        (acquisition.Session & key).fetch1('lab_name', 'subject_nickname', 'session_start_time')
    parent_session = grf(key, 'parent_session')
    if parent_session != 'None':
        key_cs['parent_session_start_time'] = \
            (acquisition.Session & 'session_uuid="{}"'.format(parent_session)).fetch1('session_start_time')
        acquisition.ChildSession.insert1(key_cs, skip_duplicates=True)

# acquisition.SessionUser
print('Ingesting acquisition.SessionUser...')
keys = (alyxraw.AlyxRaw & 'model = "actions.session"').proj(session_uuid = 'uuid')
for key in keys:
    key_s = dict()
    key['uuid'] = key['session_uuid']
    try:
        key_s['lab_name'], key_s['subject_nickname'], key_s['session_start_time'] = \
            (acquisition.Session & key).fetch1('lab_name', 'subject_nickname', 'session_start_time')
    except:
        print('session', key['session_uuid'])
        continue

    user_uuids = grf(key, 'users', multiple_entries=True)

    for user_uuid in user_uuids:
        if user_uuid != 'None':
            key_su = key_s.copy()
            key_su['user_name'] = (reference.LabMember & 'user_uuid="{}"'.format(user_uuid)).fetch1('user_name')
            acquisition.SessionUser.insert1(key_su, skip_duplicates=True)

# acquisition.SessionProcedure
print('Ingesting acquisition.SessionProcedure...')
procedure = alyxraw.AlyxRaw.Field & (alyxraw.AlyxRaw & 'model="actions.session"') & 'fname="procedure"' & 'fvalue!="None"'
keys = (alyxraw.AlyxRaw & 'model="actions.session"').proj(session_uuid='uuid')
for key in keys:
    key_s = dict()
    key['uuid'] = key['session_uuid']
    try:
        key_s['lab_name'], key_s['subject_nickname'], key_s['session_start_time'] = \
            (acquisition.Session & key).fetch1('lab_name', 'subject_nickname', 'session_start_time')
    except:
        print('session', key['session_uuid'])
        continue

    procedures = grf(key, 'procedures', multiple_entries=True)

    for procedure in procedures:
        if procedure != 'None':
            key_sp = key_s.copy()
            key_sp['procedure_type_name'] = (action.ProcedureType & 'procedure_type_uuid="{}"'.format(procedure)).fetch1('procedure_type_name')
            acquisition.SessionProcedure.insert1(key_sp, skip_duplicates=True)

# acquisition.WaterAdminstrationSession
print('Ingesting acquisition.WaterAdministrationSession...')
admin = alyxraw.AlyxRaw.Field & (alyxraw.AlyxRaw & 'model="actions.wateradministration"') & 'fname="session"' & 'fvalue!="None"'
keys = (alyxraw.AlyxRaw & admin).proj(wateradmin_uuid='uuid')
for key in keys:
    key_w = dict()
    key['uuid'] = key['wateradmin_uuid']
    
    try:
        key_w['lab_name'], key_w['subject_nickname'], key_w['administration_time'] = \
            (action.WaterAdministration & key).fetch1('lab_name', 'subject_nickname', 'administration_time')
    except:
        print('wateradimin', key['wateradmin_uuid'])
        continue
    session_uuid = grf(key, 'session', multiple_entries=False)
    key_ws = key_w.copy()
    try:
        key_ws['session_start_time'] = (acquisition.Session & 'session_uuid="{}"'.format(session_uuid)).fetch1('session_start_time')
    except:
        print('session', session_uuid)
    acquisition.WaterAdministrationSession.insert1(key_ws, skip_duplicates=True)

# data.ProjectRepository
print('Ingesting data.ProjectRespository...')
keys = (alyxraw.AlyxRaw & 'model="subjects.project"').proj(project_uuid='uuid')
for key in keys:
    key_p = dict()
    key_p['project_name'] = (reference.Project & key).fetch1('project_name')
    key['uuid'] = key['project_uuid']

    repo_uuids = grf(key, 'repositories', multiple_entries=True)

    for repo_uuid in repo_uuids:
        if repo_uuid != 'None':
            key_pr = key_p.copy()
            key_pr['repo_name'] = (data.DataRepository & 'repo_uuid="{}"'.format(repo_uuid)).fetch1('repo_name')
            data.ProjectRepository.insert1(key_pr, skip_duplicates=True)