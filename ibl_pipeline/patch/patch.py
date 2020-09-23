import datajoint as dj
from ibl_pipeline import acquisition, behavior, ephys, histology
from ibl_pipeline.analyses import behavior as behavior_analyses
from ibl_pipeline.analyses import ephys as ephys_analyses
from ibl_pipeline.plotting import behavior as behavior_plotting
from ibl_pipeline.plotting import ephys as ephys_plotting
from ibl_pipeline.group_shared import wheel
from ibl_pipeline.utils.dependent_tables import Graph
import ibl_pipeline
import re
from tqdm import tqdm
import datetime


schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_patch')


SESSION_TABLES = [
    'ephys_plotting.Waveform',
    'ephys_plotting.AutoCorrelogram',
    'ephys_plotting.SpikeAmpTime',
    'ephys_plotting.Psth',
    'ephys_plotting.Raster',
    'ephys_plotting.DepthPeth',
    'ephys_plotting.DepthRaster',
    'ephys_plotting.DepthRasterExampleTrial',
    'ephys_analyses.NormedDepthPeth',
    'ephys_analyses.DepthPeth',
    'ephys.GoodCluster',
    'ephys.AlignedTrialSpikes',
    'histology.ClusterBrainRegion',
    'ephys.ChannelGroup',
    'ephys.DefaultCluster.Ks2Label',
    'ephys.DefaultCluster.Metrics',
    'ephys.DefaultCluster.Metric',
    'ephys.DefaultCluster',
    'ephys.CompleteClusterSession',
    'behavior_plotting.SessionPsychCurve',
    'behavior_plotting.SessionReactionTimeTrialNumber',
    'behavior_plotting.SessionReactionTimeContrast',
    'behavior_analyses.SessionTrainingStatus',
    'behavior_analyses.ReactionTimeContrastBlock',
    'behavior_analyses.ReactionTime',
    'behavior_analyses.PsychResultsBlock',
    'behavior_analyses.PsychResults',
    'wheel.MovementTimes',
    'wheel.WheelMoveSet.Move',
    'wheel.WheelMoveSet',
    'behavior.CompleteWheelSession',
    'behavior.AmbientSensorData',
    'behavior.TrialSet.ExcludedTrial',
    'behavior.TrialSet.Trial',
    'behavior.TrialSet',
    'behavior.CompleteTrialSession',
]

DATE_TABLES = [
    'behavior_plotting.DatePsychCurve',
    'behavior_plotting.DateReactionTimeContrast',
    'behavior_plotting.DateReactionTimeTrialNumber',
    'behavior_analyses.BehavioralSummaryByDate.ReactionTimeByDate',
    'behavior_analyses.BehavioralSummaryByDate.ReactionTimeContrast',
    'behavior_analyses.BehavioralSummaryByDate.PsychResults',
    'behavior_analyses.BehavioralSummaryByDate',
]


@schema
class Session(dj.Manual):
    definition = """
    job_date            : date
    subject_uuid        : uuid
    session_start_time  : datetime
    ---
    subject_nickname    : varchar(64)
    session_uuid        : uuid
    """


