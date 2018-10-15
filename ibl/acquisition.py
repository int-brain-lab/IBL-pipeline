import datajoint as dj

from . import subject
from . import reference, subject, action

schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_acquisition')

'''
To simplify from Alyx schema, dropping file repositories as core
parts of tables and moving to per-table blobs. A facility for
tracking data provenance could still made avaialble via a table
linked into individual model records as a non-primary attribute.

This is probably not ideal w/r/t Alyx -

one idea would be to merge use external storage with example
field def being:

  aligned_movie :  external  # motion-aligned movie

and also have a separate 'phase 1' data schema, which is then coupled
with phase 2+ for higher level data products.

Also note: TimeScale items missing wrt TimeSeries items, which were:

- PupilTracking.xyd
- PupilTracking.movie
- HeadTracking.xy_theta
- HeadTracking.movie

TimeScale not yet defined

# SKIPPED:
# <class 'data.models.DataRepositoryType'>
# <class 'data.models.DataRepository'>
# <class 'data.models.DatasetType'>
# <class 'data.models.Dataset'>
# <class 'data.models.FileRecord'>
# <class 'data.models.DataCollection'>
# <class 'data.models.Timescale'>
# <class 'data.models.TimeSeries'>
# <class 'data.models.EventSeries'>
# <class 'data.models.IntervalSeries'>
'''


@schema
class Session(dj.Manual):
    # <class 'actions.models.Session'>
    definition = """
    -> subject.Subject
    session_start_time:         datetime	# start time
    ---
    session_uuid:               varchar(64)
    session_number:             int     	# number
    session_end_time=null:      datetime	# end time
    -> [nullable] reference.Project
    -> [nullable] reference.LabLocation
    session_type:		        varchar(255)	# type
    session_narrative=null:     varchar(1024)
    """


@schema
class ChildSession(dj.Manual):
    definition = """
    -> Session
    ---
    (parent_session_start_time) -> Session(session_start_time)
    """


@schema
class SessionLabMember(dj.Manual):
    definition = """
    -> Session
    -> reference.LabMember
    """


@schema
class SessionProcedureType(dj.Manual):
    definition = """
    -> Session
    -> action.ProcedureType
    """
