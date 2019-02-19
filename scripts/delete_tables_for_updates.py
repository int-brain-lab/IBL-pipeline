import datajoint as dj
from ibl_pipeline.ingest import alyxraw
from ibl_pipeline.ingest import action as action_shadow
from ibl_pipeline import action, data

dj.config['safemode'] = False

# delete alyxraw except for datasets and file records
(alyxraw.AlyxRaw & 'model not in ("data.dataset", "data.filerecord")').delete()

# delete alyxraw for data.filerecord if exists = 0
file_records = alyx.AlyxRaw & 'model = "data.filerecord"'
file_record_fields = alyx.AlyxRaw.Field & file_records & 'fname = "exists"' & 'fvalue = "False"'
(alyxraw.AlyxRaw & file_record_fields).delete()

# delete some shadow tables
action_shadow.WaterRestrictionProcedure.delete()
action_shadow.WaterRestrictionUser.delete()

# delete some real tables
action.Weighing.delete()
action.WaterAdministration.delete()
action.WaterRestriction.delete()