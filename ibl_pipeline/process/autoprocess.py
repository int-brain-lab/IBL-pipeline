
from ibl_pipeline.process import (
    delete_update_entries,
    ingest_alyx_raw,
    ingest_membership,
    ingest_shadow,
    ingest_real,
    populate_behavior,
    get_timezone
)
from ibl_pipeline.ingest import job
from os import path
import datetime
import time


def process_all():
    pass


def ingest_status(job_key, task, start, end):

    job.TaskStatus.insert1(
        dict(
            **job_key,
            task=task,
            task_start_time=start,
            task_end_time=end,
            task_duration=(end-start).total_seconds()/60.,
        ),
        skip_duplicates=True
    )


def process_new(previous_dump=None, latest_dump=None,
                job_date=datetime.date.today().strftime('%Y-%m-%d'),
                timezone='other'):

    job_key = dict(
        job_date=job_date,
        job_timezone=timezone,
    )

    if previous_dump is None:
        previous_dump = path.join('/', 'data', 'alyxfull.json.last')

    if latest_dump is None:
        latest_dump = path.join('/', 'data', 'alyxfull.json')

    print('Comparing json dumps ...')
    job.compare_json_dumps(previous_dump, latest_dump)

    created_pks, modified_pks, deleted_pks, modified_pks_important = (
        job.Job & job_key).fetch1(
            'created_pks', 'modified_pks', 'deleted_pks', 'modified_pks_important')

    print('Deleting modified entries from alyxraw and shadow tables...')
    start = datetime.datetime.now()

    delete_update_entries.delete_entries_from_alyxraw(
        modified_pks, modified_pks_important)

    ingest_status(job_key, 'Delete alyxraw', start, end=datetime.datetime.now())

    print('Deleting modified entries from membership tables...')
    start = datetime.datetime.now()
    delete_update_entries.delete_entries_from_membership(
        modified_pks_important)
    ingest_status(job_key, 'Delete shadow membership', start,
                  end=datetime.datetime.now())

    print('Ingesting into alyxraw...')
    start = datetime.datetime.now()
    ingest_alyx_raw.insert_to_alyxraw(
        ingest_alyx_raw.get_alyx_entries(
            latest_dump, new_pks=created_pks+modified_pks))
    ingest_status(job_key, 'Ingest alyxraw', start, end=datetime.datetime.now())

    print('Ingesting into shadow tables...')
    start = datetime.datetime.now()
    ingest_shadow.main()
    ingest_status(job_key, 'Ingest shadow', start, end=datetime.datetime.now())

    print('Ingesting into shadow membership tables...')
    start = datetime.datetime.now()
    ingest_membership.main(created_pks+modified_pks_important)
    ingest_status(job_key, 'Ingest shadow membership', start,
                  end=datetime.datetime.now())

    print('Ingesting alyx real...')
    start = datetime.datetime.now()
    ingest_real.main()
    ingest_status(job_key, 'Ingest real', start, end=datetime.datetime.now())

    print('Updating fields...')
    start = datetime.datetime.now()
    delete_update_entries.update_entries_from_real_tables(
        modified_pks_important)
    ingest_status(job_key, 'Update fields', start, end=datetime.datetime.now())

    print('Ingesting behavior...')
    start = datetime.datetime.now()
    populate_behavior.main(backtrack_days=12)
    ingest_status(job_key, 'Populate behavior', start,
                  end=datetime.datetime.now())


if __name__ == '__main__':
    process_new(previous_dump='/data/alyxfull_0914.json',
                latest_dump='/data/alyxfull_0915.json',
                job_date='2020-09-15', timezone='EST')
