
import datajoint as dj
from ibl_pipeline import action, data

dj.config['safemode'] = False

# delete some real tables
action.Weighing.delete()
action.WaterAdministration.delete()
action.WaterRestriction.delete()
