
import datajoint as dj
from ibl_pipeline import behavior, ephys
import numpy as np
import pandas as pd
import plotly
import plotly.graph_objs as go
import json
from os import path
from uuid import UUID
import datetime
from tqdm import tqdm

key = {'subject_uuid': UUID('18a54f60-534b-4ed5-8bda-b434079b8ab8'),
       'session_start_time': datetime.datetime(2019, 12, 6, 18, 30, 56),
       'cluster_revision': '0',
       'probe_idx': 0,
       'cluster_id': 100}

trials = behavior.TrialSet.Trial & key
cluster = ephys.Cluster() & key
spike_times = cluster.fetch1('cluster_spikes_times')

events = (ephys.Event & 'event!="go cue"').fetch('event')

trial_keys, trial_start_times, trial_end_times, \
    trial_stim_on_times, trial_response_times, trial_feedback_times = \
    trials.fetch('KEY', 'trial_start_time', 'trial_end_time',
                 'trial_stim_on_time', 'trial_response_time',
                 'trial_feedback_time')

# trial idx of each spike
spike_ids = np.searchsorted(
    np.sort(np.hstack([trial_start_times, trial_end_times])), spike_times)

trial_spks = []
for itrial, trial_key in tqdm(enumerate(trial_keys), position=0):

    trial_spk = dict(
        **trial_key,
        cluster_id=key['cluster_id'],
        cluster_revision=key['cluster_revision'],
        probe_idx=key['probe_idx']
    )

    trial_spike_time = spike_times[spike_ids == itrial]

    for event in events:
        if not len(trial_spike_time):
            trial_spk['trial_spike_times'] = []
        else:
            if event == 'stim on':
                trial_spk['trial_spike_times'] = \
                    trial_spike_time - trial_stim_on_times[itrial]
            elif event == 'response':
                trial_spk['trial_spike_times'] = \
                    trial_spike_time - trial_response_times[itrial]
            elif event == 'feedback':
                if trial_feedback_times[itrial]:
                    trial_spk['trial_spike_times'] = \
                        trial_spike_time - trial_feedback_times[itrial]
                else:
                    continue
        trial_spk['event'] = event
        trial_spks.append(trial_spk.copy())

# self.insert(trial_spks)
