import datajoint as dj
from ibl_pipeline import reference, subject, action
from ibl_pipeline import mode


# try to access parent schemas with virtual modules, if not created, import from package
try:
    action = dj.create_virtual_module('action', 'ibl_action')
except dj.DataJointError:
    from ibl_pipeline import action

try:
    acquisition = dj.create_virtual_module('acquisition', 'ibl_acquistion')
    Session = acquisition.Session
except dj.DataJointError:
    from ibl_pipeline.acquisition import Session

if mode == 'update':
    schema = dj.schema('ibl_acquisition')
else:
    schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_acquisition')


@schema
class WaterAdministrationSession(dj.Manual):
    definition = """
    -> action.WaterAdministration
    ---
    -> Session
    wateradministrationsession_ts=CURRENT_TIMESTAMP:   timestamp
    """
