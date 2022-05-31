import datajoint as dj
from tqdm import tqdm

from ibl_pipeline import acquisition
from ibl_pipeline.plotting import ephys

if __name__ == "__main__":

    with dj.config(safemode=False):

        for key in tqdm((ephys.Psth).fetch("KEY")):
            (ephys.Psth & key).delete_quick()
            ephys.Psth.populate(key, display_progress=True, suppress_errors=True)
