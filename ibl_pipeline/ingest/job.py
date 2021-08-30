import datajoint as dj

schema = dj.schema(dj.config.get('database.prefix', '') +
                   'ibl_ingest_job')


@schema
class TimeZone(dj.Lookup):
    definition = """
    timezone:      varchar(16)
    """
    contents = zip(['European', 'EST', 'PST', 'other'])


@schema
class Job(dj.Manual):
    definition = """
    job_date     : date
    -> TimeZone.proj(job_timezone='timezone')
    ---
    alyx_current_timestamp  : datetime          # timestamp of either current json dump or sql dump
    alyx_previous_timestamp=null : datetime     # timestamp of the previous json dump, null for postgres based ingestion
    created_pks=null   : longblob               # pks created
    modified_pks=null  : longblob               # pks where entries were modified
    deleted_pks=null   : longblob               # deleted pks
    modified_pks_important=null : longblob      # filtered modified pks, excluded for some job tables, dataset and file record tables.
    session_prefiltered=0: bool                 # whether session modification is prefiltered.
    job_ts=CURRENT_TIMESTAMP     : timestamp
    """


@schema
class Task(dj.Lookup):
    definition = """
    task                    : varchar(64)
    ---
    task_order              : tinyint
    task_description=''     : varchar(1024)
    """
    contents = [
        ['Ingest to update_alyxraw', 1, 'Ingest selected tables to schema update_alyxraw'],
        ['Get modified deleted pks', 2, 'Get modified deleted pks'],
        ['Delete alyxraw', 3, 'Delete alyxraw and shadow table entries for updated and deleted records'],
        ['Delete shadow membership', 4, 'Delete shadow membership records for updated and deleted records'],
        ['Ingest alyxraw', 5, 'Ingest to alyxraw'],
        ['Ingest shadow', 6, 'Ingest to alyx shadow tables'],
        ['Ingest shadow membership', 7, 'Ingest to alyx shadow membership tables'],
        ['Ingest real', 8, 'Ingest to alyx real tables'],
        ['Update fields', 9, 'Update fields in real tables'],
        ['Populate behavior', 10, 'Populate behavior tables']
    ]


@schema
class TaskStatus(dj.Manual):
    definition = """
    -> Job
    -> Task
    ---
    task_start_time         : datetime
    task_end_time           : datetime
    task_duration           : float     # in mins
    task_status_comments='' : varchar(1000)
    """

    @classmethod
    def insert_task_status(cls, job_key, task, start, end):
        cls.insert1(dict(**job_key,
                         task=task,
                         task_start_time=start,
                         task_end_time=end,
                         task_duration=(end - start).total_seconds() / 60.),
                    skip_duplicates=True)


# ================== Orchestrating the ingestion jobs =============
import logging
import time
import inspect
from datetime import datetime

import misc as alyx_misc
import subjects as alyx_subjects
import actions as alyx_actions
import data as alyx_data
import experiments as alyx_experiments

from ibl_pipeline.ingest import QueryBuffer, alyxraw
from ibl_pipeline.process import (ingest_alyx_raw_postgres, ingest_membership,
                                  ingest_real, delete_update_entries)

from ibl_pipeline.ingest import reference as shadow_reference
from ibl_pipeline.ingest import subject as shadow_subject
from ibl_pipeline.ingest import action as shadow_action
from ibl_pipeline.ingest import acquisition as shadow_acquisition
from ibl_pipeline.ingest import data as shadow_data
from ibl_pipeline.ingest import ephys as shadow_ephys

from ibl_pipeline import reference, subject, action, acquisition, data, ephys


logger = logging.getLogger(__name__)


