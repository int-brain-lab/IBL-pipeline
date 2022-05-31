"""
This module contains functions to help tear down the testing environment
"""

import datajoint as dj

# alyxraw schemas
alyxraw = dj.create_virtual_module("alyxraw", "test_ibl_alyxraw")
alyxraw_update = dj.create_virtual_module("alyxraw", "test_update_ibl_alyxraw")

# shadow schemas
reference_shadow = dj.create_virtual_module(
    "reference_shadow", "test_ibl_ingest_reference"
)
subject_shadow = dj.create_virtual_module("subject_shadow", "test_ibl_ingest_subject")
action_shadow = dj.create_virtual_module("action_shadow", "test_ibl_ingest_action")
acquisition_shadow = dj.create_virtual_module(
    "acquisition_shadow", "test_ibl_ingest_acquisition"
)
data_shadow = dj.create_virtual_module("data_shadow", "test_ibl_ingest_data")
ephys_shadow = dj.create_virtual_module("ephys_shadow", "test_ibl_ingest_ephys")
histology_shadow = dj.create_virtual_module(
    "histology_shadow", "test_ibl_ingest_histology"
)

# real schemas
reference = dj.create_virtual_module("reference", "test_ibl_reference")
subject = dj.create_virtual_module("subject", "test_ibl_subject")
action = dj.create_virtual_module("action", "test_ibl_action")
acquisition = dj.create_virtual_module("acquisition", "test_ibl_acquisition")
data = dj.create_virtual_module("data", "test_ibl_data")
behavior = dj.create_virtual_module("behavior", "test_ibl_behavior")
ephys = dj.create_virtual_module("ephys", "test_ibl_ephys")
histology = dj.create_virtual_module("histology", "test_ibl_histology")
qc = dj.create_virtual_module("qc", "test_ibl_qc")
wheel = dj.create_virtual_module("wheel", "test_group_shared_wheel")

behavior_analyses = dj.create_virtual_module(
    "behavior_analyses", "test_ibl_analyses_behavior"
)
ephys_analyses = dj.create_virtual_module("ephys_analyses", "test_ibl_analyses_ephys")

behavior_plotting = dj.create_virtual_module(
    "behavior_plotting", "test_ibl_plotting_behavior"
)
ephys_plotting = dj.create_virtual_module("ephys_plotting", "test_ibl_plotting_ephys")
histology_plotting = dj.create_virtual_module(
    "histology_plotting", "test_ibl_plotting_histology"
)


ALYX_RAW_TABLES = [alyxraw.AlyxRaw, alyxraw.AlyxRaw.Field]


ALYX_RAW_UPDATE_TABLES = [alyxraw_update.AlyxRaw, alyxraw_update.AlyxRaw.Field]


ALYX_SHADOW_TABLES = [
    reference_shadow.Lab,
    reference_shadow.LabMember,
    reference_shadow.LabMembership,
    reference_shadow.LabLocation,
    reference_shadow.Project,
    reference_shadow.CoordinateSystem,
    subject_shadow.Species,
    subject_shadow.Source,
    subject_shadow.Strain,
    subject_shadow.Sequence,
    subject_shadow.Allele,
    subject_shadow.Line,
    subject_shadow.Subject,
    subject_shadow.BreedingPair,
    subject_shadow.Litter,
    subject_shadow.LitterSubject,
    subject_shadow.SubjectProject,
    subject_shadow.SubjectUser,
    subject_shadow.SubjectLab,
    subject_shadow.Caging,
    subject_shadow.UserHistory,
    subject_shadow.Weaning,
    subject_shadow.Death,
    subject_shadow.GenotypeTest,
    subject_shadow.Zygosity,
    subject_shadow.SubjectCullMethod,
    action_shadow.ProcedureType,
    action_shadow.Weighing,
    action_shadow.WaterType,
    action_shadow.WaterAdministration,
    action_shadow.WaterRestriction,
    action_shadow.Surgery,
    action_shadow.CullMethod,
    action_shadow.CullReason,
    action_shadow.Cull,
    action_shadow.OtherAction,
    acquisition_shadow.Session,
    data_shadow.DataFormat,
    data_shadow.DataRepositoryType,
    data_shadow.DataRepository,
    data_shadow.DataSetType,
    data_shadow.DataSet,
    data_shadow.FileRecord,
]


