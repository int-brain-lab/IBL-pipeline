'''
This script inserts tuples in the alyxraw table into the shadow tables \
via auto-populating.
'''

import datajoint as dj
from ibl_pipeline.ingest import alyxraw, reference, subject, action, acquisition, data
from ibl_pipeline import public
import utils

kargs = dict(suppress_errors=True, display_progress=True)

# reference tables
print('-------- Populating reference shadow tables ------------')
reference.Lab.populate(**kargs)
reference.LabMembership.populate(**kargs)
reference.LabLocation.populate(**kargs)
reference.Project.populate(**kargs)

# subject tables
print('-------- Populating subject shadow tables ------------')
subject.Source.populate(**kargs)
subject.Strain.populate(**kargs)
subject.Sequence.populate(**kargs)
subject.Allele.populate(**kargs)
subject.Line.populate(**kargs)

# select specific subjects for the public website
subject_uuids = public.PublicSubjectUuid.fetch('subject_uuid')
subj_res = utils.get_uuids('subjects.subject', 'subject_uuid', subject_uuids)
subject.Subject.populate(subj_res, **kargs)
# subject.BreedingPair.populate(**kargs)
# subject.Litter.populate(**kargs)
# subject.LitterSubject.populate(**kargs)
subject.SubjectProject.populate(subj_res, **kargs)
subject.SubjectUser.populate(subj_res, **kargs)
subject.SubjectLab.populate(subj_res, **kargs)
subject.SubjectCullMethod.populate(subj_res, **kargs)
subject.Caging.populate(**kargs)
# subject.UserHistory.populate(**kargs)
subject.Weaning.populate(subj_res, **kargs)
subject.Death.populate(subj_res, **kargs)
subject.GenotypeTest.populate(**kargs)
subject.Zygosity.populate(**kargs)

# action tables
print('-------- Populating action shadow tables -----------')
action.ProcedureType.populate(**kargs)
action.Weighing.populate(
    utils.get_uuids('actions.weighing', 'weigh_uuid', subject_uuids),
    **kargs)
action.WaterType.populate(**kargs)
print('-------- Populating water administration entries -----------')
action.WaterAdministration.populate(
    utils.get_uuids('actions.wateradministration',
                    'wateradmin_uuid', subject_uuids),
    **kargs)
print('-------- Populating water restriction entries -----------')
action.WaterRestriction.populate(
    utils.get_uuids('actions.waterrestriction',
                    'restriction_uuid', subject_uuids),
    **kargs)
action.Surgery.populate(
    utils.get_uuids('actions.surgery', 'surgery_uuid', subject_uuids),
    **kargs)


# acquisition tables
print('-------- Populating session entries -----------')
acquisition.Session.populate(
    utils.get_uuids('actions.session', 'session_uuid', subject_uuids),
    **kargs)

# data tables
print('-------- Populating data shadow tables -----------')
data.DataFormat.populate(**kargs)
data.DataRepositoryType.populate(**kargs)
data.DataRepository.populate(**kargs)
data.DataSetType.populate(**kargs)
print('-------- Populating dataset entries -----------')
data.DataSet.populate(
    utils.get_uuids('data.dataset', 'dataset_uuid', subject_uuids),
    **kargs)
print('-------- Populating file record entries ----------')
data.FileRecord.populate(
    utils.get_uuids('data.filerecord', 'record_uuid', subject_uuids),
    **kargs)
