import datajoint as dj
import json
import uuid

from . import alyxraw, reference, acquisition, ShadowIngestionError
from . import get_raw_field as grf

schema = dj.schema(dj.config.get('database.prefix', '') +
                   'ibl_ingest_data')


@schema
class DataFormat(dj.Computed):
    definition = """
    (format_uuid) -> alyxraw.AlyxRaw
    ---
    format_name:                    varchar(255)
    file_extension='':              varchar(255)
    matlab_loader_function=null:    varchar(255)
    python_loader_function=null:    varchar(255)
    format_description=null:        varchar(255)
    dataformat_ts=CURRENT_TIMESTAMP:   timestamp
    """
    key_source = (alyxraw.AlyxRaw & 'model="data.dataformat"').proj(
        format_uuid='uuid')

    def make(self, key):
        key_format = key.copy()
        key['uuid'] = key['format_uuid']

        key_format['format_name'] = grf(key, 'name')

        file_extension = grf(key, 'file_extension')
        if file_extension != 'None':
            key_format['file_extension'] = file_extension

        matlab_loader_function = grf(key, 'matlab_loader_function')
        if matlab_loader_function != 'None':
            key_format['matlab_loader_function'] = matlab_loader_function

        python_loader_function = grf(key, 'python_loader_function')
        if python_loader_function != 'None':
            key_format['python_loader_function'] = python_loader_function

        format_description = grf(key, 'description')
        if format_description != 'None':
            key_format['format_description'] = format_description

        self.insert1(key_format)


@schema
class DataRepositoryType(dj.Computed):
    definition = """
    (repotype_uuid) -> alyxraw.AlyxRaw
    ---
    repotype_name: varchar(255)
    datarepositorytype_ts=CURRENT_TIMESTAMP:   timestamp
    """
    key_source = (alyxraw.AlyxRaw & 'model="data.datarepositorytype"').proj(
        repotype_uuid='uuid')

    def make(self, key):
        key_repotype = key.copy()
        key['uuid'] = key['repotype_uuid']
        key_repotype['repotype_name'] = grf(key, 'name')
        self.insert1(key_repotype)


@schema
class DataRepository(dj.Computed):
    definition = """
    (repo_uuid) -> alyxraw.AlyxRaw
    ---
    repo_name:          varchar(255)
    repotype_name:      varchar(255)
    repo_timezone:     varchar(255)
    repo_hostname:      varchar(255)
    globus_endpoint_id: varchar(255)
    globus_path:        varchar(255)
    data_url=null:      varchar(255)
    globus_is_personal: boolean
    datarepository_ts=CURRENT_TIMESTAMP:   timestamp
    """
    key_source = (alyxraw.AlyxRaw & 'model="data.datarepository"').proj(
        repo_uuid='uuid')

    def make(self, key):
        key_repo = key.copy()
        key['uuid'] = key['repo_uuid']

        key_repo['repo_name'] = grf(key, 'name')

        repotype = grf(key, 'repository_type')
        key_repo['repotype_name'] = \
            (DataRepositoryType &
                dict(repotype_uuid=uuid.UUID(repotype))).fetch1(
                    'repotype_name')
        key_repo['repo_timezone'] = grf(key, 'timezone')
        key_repo['repo_hostname'] = grf(key, 'hostname')
        key_repo['globus_endpoint_id'] = grf(key, 'globus_endpoint_id')
        key_repo['globus_path'] = grf(key, 'globus_path')

        is_personal = grf(key, 'globus_is_personal')
        key_repo['globus_is_personal'] = True if is_personal else False

        url = grf(key, 'data_url')
        if url != 'None':
            key_repo['data_url'] = url

        self.insert1(key_repo)


