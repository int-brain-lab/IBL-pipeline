import datetime
import inspect
import logging
import os
import time

import datajoint as dj
from ibl_pipeline.process import (
    alyx_models,
    extract_models_entry,
    get_django_model_name,
    get_django_models,
)
from ibl_pipeline.utils import get_logger

logger = get_logger(__name__)
logger.info("Creating ingest job tables")

schema = dj.schema(dj.config["database.prefix"] + "ibl_ingest_job")


@schema
class TimeZone(dj.Lookup):
    definition = """
    timezone:      varchar(16)
    """
    contents = zip(["European", "EST", "PST", "other"])


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


# fmt: off
@schema
class Task(dj.Lookup):
    definition = """
    task                    : varchar(64)
    ---
    task_order              : tinyint
    task_description=''     : varchar(1024)
    """

    contents = [
        ["Ingest to update_alyxraw", 1, "Ingest selected tables to schema update_alyxraw"],
        ["Get modified deleted pks", 2, "Get modified deleted pks"],
        ["Delete alyxraw", 3, "Delete alyxraw and shadow table entries for updated and deleted records"],
        ["Delete shadow membership", 4, "Delete shadow membership records for updated and deleted records"],
        ["Ingest alyxraw", 5, "Ingest to alyxraw"],
        ["Ingest shadow", 6, "Ingest to alyx shadow tables"],
        ["Ingest shadow membership", 7, "Ingest to alyx shadow membership tables"],
        ["Ingest real", 8, "Ingest to alyx real tables"],
        ["Update fields", 9, "Update fields in real tables"],
        ["Populate behavior", 10, "Populate behavior tables"],
    ]
# fmt: on


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
        cls.insert1(
            dict(
                **job_key,
                task=task,
                task_start_time=start,
                task_end_time=end,
                task_duration=(end - start).total_seconds() / 60.0,
            ),
            skip_duplicates=True,
        )


# ================== Orchestrating the ingestion jobs =============

import actions as alyx_actions
import experiments as alyx_experiments
import misc as alyx_misc
import subjects as alyx_subjects

import data as alyx_data

# isort: split
from ibl_pipeline import (
    acquisition,
    action,
    data,
    ephys,
    histology,
    mode,
    qc,
    reference,
    subject,
)
from ibl_pipeline.ingest import QueryBuffer, ShadowIngestionError
from ibl_pipeline.ingest import acquisition as shadow_acquisition
from ibl_pipeline.ingest import action as shadow_action
from ibl_pipeline.ingest import alyxraw
from ibl_pipeline.ingest import data as shadow_data
from ibl_pipeline.ingest import ephys as shadow_ephys
from ibl_pipeline.ingest import histology as shadow_histology
from ibl_pipeline.ingest import qc as shadow_qc
from ibl_pipeline.ingest import reference as shadow_reference
from ibl_pipeline.ingest import subject as shadow_subject
from ibl_pipeline.process import (
    delete_update_entries,
    ingest_alyx_raw_postgres,
    ingest_membership,
    ingest_real,
)

# --------- Some constants -------

_backtrack_days = int(os.getenv("BACKTRACK_DAYS", 0))

ALYX_MODELS = alyx_models(as_dict=True)

MEMBERSHIP_ALYX_MODELS = {
    "subjects.project": ["reference.ProjectLabMember", "data.ProjectRepository"],
    "subjects.allele": ["subject.AlleleSequence"],
    "subjects.line": ["subject.LineAllele"],
    "actions.surgery": ["action.SurgeryProcedure", "action.SurgeryUser"],
    "actions.session": [
        "acquisition.ChildSession",
        "acquisition.SessionUser",
        "acquisition.SessionProcedure",
        "acquisition.SessionProject",
        shadow_qc.SessionQCIngest,
        qc.SessionQC,
        qc.SessionExtendedQC,
    ],
    "actions.waterrestriction": [
        "action.WaterRestrictionUser",
        "action.WaterRestrictionProcedure",
    ],
    "actions.wateradministration": ["acquisition.WaterAdministrationSession"],
    "experiments.probeinsertion": [
        shadow_qc.ProbeInsertionQCIngest,
        qc.ProbeInsertionQC,
        qc.ProbeInsertionExtendedQC,
    ],
    "experiments.trajectoryestimate": [
        histology.ProbeTrajectoryTemp if mode != "public" else None
    ],
}