ALYX_SHADOW_MEMBERSHIP_TABLES = [
    reference_shadow.ProjectLabMember,
    subject_shadow.AlleleSequence,
    subject_shadow.LineAllele,
    action_shadow.SurgeryProcedure,
    acquisition_shadow.ChildSession,
    acquisition_shadow.SessionUser,
    acquisition_shadow.SessionProcedure,
    acquisition_shadow.SessionProject,
    data_shadow.ProjectRepository,
]


ALYX_TABLES = [
    reference.Lab,
    reference.LabLocation,
    reference.LabMember,
    reference.LabMembership,
    reference.Project,
    reference.ProjectLabMember,
    reference.CoordinateSystem,
    subject.Species,
    subject.Strain,
    subject.Source,
    subject.Sequence,
    subject.Allele,
    subject.AlleleSequence,
    subject.Line,
    subject.LineAllele,
    subject.Subject,
    subject.SubjectUser,
    subject.SubjectProject,
    subject.SubjectLab,
    subject.BreedingPair,
    subject.Litter,
    subject.LitterSubject,
    subject.Weaning,
    subject.Death,
    subject.SubjectCullMethod,
    subject.Caging,
    subject.UserHistory,
    subject.GenotypeTest,
    subject.Zygosity,
    subject.Implant,
    subject.Food,
    subject.CageType,
    subject.Enrichment,
    subject.Housing,
    subject.SubjectHousing,
    action.ProcedureType,
    action.Weighing,
    action.WaterType,
    action.WaterAdministration,
    action.WaterRestriction,
    action.WaterRestrictionUser,
    action.WaterRestrictionProcedure,
    action.Surgery,
    action.SurgeryUser,
    action.SurgeryProcedure,
    action.OtherAction,
    action.OtherActionUser,
    action.OtherActionProcedure,
    action.CullMethod,
    action.CullReason,
    action.Cull,
    acquisition.Session,
    acquisition.ChildSession,
    acquisition.SessionUser,
    acquisition.SessionProcedure,
    acquisition.SessionProject,
    acquisition.WaterAdministrationSession,
    data.DataFormat,
    data.DataRepositoryType,
    data.DataRepository,
    data.ProjectRepository,
    data.DataSetType,
    data.DataSet,
    data.FileRecord,
]


BEHAVIOR_TABLES = [
    behavior.CompleteWheelSession,
    behavior.CompleteTrialSession,
    behavior.TrialSet,
    behavior.TrialSet.Trial,
    behavior.TrialSet.ExcludedTrial,
    behavior.AmbientSensorData,
    behavior.Settings,
    behavior.SessionDelay,
    behavior_analyses.PsychResults,
    behavior_analyses.PsychResultsBlock,
    behavior_analyses.ReactionTime,
    behavior_analyses.ReactionTimeContrastBlock,
    behavior_analyses.SessionTrainingStatus,
    behavior_analyses.BehavioralSummaryByDate,
    behavior_analyses.BehavioralSummaryByDate.PsychResults,
    behavior_analyses.BehavioralSummaryByDate.ReactionTimeContrast,
    behavior_analyses.BehavioralSummaryByDate.ReactionTimeByDate,
    behavior_plotting.SessionPsychCurve,
    behavior_plotting.SessionReactionTimeContrast,
    behavior_plotting.SessionReactionTimeTrialNumber,
    behavior_plotting.DatePsychCurve,
    behavior_plotting.DateReactionTimeContrast,
    behavior_plotting.DateReactionTimeTrialNumber,
    behavior_plotting.CumulativeSummary,
    behavior_plotting.CumulativeSummary.WaterWeight,
    behavior_plotting.CumulativeSummary.TrialCountsSessionDuration,
    behavior_plotting.CumulativeSummary.PerformanceReactionTime,
    behavior_plotting.CumulativeSummary.ContrastHeatmap,
    behavior_plotting.CumulativeSummary.FitPars,
    behavior_plotting.DailyLabSummary,
    behavior_plotting.DailyLabSummary.SubjectSummary,
]

