import datetime
from uuid import UUID

import datajoint as dj
import numpy as np
from oneibl.one import ONE

from ibl_pipeline import acquisition, behavior, data, subject
from ibl_pipeline.ingest import acquisition as acquisition_ingest
from ibl_pipeline.ingest import alyxraw
from ibl_pipeline.ingest import data as data_ingest

if __name__ == "__main__":

    with dj.config(safemode=False):
        uuids = (
            (acquisition_ingest.Session - behavior.TrialSet.proj())
            & 'session_start_time > "2019-06-13"'
        ).fetch("session_uuid")
        uuid_str = [str(uuid) for uuid in uuids]
        for uuid in uuid_str:
            keys = (alyxraw.AlyxRaw.Field & 'fvalue="{}"'.format(uuid)).fetch("KEY")
            (alyxraw.AlyxRaw & keys).delete()
            (alyxraw.AlyxRaw & {"uuid": UUID(uuid)}).delete()

            if len(acquisition_ingest.Session & {"session_uuid": UUID(uuid)}):
                subj_uuid, session_start_time = (
                    acquisition_ingest.Session & {"session_uuid": UUID(uuid)}
                ).fetch1("subject_uuid", "session_start_time")
            else:
                continue

            key = {"subject_uuid": subj_uuid, "session_start_time": session_start_time}
            (acquisition_ingest.ChildSession & key).delete()
            (acquisition_ingest.SessionUser & key).delete()
            (acquisition_ingest.SessionProcedure & key).delete()
            (acquisition_ingest.SessionProject & key).delete()
            (acquisition_ingest.WaterAdministrationSession & key).delete()
            (data_ingest.DataSet & key).delete()
            (data_ingest.FileRecord & key).delete()
