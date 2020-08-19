'''
This script update session_uuids in DJ table to match the lasted ONE eids.
'''

import datajoint as dj
from tqdm import tqdm
from oneibl.one import ONE


if __name__ == '__main__':

    one = ONE()

    # ======= ingest subject and session tables into alyxraw `updates_ibl_alyxraw`====

    dj.config['database.prefix'] = 'updates_'

    from ibl_pipeline.ingest.ingest_alyx_raw import alyxraw, get_alyx_entries, insert_to_alyxraw


    insert_to_alyxraw(get_alyx_entries(models=['subjects.subject',
                                            'actions.session']))

    # ======= query sessions with non-matching eids =======

    acquisition = dj.create_virtual_module('acquisition', 'ibl_acquisition')
    behavior = dj.create_virtual_module('behavior', 'ibl_behavior')

    session_raw = alyxraw.AlyxRaw & 'model="actions.session"'

    prob_sessions = (acquisition.Session -
                    (acquisition.Session.proj(uuid='session_uuid') &
                    session_raw)) & behavior.TrialSet

    # eid non matching sessions with matching subject_uuid and session_start_time

    session_start_time_field = dj.U('uuid', 'session_start_time') & \
        (alyxraw.AlyxRaw.Field & session_raw & 'fname="start_time"').proj(
            session_start_time='cast(fvalue as datetime)')

    vals = (prob_sessions * session_start_time_field).fetch(
        'KEY', 'uuid', 'session_uuid')
    for (key, uuid, session_uuid) in tqdm(zip(*vals), position=0, total=len(vals[0])):
        print(uuid)
        dj.Table._update(prob_sessions, 'session_uuid', uuid.bytes)
