import os
from .behavior_shared import *

mode = dj.config.get('custom', {}).get('database.mode', "")

if mode != 'public':
    from .behavior_internal import *
