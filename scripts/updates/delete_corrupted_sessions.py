import datajoint as dj
from ibl_pipeline import subject, acquisition, data, behavior
from ibl_pipeline.ingest import acquisition as acquisition_ingest
from ibl_pipeline.ingest import alyxraw
import datetime
from oneibl.one import ONE
import numpy as np
from uuid import UUID


uuids = ((acquisition_ingest.Session - behavior.TrialSet.proj()) &
         'session_start_time > "2019-06-13"').fetch('session_uuid')
uuid_str = [str(uuid) for uuid in uuids]
for uuid in uuid_str:
    keys = (alyxraw.AlyxRaw.Field & 'fvalue="{}"'.format(uuid)).fetch('KEY')
    (alyxraw.AlyxRaw & keys).delete()
    (alyxraw.AlyxRaw & 'uuid ="{}"'.format(uuid)).delete()
