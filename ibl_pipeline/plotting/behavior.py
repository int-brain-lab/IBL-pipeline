import os

from ibl_pipeline import mode
from ibl_pipeline.plotting.behavior_shared import *

if mode != "public":
    from ibl_pipeline.plotting.behavior_internal import *