ALYX_MODELS = {
    'misc.lab': alyx_misc.models.Lab,
    'misc.lablocation': alyx_misc.models.LabLocation,
    'misc.labmember': alyx_misc.models.LabMember,
    'misc.labmembership': alyx_misc.models.LabMembership,
    'misc.cagetype': alyx_misc.models.CageType,
    'misc.enrichment': alyx_misc.models.Enrichment,
    'misc.food': alyx_misc.models.Food,
    'misc.housing': alyx_misc.models.Housing,
    'subjects.project': alyx_subjects.models.Project,
    'subjects.source': alyx_subjects.models.Source,
    'subjects.species': alyx_subjects.models.Species,
    'subjects.strain': alyx_subjects.models.Strain,
    'subjects.sequence': alyx_subjects.models.Sequence,
    'subjects.allele': alyx_subjects.models.Allele,
    'subjects.line': alyx_subjects.models.Line,
    'subjects.subject': alyx_subjects.models.Subject,
    'subjects.breedingpair': alyx_subjects.models.BreedingPair,
    'subjects.litter': alyx_subjects.models.Litter,
    'subjects.genotypetest': alyx_subjects.models.GenotypeTest,
    'subjects.zygosity': alyx_subjects.models.Zygosity,
    'actions.proceduretype': alyx_actions.models.ProcedureType,
    'actions.surgery': alyx_actions.models.Surgery,
    'actions.cullmethod': alyx_actions.models.CullMethod,
    'actions.cullreason': alyx_actions.models.CullReason,
    'actions.cull': alyx_actions.models.Cull,
    'actions.weighing': alyx_actions.models.Weighing,
    'actions.watertype': alyx_actions.models.WaterType,
    'actions.waterrestriction': alyx_actions.models.WaterRestriction,
    'actions.wateradministration': alyx_actions.models.WaterAdministration,
    'actions.session': alyx_actions.models.Session,
    'data.dataformat': alyx_data.models.DataFormat,
    'data.datarepositorytype': alyx_data.models.DataRepositoryType,
    'data.datarepository': alyx_data.models.DataRepository,
    'data.datasettype': alyx_data.models.DatasetType,
    'data.dataset': alyx_data.models.Dataset,
    'data.filerecord': alyx_data.models.FileRecord,
    'experiments.coordinatesystem': alyx_experiments.models.CoordinateSystem,
    'experiments.probemodel': alyx_experiments.models.ProbeModel,
    'experiments.probeinsertion': alyx_experiments.models.ProbeInsertion,
    'experiments.trajectoryestimate': alyx_experiments.models.TrajectoryEstimate
}

MEMBERSHIP_ALYX_MODELS = {
    'subjects.project': [reference.ProjectLabMember,
                         data.ProjectRepository],
    'subjects.allele': [subject.AlleleSequence],
    'subjects.line': [subject.LineAllele],
    'actions.surgery': [action.SurgeryProcedure,
                        action.SurgeryUser],
    'actions.session': [acquisition.ChildSession,
                        acquisition.SessionUser,
                        acquisition.SessionProcedure,
                        acquisition.SessionProject],
    'actions.waterrestriction': [action.WaterRestrictionUser,
                                 action.WaterRestrictionProcedure],
    'actions.wateradministration': [acquisition.WaterAdministrationSession]
}

