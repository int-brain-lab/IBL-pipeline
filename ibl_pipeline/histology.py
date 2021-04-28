import os
from .histology_shared import *

mode = os.environ.get('MODE')

if mode != 'public':
    from .histology_internal import *
