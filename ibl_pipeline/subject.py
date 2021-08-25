import os
from .subject_shared import *

mode = os.environ.get('MODE')

if mode != 'public':
    from .subject_internal import *
