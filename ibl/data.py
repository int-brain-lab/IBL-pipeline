import datajoint as dj
from . import reference, acquisition

schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_data')

@schema
class DataFormat(dj.Lookup):
    definition = """
    format_name:                    varchar(255)
    ---    
    format_uuid:                    varchar(64)
    file_extension='':              varchar(255)
    matlab_loader_function=null:    varchar(255)
    python_loader_function=null:    varchar(255)
    format_description=null:        varchar(255)
    """
    
@schema
class DataRepositoryType(dj.Lookup):
    definition = """
    repotype_name:  varchar(255)
    ---
    repotype_uuid:  varchar(64)
    """

@schema
class DataRepository(dj.Lookup):
    definition = """
    repo_name:          varchar(255)
    ---
    -> DataRepositoryType
    repo_uuid:          varchar(64)
    repo_time_zone:     varchar(255)
    repo_dns:           varchar(255)
    globus_endpoint_id: varchar(255)
    globus_path:        varchar(255)
    data_url=null:      varchar(255)
    globus_is_personal: boolean
    """

@schema
class ProjectRepository(dj.Manual):
    definition = """
    -> reference.Project
    -> DataRepository
    """
   
@schema
class DataSetType(dj.Lookup):
    definition = """
    dataset_type_name:              varchar(255)
    ---
    dataset_type_uuid:              varchar(64)
    user_name=null:                 varchar(255)
    filename_pattern:               varchar(255)
    dataset_type_description=null:  varchar(1024)
    """


@schema
class DataSet(dj.Manual):
    definition = """
    -> acquisition.Session
    dataset_name:               varchar(255)
    ---
    dataset_uuid:               varchar(64)
    -> reference.LabMember
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
    ---
    record_uuid:        varchar(64)
    exists:             boolean
    -> DataRepository
    relative_path:      varchar(255)
    """
