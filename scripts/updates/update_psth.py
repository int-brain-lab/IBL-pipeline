
import datajoint as dj
from ibl_pipeline.plotting import ephys
from ibl_pipeline import acquisition
from tqdm import tqdm

if __name__ == '__main__':

    with dj.config(safemode=False):

        for key in tqdm((ephys.Psth).fetch('KEY')):
            (ephys.Psth & key).delete_quick()
            ephys.Psth.populate(key, display_progress=True,
                                suppress_errors=True)
