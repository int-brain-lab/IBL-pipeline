import datajoint as dj
import os

dj.config['stores'] = {
    'ephys': dict(
        protocol='s3',
        endpoint='s3.amazonaws.com',
        access_key=os.environ.get('S3_ACCESS'),
        secret_key=os.environ.get('S3_SECRET'),
        bucket='ibl-dj-external',
        location='/ephys'
    ),
    'plotting': dict(
        protocol='s3',
        endpoint='s3.amazonaws.com',
        access_key=os.environ.get('S3_ACCESS'),
        secret_key=os.environ.get('S3_SECRET'),
        bucket='ibl-dj-external',
        location='/plotting'
    )
}
