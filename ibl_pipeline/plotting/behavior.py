import os

from ibl_pipeline.plotting.behavior_shared import *

mode = dj.config.get("custom", {}).get("database.mode", "")

if mode != "public":
    from ibl_pipeline.plotting.behavior_internal import *