@schema
class ProjectRepository(dj.Manual):
    definition = """
    project_name:       varchar(255)
    repo_name:          varchar(255)
    ---
    projectrepository_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class DataSetType(dj.Computed):
    definition = """
    (dataset_type_uuid) -> alyxraw.AlyxRaw
    ---
    dataset_type_name:              varchar(255)
    dataset_type_created_by=null:   varchar(255)
    filename_pattern:               varchar(255)
    dataset_type_description=null:  varchar(1024)
    datasettype_ts=CURRENT_TIMESTAMP:   timestamp
    """
    key_source = (alyxraw.AlyxRaw & 'model="data.datasettype"').proj(
        dataset_type_uuid='uuid')

    def make(self, key):
        key_dst = key.copy()
        key['uuid'] = key['dataset_type_uuid']

        key_dst['dataset_type_name'] = grf(key, 'name')

        user_uuid = grf(key, 'created_by')
        if user_uuid != 'None':
            key_dst['dataset_type_created_by'] = \
                (reference.LabMember &
                 dict(user_uuid=uuid.UUID(user_uuid))).fetch1('user_name')

        key_dst['filename_pattern'] = grf(key, 'filename_pattern')
        key_dst['dataset_type_description'] = grf(key, 'description')

        self.insert1(key_dst)


@schema
class DataSet(dj.Computed):
    definition = """
    (dataset_uuid) -> alyxraw.AlyxRaw
    ---
    subject_uuid:               uuid
    session_start_time:         datetime
    dataset_created_by=null:    varchar(255)
    dataset_name:               varchar(255)
    dataset_type_name:          varchar(255)
    format_name:                varchar(255)
    created_datetime:           datetime
    generating_software=null:   varchar(255)
    provenance_directory=null:  varchar(255)
    md5=null:                   varchar(255)
    file_size=null:             float
    """
    key_source = (alyxraw.AlyxRaw & 'model="data.dataset"').proj(
        dataset_uuid="uuid")

    def make(self, key):
        self.insert1(self.create_entry(key))

    @staticmethod
    def create_entry(key):
        """
        For a dataset_uuid from alyx, generate the dictionary
         to be inserted into this DataSet table
        """
        key_ds = key.copy()
        key['uuid'] = key['dataset_uuid']

        session = grf(key, 'session')
        if not len(acquisition.Session &
                   dict(session_uuid=uuid.UUID(session))):
            raise ShadowIngestionError('Non existing session: {}'.format(session))

        key_ds['subject_uuid'], key_ds['session_start_time'] = \
            (acquisition.Session &
             dict(session_uuid=uuid.UUID(session))).fetch1(
                'subject_uuid', 'session_start_time')

        key_ds['dataset_name'] = grf(key, 'name')

        dt = grf(key, 'dataset_type')
        key_ds['dataset_type_name'] = \
            (DataSetType & dict(dataset_type_uuid=uuid.UUID(dt))).fetch1(
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
            (DataFormat & dict(format_uuid=uuid.UUID(format))).fetch1(
                'format_name')

        key_ds['created_datetime'] = grf(key, 'created_datetime')

        software = grf(key, 'generating_software')
        key_ds['generating_software'] = software if software != 'None' else None

        directory = grf(key, 'provenance_directory')
        key_ds['provenance_directory'] = directory if directory != 'None' else None

        md5 = grf(key, 'md5')
        key_ds['md5'] = md5 if md5 != 'None' else None

        file_size = grf(key, 'file_size')
        key_ds['file_size'] = file_size if file_size != 'None' else None

        return key_ds

    @classmethod
    def create_session_entries(cls, session_uuid):
        """
        For a session_uuid, create a list of dictionaries representing all entries
         for the given session to be inserted into the DataSet table
        """
        alyxraw_dataset_query = (alyxraw.AlyxRaw * alyxraw.AlyxRaw.Field
                                 & 'model = "data.dataset"'
                                 & 'fname = "session"' & {'fvalue': session_uuid})
        alyxraw_dataset_keys = (alyxraw.AlyxRaw & alyxraw_dataset_query.proj()).proj(
            dataset_uuid="uuid").fetch('KEY')
        return [cls.create_entry(key) for key in alyxraw_dataset_keys]


@schema
class FileRecord(dj.Computed):
    definition = """
    (record_uuid) -> alyxraw.AlyxRaw
    ---
    exists:                     boolean
    subject_uuid:               uuid
    session_start_time:         datetime
    dataset_name:               varchar(255)
    repo_name:                  varchar(255)
    relative_path:              varchar(255)
    """
    records = alyxraw.AlyxRaw & 'model="data.filerecord"'
    repos = (DataRepository & 'repo_name LIKE "flatiron%"').fetch(
        'repo_uuid')
    records_flatiron = alyxraw.AlyxRaw.Field & records & \
        'fname = "data_repository"' & [{'fvalue': str(repo)} for repo in repos]
    record_exists = alyxraw.AlyxRaw.Field & records & \
        'fname = "exists"' & 'fvalue="True"'
    key_source = (alyxraw.AlyxRaw & record_exists & records_flatiron).proj(
        record_uuid='uuid')

    def make(self, key):
        self.insert1(self.create_entry(key))

    @staticmethod
    def create_entry(key):
        key_fr = key.copy()
        key['uuid'] = key['record_uuid']
        key_fr['exists'] = True

        dataset = grf(key, 'dataset')
        if not len(DataSet & dict(dataset_uuid=uuid.UUID(dataset))):
            raise ShadowIngestionError('Dataset is not in the table data.DataSet: {}'.format(str(key['uuid'])))

        key_fr['subject_uuid'], key_fr['session_start_time'], \
            key_fr['dataset_name'] = \
            (DataSet & dict(dataset_uuid=uuid.UUID(dataset))).fetch1(
                'subject_uuid', 'session_start_time', 'dataset_name')

        repo = grf(key, 'data_repository')
        key_fr['repo_name'] = \
            (DataRepository & dict(repo_uuid=uuid.UUID(repo))).fetch1(
                'repo_name')

        key_fr['relative_path'] = grf(key, 'relative_path')
        return key_fr

    @classmethod
    def create_session_entries(cls, session_uuid):
        """
        For a session_uuid, create a list of dictionaries representing all entries
         for the given session to be inserted into the FileRecord table
        """
        subject_uuid, session_start_time = (acquisition.Session
                                            & {'session_uuid': session_uuid}).fetch1(
            'subject_uuid', 'session_start_time')
        dataset_uuids = (DataSet & {'subject_uuid': subject_uuid,
                                    'session_start_time': session_start_time}).fetch('dataset_uuid')
        session_records = (alyxraw.AlyxRaw * alyxraw.AlyxRaw.Field & 'model="data.filerecord"'
                           & 'fname = "dataset"' & [{'fvalue': str(u)} for u in dataset_uuids])

        alyxraw_filerecord_keys = (cls.key_source
                                   & session_records.proj(record_uuid='uuid')).fetch('KEY')

        return [cls.create_entry(key) for key in alyxraw_filerecord_keys]
