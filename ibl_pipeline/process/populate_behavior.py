'''
This script ingest behavioral data into tables in the ibl_behavior schema
'''
import datetime
from ibl_pipeline import subject, reference, action
from tqdm import tqdm
import datajoint as dj
import time

from ibl_pipeline import acquisition, data, behavior
from ibl_pipeline.analyses import behavior as behavior_analyses
from ibl_pipeline.plotting import behavior as behavior_plotting


mode = dj.config.get('custom', {}).get('database.mode', "")

BEHAVIOR_TABLES = [
    behavior.CompleteWheelSession,
    behavior.CompleteTrialSession,
    behavior.TrialSet,
    behavior.AmbientSensorData,
    behavior.Settings,
    behavior.SessionDelay,
    behavior_analyses.PsychResults,
    behavior_analyses.PsychResultsBlock,
    behavior_analyses.ReactionTime,
    behavior_analyses.ReactionTimeContrastBlock,
    behavior_analyses.SessionTrainingStatus,
    behavior_analyses.BehavioralSummaryByDate,
    behavior_plotting.SessionPsychCurve,
    behavior_plotting.SessionReactionTimeContrast,
    behavior_plotting.SessionReactionTimeTrialNumber,
    behavior_plotting.DatePsychCurve,
    behavior_plotting.DateReactionTimeContrast,
    behavior_plotting.DateReactionTimeTrialNumber,
]

if mode != 'public':
    BEHAVIOR_TABLES.append(behavior_plotting.WaterTypeColor)


kwargs = dict(suppress_errors=True, display_progress=True)


def main(backtrack_days=30, excluded_tables=[], run_duration=3600*3, sleep_duration=60*10):

    start_time = time.time()
    while ((time.time() - start_time < run_duration)
           or (run_duration is None)
           or (run_duration < 0)):

        if backtrack_days:
            date_cutoff = \
                (datetime.datetime.now().date() -
                 datetime.timedelta(days=backtrack_days)).strftime('%Y-%m-%d')

        # ingest those dataset and file records where exists=False when json gets dumped
        # only check those sessions where required datasets are missing.
        # populate CompleteTrialSession first with existing file records
        behavior.CompleteTrialSession.populate(f'session_start_time > "{date_cutoff}"', **kwargs)
        sessions_missing = (acquisition.Session - behavior.CompleteTrialSession) & \
                f'session_start_time > "{(datetime.datetime.now().date() - datetime.timedelta(days=backtrack_days)).strftime("%Y-%m-%d")}"'

        uuids = [str(u) for u in sessions_missing.fetch('session_uuid')]

        data.DataSet.insert_with_alyx_rest(
            uuids, behavior.CompleteTrialSession.required_datasets + behavior.CompleteTrialSession.other_datasets)

        for table in BEHAVIOR_TABLES:

            if table.__name__ in excluded_tables:
                continue
            print(f'Populating {table.__name__}...')

            if backtrack_days and table.__name__ != 'WaterTypeColor':
                if 'Date' in table.__name__:
                    field = 'session_date'
                else:
                    field = 'session_start_time'
                restrictor = f'{field} > "{date_cutoff}"'
            else:
                restrictor = {}

            table.populate(restrictor, **kwargs)

        print('Populating SubjectLatestEvent...')
        for key in tqdm(subject.Subject.fetch('KEY'), position=0):
            behavior_plotting.SubjectLatestEvent.create_entry(key)

        print('Processing Cumulative plots...')
        with dj.config(safemode=False):
            (behavior_plotting.CumulativeSummary
             & behavior_plotting.CumulativeSummary.get_outdated_entries().fetch('KEY')).delete()
        behavior_plotting.CumulativeSummary.populate(**kwargs)

        print('Update SubjectLatestDate...')
        subject_latest_date = subject.Subject.aggr(behavior_plotting.CumulativeSummary,
                                                   latest_date='MAX(latest_date)')
        behavior_plotting.SubjectLatestDate.insert(subject_latest_date, skip_duplicates=True)

        need_update = behavior_plotting.SubjectLatestDate.proj(
            inserted_date='latest_date') * subject_latest_date & 'inserted_date != latest_date'
        for k in need_update.fetch('KEY'):
            (behavior_plotting.SubjectLatestDate & k)._update(
                'latest_date', (subject_latest_date & k).fetch1('latest_date'))

        if mode != 'public':
            print('Processing daily summary...')
            outdated_lab_summary = (behavior_plotting.DailyLabSummary
                                    - behavior_plotting.DailyLabSummary.key_source)
            with dj.config(safemode=False):
                (behavior_plotting.DailyLabSummary & outdated_lab_summary.fetch('KEY')).delete()
            behavior_plotting.DailyLabSummary.populate(**kwargs)

        time.sleep(sleep_duration)


if __name__ == '__main__':

    main(backtrack_days=30)