DJ_TABLES = {
    'reference.Lab': {'shadow': shadow_reference.Lab,
                      'real': reference.Lab},
    'reference.LabMember': {'shadow': shadow_reference.LabMember,
                            'real': reference.LabMember},
    'reference.LabMembership': {'shadow': shadow_reference.LabMembership,
                                'real': reference.LabMembership},
    'reference.LabLocation': {'shadow': shadow_reference.LabLocation,
                              'real': reference.LabLocation},
    'reference.Project': {'shadow': shadow_reference.Project,
                          'real': reference.Project},
    'reference.CoordinateSystem': {'shadow': shadow_reference.CoordinateSystem,
                                   'real': reference.CoordinateSystem},
    'subject.Species': {'shadow': shadow_subject.Species,
                        'real': subject.Species},
    'subject.Source': {'shadow': shadow_subject.Source,
                       'real': subject.Source},
    'subject.Strain': {'shadow': shadow_subject.Strain,
                       'real': subject.Strain},
    'subject.Sequence': {'shadow': shadow_subject.Sequence,
                         'real': subject.Sequence},
    'subject.Allele': {'shadow': shadow_subject.Allele,
                       'real': subject.Allele},
    'subject.Line': {'shadow': shadow_subject.Line,
                     'real': subject.Line},
    'subject.Subject': {'shadow': shadow_subject.Subject,
                        'real': subject.Subject},
    'subject.BreedingPair': {'shadow': shadow_subject.BreedingPair,
                             'real': subject.BreedingPair},
    'subject.Litter': {'shadow': shadow_subject.Litter,
                       'real': subject.Litter},
    'subject.LitterSubject': {'shadow': shadow_subject.LitterSubject,
                              'real': subject.LitterSubject},
    'subject.SubjectProject': {'shadow': shadow_subject.SubjectProject,
                               'real': subject.SubjectProject},
    'subject.SubjectUser': {'shadow': shadow_subject.SubjectUser,
                            'real': subject.SubjectUser},
    'subject.SubjectLab': {'shadow': shadow_subject.SubjectLab,
                           'real': subject.SubjectLab},
    'subject.Caging': {'shadow': shadow_subject.Caging,
                       'real': subject.Caging},
    'subject.UserHistory': {'shadow': shadow_subject.UserHistory,
                            'real': subject.UserHistory},
    'subject.Weaning': {'shadow': shadow_subject.Weaning,
                        'real': subject.Weaning},
    'subject.Death': {'shadow': shadow_subject.Death,
                      'real': subject.Death},
    'subject.GenotypeTest': {'shadow': shadow_subject.GenotypeTest,
                             'real': subject.GenotypeTest},
    'subject.Zygosity': {'shadow': shadow_subject.Zygosity,
                         'real': subject.Zygosity},
    'action.ProcedureType': {'shadow': shadow_action.ProcedureType,
                             'real': action.ProcedureType},
    'acquisition.Session': {'shadow': shadow_acquisition.Session,
                            'real': acquisition.Session},
    'data.DataFormat': {'shadow': shadow_data.DataFormat,
                        'real': data.DataFormat},
    'data.DataRepositoryType': {'shadow': shadow_data.DataRepositoryType,
                                'real': data.DataRepositoryType},
    'data.DataRepository': {'shadow': shadow_data.DataRepository,
                            'real': data.DataRepository},
    'data.DataSetType': {'shadow': shadow_data.DataSetType,
                         'real': data.DataSetType},
    'subject.SubjectCullMethod': {'shadow': shadow_subject.SubjectCullMethod,
                                  'real': subject.SubjectCullMethod},
    'action.Weighing': {'shadow': shadow_action.Weighing,
                        'real': action.Weighing},
    'action.WaterType': {'shadow': shadow_action.WaterType,
                         'real': action.WaterType},
    'action.WaterAdministration': {'shadow': shadow_action.WaterAdministration,
                                   'real': action.WaterAdministration},
    'action.WaterRestriction': {'shadow': shadow_action.WaterRestriction,
                                'real': action.WaterRestriction},
    'action.Surgery': {'shadow': shadow_action.Surgery,
                       'real': action.Surgery},
    'action.CullMethod': {'shadow': shadow_action.CullMethod,
                          'real': action.CullMethod},
    'action.CullReason': {'shadow': shadow_action.CullReason,
                          'real': action.CullReason},
    'action.Cull': {'shadow': shadow_action.Cull,
                    'real': action.Cull},
    'action.OtherAction': {'shadow': shadow_action.OtherAction,
                           'real': action.OtherAction},
    'ephys.ProbeModel': {'shadow': shadow_ephys.ProbeModel,
                         'real': ephys.ProbeModel},
    'ephys.ProbeInsertion': {'shadow': shadow_ephys.ProbeInsertion,
                             'real': ephys.ProbeInsertion},
    'reference.ProjectLabMember': {'real': reference.ProjectLabMember,
                                   'shadow': shadow_reference.ProjectLabMember},
    'subject.AlleleSequence': {'real': subject.AlleleSequence,
                               'shadow': shadow_subject.AlleleSequence},
    'subject.LineAllele': {'real': subject.LineAllele,
                           'shadow': shadow_subject.LineAllele},
    'action.SurgeryProcedure': {'real': action.SurgeryProcedure,
                                'shadow': shadow_action.SurgeryProcedure},
    'acquisition.ChildSession': {'real': acquisition.ChildSession,
                                 'shadow': shadow_acquisition.ChildSession},
    'acquisition.SessionUser': {'real': acquisition.SessionUser,
                                'shadow': shadow_acquisition.SessionUser},
    'acquisition.SessionProcedure': {'real': acquisition.SessionProcedure,
                                     'shadow': shadow_acquisition.SessionProcedure},
    'acquisition.SessionProject': {'real': acquisition.SessionProject,
                                   'shadow': shadow_acquisition.SessionProject},
    'data.ProjectRepository': {'real': data.ProjectRepository,
                               'shadow': shadow_data.ProjectRepository},
    'action.WaterRestrictionUser': {'real': action.WaterRestrictionUser,
                                    'shadow': shadow_action.WaterRestrictionUser},
    'action.WaterRestrictionProcedure': {'real': action.WaterRestrictionProcedure,
                                         'shadow': shadow_action.WaterRestrictionProcedure},
    'action.SurgeryUser': {'real': action.SurgeryUser,
                           'shadow': shadow_action.SurgeryUser},
    'acquisition.WaterAdministrationSession': {'real': acquisition.WaterAdministrationSession,
                                               'shadow': shadow_acquisition.WaterAdministrationSession}
}

