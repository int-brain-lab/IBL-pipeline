
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

key = {'subject_uuid': UUID('18a54f60-534b-4ed5-8bda-b434079b8ab8'),
       'session_start_time': datetime.datetime(2019, 12, 6, 18, 30, 56),
       'cluster_revision': '0',
       'probe_idx': 0,
       'cluster_id': 100}

trials = behavior.TrialSet.Trial & key
trial_spks = []
cluster = ephys.Cluster() & key
spike_times = cluster.fetch1('cluster_spikes_times')


# trials.fetch(as_dict=True), trials.fetch('KEY')
# f = np.searchsorted

for trial, itrial in tqdm(zip(trials.fetch(as_dict=True), trials.fetch('KEY'))):
    trial_spk = dict(
        **itrial,
        cluster_id=key['cluster_id'],
        cluster_revision=key['cluster_revision'],
        probe_idx=key['probe_idx']
    )

    f = np.logical_and(spike_times < trial['trial_end_time'],
                       spike_times > trial['trial_start_time'])

    # TODO: to move outside the loop
    events = (ephys.Event & 'event!="go cue"').fetch('event')

    spike_times[f]

    for event in events:
        if not np.any(f):
            trial_spk['trial_spike_times'] = []
        else:
            if event == 'stim on':
                trial_spk['trial_spike_times'] = \
                    spike_times[f] - trial['trial_stim_on_time']
            elif event == 'response':
                trial_spk['trial_spike_times'] = \
                    spike_times[f] - trial['trial_response_time']
            elif event == 'feedback':
                if trial['trial_feedback_time']:
                    trial_spk['trial_spike_times'] = \
                        spike_times[f] - trial['trial_feedback_time']
                else:
                    continue
        trial_spk['event'] = event
        trial_spks.append(trial_spk.copy())

# self.insert(trial_spks)
