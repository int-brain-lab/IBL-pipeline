import datajoint as dj
from os import environ


if environ.get('MODE') == 'test':
    dj.config['database.prefix'] = 'test_'