DJ_TABLES = {
    "reference.Lab": {"shadow": shadow_reference.Lab, "real": reference.Lab},
    "reference.LabMember": {
        "shadow": shadow_reference.LabMember,
        "real": reference.LabMember,
    },
    "reference.LabMembership": {
        "shadow": shadow_reference.LabMembership,
        "real": reference.LabMembership,
    },
    "reference.LabLocation": {
        "shadow": shadow_reference.LabLocation,
        "real": reference.LabLocation,
    },
    "reference.Project": {
        "shadow": shadow_reference.Project,
        "real": reference.Project,
    },
    "reference.CoordinateSystem": {
        "shadow": shadow_reference.CoordinateSystem,
        "real": reference.CoordinateSystem,
    },
    "subject.Species": {"shadow": shadow_subject.Species, "real": subject.Species},
    "subject.Source": {"shadow": shadow_subject.Source, "real": subject.Source},
    "subject.Strain": {"shadow": shadow_subject.Strain, "real": subject.Strain},
    "subject.Sequence": {"shadow": shadow_subject.Sequence, "real": subject.Sequence},
    "subject.Allele": {"shadow": shadow_subject.Allele, "real": subject.Allele},
    "subject.Line": {"shadow": shadow_subject.Line, "real": subject.Line},
    "subject.Subject": {"shadow": shadow_subject.Subject, "real": subject.Subject},
    "subject.BreedingPair": {
        "shadow": shadow_subject.BreedingPair,
        "real": subject.BreedingPair,
    },
    "subject.Litter": {"shadow": shadow_subject.Litter, "real": subject.Litter},
    "subject.LitterSubject": {
        "shadow": shadow_subject.LitterSubject,
        "real": subject.LitterSubject,
    },
    "subject.SubjectProject": {
        "shadow": shadow_subject.SubjectProject,
        "real": subject.SubjectProject,
    },
    "subject.SubjectUser": {
        "shadow": shadow_subject.SubjectUser,
        "real": subject.SubjectUser,
    },
    "subject.SubjectLab": {
        "shadow": shadow_subject.SubjectLab,
        "real": subject.SubjectLab,
    },
    "subject.Caging": {"shadow": shadow_subject.Caging, "real": subject.Caging},
    "subject.UserHistory": {
        "shadow": shadow_subject.UserHistory,
        "real": subject.UserHistory,
    },
    "subject.Weaning": {"shadow": shadow_subject.Weaning, "real": subject.Weaning},
    "subject.Death": {"shadow": shadow_subject.Death, "real": subject.Death},
    "subject.GenotypeTest": {
        "shadow": shadow_subject.GenotypeTest,
        "real": subject.GenotypeTest,
    },
    "subject.Zygosity": {"shadow": shadow_subject.Zygosity, "real": subject.Zygosity},
    "action.ProcedureType": {
        "shadow": shadow_action.ProcedureType,
        "real": action.ProcedureType,
    },
    "acquisition.Session": {
        "shadow": shadow_acquisition.Session,
        "real": acquisition.Session,
    },
    "data.DataFormat": {"shadow": shadow_data.DataFormat, "real": data.DataFormat},
    "data.DataRepositoryType": {
        "shadow": shadow_data.DataRepositoryType,
        "real": data.DataRepositoryType,
    },
    "data.DataRepository": {
        "shadow": shadow_data.DataRepository,
        "real": data.DataRepository,
    },
    "data.DataSetType": {"shadow": shadow_data.DataSetType, "real": data.DataSetType},
    "data.DataSet": {"shadow": shadow_data.DataSet, "real": data.DataSet},
    "data.FileRecord": {"shadow": shadow_data.FileRecord, "real": data.FileRecord},
    "subject.SubjectCullMethod": {
        "shadow": shadow_subject.SubjectCullMethod,
        "real": subject.SubjectCullMethod if mode != "public" else None,
    },
    "action.Weighing": {
        "shadow": shadow_action.Weighing,
        "real": action.Weighing if mode != "public" else None,
    },
    "action.WaterType": {
        "shadow": shadow_action.WaterType,
        "real": action.WaterType if mode != "public" else None,
    },
    "action.WaterAdministration": {
        "shadow": shadow_action.WaterAdministration,
        "real": action.WaterAdministration if mode != "public" else None,
    },
    "action.WaterRestriction": {
        "shadow": shadow_action.WaterRestriction,
        "real": action.WaterRestriction if mode != "public" else None,
    },
    "action.Surgery": {
        "shadow": shadow_action.Surgery,
        "real": action.Surgery if mode != "public" else None,
    },
    "action.CullMethod": {
        "shadow": shadow_action.CullMethod,
        "real": action.CullMethod if mode != "public" else None,
    },
    "action.CullReason": {
        "shadow": shadow_action.CullReason,
        "real": action.CullReason if mode != "public" else None,
    },
    "action.Cull": {
        "shadow": shadow_action.Cull,
        "real": action.Cull if mode != "public" else None,
    },
    "action.OtherAction": {
        "shadow": shadow_action.OtherAction,
        "real": action.OtherAction if mode != "public" else None,
    },
    "ephys.ProbeModel": {"shadow": shadow_ephys.ProbeModel, "real": ephys.ProbeModel},
    "ephys.ProbeInsertion": {
        "shadow": shadow_ephys.ProbeInsertion,
        "real": ephys.ProbeInsertion,
    },
    "reference.ProjectLabMember": {
        "real": reference.ProjectLabMember,
        "shadow": shadow_reference.ProjectLabMember,
    },
    "subject.AlleleSequence": {
        "real": subject.AlleleSequence,
        "shadow": shadow_subject.AlleleSequence,
    },
    "subject.LineAllele": {
        "real": subject.LineAllele,
        "shadow": shadow_subject.LineAllele,
    },
    "action.SurgeryProcedure": {
        "real": action.SurgeryProcedure if mode != "public" else None,
        "shadow": shadow_action.SurgeryProcedure,
    },
    "acquisition.ChildSession": {
        "real": acquisition.ChildSession,
        "shadow": shadow_acquisition.ChildSession,
    },
    "acquisition.SessionUser": {
        "real": acquisition.SessionUser,
        "shadow": shadow_acquisition.SessionUser,
    },
    "acquisition.SessionProcedure": {
        "real": acquisition.SessionProcedure,
        "shadow": shadow_acquisition.SessionProcedure,
    },
    "acquisition.SessionProject": {
        "real": acquisition.SessionProject,
        "shadow": shadow_acquisition.SessionProject,
    },
    "data.ProjectRepository": {
        "real": data.ProjectRepository,
        "shadow": shadow_data.ProjectRepository,
    },
    "action.WaterRestrictionUser": {
        "real": action.WaterRestrictionUser if mode != "public" else None,
        "shadow": shadow_action.WaterRestrictionUser,
    },
    "action.WaterRestrictionProcedure": {
        "real": action.WaterRestrictionProcedure if mode != "public" else None,
        "shadow": shadow_action.WaterRestrictionProcedure,
    },
    "action.SurgeryUser": {
        "real": action.SurgeryUser if mode != "public" else None,
        "shadow": shadow_action.SurgeryUser,
    },
    "acquisition.WaterAdministrationSession": {
        "real": acquisition.WaterAdministrationSession if mode != "public" else None,
        "shadow": shadow_acquisition.WaterAdministrationSession,
    },
    "qc.SessionQCIngest": {
        "real": None,
        "shadow": shadow_qc.SessionQCIngest,
    },
    "qc.ProbeInsertionQCIngest": {
        "real": None,
        "shadow": shadow_qc.ProbeInsertionQCIngest,
    },
    "histology.ProbeTrajectoryTemp": {
        "real": histology.ProbeTrajectoryTemp if mode != "public" else None,
        "shadow": shadow_histology.ProbeTrajectoryTemp,
    },
    "histology.ChannelBrainLocationTemp": {
        "real": histology.ChannelBrainLocationTemp if mode != "public" else None,
        "shadow": shadow_histology.ChannelBrainLocationTemp,
    },
}

