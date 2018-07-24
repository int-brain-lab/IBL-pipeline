import datajoint as dj

import subject
import equipment
import reference

schema = dj.schema(dj.config['names.%s' % __name__], locals())

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
    # XXX: session_type table?
    definition = """
    -> subject.Subject
    session_number:             integer		# number
    session_start_time:         datetime	# start time
    ---
    session_end_time:           datetime	# end time
    session_type:		varchar(255)	# type
    -> equipment.LabLocation
    -> reference.User
    """


@schema
class PupilTracking(dj.Manual):
    # <class 'behavior.models.PupilTracking'>
    definition = """
    -> Session
    pupil_tracking_start_time:  datetime        # start time
    eye:                        enum("L", "R")  # eye
    ---
    pupil_tracking_movie:       longblob        # pupil tracking movie (raw)
    pupil_trace:                longblob        # x y d
    """


@schema
class HeadTracking(dj.Manual):
    # <class 'behavior.models.HeadTracking'>
    definition = """
    -> Session
    head_tracking_start_time:   datetime        # start time
    ---
    head_tracking_movie:        longblob        # head tracking movie (raw)
    head_position:              longblob        # x y theta
    """


@schema
class OptogeneticStimulus(dj.Manual):
    # <class 'behavior.models.OptogeneticStimulus'>
    definition = """
    -> Session
    -> reference.BrainLocation
    ---
    -> equipment.LightSource
    light_delivery:		varchar(255)	# light delivery
    wavelength:    		float		# wavelength
    power_calculation_method:	varchar(255)	# power calculation method
    description:		varchar(255)	# description
    """

    class Pulse(dj.Part):
        definition = """
        -> OptogeneticStimulus
        pulse_start_time:       float           # pulse start time
        ---
        pulse_stop_time:        float           # pulse stop time
        pulse_power:            smallint        # pulse power
        pulse_x:                float           # pulse x position
        pulse_y:                float           # pulse y position
        pulse_z:                float           # pulse z position
        """


@schema
class Pharmacology(dj.Manual):
    # <class 'behavior.models.Pharmacology'>
    definition = """
    -> Session
    drug:			varchar(255)	# drug
    administration_start_time:  float		# start time
    ---
    administration_end_time:    float		# end time
    administration_route:	varchar(255)	# administration route
    concentration:		float           # concentration
    volume:			float   	# volume
    """
