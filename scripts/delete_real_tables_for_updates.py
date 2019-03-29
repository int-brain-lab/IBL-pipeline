
import datajoint as dj
from ibl_pipeline import action
from ibl_pipeline.ingest import action as action_ingest


dj.config['safemode'] = False

# delete some real tables when the shadow tables are available
if len(action_ingest.Weighing()):
    action.Weighing.delete()

if len(action_ingest.WaterAdiminitration()):
    action.WaterAdministration.delete()

if len(action_ingest.WaterRestriction()):
    action.WaterRestriction.delete()