DJ_SHADOW_MEMBERSHIP = {
    'reference.ProjectLabMember': {'dj_current_table': shadow_reference.ProjectLabMember,
                                   'alyx_parent_model': 'subjects.project',
                                   'alyx_field': 'users',
                                   'dj_parent_table': shadow_reference.Project,
                                   'dj_other_table': shadow_reference.LabMember,
                                   'dj_parent_fields': 'project_name',
                                   'dj_other_field': 'user_name',
                                   'dj_parent_uuid_name': 'project_uuid',
                                   'dj_other_uuid_name': 'user_uuid'},
    'subject.AlleleSequence': {
        'dj_current_table': shadow_subject.AlleleSequence,
        'alyx_parent_model': 'subjects.allele',
        'alyx_field': 'sequences',
        'dj_parent_table': shadow_subject.Allele,
        'dj_other_table': shadow_subject.Sequence,
        'dj_parent_fields': 'allele_name',
        'dj_other_field': 'sequence_name',
        'dj_parent_uuid_name': 'allele_uuid',
        'dj_other_uuid_name': 'sequence_uuid'},
    'subject.LineAllele': {'dj_current_table': shadow_subject.LineAllele,
                           'alyx_parent_model': 'subjects.line',
                           'alyx_field': 'alleles',
                           'dj_parent_table': shadow_subject.Line,
                           'dj_other_table': shadow_subject.Allele,
                           'dj_parent_fields': 'line_name',
                           'dj_other_field': 'allele_name',
                           'dj_parent_uuid_name': 'line_uuid',
                           'dj_other_uuid_name': 'allele_uuid'},
    'action.SurgeryProcedure': {
        'dj_current_table': shadow_action.SurgeryProcedure,
        'alyx_parent_model': 'actions.surgery',
        'alyx_field': 'procedures',
        'dj_parent_table': shadow_action.Surgery,
        'dj_other_table': shadow_action.ProcedureType,
        'dj_parent_fields': ['subject_uuid', 'surgery_start_time'],
        'dj_other_field': 'procedure_type_name',
        'dj_parent_uuid_name': 'surgery_uuid',
        'dj_other_uuid_name': 'procedure_type_uuid'},
    'acquisition.ChildSession': {
        'dj_current_table': shadow_acquisition.ChildSession,
        'alyx_parent_model': 'actions.session',
        'alyx_field': 'parent_session',
        'dj_parent_table': shadow_acquisition.Session,
        'dj_other_table': shadow_acquisition.Session,
        'dj_parent_fields': ['subject_uuid', 'session_start_time'],
        'dj_other_field': 'session_start_time',
        'dj_parent_uuid_name': 'session_uuid',
        'dj_other_uuid_name': 'session_uuid',
        'renamed_other_field_name': 'parent_session_start_time'},
    'acquisition.SessionUser': {
        'dj_current_table': shadow_acquisition.SessionUser,
        'alyx_parent_model': 'actions.session',
        'alyx_field': 'users',
        'dj_parent_table': shadow_acquisition.Session,
        'dj_other_table': shadow_reference.LabMember,
        'dj_parent_fields': ['subject_uuid', 'session_start_time'],
        'dj_other_field': 'user_name',
        'dj_parent_uuid_name': 'session_uuid',
        'dj_other_uuid_name': 'user_uuid'},
    'acquisition.SessionProcedure': {
        'dj_current_table': shadow_acquisition.SessionProcedure,
        'alyx_parent_model': 'actions.session',
        'alyx_field': 'procedures',
        'dj_parent_table': shadow_acquisition.Session,
        'dj_other_table': shadow_action.ProcedureType,
        'dj_parent_fields': ['subject_uuid', 'session_start_time'],
        'dj_other_field': 'procedure_type_name',
        'dj_parent_uuid_name': 'session_uuid',
        'dj_other_uuid_name': 'procedure_type_uuid'},
    'acquisition.SessionProject': {
        'dj_current_table': shadow_acquisition.SessionProject,
        'alyx_parent_model': 'actions.session',
        'alyx_field': 'project',
        'dj_parent_table': shadow_acquisition.Session,
        'dj_other_table': shadow_reference.Project,
        'dj_parent_fields': ['subject_uuid', 'session_start_time'],
        'dj_other_field': 'project_name',
        'dj_parent_uuid_name': 'session_uuid',
        'dj_other_uuid_name': 'project_uuid',
        'renamed_other_field_name': 'session_project'},
    'data.ProjectRepository': {
        'dj_current_table': shadow_data.ProjectRepository,
        'alyx_parent_model': 'subjects.project',
        'alyx_field': 'repositories',
        'dj_parent_table': shadow_reference.Project,
        'dj_other_table': shadow_data.DataRepository,
        'dj_parent_fields': 'project_name',
        'dj_other_field': 'repo_name',
        'dj_parent_uuid_name': 'project_uuid',
        'dj_other_uuid_name': 'repo_uuid'},
    'action.WaterRestrictionUser': {
        'dj_current_table': shadow_action.WaterRestrictionUser,
        'alyx_parent_model': 'actions.waterrestriction',
        'alyx_field': 'users',
        'dj_parent_table': shadow_action.WaterRestriction,
        'dj_other_table': shadow_reference.LabMember,
        'dj_parent_fields': ['subject_uuid', 'restriction_start_time'],
        'dj_other_field': 'user_name',
        'dj_parent_uuid_name': 'restriction_uuid',
        'dj_other_uuid_name': 'user_uuid'},
    'action.WaterRestrictionProcedure': {
        'dj_current_table': shadow_action.WaterRestrictionProcedure,
        'alyx_parent_model': 'actions.waterrestriction',
        'alyx_field': 'procedures',
        'dj_parent_table': shadow_action.WaterRestriction,
        'dj_other_table': shadow_action.ProcedureType,
        'dj_parent_fields': ['subject_uuid', 'restriction_start_time'],
        'dj_other_field': 'procedure_type_name',
        'dj_parent_uuid_name': 'restriction_uuid',
        'dj_other_uuid_name': 'procedure_type_uuid'},
    'action.SurgeryUser': {'dj_current_table': shadow_action.SurgeryUser,
                           'alyx_parent_model': 'actions.surgery',
                           'alyx_field': 'users',
                           'dj_parent_table': shadow_action.Surgery,
                           'dj_other_table': shadow_reference.LabMember,
                           'dj_parent_fields': ['subject_uuid', 'surgery_start_time'],
                           'dj_other_field': 'user_name',
                           'dj_parent_uuid_name': 'surgery_uuid',
                           'dj_other_uuid_name': 'user_uuid'},
    'acquisition.WaterAdministrationSession': {
        'dj_current_table': shadow_acquisition.WaterAdministrationSession,
        'alyx_parent_model': 'actions.wateradministration',
        'alyx_field': 'session',
        'dj_parent_table': shadow_action.WaterAdministration,
        'dj_other_table': shadow_acquisition.Session,
        'dj_parent_fields': ['subject_uuid', 'administration_time'],
        'dj_other_field': 'session_start_time',
        'dj_parent_uuid_name': 'wateradmin_uuid',
        'dj_other_uuid_name': 'session_uuid'}}

