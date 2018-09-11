
import datajoint as dj

from .. import reference as ds_reference


schema = dj.schema('ibl_ingest_reference')


@schema
class User(dj.Computed):
    definition = ds_reference.User.definition


@schema
class Severity(dj.Computed):
    definition = ds_reference.Severity.definition


@schema
class Note(dj.Computed):
    definition = ds_reference.Note.definition


@schema
class BrainLocationAcronym(dj.Computed):
    definition = ds_reference.BrainLocationAcronym.definition


