import datajoint as dj
from ibl_pipeline.ingest import alyxraw
from ibl_pipeline.ingest import action as action_shadow
from ibl_pipeline import action, data

dj.config['safemode'] = False

# delete alyxraw
alyxraw.AlyxRaw.delete()

# delete some shadow tables
action_shadow.WaterRestrictionProcedure.delete()
action_shadow.WaterRestrictionUser.delete()

# delete some real tables
action.Weighing.delete()
action.WaterAdministration.delete()
action.WaterRestriction.delete()
data.FileRecord.delete()