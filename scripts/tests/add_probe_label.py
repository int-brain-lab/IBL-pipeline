from ibl_pipeline import ephys, acquisition
import datajoint as dj
from oneibl.one import ONE
import re
import alf.io
from tqdm import tqdm

one = ONE()

keys = ephys.ProbeInsertion.fetch('KEY')

dtypes = ['probes.description']
for key in tqdm(keys):
    eID = str((acquisition.Session & key).fetch1('session_uuid'))
    files = one.load(eID, dataset_types=dtypes, download_only=True)
    ses_path = alf.io.get_session_path(files[0])
    probes = alf.io.load_object(ses_path.joinpath('alf'), 'probes')
    # ingest probe insertion
    for p in probes['description']:
        print(p['label'])
        idx = int(re.search('probe.?0([0-3])', p['label']).group(1))
        if idx == key['probe_idx']:
            dj.Table._update(
                ephys.ProbeInsertion & key, 'probe_label', p['label'])
