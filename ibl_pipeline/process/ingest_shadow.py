import datajoint as dj
from datajoint import DataJointError

from ibl_pipeline import mode
from ibl_pipeline.ingest import (
    QueryBuffer,
    acquisition,
    action,
    alyxraw,
    data,
    reference,
    subject,
)

if mode != "public":
    from ibl_pipeline.ingest import ephys, histology

import uuid

from tqdm import tqdm

from ibl_pipeline.ingest import get_raw_field as grf

SHADOW_TABLES = [
    reference.Lab,
    reference.LabMember,
    reference.LabMembership,
    reference.LabLocation,
    reference.Project,
    reference.CoordinateSystem,
    subject.Species,
    subject.Source,
    subject.Strain,
    subject.Sequence,
    subject.Allele,
    subject.Line,
    subject.Subject,
    subject.BreedingPair,
    subject.Litter,
    subject.LitterSubject,
    subject.SubjectProject,
    subject.SubjectUser,
    subject.SubjectLab,
    subject.Caging,
    subject.UserHistory,
    subject.Weaning,
    subject.Death,
    subject.GenotypeTest,
    subject.Zygosity,
    action.ProcedureType,
    acquisition.Session,
    data.DataFormat,
    data.DataRepositoryType,
    data.DataRepository,
    data.DataSetType,
]

if mode != "public":
    SHADOW_TABLES.extend(
        [
            subject.SubjectCullMethod,
            action.Weighing,
            action.WaterType,
            action.WaterAdministration,
            action.WaterRestriction,
            action.Surgery,
            action.CullMethod,
            action.CullReason,
            action.Cull,
            action.OtherAction,
        ]
    )


if mode != "public":
    SHADOW_TABLES = SHADOW_TABLES + [ephys.ProbeModel, ephys.ProbeInsertion]


def main(excluded_tables=[], modified_sessions_pks=None):
    kwargs = dict(display_progress=True, suppress_errors=True)

    for t in SHADOW_TABLES:
        if t.__name__ in excluded_tables:
            continue
        print(f"Ingesting shadow table {t.__name__}...")

        # if a session entry is modified, replace the entry without deleting
        # this is to keep the session entry when uuid is not changed but start time changed
        # by one sec. We don't update start_time in alyxraw in this case.
        if t.__name__ == "Session" and modified_sessions_pks:
            modified_session_keys = [
                {"session_uuid": pk} for pk in modified_sessions_pks
            ]
            sessions = acquisition.Session & modified_session_keys
            if sessions:
                modified_session_entries = []
                for key in sessions.fetch("KEY"):
                    try:
                        entry = acquisition.Session.create_entry(key)
                        modified_session_entries.append(entry)
                    except:
                        print("Error creating entry for key: {}".format(key))
                if modified_session_entries:
                    try:
                        t.insert(
                            modified_session_entries,
                            allow_direct_insert=True,
                            replace=True,
                        )
                    except DataJointError:
                        for entry in modified_session_entries:
                            t.insert1(entry, allow_direct_insert=True, replace=True)

        t.populate(**kwargs)

    # ---- populate `DataSet` and `FileRecord` ----
    # essentially calling their respective `.make()`
    # but using the QueryBuffer to do batch insertion

    if "DataSet" not in excluded_tables:
        print("Ingesting dataset entries...")
        data_set_buffer = QueryBuffer(data.DataSet)
        for key in tqdm(
            (data.DataSet.key_source - data.DataSet).fetch("KEY"), position=0
        ):
            data_set_buffer.add_to_queue1(data.DataSet.create_entry(key))

            if data_set_buffer.flush_insert(
                skip_duplicates=True, allow_direct_insert=True, chunksz=100
            ):
                print("Inserted 100 dataset tuples")

        if data_set_buffer.flush_insert(skip_duplicates=True, allow_direct_insert=True):
            print("Inserted all remaining dataset tuples")

    if "FileRecord" not in excluded_tables:
        print("Ingesting file record entries...")
        file_record_buffer = QueryBuffer(data.FileRecord)
        for key in tqdm(
            (data.FileRecord.key_source - data.FileRecord).fetch("KEY"), position=0
        ):
            file_record_buffer.add_to_queue1(data.FileRecord.create_entry(key))

            if file_record_buffer.flush_insert(
                skip_duplicates=True, allow_direct_insert=True, chunksz=1000
            ):
                print("Inserted 1000 raw field tuples")

        if file_record_buffer.flush_insert(
            skip_duplicates=True, allow_direct_insert=True
        ):
            print("Inserted all remaining file record tuples")


if __name__ == "__main__":
    main()
