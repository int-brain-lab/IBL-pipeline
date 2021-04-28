import datajoint as dj
from ibl_pipeline import ephys
from tqdm import tqdm


if __name__ == '__main__':

    clusters = ephys.DefaultCluster & \
        (ephys.AlignedTrialSpikes & 'event="movement"')

    with dj.config(safemode=False):
        for key in tqdm(clusters.fetch('KEY'), position=0):
            (ephys.AlignedTrialSpikes & 'event="movement"' & key).delete_quick()
