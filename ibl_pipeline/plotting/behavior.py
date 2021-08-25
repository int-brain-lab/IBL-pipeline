import os
from .behavior_shared import *

mode = os.environ.get('MODE')

if mode != 'public':
    from .behavior_internal import *
