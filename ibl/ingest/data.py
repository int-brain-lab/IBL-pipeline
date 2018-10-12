import datajoint as dj
import json

from ibl.ingest import alyxraw, reference, acquisition
from ibl.ingest import get_raw_field as grf

schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_ingest_data')

@schema
class DataFormat(dj.Computed):
    definition = """
    (format_uuid) -> alyxraw.AlyxRaw
    ---
    format_name:                    varchar(255)
    file_extension=null:            varchar(255)
    matlab_loader_function=null:    varchar(255)
    python_loader_function=null:    varchar(255)
    format_description=null:        varchar(255)
    """
    key_source = (alyxraw.AlyxRaw & 'model="data.dataformat"').proj(format_uuid='uuid')

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
    """
    key_source = (alyxraw.AlyxRaw & 'model="data.datarepositorytype"').proj(repotype_uuid='uuid')
    
    def make(self,key):
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
    repo_time_zone:     varchar(255)
    repo_dns:           varchar(255)
    globus_endpoint_id: varchar(255)
    globus_path:        varchar(255)
    data_url=null:      varchar(255)
    globus_is_personal: boolean
    """
    key_source = (alyxraw.AlyxRaw & 'model="data.datarepository"').proj(repo_uuid='uuid')

    def make(self, key):
        key_repo = key.copy()
        key['uuid'] = key['repo_uuid']
        
        key_repo['repo_name'] = grf(key, 'name')
        
        repotype_uuid = grf(key, 'repository_type')
        key_repo['repotype_name'] = (DataRepositoryType & 'repotype_uuid="{}"'.format(repotype_uuid)).fetch1('repotype_name')
        key_repo['repo_time_zone'] = grf(key, 'timezone')
        key_repo['repo_dns'] = grf(key, 'dns')
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
    """
    
@schema
class DataSetType(dj.Computed):
    definition = """
    (dataset_type_uuid) -> alyxraw.AlyxRaw
    ---
    dataset_type_name:              varchar(255)
    user_name=null:                 varchar(255)
    filename_pattern:               varchar(255)
    dataset_type_description=null:  varchar(1024)
    """
    key_source = (alyxraw.AlyxRaw & 'model="data.datasettype"').proj(dataset_type_uuid='uuid')
    def make(self, key):
        key_dst = key.copy()
        key['uuid'] = key['dataset_type_uuid']

        key_dst['dataset_type_name'] = grf(key, 'name')
        
        user_uuid = grf(key, 'created_by')
        if user_uuid != 'None':
            key_dst['user_name'] = (reference.LabMember & 'user_uuid="{}"'.format(user_uuid)).fetch1('user_name')
    
        key_dst['filename_pattern'] = grf(key, 'filename_pattern')
        key_dst['dataset_type_description'] = grf(key, 'description')
        
        self.insert1(key_dst)


@schema
class DataSet(dj.Computed):
    definition = """
    (dataset_uuid) -> alyxraw.AlyxRaw
    ---
    subject_uuid:               varchar(64)
    session_start_time:         datetime
    user_name:                  varchar(255)
    dataset_name:               varchar(255)
    dataset_type_name:          varchar(255)
    format_name:                varchar(255)
    created_datetime:           datetime
    generating_software=null:   varchar(255)
    provenance_directory=null:  varchar(255)
    md5=null:                   varchar(255)
    file_size=null:             float
    """
    key_source = (alyxraw.AlyxRaw & 'model="data.dataset"').proj(dataset_uuid="uuid")
    
    def make(self, key):
        key_ds = key.copy()
        key['uuid'] = key['dataset_uuid']

        session_uuid = grf(key, 'session')
        key_ds['subject_uuid'], key_ds['session_start_time'] = \
            (acquisition.Session & 'session_uuid="{}"'.format(session_uuid)).fetch1('subject_uuid', 'session_start_time')

        key_ds['dataset_name'] = grf(key, 'name')

        dt_uuid = grf(key, 'dataset_type')
        key_ds['dataset_type_name'] = (DataSetType & 'dataset_type_uuid="{}"'.format(dt_uuid)).fetch1('dataset_type_name')

        user_uuid = grf(key, 'created_by')
        key_ds['user_name'] = (reference.LabMember & 'user_uuid="{}"'.format(user_uuid)).fetch1('user_name')
        
        format_uuid = grf(key, 'data_format')
        key_ds['format_name'] = (DataFormat & 'format_uuid="{}"'.format(format_uuid)).fetch1('format_name')

        key_ds['created_datetime'] = grf(key, 'created_datetime')
        
        software = grf(key, 'generating_software')
        if software != 'None':
            key_ds['generating_software'] = software
        
        directory = grf(key, 'provenance_directory')
        if directory != 'None':
            key_ds['provenance_directory'] = directory
        
        md5 = grf(key, 'md5')
        if md5 != 'None':
            key_ds['md5'] = md5

        file_size = grf(key, 'file_size')
        if file_size != 'None':
            key_ds['file_size'] = file_size
        
        self.insert1(key_ds)

@schema
class FileRecord(dj.Computed):
    definition = """
    (record_uuid) -> alyxraw.AlyxRaw
    ---
    exists:                     boolean
    subject_uuid:               varchar(64)
    session_start_time:         datetime
    dataset_name:              varchar(255)
    repo_name:                  varchar(255)
    relative_path:              varchar(255)
    """
    key_source = (alyxraw.AlyxRaw & 'model="data.filerecord"').proj(record_uuid='uuid')

    def make(self, key):
        key_fr = key.copy()
        key['uuid'] = key['record_uuid']
        exists = grf(key, 'exists')
        key_fr['exists'] = True if exists=="True" else False
        dataset_uuid = grf(key, 'dataset')
        key_fr['subject_uuid'], key_fr['session_start_time'], key_fr['dataset_name'] = \
            (DataSet & 'dataset_uuid="{}"'.format(dataset_uuid)).fetch1('subject_uuid', 'session_start_time', 'dataset_name')

        repo_uuid = grf(key, 'data_repository')
        key_fr['repo_name'] = (DataRepository & 'repo_uuid="{}"'.format(repo_uuid)).fetch1('repo_name')

        key_fr['relative_path'] = grf(key, 'relative_path')
        self.insert1(key_fr)

