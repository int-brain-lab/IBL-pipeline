'''
This script repopulates the data sets where probLeft has a problem.
Shan Shen,
2020-03-23
'''

from ibl_pipeline import subject, acquisition, behavior, ephys
from ibl_pipeline.analyses import behavior as behavior_analyses
from ibl_pipeline.plotting import behavior as behavior_plotting
from ibl_pipeline.plotting import ephys as ephys_plotting
from uuid import UUID
import datetime
import datajoint as dj
from tqdm import tqdm

dj.config['safemode'] = False

kargs = dict(suppress_errors=True, display_progress=True)

keys = [
    {'subject_uuid': UUID('088b6898-0a86-435e-b91f-eab829a846f6'),
     'session_start_time': datetime.datetime(2019, 11, 21, 17, 11, 10),
     'session_date': datetime.date(2019, 11, 21)}]


for key in tqdm(keys):
    print('----------- Deleting AlignedTrialSpikes ---------')
    clusters = (ephys.Cluster & key).fetch('KEY')
    for cluster in clusters:
        (ephys.AlignedTrialSpikes & cluster).delete_quick()

    print('---- Deleting TrialSet downstream plotting tables ----')
    (behavior_plotting.DateReactionTimeTrialNumber & key).delete_quick()
    (behavior_plotting.DateReactionTimeContrast & key).delete_quick()
    (behavior_plotting.DateReactionTimeContrast & key).delete_quick()
    (behavior_plotting.DatePsychCurve & key).delete_quick()
    (behavior_plotting.SessionReactionTimeTrialNumber & key).delete_quick()
    (behavior_plotting.SessionReactionTimeContrast & key).delete_quick()
    (behavior_plotting.SessionPsychCurve & key).delete_quick()

    print('---- Deleting TrialSet downstream analyses tables ----')
    (behavior_analyses.ReactionTimeContrastBlock & key).delete_quick()
    (behavior_analyses.ReactionTime & key).delete_quick()
    (behavior_analyses.BehavioralSummaryByDate & key).delete()
    (behavior_analyses.SessionTrainingStatus & key).delete()
    (behavior_analyses.PsychResultsBlock & key).delete_quick()
    (behavior_analyses.PsychResults & key).delete_quick()

    print('---- Deleting TrialSet main tables ----')
    (behavior.AmbientSensorData & key).delete_quick()
    (behavior.TrialSet & key).delete_quick()

    print('----------- Populating TrialSet ------------')
    behavior.TrialSet.populate(key, **kargs)
    print('----------- Populating Ambient Sensor data------------')
    behavior.AmbientSensorData.populate(key, **kargs)
    print('----------- Populating PsychResults ------------')
    behavior_analyses.PsychResults.populate(key, **kargs)
    print('--------- Populating PsychResultsBlock ---------')
    behavior_analyses.PsychResultsBlock.populate(key, **kargs)
    print('----------- Populating ReactionTime ------------')
    behavior_analyses.ReactionTime.populate(key, **kargs)
    print('----- Populating ReactionTimeContrastBlock -----')
    behavior_analyses.ReactionTimeContrastBlock.populate(key, **kargs)
    print('------- Populating SessionTrainingStatus -------')
    behavior_analyses.SessionTrainingStatus.populate(key, **kargs)
    print('------ Populating BehavioralSummaryByDate ------')
    behavior_analyses.BehavioralSummaryByDate.populate(key, **kargs)
    print('------------ Populating plotting.SessionPsychCurve -----------')
    behavior_plotting.SessionPsychCurve.populate(key, **kargs)
    print('------ Populating plotting.SessionReactionTimeContrast -------')
    behavior_plotting.SessionReactionTimeContrast.populate(key, **kargs)
    print('---- Populating plotting.SessionReactionTimeTrialNumber ------')
    behavior_plotting.SessionReactionTimeTrialNumber.populate(key, **kargs)
    print('--------------- Populating plotting.DatePsychCurve -----------')
    behavior_plotting.DatePsychCurve.populate(key, **kargs)
    print('-------- Populating plotting.DateReactionTimeContrast --------')
    behavior_plotting.DateReactionTimeContrast.populate(key, **kargs)
    print('------ Populating plotting.DateReactionTimeTrialNumber -------')
    behavior_plotting.DateReactionTimeTrialNumber.populate(key, **kargs)
    print('--------------- Populating AlignedTrial -----------')
    ephys.AlignedTrialSpikes.populate(key, **kargs)