@schema
class Table(dj.Lookup):
    definition = """
    full_table_name         : varchar(128)  # full table name in MySQL
    ---
    table_class             : varchar(128)
    table_order             : smallint      # order to repopulate, the bigger, the earlier to delete and later to repopulate
    table_order_category    : enum('virtual', 'session', 'date') # the table order is within one category
    table_label             : enum('virtual', 'auto', 'part')  # virtual for virtual module, auto for computed or imported table, manual for manual table
    table_parent=''         : varchar(128)  # only applicable to part table
    """

    @classmethod
    def _insert_package_tables(self, table_list, table_type):
        for itable, table in enumerate(table_list[::-1]):
            table_obj = eval(table)
            table_key = dict(full_table_name=table_obj.full_table_name)

            if self & table_key:
                dj.Table._update(self & table_key, 'table_order', itable)
            else:
                self.insert1(dict(
                    **table_key,
                    table_class=table,
                    table_order=itable,
                    table_order_category=table_type,
                    table_label='auto' if issubclass(table_obj,
                                                     (dj.Imported, dj.Computed))
                                else 'part',
                    table_parent=eval(re.match('(^.*)\..*$', table).group(1)).full_table_name
                                 if issubclass(table_obj, dj.Part) else None))

    def _insert_virtual_tables(self):
        # insert virtual modules tables in order
        virtuals = Graph(behavior.TrialSet()).get_table_list(virtual_only=True) + \
            Graph(ephys.DefaultCluster()).get_table_list(virtual_only=True) + \
            Graph(behavior_analyses.BehavioralSummaryByDate()).get_table_list(virtual_only=True)

        for itable, vtable in enumerate(virtuals[::-1]):
            table_key = dict(full_table_name=vtable['full_table_name'])

            if Table & table_key:
                dj.Table._update(self & table_key, 'table_order', itable)
            else:
                self.insert1(
                    dict(
                        full_table_name=vtable['full_table_name'],
                        table_class=vtable['table'],
                        table_order_category='virtual',
                        table_order=itable,
                        table_label='virtual'),
                    skip_duplicates=True)

    def insert_tables(self, table_type='All'):

        if table_type == 'session':
            self._insert_package_tables(SESSION_TABLES, table_type)
        elif table_type == 'date':
            self._insert_package_tables(DATE_TABLES, table_type)
        elif table_type == 'virtual':
            self._insert_virtual_tables()
        elif table_type == 'All':
            self._insert_package_tables(SESSION_TABLES, 'session')
            self._insert_package_tables(DATE_TABLES, 'date')
            self._insert_virtual_tables()
        else:
            ValueError('Invalid table_type. It has to be one of the following: session, date, virtual')


table_kwargs = dict(order_by='table_order desc', as_dict=True)
populate_kwargs = dict(
    suppress_errors=True, display_progress=True,
    return_exception_objects=True)


