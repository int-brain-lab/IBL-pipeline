
import datajoint as dj

from . import subject
from . import reference

from .. import acquisition as ds_acquisition

schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_ingest_acquisition')


@schema
class Session(dj.Computed):
    definition = ds_acquisition.Session.definition
