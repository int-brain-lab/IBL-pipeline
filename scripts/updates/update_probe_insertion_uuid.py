'''
This script update probe insertion uuid for old entries

Shan Shen, 2021-03-05
'''
import datajoint as dj
from tqdm import tqdm
from ibl_pipeline import acquisition
from ibl_pipeline.ingest import alyxraw


ephys = dj.create_virtual_module('ephys', 'ibl_ephys')
ephys_ingest = dj.create_virtual_module('ephys_ingest', 'ibl_ingest_ephys')

# Get mismatching probe uuids
mismatch_probe_insertions = \
    (ephys.ProbeInsertion &
     (dj.U('subject_uuid', 'session_start_time', 'probe_idx') & ephys_ingest.ProbeInsertion)) - \
    ephys_ingest.ProbeInsertion.proj()


alyx_keys = (alyxraw.AlyxRaw & 'model="experiments.probeinsertion"').fetch('KEY')

for key in tqdm(mismatch_probe_insertions.fetch('KEY')):

    # get corresponding entries in alyxraw

    session_uuid = str((acquisition.Session & key).fetch1('session_uuid'))
    probe_name, probe_idx = (ephys.ProbeInsertion & key).fetch1('probe_label', 'probe_idx')

    if not probe_name:
        probe_name = 'probe0' + str(probe_idx)

    q = alyxraw.AlyxRaw & alyx_keys & \
        (alyxraw.AlyxRaw.Field & alyx_keys & dict(fname='session', fvalue=session_uuid)) & \
        (alyxraw.AlyxRaw.Field & alyx_keys & dict(fname='name', fvalue=probe_name))

    if len(q) == 1:
        ephys.ProbeInsertion.update1(
            dict(**key, probe_insertion_uuid=q.fetch1('uuid')))
