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
    {'subject_uuid': UUID('18a54f60-534b-4ed5-8bda-b434079b8ab8'),
     'session_start_time': datetime.datetime(2019, 12, 4, 12, 34, 21),
     'session_date': datetime.date(2019, 12, 4)},
    {'subject_uuid': UUID('18a54f60-534b-4ed5-8bda-b434079b8ab8'),
     'session_start_time': datetime.datetime(2019, 12, 5, 16, 28, 54),
     'session_date': datetime.date(2019, 12, 5)},
    {'subject_uuid': UUID('18a54f60-534b-4ed5-8bda-b434079b8ab8'),
     'session_start_time': datetime.datetime(2019, 12, 6, 18, 30, 56),
     'session_date': datetime.date(2019, 12, 6)},
    {'subject_uuid': UUID('18a54f60-534b-4ed5-8bda-b434079b8ab8'),
     'session_start_time': datetime.datetime(2019, 12, 7, 16, 19, 38),
     'session_date': datetime.date(2019, 12, 7)},
    {'subject_uuid': UUID('354e6122-de4a-4945-bafd-d46df65768f6'),
     'session_start_time': datetime.datetime(2019, 12, 4, 15, 54, 19),
     'session_date': datetime.date(2019, 12, 4)},
    {'subject_uuid': UUID('354e6122-de4a-4945-bafd-d46df65768f6'),
     'session_start_time': datetime.datetime(2019, 12, 5, 18, 57, 56),
     'session_date': datetime.date(2019, 12, 5)},
    {'subject_uuid': UUID('354e6122-de4a-4945-bafd-d46df65768f6'),
     'session_start_time': datetime.datetime(2019, 12, 6, 15, 36, 44),
     'session_date': datetime.date(2019, 12, 6)},
    {'subject_uuid': UUID('354e6122-de4a-4945-bafd-d46df65768f6'),
     'session_start_time': datetime.datetime(2019, 12, 8, 20, 1, 23),
     'session_date': datetime.date(2019, 12, 8)},
    {'subject_uuid': UUID('354e6122-de4a-4945-bafd-d46df65768f6'),
     'session_start_time': datetime.datetime(2019, 12, 9, 17, 31, 24),
     'session_date': datetime.date(2019, 12, 9)},
    {'subject_uuid': UUID('4e4b8689-cfc7-40b1-986a-b8d642920c98'),
     'session_start_time': datetime.datetime(2019, 11, 26, 12, 0, 15),
     'session_date': datetime.date(2019, 11, 26)},
    {'subject_uuid': UUID('4eb8afda-a4d9-4314-8956-cdf773223fe5'),
     'session_start_time': datetime.datetime(2019, 12, 3, 11, 30, 35),
     'session_date': datetime.date(2019, 12, 3)},
    {'subject_uuid': UUID('4eb8afda-a4d9-4314-8956-cdf773223fe5'),
     'session_start_time': datetime.datetime(2019, 12, 4, 11, 12, 38),
     'session_date': datetime.date(2019, 12, 4)},
    {'subject_uuid': UUID('4eb8afda-a4d9-4314-8956-cdf773223fe5'),
     'session_start_time': datetime.datetime(2019, 12, 5, 10, 5, 36),
     'session_date': datetime.date(2019, 12, 5)},
    {'subject_uuid': UUID('4eb8afda-a4d9-4314-8956-cdf773223fe5'),
     'session_start_time': datetime.datetime(2019, 12, 6, 10, 7, 39),
     'session_date': datetime.date(2019, 12, 6)},
    {'subject_uuid': UUID('7d334e82-1270-4346-86c2-4a8b7530946d'),
     'session_start_time': datetime.datetime(2019, 11, 25, 22, 53, 11),
     'session_date': datetime.date(2019, 11, 25)},
    {'subject_uuid': UUID('7d334e82-1270-4346-86c2-4a8b7530946d'),
     'session_start_time': datetime.datetime(2019, 11, 26, 18, 34, 56),
     'session_date': datetime.date(2019, 11, 26)},
    {'subject_uuid': UUID('7dfc4f76-3ab2-4d2b-9e01-f8c76e47f770'),
     'session_start_time': datetime.datetime(2019, 12, 11, 11, 35, 51),
     'session_date': datetime.date(2019, 12, 11)},
    {'subject_uuid': UUID('892316ab-346c-4592-a4ea-ee5e668fbdaa'),
     'session_start_time': datetime.datetime(2019, 11, 26, 17, 57, 15),
     'session_date': datetime.date(2019, 11, 26)},
    {'subject_uuid': UUID('9bebfe0b-082e-4d66-aca7-fae29317f708'),
     'session_start_time': datetime.datetime(2020, 1, 8, 15, 52, 42),
     'session_date': datetime.date(2020, 1, 8)},
    {'subject_uuid': UUID('9bebfe0b-082e-4d66-aca7-fae29317f708'),
     'session_start_time': datetime.datetime(2020, 1, 9, 15, 43, 58),
     'session_date': datetime.date(2020, 1, 9)},
    {'subject_uuid': UUID('9bebfe0b-082e-4d66-aca7-fae29317f708'),
     'session_start_time': datetime.datetime(2020, 1, 10, 14, 11, 34),
     'session_date': datetime.date(2020, 1, 10)},
    {'subject_uuid': UUID('9bebfe0b-082e-4d66-aca7-fae29317f708'),
     'session_start_time': datetime.datetime(2020, 1, 11, 13, 42, 47),
     'session_date': datetime.date(2020, 1, 11)},
    {'subject_uuid': UUID('b57c1934-f9d1-4dc4-a474-e2cb4acdf918'),
     'session_start_time': datetime.datetime(2019, 12, 8, 21, 58, 58),
     'session_date': datetime.date(2019, 12, 8)},
    {'subject_uuid': UUID('b57c1934-f9d1-4dc4-a474-e2cb4acdf918'),
     'session_start_time': datetime.datetime(2019, 12, 9, 19, 35, 10),
     'session_date': datetime.date(2019, 12, 9)},
    {'subject_uuid': UUID('b57c1934-f9d1-4dc4-a474-e2cb4acdf918'),
     'session_start_time': datetime.datetime(2019, 12, 10, 14, 40, 58),
     'session_date': datetime.date(2019, 12, 10)},
    {'subject_uuid': UUID('c00e0ffb-b8c6-4953-b9e7-975a3f4fd989'),
     'session_start_time': datetime.datetime(2019, 12, 4, 18, 33, 48),
     'session_date': datetime.date(2019, 12, 4)},
    {'subject_uuid': UUID('c25a02e4-d912-4c7e-8381-5cc1cec06faf'),
     'session_start_time': datetime.datetime(2019, 12, 10, 18, 32, 56),
     'session_date': datetime.date(2019, 12, 10)},
    {'subject_uuid': UUID('c25a02e4-d912-4c7e-8381-5cc1cec06faf'),
     'session_start_time': datetime.datetime(2019, 12, 11, 17, 30, 53),
     'session_date': datetime.date(2019, 12, 11)},
    {'subject_uuid': UUID('c25a02e4-d912-4c7e-8381-5cc1cec06faf'),
     'session_start_time': datetime.datetime(2019, 12, 15, 19, 51, 40),
     'session_date': datetime.date(2019, 12, 15)},
    {'subject_uuid': UUID('c6e8125f-b6c7-4349-b74d-32e8bd606f63'),
     'session_start_time': datetime.datetime(2019, 12, 6, 12, 14, 53),
     'session_date': datetime.date(2019, 12, 6)},
    {'subject_uuid': UUID('c6e8125f-b6c7-4349-b74d-32e8bd606f63'),
     'session_start_time': datetime.datetime(2019, 12, 7, 14, 15, 47),
     'session_date': datetime.date(2019, 12, 7)},
    {'subject_uuid': UUID('c6e8125f-b6c7-4349-b74d-32e8bd606f63'),
     'session_start_time': datetime.datetime(2019, 12, 8, 17, 40, 34),
     'session_date': datetime.date(2019, 12, 8)},
    {'subject_uuid': UUID('c6e8125f-b6c7-4349-b74d-32e8bd606f63'),
     'session_start_time': datetime.datetime(2019, 12, 10, 16, 44, 13),
     'session_date': datetime.date(2019, 12, 10)}]

au_behavior = dj.create_virtual_module('au_behavior', 'user_anneurai_behavior')


for key in tqdm(keys, position=0):
    print('----------- Deleting AlignedTrialSpikes ---------')
    (ephys.AlignedTrialSpikes & key).delete_quick()

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
    (au_behavior.ChoiceHistory & key).delete_quick()
    (behavior.TrialSet.Trial & key).delete_quick()
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
