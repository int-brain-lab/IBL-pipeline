"""
This script computes the latest event date happen to individual subject
and manually insert into the table behavior_plotting.LatestDate
"""

from datetime import datetime

import datajoint as dj
import numpy as np
from tqdm import tqdm

from ibl_pipeline import acquisition, action, behavior, data, reference, subject
from ibl_pipeline.analyses import behavior as behavior_analyses
from ibl_pipeline.plotting import behavior as behavior_plotting

if __name__ == "__main__":
    print("Populating latest date...")
    for key in tqdm(subject.Subject.fetch("KEY"), position=0):
        behavior_plotting.SubjectLatestEvent.create_entry(key)