DJ_UPDATES = {
    'reference.Project': {
        'members': [],
        'alyx_model': alyx_subjects.models.Project,
    },
    'subject.Subject': {
        'members': ['SubjectLab', 'SubjectUser', 'SubjectProject', 'Death'],
        'alyx_model': alyx_subjects.models.Subject,
    },
    'action.Weighing': {
        'members': [],
        'alyx_model': alyx_actions.models.Weighing,
    },
    'action.WaterRestriction': {
        'members': [],
        'alyx_model': alyx_actions.models.WaterRestriction,
    },
    'action.WaterAdministration': {
        'members': [],
        'alyx_model': alyx_actions.models.WaterAdministration,
    },
    'acquisition.Session': {
        'members': ['SessionUser', 'SessionProject'],
        'alyx_model': alyx_actions.models.Session,
    }
}


@schema
class IngestionJob(dj.Manual):
    """
    Starting point of the ingestion routine
    There is an external process doing:
    1. download the latest alyx sql-dump
    2. load that sql-dump to post-gres DB
    3. Create and insert an entry into this table
    """
    definition = """
    job_datetime: datetime  # UTC time
    ---
    alyx_sql_dump: varchar(36)
    job_status: enum('completed', 'on-going', 'terminated')
    """

    @classmethod
    def create_entry(cls, alyx_sql_dump):
        for key in (IngestionJob & 'job_status = "on-going"').fetch('KEY'):
            (IngestionJob & key)._update('job_status', 'terminated')
        cls.insert1({'job_datetime': datetime.utcnow(),
                     'alyx_sql_dump': alyx_sql_dump,
                     'job_status': 'on-going'})


