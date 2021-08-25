'''
This script ingest behavioral data into tables in the ibl_behavior schema
'''
import datajoint as dj
from ibl_pipeline import acquisition, data, behavior
from ibl_pipeline.analyses import behavior as behavior_analyses
from ibl_pipeline.plotting import behavior as behavior_plotting

import datetime
from ibl_pipeline import subject, reference, action
from tqdm import tqdm
from os import environ

mode = environ.get('MODE')

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


kwargs = dict(
        suppress_errors=True, display_progress=True)


def compute_latest_date():

    for key in tqdm(subject.Subject.fetch('KEY'), position=0):
        behavior_summary = behavior_analyses.BehavioralSummaryByDate & key
        if behavior_summary:
            latest_behavior = subject.Subject.aggr(
                behavior_summary,
                last_behavior_date='MAX(session_date)')

        if mode != 'public':
            water_weight = action.Weighing * action.WaterAdministration & key

            if water_weight:
                latest_weight = subject.Subject.aggr(
                    action.Weighing & key,
                    last_weighing_date='DATE(MAX(weighing_time))')
                latest_water = subject.Subject.aggr(
                    action.WaterAdministration & key,
                    last_water_date='DATE(MAX(administration_time))')

                latest_water_weight = (latest_water * latest_weight).proj(
                    last_water_weight_date='GREATEST(last_water_date, \
                                                    last_weighing_date)')
        else:
            water_weight = None

        if not(behavior_summary or water_weight):
            continue
        elif behavior_summary and water_weight:
            last_behavior_date = latest_behavior.fetch1(
                'last_behavior_date'
            )
            last_water_weight_date = latest_water_weight.fetch1(
                'last_water_weight_date'
            )
            latest_date = max([last_behavior_date, last_water_weight_date])
        elif behavior_summary:
            latest_date = latest_behavior.fetch1(
                'last_behavior_date'
            )
        elif water_weight:
            latest_date = latest_water_weight.fetch1(
                'last_water_weight_date'
            )

        key['latest_date'] = latest_date
        behavior_plotting.LatestDate.insert1(key)


def process_cumulative_plots(backtrack_days=30):

    kwargs = dict(
        suppress_errors=True, display_progress=True)

    if mode != 'public':
        latest = subject.Subject.aggr(
            behavior_plotting.LatestDate,
            checking_ts='MAX(checking_ts)') * behavior_plotting.LatestDate & \
                [f'latest_date between curdate() - interval {backtrack_days} day and curdate()',
                (subject.Subject - subject.Death)] & \
                (subject.Subject & 'subject_nickname not like "%human%"').proj()
    else:
        latest = subject.Subject.aggr(
            behavior_plotting.LatestDate,
            checking_ts='MAX(checking_ts)') & \
                (subject.Subject & 'subject_nickname not like "%human%"').proj()

    subj_keys = (subject.Subject & behavior_plotting.CumulativeSummary & latest).fetch('KEY')

    # delete and repopulate subject by subject
    with dj.config(safemode=False):
        for subj_key in tqdm(subj_keys, position=0):
            (behavior_plotting.CumulativeSummary & subj_key & latest).delete()
            print('populating...')
            behavior_plotting.CumulativeSummary.populate(
                latest & subj_key, **kwargs)
            # --- update the latest date of the subject -----
            # get the latest date of the CumulativeSummary of the subject
            subj_with_latest_date = (subject.Subject & subj_key).aggr(
                behavior_plotting.CumulativeSummary, latest_date='max(latest_date)')
            if len(subj_with_latest_date):
                new_date = subj_with_latest_date.fetch1('latest_date')
                current_subj = behavior_plotting.SubjectLatestDate & subj_key
                if len(current_subj):
                    current_subj._update('latest_date', new_date)
                else:
                    behavior_plotting.SubjectLatestDate.insert1(
                        subj_with_latest_date.fetch1())

        behavior_plotting.CumulativeSummary.populate(**kwargs)


def process_daily_summary():

    with dj.config(safemode=False):
        print('Populating plotting.DailyLabSummary...')
        last_sessions = (reference.Lab.aggr(
            behavior_plotting.DailyLabSummary,
            last_session_time='max(last_session_time)')).fetch('KEY')
        (behavior_plotting.DailyLabSummary & last_sessions).delete()
        behavior_plotting.DailyLabSummary.populate(**kwargs)


def main(backtrack_days=30, excluded_tables=[]):

    if backtrack_days:
        date_cutoff = \
            (datetime.datetime.now().date() -
             datetime.timedelta(days=backtrack_days)).strftime('%Y-%m-%d')

    # ingest those dataset and file records where exists=False when json gets dumped
    # only check those sessions where required datasets are missing.
    # populate CompleteTrialSession first with existing file records
    behavior.CompleteTrialSession.populate(f'session_start_time > "{date_cutoff}"', **kwargs)
    sessions_missing = (acquisition.Session - behavior.CompleteTrialSession) & \
            f'session_start_time > "{(datetime.datetime.now().date() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")}"'

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

    print('Populating latest date...')
    compute_latest_date()

    print('Processing Cumulative plots...')
    process_cumulative_plots()

    if mode != 'public':
        print('Processing daily summary...')
        process_daily_summary()


if __name__ == '__main__':

    main(backtrack_days=30)
