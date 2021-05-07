import os
from .acquisition_shared import *

mode = os.environ.get('MODE')

if mode != 'public':
    from .acquisition_internal import *