@schema
class Run(dj.Manual):
    definition = """
    # the table that drives deletion and repopulate
    -> Session
    ---
    job_status='' : enum('Success', 'Partial Success', 'Error', '')
    """

    def _delete_table(self, t, key, table_type='session'):

        key_del = key.copy()
        if table_type == 'virtual':
            Graph.get_virtual_module(t['full_table_name'])

        elif table_type == 'date':
            key_del['session_date'] = key_del.pop('session_start_time').date()

        table_class = eval(t['table_class'])
        key_table = dict(**key, full_table_name=t['full_table_name'])

        if table_class & key:
            original = True
        else:
            original = False

        RunStatus.TableStatus.insert1(
            dict(**key_table, original=original), skip_duplicates=True)

        print('Deleting table {} ...'.format(t['full_table_name']))
        if t['full_table_name'] == '`ibl_ephys`.`__aligned_trial_spikes`':
            for cluster in tqdm((ephys.DefaultCluster & key).fetch('KEY'),
                                position=0):
                (table_class & cluster).delete_quick()
        else:
            (table_class & key_del).delete_quick()
        dj.Table._update(
            RunStatus.TableStatus & key_table,
            'status', 'Deleted')
        dj.Table._update(
            RunStatus.TableStatus & key_table,
            'delete_time', datetime.datetime.now())

    def make(self, key):

        tables_session = (Table & 'table_order_category="session"').fetch(**table_kwargs)
        tables_date = (Table & 'table_order_category="date"').fetch(**table_kwargs)
        tables_virtual = (Table & 'table_order_category="virtual"').fetch(**table_kwargs)

        # start this job
        if not RunStatus & key:
            RunStatus.insert1(
                dict(**key, run_start_time=datetime.datetime.now()))
        else:
            dj.Table._update(
                RunStatus & key,
                'run_restart_time', datetime.datetime.now())

        # delete tables
        for t in tables_virtual:
            self._delete_table(t, key, table_type='virtual')

        for t in tables_session + tables_date:
            table_key = dict(**key, full_table_name=t['full_table_name'])
            if (RunStatus.TableStatus & table_key &
                    'status in ("Success", "Partial Success")'):
                continue

            self._delete_table(t, key, table_type=t['table_order_category'])

        # repopulate tables
        for t in (tables_session[::-1] + tables_date[::-1]):
            key_pop = key.copy()
            if t['table_order_category'] == 'date':
                key_pop['session_date'] = key_pop.pop('session_start_time').date()
            if t['table_label'] == 'auto':
                table_class = eval(t['table_class'])
                table_key = dict(**key, full_table_name=t['full_table_name'])
                status = RunStatus.TableStatus & table_key
                print('Repopulating {}'.format(t['table_class']))
                dj.Table._update(status, 'status', 'Repopulating')
                dj.Table._update(
                    status, 'populate_start_time', datetime.datetime.now())

                if (not (table_class.key_source - table_class.proj()) & key_pop) \
                        and (not RunStatus.TableStatus & table_key & 'status="Success"'):
                    dj.Table._update(status, 'status', 'Error')
                    dj.Table._update(
                        status, 'populate_done_time', datetime.datetime.now())
                    dj.Table._update(
                        status, 'error_message', 'No tuples to populate')
                else:
                    errors = table_class.populate(key_pop, **populate_kwargs)
                    dj.Table._update(
                        status, 'populate_done_time', datetime.datetime.now())
                    if errors:
                        if table_class & key_pop:
                            dj.Table._update(status, 'status', 'Partial Success')
                        else:
                            dj.Table._update(status, 'status', 'Error')

                        if len(errors) > 10:
                            errors = errors[:10]
                        dj.Table._update(
                            status, 'error_message', str(errors))
                    else:
                        dj.Table._update(status, 'status', 'Success')
                        dj.Table._update(
                            status, 'error_message', '')
                        # mark its part table to Success
                        for part_table in (Table &
                                           dict(table_parent=t['full_table_name'])).fetch('KEY'):
                            dj.Table._update(
                                RunStatus.TableStatus & key & part_table,
                                'status', 'Success')
                            dj.Table._update(
                                RunStatus.TableStatus & key & part_table,
                                'error_message', '')

        # end this job
        dj.Table._update(
            RunStatus & key,
            'run_end_time', datetime.datetime.now())

        if RunStatus.TableStatus & key & [tables_session, tables_date] & 'status in ("Success")':
            job_status = 'Partial Success'
            if not RunStatus.TableStatus & key & [tables_session, tables_date] & \
                    'status in ("Error", "Partial Success")':
                job_status = 'Success'
        else:
            job_status = 'Error'

        if self & key:
            dj.Table._update(self & key, 'job_status', job_status)
        else:
            self.insert1(dict(**key, job_status=job_status))

    def populate(self, *restrictions, level='New', display_progress=False):

        # populate new jobs only
        if level == 'New':
            cond = {}
        # populate new jobs and error jobs only
        elif level == 'Error':
            cond = 'job_status in ("Success", "Partial Success")'
        # populate new jobs, partial success jobs and error jobs
        elif level == 'Partial':
            cond = 'job_status in ("Success")'
        elif level == 'All':
            cond = []

        self.key_source = (Session - (self & cond)) & dj.AndList(restrictions)
        keys = self.key_source.fetch('KEY')

        for key in (tqdm(keys, position=0) if display_progress else keys):
            self.make(key)


@schema
class RunStatus(dj.Manual):
    definition = """
    -> Session
    ---
    run_start_time          : datetime
    run_restart_time=null   : datetime      # latest starting time to run this job
    run_end_time=null       : datetime
    """

    class TableStatus(dj.Part):
        definition = """
        -> master
        -> Table
        ---
        original                : bool
        status=null             : enum('Deleted', 'Repopulating', 'Partial Success', 'Success', 'Error')
        delete_time=null        : datetime
        populate_start_time=null: datetime
        populate_done_time=null : datetime
        error_message=''        : varchar(10000)
        """


if __name__ == '__main__':

    session = acquisition.Session & {'session_uuid': 'f8d5c8b0-b931-4151-b86c-c471e2e80e5d'}
    entry = (acquisition.Session*subject.Subject & session).fetch(
        'subject_uuid', 'session_start_time',
        'session_uuid', 'subject_nickname', as_dict=True)
    Session.insert1(
        dict(**entry[0], job_date=datetime.datetime.now().date()),
        skip_duplicates=True)

    Table.insert_tables('All')

    Run.populate(display_progress=True)

    # check results at location https://djcompute.internationalbrainlab.org/session/f8d5c8b0-b931-4151-b86c-c471e2e80e5d
