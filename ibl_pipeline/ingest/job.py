
import datajoint as dj
import os
import json
import datetime
import ibl_pipeline

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
    created_keys   : longblob
    modified_keys  : longblob
    deleted_keys   : longblob
    job_ts=CURRENT_TIMESTAMP : timestamp
    """


def compare_json_dumps(previous_dump=None, latest_dump=None,
                       create_files=True, insert_to_table=True):
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
    created_pks = sorted(set(new_pks) - set(old_pks))
    deleted_pks = sorted(set(old_pks) - set(new_pks))
    print("Computing differences...")
    d0 = {_['pk']: json.dumps(_['fields'], sort_keys=True) for _ in data0}
    d1 = {_['pk']: json.dumps(_['fields'], sort_keys=True) for _ in data1}
    di = d0.keys() & d1.keys()
    d0 = {k:v for k, v in d0.items() if k in di}
    d1 = {k:v for k, v in d1.items() if k in di}
    s0 = set(d0.items())
    s1 = set(d1.items())
    sd = s0 ^ s1
    modified_pks = sorted(dict(sd).keys())

    # figure out job date and timezone
    latest_modified_time = datetime.datetime.fromtimestamp(os.path.getmtime(latest_dump))
    d = latest_modified_time.date()
    t = latest_modified_time.time()
    previous_modified_time = datetime.datetime.fromtimestamp(os.path.getmtime(previous_dump))

    if t < datetime.time(5, 30):
        timezone = 'European'
    elif t > datetime.time(5, 30) and t < datetime.time(10, 30):
        timezone = 'EST'
    elif t > datetime.time(10, 30) and t < datetime.time(14, 30):
        timezone = 'PST'
    else:
        timezone = 'other'

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
        with open(f"{root_dir}modified_keys_{suffix}.json", "w") as f:
            json.dump(modified_pks, f)

    if insert_to_table:
        Job.insert1(
            dict(
                job_date=d,
                job_timezone=timezone,
                alyx_current_timestamp=latest_modified_time,
                alyx_previous_timestamp=previous_modified_time,
                created_keys=created_pks,
                modified_keys=modified_pks,
                deleted_keys=deleted_pks))


if __name__ == '__main__':

    compare_json_dumps('/data/alyxfull.json.0902', '/data/alyxfull.json.0903')
