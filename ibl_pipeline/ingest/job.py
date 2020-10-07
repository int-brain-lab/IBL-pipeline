
import datajoint as dj
import os
import json
import datetime
from ibl_pipeline.process.ingest_alyx_raw import insert_to_alyxraw, get_alyx_entries
from ibl_pipeline.process import get_important_pks, get_timezone
from ibl_pipeline.utils import is_valid_uuid

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

SESSION_FIELDS = [
    'location', 'subject', 'lab', 'start_time',
    'end_time', 'parent_session', 'project', 'type',
    'task_protocol', 'users', 'procedures']

def compare_json_dumps(previous_dump=None, latest_dump=None,
                       create_files=True, insert_to_table=True,
                       filter_modified_pks=True,
                       session_prefiltered=True):
    '''
    Compare two json dumps from alyx and created files with the added, deleted, modified fields.
    Inputs:     previous_dump:   filepath of the previous version of alyx json dump
                latest_dump:     filepath of the latest version of alyx json dump
    '''
    if not previous_dump:
        previous_dump = '/data/alyxfull.json'

    if not latest_dump:
        latest_dump = '/data/alyxfull.json.last'

    print("Loading first JSON dump...")
    with open(previous_dump, 'r') as f:
        data0 = json.load(f)
    print("Loading second JSON dump...")
    with open(latest_dump, 'r') as f:
        data1 = json.load(f)
    print("Finished loading JSON dumps.")
    old_pks = [_['pk'] for _ in data0]
    new_pks = [_['pk'] for _ in data1]
    created_pks = [pk for pk in sorted(set(new_pks) - set(old_pks)) if is_valid_uuid(pk)]
    deleted_pks = [pk for pk in sorted(set(old_pks) - set(new_pks)) if is_valid_uuid(pk)]
    print("Computing differences...")
    d0 = {_['pk']: json.dumps(_['fields'], sort_keys=True) for _ in data0}
    d1 = {_['pk']: json.dumps(_['fields'], sort_keys=True) for _ in data1}
    di = d0.keys() & d1.keys()
    d0 = {k:v for k, v in d0.items() if k in di}
    d1 = {k:v for k, v in d1.items() if k in di}
    s0 = set(d0.items())
    s1 = set(d1.items())
    sd = s0 ^ s1
    modified_pks = [pk for pk in sorted(dict(sd).keys()) if is_valid_uuid(pk)]
    del d0, d1

    if session_prefiltered:
        print('Filtering modified sessions that does not have a change in fields of interest...')
        sessions0 = {_['pk']: json.dumps({key:_['fields'][key] for key in SESSION_FIELDS}, sort_keys=True)
                     for _ in data0 if _['model']=='actions.session'}
        sessions1 = {_['pk']: json.dumps({key:_['fields'][key] for key in SESSION_FIELDS}, sort_keys=True)
                     for _ in data1 if _['model']=='actions.session'}
        sessions_same = dict(sessions0.items() & sessions1.items()).keys()
        modified_pks = list(set(modified_pks) - set(sessions_same))


    if filter_modified_pks:
        modified_pks_important = get_important_pks(modified_pks)

    # figure out job date and timezone
    latest_modified_time = datetime.datetime.fromtimestamp(os.path.getmtime(latest_dump))
    d = latest_modified_time.date()
    print(d)
    t = latest_modified_time.time()
    previous_modified_time = datetime.datetime.fromtimestamp(os.path.getmtime(previous_dump))

    timezone = get_timezone(t)

    if create_files:
        suffix = f'_{latest_modified_time.strftime("%Y-%m-%d")}_{timezone}'
        root_dir = '/data/daily_increments/'
        print(f"New objects: {len(created_pks)}")
        with open(f"{root_dir}created_pks_{suffix}.json", "w") as f:
            json.dump(created_pks, f)
        print(f"Deleted objects: {len(deleted_pks)}")
        with open(f"{root_dir}deleted_pks_{suffix}.json", "w") as f:
            json.dump(deleted_pks, f)
        print(f"Modified objects: {len(modified_pks)}")
        with open(f"{root_dir}modified_pks_{suffix}.json", "w") as f:
            json.dump(modified_pks, f)
        print(f"Important modified objects: {len(modified_pks_important)}")
        if filter_modified_pks:
            with open(f"{root_dir}modified_pks_important{suffix}.json", "w") as f:
                json.dump(modified_pks_important, f)

    if insert_to_table:
        entry = dict(
            job_date=d,
            job_timezone=timezone,
            alyx_current_timestamp=latest_modified_time,
            alyx_previous_timestamp=previous_modified_time,
            created_pks=created_pks,
            modified_pks=modified_pks,
            deleted_pks=deleted_pks,
            session_prefiltered=session_prefiltered
        )
        if filter_modified_pks:
            Job.insert1(
                dict(**entry,
                     modified_pks_important=modified_pks_important),
                skip_duplicates=True)
        else:
            Job.insert1(entry, skip_duplicates=True)


if __name__ == '__main__':

    # compare_json_dumps('/data/alyxfull.json.0902', '/data/alyxfull.json.0903')

    created_pks, modified_pks = (Job & 'job_date="2020-09-03"').fetch1(
        'created_pks', 'modified_pks')
    insert_to_alyxraw(
        get_alyx_entries('/data/alyxfull.json.0903',
                         new_pks=created_pks+modified_pks))
