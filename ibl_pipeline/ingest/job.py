
import datajoint as dj


schema = dj.schema(dj.config.get('database.prefix', '') +
                   'ibl_ingest_job')


@schema
class TimeZone(dj.Lookup):
    definition = """
    timezone:       varchar(16)
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
    task_start_time         :  datetime
    task_end_time           :  datetime
    task_duration           :  float     # in mins
    task_status_comments='' :  varchar(1000)
    """
