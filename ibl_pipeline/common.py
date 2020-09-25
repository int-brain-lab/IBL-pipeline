from ibl_pipeline import reference, subject, action, acquisition, data, behavior
from ibl_pipeline.analyses import behavior as behavior_analyses
from ibl_pipeline.plotting import behavior as behavior_plotting

from os import environ

mode = environ.get('MODE')
if mode != 'public':
    from ibl_pipeline import ephys, histology
    from ibl_pipeline.analyses import ephys as ephys_analyses
    from ibl_pipeline.plotting import ephys as ephys_plotting