@schema
class UpdateAlyxRawModel(dj.Computed):
    definition = """
    -> IngestionJob
    alyx_model_name: varchar(36)
    """

    key_source = IngestionJob & 'job_status = "on-going"'

    def make(self, key):
        # delete UpdateAlyxRaw
        with dj.config(safemode=False):
            alyxraw.UpdateAlyxRaw.delete()
        # specify alyx models to be ingested into UpdateAlyxRaw
        self.insert({**key, 'alyx_model_name': alyx_model_name}
                    for alyx_model_name in ALYX_MODELS)


@schema
class IngestUpdateAlyxRawModel(dj.Computed):
    definition = """
    -> UpdateAlyxRawModel
    ---
    record_count: int
    duration: float
    """

    key_source = UpdateAlyxRawModel * IngestionJob & 'job_status = "on-going"'

    def make(self, key):
        alyx_model = ALYX_MODELS[key['alyx_model_name']]

        start_time = time.time()
        ingest_alyx_raw_postgres.insert_alyx_entries_model(alyx_model,
                                                           AlyxRawTable=alyxraw.UpdateAlyxRaw,
                                                           skip_existing_alyxraw=True)
        end_time = time.time()

        self.insert1({**key,
                      'record_count': len(alyxraw.UpdateAlyxRaw
                                          & {'model': key['alyx_model_name']}),
                      'duration': end_time - start_time})


@schema
class AlyxRawDiff(dj.Computed):
    definition = """
    -> IngestUpdateAlyxRawModel
    """

    class CreatedEntry(dj.Part):
        definition = """
        -> master
        -> alyxraw.UpdateAlyxRaw
        """

    class DeletedEntry(dj.Part):
        definition = """
        -> master
        -> alyxraw.UpdateAlyxRaw
        """

    class ModifiedEntry(dj.Part):
        definition = """
        -> master
        -> alyxraw.UpdateAlyxRaw
        """

    key_source = IngestUpdateAlyxRawModel * IngestionJob & 'job_status = "on-going"'

    def make(self, key):
        self.insert1(key)

        # newly created
        created_entries = ((alyxraw.UpdateAlyxRaw - alyxraw.AlyxRaw.proj())
                           & {'model': key['alyx_model_name']})
        self.CreatedEntry.insert(created_entries.proj(
            ..., alyx_model_name=f'"{key["alyx_model_name"]}"',
            job_datetime=f'"{key["job_datetime"]}"'))

        if key['alyx_model_name'] in ('subjects.project',
                                      'subjects.subject',
                                      'actions.weighing',
                                      'actions.waterrestriction',
                                      'actions.wateradministration',
                                      'actions.models.session'):
            # deleted
            deleted_entries = ((alyxraw.AlyxRaw - alyxraw.UpdateAlyxRaw.proj()) &
                               {'model': key['alyx_model_name']})
            self.DeletedEntry.insert(deleted_entries.proj(
                ..., alyx_model_name=f'"{key["alyx_model_name"]}"',
                job_datetime=f'"{key["job_datetime"]}"'))

            # updated
            fields_original = (alyxraw.AlyxRaw.Field
                               & (alyxraw.AlyxRaw & {'model': key['alyx_model_name']}))
            fields_update = (alyxraw.UpdateAlyxRaw.Field
                             & (alyxraw.UpdateAlyxRaw & {'model': key['alyx_model_name']}))

            fields_restriction = {}

            modified_entries = (alyxraw.AlyxRaw &
                                (fields_update.proj(fvalue_new='fvalue') * fields_original
                                 & 'fvalue_new != fvalue' & 'fname not in ("json")'
                                 & fields_restriction))
            self.ModifiedEntry.insert(modified_entries.proj(
                ..., alyx_model_name=f'"{key["alyx_model_name"]}"',
                job_datetime=f'"{key["job_datetime"]}"'))


