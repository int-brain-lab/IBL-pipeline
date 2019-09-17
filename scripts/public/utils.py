import datajoint as dj
from uuid import UUID
from ibl_pipeline.ingest import alyxraw.AlyxRaw
from ibl_pipeline import public


def get_uuids(model_name, uuid_name, subject_uuids):
    """
    This function get the uuids of entries in a particular alyx table.

    Parameters:
    model_name (str): alyx table name, for example 'actions.weighing'
    subject_uuids (list of UUIDs): list of uuids for subjects to be included in the public database

    Returns:
    list of dictionaries as the restrictor for that table to be populated
    """

    if model_name == 'subjects.subject':
        return [dict(subject_uuid=subject_uuid)
                for subject_uuid in subject_uuids]
    else:
        session_start_date, session_end_date = public.

        subjects = [dict(fname='subject', fvalue=str(uuid))
                    for uuid in subject_uuids]

        if 'actions.' in model_name:
            uuids = (alyxraw.AlyxRaw & {'model_name': model_name} &
                     (alyxraw.AlyxRaw.Field & subjects)).fetch('uuid')

        elif 'data.' in model_name:
            session_uuids = (alyxraw.AlyxRaw & {'model_name': 'actions.session'} &
                             (alyxraw.AlyxRaw.Field & subjects)).fetch('uuid')
            sessions = [dict(fname='session', fvalue=str(uuid))
                        for uuid in session_uuids]

            if model_name != 'data.filerecord':
                uuids = (alyxraw.AlyxRaw & {'model_name': model_name} &
                         (alyxraw.AlyxRaw.Field & subjects)).fetch('uuid')
            else:
                dataset_uuids = (alyxraw.AlyxRaw & {'model_name': model_name} &
                                 (alyxraw.AlyxRaw.Field & subjects)).fetch('uuid')
                datasets = [dict(fname='dataset', fvalue=str(uuid))
                            for uuid in dataset_uuids]
                uuids = (alyxraw.AlyxRaw & {'model_name': model_name} &
                         (alyxraw.AlyxRaw.Field & datasets)).fetch('uuid')

        return [{uuid_name: uuid} for uuid in uuids]
