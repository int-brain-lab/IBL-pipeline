'''
This script inserts tuples in the alyxraw table into the shadow tables \
via auto-populating.
'''

import datajoint as dj
from ibl_pipeline.ingest import alyxraw, reference, subject, action, acquisition, data
from ibl_pipeline import public
import utils

# reference tables
reference.Lab.populate(suppress_errors=True)
reference.LabMember.populate(suppress_errors=True)
reference.LabMembership.populate(suppress_errors=True)
reference.LabLocation.populate(suppress_errors=True)
reference.Project.populate(suppress_errors=True)

# subject tables
subject.Species.populate(suppress_errors=True)
subject.Source.populate(suppress_errors=True)
subject.Strain.populate(suppress_errors=True)
subject.Sequence.populate(suppress_errors=True)
subject.Allele.populate(suppress_errors=True)
subject.Line.populate(suppress_errors=True)

# select specific subjects for the public website
subject_uuids = public.PublicSubjectUuid.fetch('subject_uuid')
subj_res = utils.get_uuids('subjects.subject', 'subject_uuid', subject_uuids)
subject.Subject.populate(subj_res, suppress_errors=True)
# subject.BreedingPair.populate(suppress_errors=True)
# subject.Litter.populate(suppress_errors=True)
# subject.LitterSubject.populate(suppress_errors=True)
subject.SubjectProject.populate(subj_res, suppress_errors=True)
subject.SubjectUser.populate(subj_res, suppress_errors=True)
subject.SubjectLab.populate(subj_res, suppress_errors=True)
# subject.Caging.populate(suppress_errors=True)
# subject.UserHistory.populate(suppress_errors=True)
# subject.Weaning.populate(suppress_errors=True)
subject.Death.populate(subj_res, suppress_errors=True)
# subject.GenotypeTest.populate(suppress_errors=True)
# subject.Zygosity.populate(suppress_errors=True)

# action tables
action.ProcedureType.populate(suppress_errors=True)
action.Weighing.populate(
    utils.get_uuids('actions.weighing', 'weighing_uuid', subject_uuids),
    suppress_errors=True)
action.WaterType.populate(suppress_errors=True)
action.WaterAdministration.populate(
    utils.get_uuids('actions.wateradministration',
                    'wateradmin_uuid', subject_uuids),
    suppress_errors=True)
action.WaterRestriction.populate(
    utils.get_uuids('actions.waterrestriction',
                    'restriction_uuid', subject_uuids),
    suppress_errors=True)
action.Surgery.populate(
    utils.get_uuids('actions.surgery', 'surgery_uuid', subject_uuids),
    suppress_errors=True)


# acquisition tables
acquisition.Session.populate(
    utils.get_uuids('actions.session', 'session_uuid', subject_uuids),
    suppress_errors=True)

# data tables
data.DataFormat.populate(suppress_errors=True)
data.DataRepositoryType.populate(suppress_errors=True)
data.DataRepository.populate(suppress_errors=True)
data.DataSetType.populate(suppress_errors=True)
data.DataSet.populate(
    utils.get_uuids('data.dataset', 'dataset_uuid', subject_uuids),
    suppress_errors=True)
data.FileRecord.populate(
    utils.get_uuids('data.filerecord', 'record_uuid', subject_uuids),
    suppress_errors=True)
