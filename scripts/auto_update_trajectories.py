
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

print('Repopulate shadow histology.ProbeTrajectory and ChannelBrainRegion...')
histology_ingest.ProbeTrajectory.populate(**kwargs)
histology_ingest.ChannelBrainRegion.populate(**kwargs)

print('Updating and populate real histology.ProbeTrajectory and ChannelBrainRegion...')
for key in tqdm((histology.ProbeTrajectory &
                 changed.proj(probe_trajectory_uuid='uuid')).fetch('KEY')):
    (histology.ProbeTrajectory & key).delete()
    histology.ProbeTrajectory.populate(key, **kwargs)
    copy_table(histology, histology_ingest, 'ChannelBrainRegion')
    (histology.ClusterBrainRegion & key).delete()
    histology.ClusterBrainRegion.populate(key, **kwargs)
    (histology.SessionBrainRegion & key).delete()
    histology.SessionBrainRegion.populate(key, **kwargs)