DJ_SHADOW_MEMBERSHIP = {
    "reference.ProjectLabMember": {
        "dj_current_table": shadow_reference.ProjectLabMember,
        "alyx_parent_model": "subjects.project",
        "alyx_field": "users",
        "dj_parent_table": shadow_reference.Project,
        "dj_other_table": shadow_reference.LabMember,
        "dj_parent_fields": "project_name",
        "dj_other_field": "user_name",
        "dj_parent_uuid_name": "project_uuid",
        "dj_other_uuid_name": "user_uuid",
    },
    "subject.AlleleSequence": {
        "dj_current_table": shadow_subject.AlleleSequence,
        "alyx_parent_model": "subjects.allele",
        "alyx_field": "sequences",
        "dj_parent_table": shadow_subject.Allele,
        "dj_other_table": shadow_subject.Sequence,
        "dj_parent_fields": "allele_name",
        "dj_other_field": "sequence_name",
        "dj_parent_uuid_name": "allele_uuid",
        "dj_other_uuid_name": "sequence_uuid",
    },
    "subject.LineAllele": {
        "dj_current_table": shadow_subject.LineAllele,
        "alyx_parent_model": "subjects.line",
        "alyx_field": "alleles",
        "dj_parent_table": shadow_subject.Line,
        "dj_other_table": shadow_subject.Allele,
        "dj_parent_fields": "line_name",
        "dj_other_field": "allele_name",
        "dj_parent_uuid_name": "line_uuid",
        "dj_other_uuid_name": "allele_uuid",
    },
    "action.SurgeryProcedure": {
        "dj_current_table": shadow_action.SurgeryProcedure,
        "alyx_parent_model": "actions.surgery",
        "alyx_field": "procedures",
        "dj_parent_table": shadow_action.Surgery,
        "dj_other_table": shadow_action.ProcedureType,
        "dj_parent_fields": ["subject_uuid", "surgery_start_time"],
        "dj_other_field": "procedure_type_name",
        "dj_parent_uuid_name": "surgery_uuid",
        "dj_other_uuid_name": "procedure_type_uuid",
    },
    "acquisition.ChildSession": {
        "dj_current_table": shadow_acquisition.ChildSession,
        "alyx_parent_model": "actions.session",
        "alyx_field": "parent_session",
        "dj_parent_table": shadow_acquisition.Session,
        "dj_other_table": shadow_acquisition.Session,
        "dj_parent_fields": ["subject_uuid", "session_start_time"],
        "dj_other_field": "session_start_time",
        "dj_parent_uuid_name": "session_uuid",
        "dj_other_uuid_name": "session_uuid",
        "renamed_other_field_name": "parent_session_start_time",
    },
    "acquisition.SessionUser": {
        "dj_current_table": shadow_acquisition.SessionUser,
        "alyx_parent_model": "actions.session",
        "alyx_field": "users",
        "dj_parent_table": shadow_acquisition.Session,
        "dj_other_table": shadow_reference.LabMember,
        "dj_parent_fields": ["subject_uuid", "session_start_time"],
        "dj_other_field": "user_name",
        "dj_parent_uuid_name": "session_uuid",
        "dj_other_uuid_name": "user_uuid",
    },
    "acquisition.SessionProcedure": {
        "dj_current_table": shadow_acquisition.SessionProcedure,
        "alyx_parent_model": "actions.session",
        "alyx_field": "procedures",
        "dj_parent_table": shadow_acquisition.Session,
        "dj_other_table": shadow_action.ProcedureType,
        "dj_parent_fields": ["subject_uuid", "session_start_time"],
        "dj_other_field": "procedure_type_name",
        "dj_parent_uuid_name": "session_uuid",
        "dj_other_uuid_name": "procedure_type_uuid",
    },
    "acquisition.SessionProject": {
        "dj_current_table": shadow_acquisition.SessionProject,
        "alyx_parent_model": "actions.session",
        "alyx_field": "project",
        "dj_parent_table": shadow_acquisition.Session,
        "dj_other_table": shadow_reference.Project,
        "dj_parent_fields": ["subject_uuid", "session_start_time"],
        "dj_other_field": "project_name",
        "dj_parent_uuid_name": "session_uuid",
        "dj_other_uuid_name": "project_uuid",
        "renamed_other_field_name": "session_project",
    },
    "data.ProjectRepository": {
        "dj_current_table": shadow_data.ProjectRepository,
        "alyx_parent_model": "subjects.project",
        "alyx_field": "repositories",
        "dj_parent_table": shadow_reference.Project,
        "dj_other_table": shadow_data.DataRepository,
        "dj_parent_fields": "project_name",
        "dj_other_field": "repo_name",
        "dj_parent_uuid_name": "project_uuid",
        "dj_other_uuid_name": "repo_uuid",
    },
    "action.WaterRestrictionUser": {
        "dj_current_table": shadow_action.WaterRestrictionUser,
        "alyx_parent_model": "actions.waterrestriction",
        "alyx_field": "users",
        "dj_parent_table": shadow_action.WaterRestriction,
        "dj_other_table": shadow_reference.LabMember,
        "dj_parent_fields": ["subject_uuid", "restriction_start_time"],
        "dj_other_field": "user_name",
        "dj_parent_uuid_name": "restriction_uuid",
        "dj_other_uuid_name": "user_uuid",
    },
    "action.WaterRestrictionProcedure": {
        "dj_current_table": shadow_action.WaterRestrictionProcedure,
        "alyx_parent_model": "actions.waterrestriction",
        "alyx_field": "procedures",
        "dj_parent_table": shadow_action.WaterRestriction,
        "dj_other_table": shadow_action.ProcedureType,
        "dj_parent_fields": ["subject_uuid", "restriction_start_time"],
        "dj_other_field": "procedure_type_name",
        "dj_parent_uuid_name": "restriction_uuid",
        "dj_other_uuid_name": "procedure_type_uuid",
    },
    "action.SurgeryUser": {
        "dj_current_table": shadow_action.SurgeryUser,
        "alyx_parent_model": "actions.surgery",
        "alyx_field": "users",
        "dj_parent_table": shadow_action.Surgery,
        "dj_other_table": shadow_reference.LabMember,
        "dj_parent_fields": ["subject_uuid", "surgery_start_time"],
        "dj_other_field": "user_name",
        "dj_parent_uuid_name": "surgery_uuid",
        "dj_other_uuid_name": "user_uuid",
    },
    "acquisition.WaterAdministrationSession": {
        "dj_current_table": shadow_acquisition.WaterAdministrationSession,
        "alyx_parent_model": "actions.wateradministration",
        "alyx_field": "session",
        "dj_parent_table": shadow_action.WaterAdministration,
        "dj_other_table": shadow_acquisition.Session,
        "dj_parent_fields": ["subject_uuid", "administration_time"],
        "dj_other_field": "session_start_time",
        "dj_parent_uuid_name": "wateradmin_uuid",
        "dj_other_uuid_name": "session_uuid",
    },
}

