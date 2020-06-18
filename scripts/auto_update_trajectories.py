
import datajoint as dj
from ibl_pipeline import histology
from ibl_pipeline.ingest import histology as histology_ingest
from ibl_pipeline.ingest import alyxraw
from ingest_alyx_raw import get_alyx_entries, insert_to_alyxraw
from ibl_pipeline.ingest.ingest_utils import copy_table

from tqdm import tqdm

dj.config['safemode'] = False

kwargs = dict(display_progress=True, suppress_errors=True)

# Get the entries whose timestamp has changed
changed = histology_ingest.ProbeTrajectory.proj(
    'trajectory_ts', uuid='probe_trajectory_uuid') * \
          (alyxraw.AlyxRaw.Field & 'fname="datetime"').proj(
            ts='cast(fvalue as datetime)') & 'ts!=trajectory_ts'

print('Deleting alyxraw entries for histology...')
(alyxraw.AlyxRaw & changed).delete()

print('Repopulate alyxraw.AlyxRaw for updates...')
insert_to_alyxraw(get_alyx_entries(models='experiments.trajectoryestimate'))

print('Repopulate shadow histology.ProbeTrajectory and ChannelBrainLocation...')
histology_ingest.ProbeTrajectory.populate(**kwargs)
histology_ingest.ChannelBrainLocation.populate(**kwargs)

print('Updating and populate real histology.ProbeTrajectory and ChannelBrainLocation...')
for key in tqdm((histology.ProbeTrajectory &
                 changed.proj(probe_trajectory_uuid='uuid')).fetch('KEY')):
    (histology.ProbeTrajectory & key).delete()
    histology.ProbeTrajectory.populate(key, **kwargs)
    copy_table(histology, histology_ingest, 'ChannelBrainLocation')
    (histology.ClusterBrainLocation & key).delete()
    histology.ClusterBrainLocation.populate(key, **kwargs)
    (histology.SessionBrainLocation & key).delete()
    histology.SessionBrainLocation.populate(key, **kwargs)
