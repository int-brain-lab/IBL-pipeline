import datajoint as dj
from ibl_pipeline import ephys
from tqdm import tqdm


if __name__ == '__main__':

    dj.config['safemode'] = False

    clusters = ephys.DefaultCluster & \
        (ephys.AlignedTrialSpikes & 'event="movement"')

    for key in tqdm(clusters.fetch('KEY'), position=0):
        (ephys.AlignedTrialSpikes & 'event="movement"' & key).delete_quick()
