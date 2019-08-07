import datajoint as dj
from . import reference, acquisition
import os

mode = os.environ.get('MODE')

if mode == 'update':
    schema = dj.schema('ibl_data')
else:
    schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_data')


@schema
class DataFormat(dj.Lookup):
    definition = """
    format_name:                    varchar(255)
    ---
    format_uuid:                    uuid
    file_extension='':              varchar(255)
    matlab_loader_function=null:    varchar(255)
    python_loader_function=null:    varchar(255)
    format_description=null:        varchar(255)
    dataformat_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class DataRepositoryType(dj.Lookup):
    definition = """
    repotype_name:  varchar(255)
    ---
    repotype_uuid:  uuid
    datarepositorytype_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class DataRepository(dj.Lookup):
    definition = """
    repo_name:          varchar(255)
    ---
    -> DataRepositoryType
    repo_uuid:          uuid
    repo_timezone:      varchar(255)
    repo_hostname:      varchar(255)
    globus_endpoint_id: varchar(255)
    globus_path:        varchar(255)
    data_url=null:      varchar(255)
    globus_is_personal: boolean
    datarepository_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class ProjectRepository(dj.Manual):
    definition = """
    -> reference.Project
    -> DataRepository
    projectrepository=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class DataSetType(dj.Lookup):
    definition = """
    dataset_type_name:              varchar(255)
    ---
    dataset_type_uuid:              uuid
    -> [nullable] reference.LabMember.proj(dataset_type_created_by='user_name')
    filename_pattern:               varchar(255)
    dataset_type_description=null:  varchar(1024)
    datasettype_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class DataSet(dj.Manual):
    definition = """
    -> acquisition.Session
    dataset_name:               varchar(255)
    ---
    dataset_uuid:               uuid
    -> [nullable] reference.LabMember.proj(dataset_created_by='user_name')
    -> DataSetType
    -> DataFormat
    created_datetime:           datetime
    generating_software=null:   varchar(255)
    provenance_directory=null:  varchar(255)
    md5=null:                   varchar(255)
    file_size=null:             float
    """


@schema
class FileRecord(dj.Manual):
    definition = """
    -> DataSet
    -> DataRepository
    ---
    record_uuid:        uuid
    exists:             boolean
    relative_path:      varchar(255)
    """
