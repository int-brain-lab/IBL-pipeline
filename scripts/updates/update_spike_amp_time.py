import datajoint as dj
from tqdm import tqdm

from ibl_pipeline import ephys
from ibl_pipeline.plotting import ephys as ephys_plotting

if __name__ == "__main__":

    with dj.config(safemode=False):
        for key in tqdm(
            (ephys.ProbeInsertion & ephys_plotting.SpikeAmpTime).fetch("KEY"),
            position=0,
        ):
            (ephys_plotting.SpikeAmpTime & key).delete()
            ephys_plotting.SpikeAmpTime.populate(key, suppress_errors=True)
