import os, gc, json, datetime
from ibl_pipeline.ingest import job
from ibl_pipeline.process import get_important_pks, get_timezone
from ibl_pipeline.utils import is_valid_uuid


SESSION_FIELDS = [
    'location', 'subject', 'lab', 'start_time',
    'end_time', 'parent_session', 'project', 'type',
    'task_protocol', 'users', 'procedures']


def get_modified_pks(data0, data1):
    d0 = {_['pk']: json.dumps(_['fields'], sort_keys=True) for _ in data0}
    d1 = {_['pk']: json.dumps(_['fields'], sort_keys=True) for _ in data1}
    d0 = {k: v for k, v in d0.items() if k in d1.keys()}
    d1 = {k: v for k, v in d1.items() if k in d0.keys()}

    return [k for k in d0.keys() if d0[k] != d1[k] and is_valid_uuid(k)]


def get_created_deleted_pks(data0, data1):

    old_pks = {_['pk'] for _ in data0}
    new_pks = {_['pk'] for _ in data1}

    return [pk for pk in sorted(new_pks - old_pks) if is_valid_uuid(pk)], \
        [pk for pk in sorted(old_pks - new_pks) if is_valid_uuid(pk)]


def filter_modified_keys_session(data0, data1, modified_pks):

    sessions0 = {_['pk']: json.dumps({key: _['fields'][key] for key in SESSION_FIELDS}, sort_keys=True)
                 for _ in data0 if _['model'] == 'actions.session'}
    sessions1 = {_['pk']: json.dumps({key: _['fields'][key] for key in SESSION_FIELDS}, sort_keys=True)
                 for _ in data1 if _['model'] == 'actions.session'}
    sessions_same = dict(sessions0.items() & sessions1.items()).keys()
    return list(set(modified_pks) - set(sessions_same))


def compare_json_dumps(previous_dump='/data/alyxfull.json',
                       latest_dump='/data/alyxfull.json.last',
                       create_files=True, insert_to_table=True,
                       filter_pks_for_unused_models=True,
                       filter_pks_for_unused_session_fields=True):

    """Compare two json dumps from alyx and created files with the added, deleted, modified fields.

    Args:
        previous_dump (json filepath, optional): filepath of alyx json dump of the last ingestion Defaults to /data/alyxfull.json.
        latest_dump (json filepath, optional): filepath of alyx json dump of the current ingestion. Defaults to '/data/alyxfull.json.last'
        create_files (bool, optional): whether to create files saving the created, deleted, modified keys. Defaults to True.
        insert_to_table (bool, optional): whether to insert the result to DataJoint job table. Defaults to True.
        filter_pks_for_unused_models (bool, optional): filter modified pks in models of interest. Defaults to True.
        filter_pks_for_unused_session_fields (bool, optional): only keep the modified keys when there is a change in fields of interest. Defaults to True.

    """

    print("Loading first JSON dump...")
    with open(previous_dump, 'r') as f:
        data0 = json.load(f)
    print("Loading second JSON dump...")
    with open(latest_dump, 'r') as f:
        data1 = json.load(f)
    print("Finished loading JSON dumps.")

    print("Computing differences...")
    modified_pks = get_modified_pks(data0, data1)

    print("Finished creating modified keys.")
    print("Computing created and deleted_keys...")

    created_pks, deleted_pks = get_created_deleted_pks(data0, data1)

    print("Finished creating created_pks and deleted_pks.")

    if filter_pks_for_unused_session_fields:
        print('Filtering modified sessions that does not have a change in fields of interest...')
        modified_pks = filter_modified_keys_session(data0, data1, modified_pks)

    if filter_pks_for_unused_models:
        print('Remove modified entries in tables data.filerecord and jobs.task')
        modified_pks_important = get_important_pks(modified_pks)

    # figure out job date and timezone
    latest_modified_time = datetime.datetime.fromtimestamp(
        os.path.getmtime(latest_dump))
    d = latest_modified_time.date()
    t = latest_modified_time.time()
    previous_modified_time = datetime.datetime.fromtimestamp(
        os.path.getmtime(previous_dump))

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

        if filter_pks_for_unused_models:
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
            filter_pks_for_unused_session_fields=filter_pks_for_unused_session_fields
        )
        if filter_pks_for_unused_models:
            job.Job.insert1(
                dict(**entry,
                     modified_pks_important=modified_pks_important),
                skip_duplicates=True)
        else:
            job.Job.insert1(entry, skip_duplicates=True)


if __name__ == '__main__':

    compare_json_dumps(insert_to_table=False)
