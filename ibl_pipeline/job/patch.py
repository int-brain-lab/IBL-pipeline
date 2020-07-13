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


schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_patch')


TABLES = [
    ephys_plotting.Waveform,
    ephys_plotting.AutoCorrelogram,
    ephys_plotting.SpikeAmpTime,
    ephys_plotting.Psth,
    ephys_plotting.Raster,
    ephys_plotting.DepthPeth,
    ephys_plotting.DepthRaster,
    ephys_plotting.DepthRasterExampleTrial,
    ephys_analyses.NormedDepthPeth,
    ephys_analyses.DepthPeth,
    ephys.GoodCluster,
    ephys.AlignedTrialSpikes,
    histology.ClusterBrainRegion,
    ephys.DefaultCluster.Metrics,
    ephys.DefaultCluster,
    ephys.CompleteClusterSession,
    behavior_plotting.SessionPsychCurve,
    behavior_plotting.SessionReactionTimeTrialNumber,
    behavior_plotting.SessionReactionTimeContrast,
    behavior_analyses.SessionTrainingStatus,
    behavior_analyses.ReactionTimeContrastBlock,
    behavior_analyses.ReactionTime,
    behavior_analyses.PsychResultsBlock,
    behavior_analyses.PsychResults,
    wheel.MovementTimes,
    behavior.AmbientSensorData,
    behavior.TrialSet.ExcludedTrial,
    behavior.TrialSet.Trial,
    behavior.TrialSet,
    behavior.CompleteTrialSession,
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
    full_table_name : varchar(128)  # full table name in MySQL
    ---
    table_class     : varchar(128)
    table_order     : smallint      # order to repopulate, the bigger, the earlier to delete and later to repopulate
    table_label     : enum('virtual', 'auto', 'manual')  # virtual for virtual module, auto for computed or imported table, manual for manual table
    """


table_kwargs = dict(order_by='table_order desc', as_dict=True)

TABLES_PACKAGE = (Table & 'table_label!="virtual"').fetch(**table_kwargs)
TABLES_VIRTUAL = (Table & 'table_lable="virtual"').fetch(**table_kwargs)

populate_kwargs = dict(
    suppress_errors=True, display_progress=True,
    return_exception_objects=True)


@schema
class Run(dj.Manual):
    definition = """
    # the table that drives deletion and repopulate
    -> Session
    """

    def _delete_table(self, t, key, virtual=True):

        if virtual:
            Graph.get_virtual_module(t['full_table_name'])

        table_class = eval(t['table_class'])
        key_table = dict(**key, full_table_name=t['full_table_name'])

        if len(table_class & key):
            original = True
        else:
            original = False

        RunStatus.TableStatus.insert1(
            dict(**key_table, original=original))

        print('Deleting table {} ...'.format(t['full_table_name']))
        (table_class & key).delete_quick()
        dj.Table._update(
            RunStatus.TableStatus & key_table,
            'status', 'Deleted')
        dj.Table._update(
            RunStatus.TableStatus & key_table,
            'delete_time', datetime.datetime.now())

    def make(self, key):

        # start this job
        if not len(RunStatus & key):
            RunStatus.insert1(
                **key,
                run_start_time=datetime.datetime.now())
        else:
            dj.Table._update(
                RunStatus & key,
                'run_start_time', datetime.datetime.now())

        # delete tables
        for t in TABLES_VIRTUAL:
            self._delete_table(t, key)

        for t in TABLES_PACKAGE:
            self._delete_table(t, key, virtual=False)

        # repopulate tables
        for t in TABLES_PACKAGE[::-1]:
            if t['table_label'] == 'auto':
                table_class = eval(t['table_class'])
                table_key = dict(**key, full_table_name=t['full_table_name'])
                status = RunStatus.TableStatus & table_key
                print('Repopulating {}'.format(t['table_class']))
                dj.Table._update(status, 'status', 'Populating')
                dj.Table._update(
                    status, 'populate_start_time', datetime.datetime.now())

                if not len((table_class.key_source - table_class.proj()) & key):
                    dj.Table._update(status, 'status', 'Error')
                    dj.Table._update(
                        status, 'populate_done_time', datetime.datetime.now())
                    dj.Table._update(
                        status, 'error_message', 'No tuples to populate')
                else:
                    errors = table_class.populate(**populate_kwargs)
                    dj.Table._update(
                        status, 'populate_end_time', datetime.datetime.now())
                    if len(errors):
                        dj.Table._update(status, 'status', 'Error')
                        dj.Table._update(
                            status, 'error_message', str(errors))
                    else:
                        dj.Table._update(status, 'status', 'Success')
                        dj.Table._update(
                            status, 'error_message', '')

        # end this job
        dj.Table._update(
            RunStatus & key,
            'run_end_time', datetime.datetime.now())

    def populate(self, *restrictions, display_progress=False):

        self.key_source = (Session - self) & dj.AndList(restrictions)
        keys = self.key_source.fetch('KEY')

        for key in (tqdm(keys) if display_progress else keys):
            self.make(key)


@schema
class RunStatus(dj.Manual):
    definition = """
    -> Session
    ---
    run_start_time          : datetime
    run_end_time=null       : datetime
    """

    class TableStatus(dj.Part):
        definition = """
        -> master
        -> Table
        ---
        original                : bool
        status=null             : enum('Deleted', 'Repopulating', 'Success', 'Error')
        delete_time=null        : datetime
        populate_start_time=null: datetime
        populate_done_time=null : datetime
        error_message=''        : varchar(10000)
        """


if __name__ == '__main__':

    # insert regular tables in order
    Table.insert([
        dict(
            full_table_name=table.full_table_name,
            table_class=table.__module__ + '.' + table.__name__,
            table_order=itable,
            table_label='auto' if issubclass(table, (dj.Imported, dj.Computed))
                        else 'manual')
        for itable, table in enumerate(TABLES[::-1])])

    # insert virtual modules tables in order
    virtuals = Graph(behavior.TrialSet()).get_table_list(virtual_only=True) + \
        Graph(ephys.DefaultCluster()).get_table_list(virtual_only=True)
    virtual_classes = [eval(v) for v in virtuals]

    Table.insert([
        dict(
            full_table_name=table.full_table_name,
            table_class=table.__module__ + '.' + table.__name__,
            table_order=itable,
            table_label='virtual')
        for itable, table in enumerate(virtual_classes[::-1])])
