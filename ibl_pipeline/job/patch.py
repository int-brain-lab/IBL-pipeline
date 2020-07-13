import datajoint as dj
from ibl_pipeline import acquisition, behavior, ephys, histology
from ibl_pipeline.analyses import behavior as behavior_analyses
from ibl_pipeline.analyses import ephys as ephys_analyses
from ibl_pipeline.plotting import behavior as behavior_plotting
from ibl_pipeline.plotting import ephys as ephys_plotting
from ibl_pipeline.group_shared import wheel
from ibl_pipeline.utils.dependent_tables import Graph


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