@schema
class DeleteModifiedAlyxRaw(dj.Computed):
    definition = """
    -> AlyxRawDiff
    """

    key_source = (AlyxRawDiff * IngestionJob
                  & [AlyxRawDiff.ModifiedEntry, AlyxRawDiff.DeletedEntry]
                  & 'job_status = "on-going"')

    def make(self, key):
        """
        For actions.session, delete only the AlyxRaw.Field of the modified/deleted entries
        For any other alyx model, delete the AlyxRaw
        (note: deleting is tricky, beware grid-lock)
        """
        entries_to_delete = AlyxRawDiff.ModifiedEntry + AlyxRawDiff.DeletedEntry & key
        keys_to_delete = entries_to_delete.fetch('KEY')

        logger.info(f'Deletion in AlyxRaw: {key["alyx_model_name"]}'
                    f' - {len(keys_to_delete)} records')

        # handle AlyxRaw table
        if key['alyx_model_name'] == 'actions.session':
            alyxraw_field_buffer = QueryBuffer(
                alyxraw.AlyxRaw.Field & 'fname!="start_time"'
                & (alyxraw.AlyxRaw & {'model': key['alyx_model_name']}))
            for pk in keys_to_delete:
                alyxraw_field_buffer.add_to_queue1(pk)
                alyxraw_field_buffer.flush_delete(chunksz=50, quick=True)
            alyxraw_field_buffer.flush_delete(quick=True)
        else:
            alyxraw_buffer = QueryBuffer(alyxraw.AlyxRaw & {'model': key['alyx_model_name']})
            for pk in keys_to_delete:
                alyxraw_buffer.add_to_queue1(pk)
                alyxraw_buffer.flush_delete(chunksz=50, quick=False)
            alyxraw_buffer.flush_delete(quick=False)

        # handle shadow membership tables
        if key['alyx_model_name'] in MEMBERSHIP_ALYX_MODELS:
            for membership_table in MEMBERSHIP_ALYX_MODELS[key['alyx_model_name']]:
                logger.info(f'\tDeleting shadow membership table: {membership_table.__name__}')

                uuid_attr = next((attr for attr in membership_table.heading.names
                                  if attr.endswith('uuid')))
                with dj.config(safemode=False):
                    (membership_table & entries_to_delete.proj(**{uuid_attr: 'uuid'})).delete()

        self.insert1(key)


@schema
class IngestAlyxRawModel(dj.Computed):
    definition = """
    -> AlyxRawDiff
    """

    @property
    def key_source(self):
        key_source = (AlyxRawDiff * IngestionJob
                      & [AlyxRawDiff.CreatedEntry, AlyxRawDiff.ModifiedEntry]
                      & 'job_status = "on-going"')
        return (key_source - DeleteModifiedAlyxRaw.key_source) + DeleteModifiedAlyxRaw

    def make(self, key):
        entries_to_ingest = AlyxRawDiff.CreatedEntry + AlyxRawDiff.ModifiedEntry & key

        logger.info(f'Ingestion to AlyxRaw: {key["alyx_model_name"]}'
                    f' - {len(entries_to_ingest)} records')

        if key['alyx_model_name'] != 'actions.session':
            alyxraw.AlyxRaw.insert(alyxraw.UpdateAlyxRaw & entries_to_ingest)

        alyxraw.AlyxRaw.Field.insert(alyxraw.UpdateAlyxRaw.Field & entries_to_ingest)

        self.insert1(key)


@schema
class ShadowTable(dj.Computed):
    definition = """
    -> IngestionJob
    table_name: varchar(36)
    """

    # this table is populated only after all the IngestAlyxRawModel populate jobs have finished
    key_source = (IngestionJob & 'job_status = "on-going"'
                  & ((IngestionJob.aggr(IngestAlyxRawModel.key_source, ks_count='count(*)'))
                     * (IngestionJob.aggr(IngestAlyxRawModel, completed_count='count(*)'))
                     & 'ks_count = completed_count'))

    def make(self, key):
        self.insert({**key, 'table_name': table_name}
                    for table_name in DJ_TABLES)


