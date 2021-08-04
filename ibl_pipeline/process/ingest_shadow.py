import datajoint as dj
from datajoint import DataJointError
from ibl_pipeline.ingest import \
    (alyxraw, QueryBuffer,
     reference, subject, action, acquisition, data)

from os import environ

mode = environ.get('MODE')
if mode != 'public':
    from ibl_pipeline.ingest import ephys, histology

from ibl_pipeline.ingest import get_raw_field as grf
import uuid
from tqdm import tqdm


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
    data.DataSetType
]

if mode != 'public':
    SHADOW_TABLES.extend([
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
    ])


if mode != 'public':
    SHADOW_TABLES = SHADOW_TABLES + [
        ephys.ProbeModel,
        ephys.ProbeInsertion
    ]


def main(excluded_tables=[], modified_pks=None):

    kwargs = dict(
        display_progress=True,
        suppress_errors=True)

    for t in SHADOW_TABLES:
        if t.__name__ in excluded_tables:
            continue
        print(f'Ingesting shadow table {t.__name__}...')

        # if a session entry is modified, replace the entry without deleting
        # this is to keep the session entry when uuid is not changed but start time changed
        # by one sec. We don't update start_time in alyxraw in this case.
        if t.__name__ == 'Session' and modified_pks:
            modified_session_keys = [
                {'session_uuid': pk} for pk in modified_pks]
            sessions = acquisition.Session & modified_session_keys
            if sessions:
                modified_session_entries = []
                for key in sessions.fetch('KEY'):
                    try:
                        entry = acquisition.Session.create_entry(key)
                        modified_session_entries.append(entry)
                    except:
                        print("Error creating entry for key: {}".format(key))
                if modified_session_entries:
                    try:
                        t.insert(modified_session_entries,
                                 allow_direct_insert=True, replace=True)
                    except DataJointError:
                        for entry in modified_session_entries:
                            t.insert1(entry, allow_direct_insert=True,
                                      replace=True)

        t.populate(**kwargs)

    if 'DataSet' not in excluded_tables:

        print('Ingesting dataset entries...')
        key_source = (alyxraw.AlyxRaw & 'model="data.dataset"').proj(
            dataset_uuid="uuid") - data.DataSet

        data_set = QueryBuffer(data.DataSet)

        for key in tqdm(key_source.fetch('KEY'), position=0):
            key_ds = key.copy()
            key['uuid'] = key['dataset_uuid']

            session = grf(key, 'session')
            if not len(acquisition.Session &
                       dict(session_uuid=uuid.UUID(session))):
                print('Session {} is not in the table acquisition.Session'.format(
                    session))
                print('dataset_uuid: {}'.format(str(key['uuid'])))
                continue

            key_ds['subject_uuid'], key_ds['session_start_time'] = \
                (acquisition.Session &
                    dict(session_uuid=uuid.UUID(session))).fetch1(
                    'subject_uuid', 'session_start_time')

            key_ds['dataset_name'] = grf(key, 'name')

            dt = grf(key, 'dataset_type')
            key_ds['dataset_type_name'] = \
                (data.DataSetType & dict(dataset_type_uuid=uuid.UUID(dt))).fetch1(
                    'dataset_type_name')

            user = grf(key, 'created_by')

            if user != 'None':
                try:
                    key_ds['dataset_created_by'] = \
                        (reference.LabMember & dict(user_uuid=uuid.UUID(user))).fetch1(
                            'user_name')
                except:
                    print(user)
            else:
                key_ds['dataset_created_by'] = None

            format = grf(key, 'data_format')
            key_ds['format_name'] = \
                (data.DataFormat & dict(format_uuid=uuid.UUID(format))).fetch1(
                    'format_name')

            key_ds['created_datetime'] = grf(key, 'created_datetime')

            software = grf(key, 'generating_software')
            if software != 'None':
                key_ds['generating_software'] = software
            else:
                key_ds['generating_software'] = None

            directory = grf(key, 'provenance_directory')
            if directory != 'None':
                key_ds['provenance_directory'] = directory
            else:
                key_ds['provenance_directory'] = None

            md5 = grf(key, 'md5')
            if md5 != 'None':
                key_ds['md5'] = md5
            else:
                key_ds['md5'] = None

            file_size = grf(key, 'file_size')
            if file_size != 'None':
                key_ds['file_size'] = file_size
            else:
                key_ds['file_size'] = None

            data_set.add_to_queue1(key_ds)

            if data_set.flush_insert(
                    skip_duplicates=True,
                    allow_direct_insert=True, chunksz=100):
                print('Inserted 100 dataset tuples')

        if data_set.flush_insert(skip_duplicates=True, allow_direct_insert=True):
            print('Inserted all remaining dataset tuples')

    if 'FileRecord' not in excluded_tables:
        print('Ingesting file record entries...')
        records = alyxraw.AlyxRaw & 'model="data.filerecord"'
        repos = (data.DataRepository & 'repo_name LIKE "flatiron%"').fetch(
            'repo_uuid')
        records_flatiron = alyxraw.AlyxRaw.Field & records & \
            'fname = "data_repository"' & [{'fvalue': str(repo)} for repo in repos]
        record_exists = alyxraw.AlyxRaw.Field & records & \
            'fname = "exists"' & 'fvalue="True"'
        key_source = (alyxraw.AlyxRaw & record_exists & records_flatiron).proj(
            record_uuid='uuid') - data.FileRecord

        file_record = QueryBuffer(data.FileRecord)

        for key in tqdm(key_source.fetch('KEY'), position=0):
            key_fr = key.copy()
            key['uuid'] = key['record_uuid']
            key_fr['exists'] = True

            dataset = grf(key, 'dataset')
            if not len(data.DataSet & dict(dataset_uuid=uuid.UUID(dataset))):
                print('Dataset {} is not in the table data.DataSet')
                print('Record_uuid: {}'.format(str(key['uuid'])))
                continue

            key_fr['subject_uuid'], key_fr['session_start_time'], \
                key_fr['dataset_name'] = \
                (data.DataSet & dict(dataset_uuid=uuid.UUID(dataset))).fetch1(
                    'subject_uuid', 'session_start_time', 'dataset_name')

            repo = grf(key, 'data_repository')
            key_fr['repo_name'] = \
                (data.DataRepository & dict(repo_uuid=uuid.UUID(repo))).fetch1(
                    'repo_name')

            key_fr['relative_path'] = grf(key, 'relative_path')

            file_record.add_to_queue1(key_fr)

            if file_record.flush_insert(
                    skip_duplicates=True, allow_direct_insert=True, chunksz=1000):
                print('Inserted 1000 raw field tuples')

        if file_record.flush_insert(skip_duplicates=True, allow_direct_insert=True):
            print('Inserted all remaining file record tuples')


if __name__ == '__main__':
    main()
