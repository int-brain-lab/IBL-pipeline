import datajoint as dj
from ibl_pipeline.ingest import alyxraw
from ibl_pipeline.ingest import action as action_shadow
from ibl_pipeline import action, data

dj.config['safemode'] = False

# delete alyxraw except for datasets and file records
#(alyxraw.AlyxRaw & 'model not in ("data.dataset", "data.filerecord")').delete()

# delete alyxraw for data.filerecord if exists = 0
# file_record_fields = alyxraw.AlyxRaw.Field & 'fname = "exists"' & 'fvalue = "False"'
# keys = (alyxraw.AlyxRaw & file_record_fields).fetch('KEY')
# (alyxraw.AlyxRaw & keys).delete()
alyxraw.AlyxRaw.delete()

# delete some shadow tables
action_shadow.WaterRestrictionProcedure.delete()
action_shadow.WaterRestrictionUser.delete()