@schema
class PopulateShadowTable(dj.Computed):
    definition = """
    -> ShadowTable
    ---
    incomplete_count=null: int  # how many to be populated
    completion_count=null: int  # how many has been populated
    """

    key_source = ShadowTable * IngestionJob & 'job_status = "on-going"'

    def make(self, key):
        is_membership = key['table_name'] in DJ_SHADOW_MEMBERSHIP
        
        shadow_table = DJ_TABLES[key['table_name']]['shadow']
        before_count, _ = shadow_table.progress() if not is_membership else (None, None)

        if key['table_name'] == 'acquisition.Session':
            """
            if a session entry is modified, replace the entry without deleting
            this is to keep the session entry when uuid is not changed but start time changed
            by one sec. We don't update start_time in alyxraw in this case.
            """
            modified_uuids = (AlyxRawDiff.ModifiedEntry
                              & {'model': 'actions.session'} & key).fetch('uuid')
            modified_session_keys = [{'session_uuid': uuid} for uuid in modified_uuids]

            sessions = shadow_table & modified_session_keys
            if sessions:
                modified_session_entries = []
                for key in sessions.fetch('KEY'):
                    try:
                        modified_session_entries.append(shadow_table.create_entry(key))
                    except:
                        logger.debug(f'Error creating entry for key: {key}')
                if modified_session_entries:
                    try:
                        shadow_table.insert(modified_session_entries,
                                 allow_direct_insert=True, replace=True)
                    except dj.DataJointError:
                        for entry in modified_session_entries:
                            shadow_table.insert1(entry, allow_direct_insert=True, replace=True)

        if key['table_name'] in ('data.DataSet', 'data.FileRecord'):
            query_buffer = QueryBuffer(shadow_table, verbose=True)
            for key in (shadow_table.key_source - shadow_table).fetch('KEY'):
                query_buffer.add_to_queue1(shadow_table.create_entry(key))
                query_buffer.flush_insert(skip_duplicates=True, allow_direct_insert=True,
                                          chunksz=1000)
            query_buffer.flush_insert(skip_duplicates=True, allow_direct_insert=True)
        elif is_membership:
            tab_args = DJ_SHADOW_MEMBERSHIP[key['table_name']]
            ingest_membership.ingest_membership_table(**tab_args)
        else:
            self.connection.cancel_transaction()
            # no parallelization here
            shadow_table.populate(display_progress=True, suppress_errors=True)

        after_count, _ = shadow_table.progress() if not is_membership else (None, None)
        self.insert1({**key, 'incomplete_count': before_count,
                      'completion_count': before_count - after_count})


@schema
class CopyRealTable(dj.Computed):
    definition = """
    -> PopulateShadowTable
    """

    key_source = PopulateShadowTable * IngestionJob & 'job_status = "on-going"'

    def make(self, key):
        shadow_table = DJ_TABLES[key['table_name']]['shadow']
        real_table = DJ_TABLES[key['table_name']]['real']
        target_module = inspect.getmodule(real_table)
        source_module = inspect.getmodule(shadow_table)

        ingest_real.copy_table(target_module, source_module, key['table_name'])

        self.insert1(key)


@schema
class UpdateRealTable(dj.Computed):
    definition = """
    -> CopyRealTable
    """

    key_source = (CopyRealTable * IngestionJob & 'job_status = "on-going"'
                  & [f'table_name = "{table_name}"' for table_name in DJ_UPDATES])

    def make(self, key):
        alyx_model_name = DJ_UPDATES[key['table_name']]['alyx_model']

        real_table = DJ_TABLES[key['table_name']]['real']
        shadow_table = DJ_TABLES[key['table_name']]['shadow']
        target_module = inspect.getmodule(real_table)
        source_module = inspect.getmodule(shadow_table)

        modified_uuids = (AlyxRawDiff.ModifiedEntry & key
                          & {'alyx_model_name': alyx_model_name}).fetch('uuid')

        uuid_attr = next((attr for attr in real_table.heading.names
                          if attr.endswith('uuid')))

        query = real_table & [{uuid_attr: u} for u in modified_uuids]

        if query:
            delete_update_entries.update_fields(target_module,
                                                source_module,
                                                real_table.__name__,
                                                pks=query.fetch('KEY'),
                                                log_to_UpdateRecord=False)
            member_tables = DJ_UPDATES[key['table_name']]['members']
            for member_table_name in member_tables:
                member_table = getattr(source_module, member_table_name)
                if member_table & query:
                    delete_update_entries.update_fields(
                        target_module, source_module, member_table_name,
                        pks=(member_table & query).fetch('KEY'),
                        log_to_UpdateRecord=True)

        self.insert1(key)

# what's next
"""
    populate_behavior.main(backtrack_days=30)
    populate_wheel.main(backtrack_days=30)
    populate_ephys.main()
"""
