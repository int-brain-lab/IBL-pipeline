# clean up external files
import datajoint as dj

schema = dj.schema("ibl_ephys")

# This only deletes entries that has been deleted before in the database.
schema.external["ephys_local"].delete(delete_external_files=True)
