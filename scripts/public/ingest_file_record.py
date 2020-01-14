
from ibl_pipeline.ingest import alyxraw, data, InsertBuffer
from ibl_pipeline.ingest import get_raw_field as grf
import uuid
from tqdm import tqdm

records = alyxraw.AlyxRaw & 'model="data.filerecord"'
repos = (data.DataRepository & 'repo_name LIKE "flatiron%"').fetch(
    'repo_uuid')
records_flatiron = alyxraw.AlyxRaw.Field & records & \
    'fname = "data_repository"' & [{'fvalue': str(repo)} for repo in repos]
record_exists = alyxraw.AlyxRaw.Field & records & \
    'fname = "exists"' & 'fvalue="True"'
key_source = (alyxraw.AlyxRaw & record_exists & records_flatiron).proj(
    record_uuid='uuid') - data.FileRecord

file_record = InsertBuffer(data.FileRecord)

for key in tqdm(key_source.fetch('KEY')):
    key_fr = key.copy()
    key['uuid'] = key['record_uuid']
    key_fr['exists'] = True

    dataset = grf(key, 'dataset')
    if not len(data.DataSet & dict(dataset_uuid=uuid.UUID(dataset))):
        print('Dataset {} is not in the table data.DataSet')
        print('Record_uuid: {}'.format(str(key['uuid'])))
        continue

    key_fr['subject_uuid'], key_fr['session_start_time'], \
        key_fr['dataset_name'] = \
        (data.DataSet & dict(dataset_uuid=uuid.UUID(dataset))).fetch1(
            'subject_uuid', 'session_start_time', 'dataset_name')

    repo = grf(key, 'data_repository')
    key_fr['repo_name'] = \
        (data.DataRepository & dict(repo_uuid=uuid.UUID(repo))).fetch1(
            'repo_name')

    key_fr['relative_path'] = grf(key, 'relative_path')

    file_record.insert1(key_fr)

    if file_record.flush(
            skip_duplicates=True, allow_direct_insert=True, chunksz=100):
        print('Inserted 10000 raw field tuples')
