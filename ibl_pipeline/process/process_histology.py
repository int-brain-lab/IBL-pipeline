from ibl_pipeline.process import ingest_alyx_raw
from ibl_pipeline.ingest.common import *
from ibl_pipeline.ingest import populate_batch, InsertBuffer
from ibl_pipeline.common import *
from ibl_pipeline.process import update_utils
from tqdm import tqdm


ALYX_HISTOLOGY_MODELS = [
    'misc.lab', 'misc.labmember', 'misc.labmembership', 'misc.lablocation',
    'subjects.project', 'subjects.species', 'subjects.strain', 'subjects.source',
    'subjects.allele', 'subjects.sequence', 'subjects.subject',
    'actions.proceduretype', 'actions.wateradministration', 'actions.session',
    'experiments.probeinsertion', 'experiments.coordinatesystem',
    'experiments.trajectoryestimate', 'experiments.channel']

HISTOLOGY_SHADOW_TABLES = [
    reference_ingest.Lab,
    reference_ingest.LabMember,
    reference_ingest.LabMembership,
    reference_ingest.LabLocation,
    reference_ingest.Project,
    reference_ingest.CoordinateSystem,
    subject_ingest.Species,
    subject_ingest.Source,
    subject_ingest.Strain,
    subject_ingest.Sequence,
    subject_ingest.Allele,
    subject_ingest.Line,
    subject_ingest.Subject,
    subject_ingest.SubjectProject,
    subject_ingest.SubjectUser,
    subject_ingest.SubjectLab,
    subject_ingest.UserHistory,
    action_ingest.ProcedureType,
    action_ingest.WaterAdministration,
    acquisition_ingest.Session,
    ephys_ingest.ProbeInsertion,
    histology_ingest.ProbeTrajectoryTemp,
    histology_ingest.ChannelBrainLocationTemp
]


def process_alyxraw_histology(
        filename='/data/alyxfull.json', models=ALYX_HISTOLOGY_MODELS):

    '''
    Ingest all histology entries in a particular alyx dump, regardless of the current status.
    '''
    ingest_alyx_raw.insert_to_alyxraw(
        ingest_alyx_raw.get_alyx_entries(
            filename=filename,
            models=models
        )
    )


def process_shadow_tables():

    kwargs = dict(
        display_progress=True,
        suppress_errors=True)

    for t in HISTOLOGY_SHADOW_TABLES:

        print(f'Populating {t.__name__}...')
        if t.__name__ == 'ChannelBrainLocationTemp':
            populate_batch(t)
        else:
            t.populate(**kwargs)


def delete_histology_alyx_shadow():

    CHANNEL_TABLES = [
        histology_ingest.ChannelBrainLocationTemp,
        histology_ingest.ChannelBrainLocation,
        alyxraw.AlyxRaw.Field,
        alyxraw.AlyxRaw
    ]

    channel_loc_keys = update_utils.get_deleted_keys('experiments.channel')
    for t in CHANNEL_TABLES:
        print(f'Deleting from table {t.__name__}')
        uuid_name = t.heading.primary_key[0]
        keys = [{uuid_name: k['uuid']} for k in tqdm(channel_loc_keys)]
        table = InsertBuffer(t)

        for k in tqdm(keys, position=0):
            table.delete1(k)
            if table.flush_delete(chunksz=1000, quick=True):
                print(f'Deleted 1000 entries from {t.__name__}')

        table.flush_delete(quick=True)

    traj_keys = update_utils.get_deleted_keys('experiments.trajectoryestimate') + \
                update_utils.get_updated_keys('experiments.trajectoryestimate')

    TRAJ_TABLES = [
        histology_ingest.ProbeTrajectoryTemp,
        histology_ingest.ProbeTrajectory,
        alyxraw.AlyxRaw.Field,
        alyxraw.AlyxRaw
    ]

    for t in TRAJ_TABLES:
        uuid_name = t.heading.primary_key[0]
        keys = [{uuid_name: k['uuid']} for k in traj_keys]
        table = InsertBuffer(t)
        for k in tqdm(keys, position=0):
            table.delete1(k)
            if table.flush_delete(chunksz=1000, quick=True):
                print(f'Deleted 1000 entries from {t.__name__}')
        table.flush_delete(quick=True)

# def process_real_tables():

#     for shadow_table in HISTOLOGY_SHADOW_TABLES:
#         real_table = getattr()
#         print(f'Populating {t.__name__}')
#         t.populate(**kwargs)


if __name__ == '__main__':

    process_alyxraw_histology(filename='/data/alyxfull_20201010_1200.json')
    process_shadow_tables()
    # delete_histology_alyx_shadow()
