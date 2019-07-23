import datajoint as dj
import os


if os.environ.get('MODE') == 'test':
    dj.config['database.prefix'] = 'test_'

dj.config['stores'] = {
    'ephys': dict(
        protocol='s3',
        endpoint='https://s3.amazonaws.com',
        access_key='AKIAX2NIY5IRJVKSPHVW',
        secret_key='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',
        bucket='ibl_external',
        location='ephys'
    ),
    'plotting': dict(
        protocol='s3',
        endpoint='https://s3.amazonaws.com',
        access_key='AKIAX2NIY5IRJVKSPHVW',
        secret_key='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',
        bucket='ibl_external',
        location='plotting'
    )
}