WHEEL_TABLES = [behavior.CompleteWheelSession, wheel.WheelMoveSet, wheel.MovementTimes]

EPHYS_SHADOW_TABLES = [ephys_shadow.ProbeModel, ephys_shadow.ProbeInsertion]


EPHYS_TABLES = [
    ephys.CompleteClusterSession,
    ephys.DefaultCluster,
    ephys.AlignedTrialSpikes,
    ephys.GoodCluster,
    ephys.ChannelGroup,
    ephys_analyses.DepthPeth,
    ephys_analyses.NormedDepthPeth,
    ephys_plotting.DepthRaster,
    ephys_plotting.DepthPeth,
    ephys_plotting.Raster,
    ephys_plotting.Psth,
    ephys_plotting.SpikeAmpTime,
    ephys_plotting.AutoCorrelogram,
    ephys_plotting.Waveform,
    ephys_plotting.DepthRasterExampleTrial,
]


HISTOLOGY_SHADOW_TABLES = [
    histology_shadow.Provenance,
    histology_shadow.ProbeTrajectoryTemp,
    histology_shadow.ChannelBrainLocationTemp,
]


HISTOLOGY_TABLES = [
    histology.ClusterBrainRegionTemp,
    histology.ChannelBrainLocationTemp,
    histology.ProbeBrainRegionTemp,
    histology.ProbeTrajectoryTemp,
    histology.ProbeTrajectory,
    histology.ChannelBrainLocation,
    histology.ClusterBrainRegion,
    histology_plotting.SubjectSpinningBrain,
    histology_plotting.ProbeTrajectoryCoronal,
]

QC_TABLES = [
    qc.SessionQC,
    qc.SessionExtendedQC,
    qc.SessionExtendedQC.Field,
    qc.ProbeInsertionQC,
    qc.ProbeInsertionExtendedQC,
    qc.ProbeInsertionExtendedQC.Field,
]


def delete_tables(tables):

    for t in tables[::-1]:
        print(f"Deleting table {t.__name__}...")
        t.delete_quick()


def delete_real_all():
    """Delete real tables in graphical order"""
    tables = (
        ALYX_TABLES
        + BEHAVIOR_TABLES
        + WHEEL_TABLES
        + EPHYS_TABLES
        + HISTOLOGY_TABLES
        + QC_TABLES
    )
    delete_tables(tables)


def delete_shadow():
    tables = (
        ALYX_SHADOW_TABLES
        + ALYX_SHADOW_MEMBERSHIP_TABLES
        + EPHYS_SHADOW_TABLES
        + HISTOLOGY_SHADOW_TABLES
    )
    delete_tables(tables)


def delete_shadow_membership():
    delete_tables(ALYX_SHADOW_MEMBERSHIP_TABLES)


def delete_alyxraw():
    delete_tables(ALYX_RAW_TABLES + ALYX_SHADOW_TABLES)


def delete_alyxraw_update():
    delete_tables(ALYX_RAW_UPDATE_TABLES)


def delete_ephys_all():
    delete_tables(EPHYS_SHADOW_TABLES + EPHYS_TABLES + HISTOLOGY_TABLES)


def delete_ephys_real():
    delete_tables(EPHYS_TABLES + HISTOLOGY_TABLES)


def delete_histology_all():
    delete_tables(HISTOLOGY_SHADOW_TABLES + HISTOLOGY_TABLES)


def delete_histology_real():
    delete_tables(HISTOLOGY_TABLES)


def delete_qc():
    delete_tables(QC_TABLES)
