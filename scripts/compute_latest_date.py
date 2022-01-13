'''
This script computes the latest event date happen to individual subject
and manually insert into the table behavior_plotting.LatestDate
'''

import datajoint as dj
from ibl_pipeline import reference, subject, action, acquisition, data, behavior
from ibl_pipeline.analyses import behavior as behavior_analyses
from ibl_pipeline.plotting import behavior as behavior_plotting
import numpy as np
from datetime import datetime
from tqdm import tqdm


if __name__ == '__main__':
    print('Populating latest date...')
    for key in tqdm(subject.Subject.fetch('KEY'), position=0):
        behavior_plotting.SubjectLatestEvent.create_entry(key)
