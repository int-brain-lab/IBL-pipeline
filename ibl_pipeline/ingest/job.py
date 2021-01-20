
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
    alyx_current_timestamp  : datetime
    alyx_previous_timestamp : datetime
    created_pks   : longblob
    modified_pks  : longblob
    deleted_pks   : longblob
    modified_pks_important=null : longblob
    session_prefiltered=0: bool
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
        ['Delete alyxraw', 1, 'Delete alyxraw and shadow table entries for updated and deleted records'],
        ['Delete shadow membership', 2, 'Delete shadow membership records for updated and deleted records'],
        ['Ingest alyxraw', 3, 'Ingest to alyxraw'],
        ['Ingest shadow', 4, 'Ingest to alyx shadow tables'],
        ['Ingest shadow membership', 5, 'Ingest to alyx shadow membership tables'],
        ['Ingest real', 6, 'Ingest to alyx real tables'],
        ['Update fields', 7, 'Update fields in real tables'],
        ['Populate behavior', 8, 'Populate behavior tables']
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
