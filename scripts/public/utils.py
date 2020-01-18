import datajoint as dj
from uuid import UUID
from ibl_pipeline.ingest import alyxraw
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

        subjects = [dict(fvalue=str(uuid)) for uuid in subject_uuids]

        if 'actions.' in model_name and model_name != 'actions.session':
            uuids = (alyxraw.AlyxRaw & {'model': model_name} &
                     (alyxraw.AlyxRaw.Field & dict(fname='subject') &
                      subjects)).fetch('uuid')

        elif 'data.' in model_name or model_name == 'actions.session':

            # loop over subjects and get sessions between the session range

            sessions = []
            for subj_uuid, subj in zip(subject_uuids, subjects):

                session_start, session_end = (
                    public.PublicSubject &
                    (public.PublicSubjectUuid &
                     {'subject_uuid': subj_uuid})).fetch1(
                        'session_start_date', 'session_end_date')
                session_start = session_start.strftime('%Y-%m-%d')
                session_end = session_end.strftime('%Y-%m-%d')
                session_uuids = (
                    alyxraw.AlyxRaw & {'model': 'actions.session'} &
                    (alyxraw.AlyxRaw.Field & 'fname="subject"' & subj) &
                    (alyxraw.AlyxRaw.Field & 'fname="start_time"' &
                     'fvalue between "{}" and "{}"'.format(
                         session_start, session_end))
                ).fetch('uuid')

                if model_name == 'actions.session':
                    sessions += [dict(uuid=uuid) for uuid in session_uuids]
                else:
                    sessions += [dict(fvalue=str(uuid)) for uuid in session_uuids]

            if model_name == 'actions.session':
                uuids = (
                    alyxraw.AlyxRaw &
                    {'model': model_name} &
                    sessions
                ).fetch('uuid')

            elif model_name != 'data.filerecord':
                uuids = (
                    alyxraw.AlyxRaw & {'model': model_name} &
                    (alyxraw.AlyxRaw.Field & 'fname="session"' & sessions)
                ).fetch('uuid')
            else:
                dataset_uuids = (
                    alyxraw.AlyxRaw & {'model': 'data.dataset'} &
                    (alyxraw.AlyxRaw.Field & 'fname="session"' & sessions)
                ).fetch('uuid')
                datasets = [dict(fvalue=str(uuid))
                            for uuid in dataset_uuids]
                uuids = (
                    alyxraw.AlyxRaw & {'model': model_name} &
                    (alyxraw.AlyxRaw.Field & 'fname="dataset"' & datasets)
                ).fetch('uuid')

        return [{uuid_name: uuid} for uuid in uuids]
