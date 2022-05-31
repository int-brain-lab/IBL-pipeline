import datajoint as dj
from tqdm import tqdm

from ibl_pipeline import acquisition, mode, one, reference

if mode == "update":
    schema = dj.schema("ibl_data")
else:
    schema = dj.schema(dj.config.get("database.prefix", "") + "ibl_data")


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

    @classmethod
    def insert_with_alyx_rest(cls, session_uuids, dataset_names):
        """Helper function that inserts dataset and file record entries by query alyx with rest api
        This is used when finding dataset/filerecord entries do not exist for particular sessions
        - Shan Shen 07/28/2021

        Args:
            session_uuids (list of str): list of uuids (as str) for sessions whose datasets are missing
            dataset_name (list of str): list of the dataset names
        """
        for uuid in tqdm(session_uuids):
            for dataset_name in tqdm(dataset_names):
                try:
                    dataset = one.alyx.rest(
                        "datasets", "list", session=uuid, name=dataset_name
                    )
                    if not dataset:
                        print(
                            f"Dataset {dataset_name} for session {uuid} does not exist in alyx."
                        )
                        continue
                    else:
                        dataset = dataset[0]
                    session_key = (acquisition.Session & {"session_uuid": uuid}).fetch1(
                        "KEY"
                    )
                    dataset_entry = dict(
                        session_key,
                        dataset_name=dataset_name,
                        dataset_uuid=dataset["hash"],
                        dataset_created_by=dataset["created_by"],
                        dataset_type_name=dataset["dataset_type"],
                        format_name=dataset["data_format"],
                        created_datetime=dataset["created_datetime"],
                        file_size=dataset["file_size"],
                    )

                    cls.insert1(dataset_entry, skip_duplicates=True)
                    # except Exception as e:
                    #     print(f'Error inserting {dataset_name} in table DataSet for session {uuid}: {str(e)}')

                    file_record_entries = []
                    for fr in dataset["file_records"]:
                        if fr["exists"] and "flatiron" in fr["data_repository"]:
                            file_record_entry = dict(
                                session_key,
                                dataset_name=dataset_name,
                                repo_name=fr["data_repository"],
                                record_uuid=fr["id"],
                                exists=fr["exists"],
                                relative_path=fr["relative_path"],
                            )
                            file_record_entries.append(file_record_entry)
                    # try:
                    FileRecord.insert(file_record_entries, skip_duplicates=True)
                    # except Exception as e:
                    #     print(f'Error inserting {dataset_name} in table FileRecord for session {uuid}: {str(e)}')
                except Exception as e:
                    print(str(e))
                    continue


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