DJ_UPDATES = {
    "reference.Project": {
        "members": [],
        "alyx_model": alyx_subjects.models.Project,
    },
    "subject.Subject": {
        "members": ["SubjectLab", "SubjectUser", "SubjectProject", "Death"],
        "alyx_model": alyx_subjects.models.Subject,
    },
    "action.Weighing": {
        "members": [],
        "alyx_model": alyx_actions.models.Weighing,
    },
    "action.WaterRestriction": {
        "members": [],
        "alyx_model": alyx_actions.models.WaterRestriction,
    },
    "action.WaterAdministration": {
        "members": [],
        "alyx_model": alyx_actions.models.WaterAdministration,
    },
    "acquisition.Session": {
        "members": ["SessionUser", "SessionProject"],
        "alyx_model": alyx_actions.models.Session,
    },
}


# ------ Pipeline for ingestion orchestration ------


def cleanup_shadow_schema_jobs():
    """
    Routine to clean up any error jobs of type "ShadowIngestionError"
     in jobs tables of the shadow schemas
    """
    _generic_errors = [
        "%Deadlock%",
        "%DuplicateError%",
        "%Lock wait timeout%",
        "%MaxRetryError%",
        "%KeyboardInterrupt%",
        "InternalError: (1205%",
        "%SIGTERM%",
        "LostConnectionError",
    ]

    for shadow_schema in (
        shadow_reference,
        shadow_subject,
        shadow_action,
        shadow_acquisition,
        shadow_data,
        shadow_ephys,
        shadow_qc,
        shadow_histology,
    ):
        # clear generic error jobs
        (
            shadow_schema.schema.jobs
            & 'status = "error"'
            & [
                f'error_message LIKE "{e}"'
                for e in _generic_errors + ["%ShadowIngestionError%"]
            ]
        ).delete()
        # clear stale "reserved" jobs
        stale_jobs = (shadow_schema.schema.jobs & 'status = "reserved"').proj(
            elapsed_days="TIMESTAMPDIFF(DAY, timestamp, NOW())"
        ) & "elapsed_days > 1"
        (shadow_schema.schema.jobs & stale_jobs).delete()


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
    new_job_string: varchar(36)  # '2021-10-26'
    job_status: enum('completed', 'on-going', 'terminated')
    job_endtime=null: datetime  # UTC time
    """

    @classmethod
    def create_entry(cls, new_job_string):
        try:
            with cls.connection.transaction:
                for key in (cls & 'job_status = "on-going"').fetch("KEY"):
                    (cls & key)._update("job_status", "terminated")
                    (cls & key)._update("job_endtime", datetime.datetime.utcnow())
                cls.insert1(
                    {
                        "job_datetime": datetime.datetime.utcnow(),
                        "new_job_string": new_job_string,
                        "job_status": "on-going",
                    }
                )
                assert len(cls & 'job_status = "on-going"') == 1
        except AssertionError:
            pass
        else:
            cleanup_shadow_schema_jobs()

    @classmethod
    def get_on_going_key(cls):
        return (cls & 'job_status = "on-going"').fetch1("KEY")

    @classmethod
    def get_latest_key(cls):
        latest = cls.fetch("KEY", order_by="job_datetime DESC", limit=1)
        return latest[0] if latest else {}


def _terminate_all():
    with IngestionJob.connection.transaction:
        for key in (IngestionJob & 'job_status = "on-going"').fetch("KEY"):
            (IngestionJob & key)._update("job_status", "terminated")
            (IngestionJob & key)._update("job_endtime", datetime.datetime.utcnow())

    reserved_connections = (schema.jobs & 'status = "reserved"').fetch("connection_id")

    terminated_count = 0
    if len(reserved_connections):
        restriction_str = ",".join(reserved_connections.astype(str))
        terminated_count = dj.admin.kill_quick(restriction=f"ID in ({restriction_str})")
    print(f"{terminated_count} connections killed")


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
        self.insert(
            {**key, "alyx_model_name": alyx_model_name}
            for alyx_model_name in ALYX_MODELS
        )


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
        logger.info(f"Populating UpdateAlyxRaw for: {key['alyx_model_name']}")
        alyx_model = ALYX_MODELS[key["alyx_model_name"]]

        # break transaction here, allowing for partial completion
        self.connection.cancel_transaction()

        start_time = time.time()
        ingest_alyx_raw_postgres.insert_alyx_entries_model(
            alyx_model,
            AlyxRawTable=alyxraw.UpdateAlyxRaw,
            backtrack_days=_backtrack_days,
            skip_existing_alyxraw=True,
        )
        end_time = time.time()

        self.insert1(
            {
                **key,
                "record_count": len(
                    alyxraw.UpdateAlyxRaw & {"model": key["alyx_model_name"]}
                ),
                "duration": end_time - start_time,
            }
        )


@schema
class AlyxRawDiff(dj.Computed):
    definition = """
    -> IngestUpdateAlyxRawModel
    """

    class CreatedEntry(dj.Part):
        definition = """
        -> master
        uuid: uuid  # pk field (uuid string repr)
        """

    class DeletedEntry(dj.Part):
        definition = """
        -> master
        uuid: uuid  # pk field (uuid string repr)
        """

    class ModifiedEntry(dj.Part):
        definition = """
        -> master
        uuid: uuid  # pk field (uuid string repr)
        """

    key_source = IngestUpdateAlyxRawModel * IngestionJob & 'job_status = "on-going"'

    def make(self, key):
        self.insert1(key)

        # newly created
        created_entries = (alyxraw.UpdateAlyxRaw - alyxraw.AlyxRaw.proj()) & {
            "model": key["alyx_model_name"]
        }
        self.CreatedEntry.insert(
            created_entries.proj(
                ...,
                alyx_model_name=f'"{key["alyx_model_name"]}"',
                job_datetime=f'"{key["job_datetime"]}"',
            ),
            ignore_extra_fields=True,
        )

        if key["alyx_model_name"] in (
            "subjects.project",
            "subjects.subject",
            "actions.weighing",
            "actions.waterrestriction",
            "actions.wateradministration",
            "actions.session",
        ):
            # deleted
            deleted_entries = (alyxraw.AlyxRaw - alyxraw.UpdateAlyxRaw.proj()) & {
                "model": key["alyx_model_name"]
            }
            self.DeletedEntry.insert(
                deleted_entries.proj(
                    ...,
                    alyx_model_name=f'"{key["alyx_model_name"]}"',
                    job_datetime=f'"{key["job_datetime"]}"',
                ),
                ignore_extra_fields=True,
            )

            # updated
            fields_original = alyxraw.AlyxRaw.Field & (
                alyxraw.AlyxRaw & {"model": key["alyx_model_name"]}
            )
            fields_update = alyxraw.UpdateAlyxRaw.Field & (
                alyxraw.UpdateAlyxRaw & {"model": key["alyx_model_name"]}
            )

            fields_restriction = {}

            modified_entries = alyxraw.AlyxRaw & (
                fields_update.proj(fvalue_new="fvalue") * fields_original
                & "fvalue_new != fvalue"
                & 'fname not in ("json")'
                & fields_restriction
            )
            self.ModifiedEntry.insert(
                modified_entries.proj(
                    ...,
                    alyx_model_name=f'"{key["alyx_model_name"]}"',
                    job_datetime=f'"{key["job_datetime"]}"',
                ),
                ignore_extra_fields=True,
            )


@schema
class DeleteModifiedAlyxRaw(dj.Computed):
    definition = """
    -> AlyxRawDiff
    """

    class HandledDeletedAndModified(dj.Part):
        definition = """  # entries from AlyxRawDiff.DeletedEntry and AlyxRawDiff.ModifiedEntry that are handled
        -> master
        uuid: uuid  # pk field (uuid string repr)
        """

    key_source = (
        AlyxRawDiff * IngestionJob
        & [AlyxRawDiff.ModifiedEntry, AlyxRawDiff.DeletedEntry]
        & 'job_status = "on-going"'
    )

    def make(self, key):
        """
        Delete from AlyxRaw those entries found in ModifiedEntry and DeletedEntry
            + For actions.session, delete only the AlyxRaw.Field of the modified/deleted entries
            + For any other alyx model, delete the AlyxRaw
        (note: deleting is tricky, beware grid-lock)
        """
        # Find all unhandled deleted/modified entries
        #  include also the unhandled ones from all previous jobs
        #  upon completion, the unhandled from previous jobs will be marked as handled in this job

        entries_to_delete = (
            AlyxRawDiff.ModifiedEntry
            + AlyxRawDiff.DeletedEntry
            - self.HandledDeletedAndModified
            & {"alyx_model_name": key["alyx_model_name"]}
        )
        keys_to_delete = [{"uuid": u} for u in entries_to_delete.fetch("uuid")]

        logger.info(
            f'Deletion in AlyxRaw: {key["alyx_model_name"]}'
            f" - {len(keys_to_delete)} records"
        )

        # handle AlyxRaw table
        if key["alyx_model_name"] == "actions.session":
            alyxraw_field_buffer = QueryBuffer(
                alyxraw.AlyxRaw.Field
                & 'fname!="start_time"'
                & (alyxraw.AlyxRaw & {"model": key["alyx_model_name"]})
            )
            for pk in keys_to_delete:
                alyxraw_field_buffer.add_to_queue1(pk)
                alyxraw_field_buffer.flush_delete(chunksz=50, quick=True)
            alyxraw_field_buffer.flush_delete(quick=True)
        else:
            alyxraw_buffer = QueryBuffer(
                alyxraw.AlyxRaw & {"model": key["alyx_model_name"]}
            )
            for pk in keys_to_delete:
                alyxraw_buffer.add_to_queue1(pk)
                alyxraw_buffer.flush_delete(chunksz=50, quick=False)
            alyxraw_buffer.flush_delete(quick=False)

        # handle shadow membership tables
        if key["alyx_model_name"] in MEMBERSHIP_ALYX_MODELS:
            for membership_table_name in MEMBERSHIP_ALYX_MODELS[key["alyx_model_name"]]:
                if membership_table_name is None:
                    continue
                elif isinstance(membership_table_name, str):
                    logger.info(
                        f"\tDeleting shadow membership table: {membership_table_name}"
                    )

                    shadow_membership_table = DJ_TABLES[membership_table_name]["shadow"]
                    shadow_parent_table = DJ_SHADOW_MEMBERSHIP[membership_table_name][
                        "dj_parent_table"
                    ]

                    uuid_attr = next(
                        (
                            attr
                            for attr in shadow_parent_table.heading.names
                            if attr.endswith("uuid")
                        )
                    )

                    with dj.config(safemode=False):
                        (
                            shadow_membership_table
                            & (
                                shadow_membership_table
                                * shadow_parent_table
                                * entries_to_delete.proj(**{uuid_attr: "uuid"})
                            ).fetch("KEY")
                        ).delete()
                elif isinstance(membership_table_name, dj.user_tables.OrderedClass):
                    related_table = membership_table_name
                    logger.info(f"\tDeleting related table: {related_table.__name__}")
                    uuid_attr = next(
                        (
                            attr
                            for attr in related_table.heading.names
                            if attr.endswith("uuid")
                        )
                    )
                    with dj.config(safemode=False):
                        (
                            related_table
                            & entries_to_delete.proj(**{uuid_attr: "uuid"})
                        ).delete()
                else:
                    raise NotImplementedError

        self.insert1(key)
        self.HandledDeletedAndModified.insert({**key, **k} for k in keys_to_delete)


@schema
class IngestAlyxRawModel(dj.Computed):
    definition = """
    -> AlyxRawDiff
    """

    @property
    def key_source(self):
        """
        Only AlyxRawDiff with existing Created or Modified entries
            wait for DeleteModifiedAlyxRaw to finish
        """
        key_source = (
            AlyxRawDiff * IngestionJob
            & [AlyxRawDiff.CreatedEntry, AlyxRawDiff.ModifiedEntry]
            & 'job_status = "on-going"'
        )
        return key_source.proj() - (
            DeleteModifiedAlyxRaw.key_source.proj() - DeleteModifiedAlyxRaw
        )

    def make(self, key):
        """
        Data copy from UpdateAlyxRaw to AlyxRaw, with `skip_duplicates=True`
            only for those entries found in CreatedEntry and ModifiedEntry
        For ModifiedEntry, taking from `DeleteModifiedAlyxRaw.HandledDeletedAndModified`
            instead of `AlyxRawDiff.ModifiedEntry`, as this represents the true set of
            ModifiedEntries entries that have been deleted from `alyxraw.AlyxRaw`
        """
        entries_to_ingest = (
            AlyxRawDiff.CreatedEntry + DeleteModifiedAlyxRaw.HandledDeletedAndModified
            & key
        )

        logger.info(
            f'Ingestion to AlyxRaw: {key["alyx_model_name"]}'
            f" - {len(entries_to_ingest)} records"
        )

        alyxraw.AlyxRaw.insert(
            alyxraw.UpdateAlyxRaw & entries_to_ingest, skip_duplicates=True
        )
        alyxraw.AlyxRaw.Field.insert(alyxraw.UpdateAlyxRaw.Field & entries_to_ingest)

        self.insert1(key)


@schema
class ShadowTable(dj.Computed):
    definition = """
    -> IngestionJob
    table_name: varchar(48)
    """

    # this table is populated only after all the
    # IngestIngestAlyxRawModel and IngestAlyxRawModel populate jobs have finished
    @property
    def key_source(self):
        key_source = IngestionJob & 'job_status = "on-going"'
        UpdateAlyxRaw_finished = (
            key_source.proj().aggr(
                IngestUpdateAlyxRawModel.key_source, ks_count="count(*)"
            )
        ) * (
            key_source.proj().aggr(IngestUpdateAlyxRawModel, completed_count="count(*)")
        ) & "completed_count = ks_count"
        if IngestAlyxRawModel.key_source:
            AlyxRaw_finished = (
                key_source.proj().aggr(
                    IngestAlyxRawModel.key_source, ks_count="count(*)"
                )
            ) * (
                key_source.proj().aggr(IngestAlyxRawModel, completed_count="count(*)")
            ) & "completed_count = ks_count"
        else:
            AlyxRaw_finished = {}
        return key_source & UpdateAlyxRaw_finished & AlyxRaw_finished

    def make(self, key):
        self.insert({**key, "table_name": table_name} for table_name in DJ_TABLES)


@schema
class PopulateShadowTable(dj.Computed):
    definition = """
    -> ShadowTable
    ---
    incomplete_count=null: int  # how many to be populated before this job
    completion_count=null: int  # how many has been populated by this job
    """

    key_source = ShadowTable * IngestionJob & 'job_status = "on-going"'

    def make(self, key):
        is_membership = key["table_name"] in DJ_SHADOW_MEMBERSHIP

        shadow_table = DJ_TABLES[key["table_name"]]["shadow"]
        before_count, _ = shadow_table.progress() if not is_membership else (None, None)

        if key["table_name"] == "acquisition.Session":
            """
            if a session entry is modified, replace the entry without deleting
            this is to keep the session entry when uuid is not changed but start time changed
            by one sec. We don't update start_time in alyxraw in this case.
            """
            modified_uuids = (
                AlyxRawDiff.ModifiedEntry & {"model": "actions.session"} & key
            ).fetch("uuid")
            modified_session_keys = [{"session_uuid": uuid} for uuid in modified_uuids]

            sessions = shadow_table & modified_session_keys
            if sessions:
                modified_session_entries = []
                for key in sessions.fetch("KEY"):
                    try:
                        modified_session_entries.append(shadow_table.create_entry(key))
                    except:
                        logger.debug(f"Error creating entry for key: {key}")
                if modified_session_entries:
                    try:
                        shadow_table.insert(
                            modified_session_entries,
                            allow_direct_insert=True,
                            replace=True,
                        )
                    except dj.DataJointError:
                        for entry in modified_session_entries:
                            shadow_table.insert1(
                                entry, allow_direct_insert=True, replace=True
                            )

        if key["table_name"] in ("data.DataSet", "data.FileRecord"):
            if _backtrack_days:
                date_cutoff = (
                    datetime.datetime.now().date()
                    - datetime.timedelta(days=_backtrack_days)
                ).strftime("%Y-%m-%d")
            else:
                date_cutoff = "1970-01-01"

            uuid_attr = shadow_table.primary_key[0]
            key_source = (
                shadow_table.key_source.proj(uuid=uuid_attr)
                & (
                    alyxraw.AlyxRaw * alyxraw.AlyxRaw.Field
                    & 'fname = "auto_datetime"'
                    & f'fvalue > "{date_cutoff}"'
                )
            ).proj(**{uuid_attr: "uuid"})

            query_buffer = QueryBuffer(shadow_table, verbose=True)
            for k in (key_source - shadow_table).fetch("KEY"):
                try:
                    query_buffer.add_to_queue1(shadow_table.create_entry(k))
                except ShadowIngestionError:
                    pass
                query_buffer.flush_insert(
                    skip_duplicates=True, allow_direct_insert=True, chunksz=1000
                )
            query_buffer.flush_insert(skip_duplicates=True, allow_direct_insert=True)
        elif is_membership:
            tab_args = DJ_SHADOW_MEMBERSHIP[key["table_name"]]
            ingest_membership.ingest_membership_table(**tab_args)
        else:
            self.connection.cancel_transaction()
            shadow_table.populate(
                reserve_jobs=True, display_progress=True, suppress_errors=True
            )

        after_count, _ = shadow_table.progress() if not is_membership else (None, None)
        self.insert1(
            {
                **key,
                "incomplete_count": before_count,
                "completion_count": before_count - after_count
                if not is_membership
                else None,
            }
        )


@schema
class CopyRealTable(dj.Computed):
    definition = """
    -> PopulateShadowTable
    ---
    transferred_count=null: int
    """

    _real_tables = [
        table_name for table_name, v in DJ_TABLES.items() if v["real"] is not None
    ]

    key_source = (
        PopulateShadowTable * IngestionJob
        & 'job_status = "on-going"'
        & [f'table_name = "{table_name}"' for table_name in _real_tables]
    )

    def make(self, key):
        shadow_table = DJ_TABLES[key["table_name"]]["shadow"]
        real_table = DJ_TABLES[key["table_name"]]["real"]

        # Ensure the real-table copy routine is "in topologically sorted order"
        # so, if ancestors of this table is not yet copied, exit and retry later
        schema_prefix = dj.config["database.prefix"] + "ibl_"
        ancestors = [tbl_name.split(".") for tbl_name in real_table.ancestors()]
        ancestors = [
            schema_name.strip("`").replace(schema_prefix, "")
            + "."
            + ".".join(
                [
                    dj.utils.to_camel_case(s)
                    for s in tbl_name.strip("`").split("__")
                    if s
                ]
            )
            for schema_name, tbl_name in ancestors
        ]

        ancestors = [
            n for n in ancestors if n in self._real_tables and n != key["table_name"]
        ]

        are_ancestors_copied = len(
            self & (IngestionJob & key) & [{"table_name": n} for n in ancestors]
        ) == len(ancestors)

        if not are_ancestors_copied:
            return

        # Do the copying
        target_module = inspect.getmodule(real_table)
        source_module = inspect.getmodule(shadow_table)

        transferred_count = ingest_real.copy_table(
            target_module, source_module, real_table.__name__
        )

        self.insert1({**key, "transferred_count": transferred_count})


@schema
class UpdateRealTable(dj.Computed):
    definition = """
    -> CopyRealTable
    """

    key_source = (
        CopyRealTable * IngestionJob
        & 'job_status = "on-going"'
        & [f'table_name = "{table_name}"' for table_name in DJ_UPDATES]
    )

    def make(self, key):
        alyx_model_name = get_django_model_name(
            DJ_UPDATES[key["table_name"]]["alyx_model"]
        )

        real_table = DJ_TABLES[key["table_name"]]["real"]
        if real_table is None:
            return
        shadow_table = DJ_TABLES[key["table_name"]]["shadow"]
        target_module = inspect.getmodule(real_table)
        source_module = inspect.getmodule(shadow_table)

        # per-attribute comparison between real and shadow table
        shadow_attrs_rename = {
            f"s_{attr}": attr
            for attr in shadow_table.heading.secondary_attributes
            if attr not in real_table.primary_key
        }

        modified_entries = real_table * shadow_table.proj(
            ..., **shadow_attrs_rename
        ) & [
            f"{r} != {s}"
            for s, r in shadow_attrs_rename.items()
            if not r.endswith("_ts")
        ]

        # modified uuids from AlyxRawDiff
        modified_uuids = (
            AlyxRawDiff.ModifiedEntry & key & {"alyx_model_name": alyx_model_name}
        ).fetch("uuid")

        uuid_attr = next(
            (attr for attr in shadow_table.heading.names if attr.endswith("uuid"))
        )

        # combined modified_uuids
        modified_uuids = set(
            list(modified_uuids) + list(modified_entries.fetch(uuid_attr))
        )

        query = real_table & [{uuid_attr: u} for u in modified_uuids]

        if query:
            delete_update_entries.update_fields(
                target_module,
                source_module,
                real_table.__name__,
                pks=query.fetch("KEY"),
                log_to_UpdateRecord=False,
            )
            member_tables = DJ_UPDATES[key["table_name"]]["members"]
            for member_table_name in member_tables:
                member_table = getattr(source_module, member_table_name)
                if member_table & query:
                    delete_update_entries.update_fields(
                        target_module,
                        source_module,
                        member_table_name,
                        pks=(member_table & query).fetch("KEY"),
                        log_to_UpdateRecord=True,
                    )

        self.insert1(key)


def _check_ingestion_completion():
    """
    Check if the current "on-going" job is completed, if so, mark `job_status` to "completed"
    """
    on_going_job = IngestionJob & 'job_status = "on-going"'
    if not on_going_job:
        return True

    finished_copy_real, total_copy_real = CopyRealTable.progress(display=False)
    copy_real_completed = (
        total_copy_real == len(CopyRealTable._real_tables) and finished_copy_real == 0
    )

    finished_update_real, total_update_real = UpdateRealTable.progress(display=False)
    update_real_completed = (
        total_update_real == len(DJ_UPDATES) and finished_update_real == 0
    )

    if copy_real_completed and update_real_completed:
        key = on_going_job.fetch1("KEY")
        (IngestionJob & key)._update("job_status", "completed")
        (IngestionJob & key)._update("job_endtime", datetime.datetime.utcnow())
        logger.info(f"All ingestion jobs completed: {key}")
        return True

    return False


_ingestion_tables = (
    UpdateAlyxRawModel,
    IngestUpdateAlyxRawModel,
    AlyxRawDiff,
    DeleteModifiedAlyxRaw,
    IngestAlyxRawModel,
    ShadowTable,
    PopulateShadowTable,
    CopyRealTable,
    UpdateRealTable,
)


def populate_ingestion_tables(
    run_duration=3600 * 3,
    sleep_duration=60,
    new_job_string=None,
    populate_settings=None,
    **kwargs,
):
    """
    Routine to populate all ingestion tables
    Run in continuous loop for the duration defined in "run_duration" (default 3 hours)
    """
    populate_settings = (populate_settings or {}) | {
        "display_progress": True,
        "reserve_jobs": True,
        "suppress_errors": True,
    }

    start_time = time.time()
    while (
        (time.time() - start_time < run_duration)
        or (run_duration is None)
        or (run_duration < 0)
    ):

        # create new ingestion job
        last_job_datetime = IngestionJob.get_latest_key()

        if not last_job_datetime:
            IngestionJob.create_entry(datetime.datetime.utcnow().strftime("%Y-%m-%d"))
        else:
            recent_job_str = (IngestionJob & last_job_datetime).fetch1("new_job_string")
            if new_job_string and recent_job_str != new_job_string:
                IngestionJob.create_entry(new_job_string)

        # check if completed
        if _check_ingestion_completion():
            cleanup_shadow_schema_jobs()
            logger.info("Ingestion completed, waiting for next job...")
        else:
            for table in _ingestion_tables:
                logger.info(f"POPULATING: {table.__name__}")
                table.populate(**populate_settings)

        (schema.jobs & 'status = "error"').delete()
        stale_jobs = (schema.jobs & 'status = "reserved"').proj(
            elapsed_days="TIMESTAMPDIFF(DAY, timestamp, NOW())"
        ) & "elapsed_days > 1"
        (schema.jobs & stale_jobs).delete()

        logger.info(f"Sleeping for {sleep_duration} seconds...")
        time.sleep(sleep_duration)


if __name__ == "__main__":
    populate_ingestion_tables(run_duration=-1, sleep_duration=30)
