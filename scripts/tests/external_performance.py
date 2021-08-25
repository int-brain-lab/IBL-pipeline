import datajoint as dj
import numpy as np
from os import path, environ
from ibl_pipeline.common import *
from tqdm import tqdm
import numpy as np
import pandas as pd
from uuid import UUID
import re
import alf.io
from ibl_pipeline.utils import atlas
import time

if mode == 'update':
    schema = dj.schema('ibl_ephys')
else:
    schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_ephys')


@schema
class TrialSpikes(dj.Computed):
    definition = """
    # Spike times of each trial aligned to different events
    -> DefaultCluster
    -> behavior.TrialSet.Trial
    -> Event
    ---
    trial_spike_times=null:   blob@ephys     # spike time for each trial, aligned to different event times
    trial_spikes_ts=CURRENT_TIMESTAMP:    timestamp
    """
    key_source = behavior.TrialSet * DefaultCluster * Event & \
        ['event in ("stim on", "feedback")',
         wheel.MovementTimes & 'event="movement"']

    def make(self, key):

        cluster = DefaultCluster() & key
        spike_times = cluster.fetch1('cluster_spikes_times')
        event = (Event & key).fetch1('event')

        if event == 'movement':
            trials = behavior.TrialSet.Trial * wheel.MovementTimes & key
            trial_keys, trial_start_times, trial_end_times, \
                trial_stim_on_times, trial_feedback_times, \
                trial_movement_times = \
                trials.fetch('KEY', 'trial_start_time', 'trial_end_time',
                             'trial_stim_on_time', 'trial_feedback_time',
                             'movement_onset')
        else:
            trials = behavior.TrialSet.Trial & key
            trial_keys, trial_start_times, trial_end_times, \
                trial_stim_on_times, trial_feedback_times = \
                trials.fetch('KEY', 'trial_start_time', 'trial_end_time',
                             'trial_stim_on_time', 'trial_feedback_time')

        # trial idx of each spike
        spike_ids = np.searchsorted(
            np.sort(np.hstack(np.vstack([trial_start_times, trial_end_times]).T)),
            spike_times)

        trial_spks = []
        for itrial, trial_key in enumerate(trial_keys):

            trial_spk = dict(
                **trial_key,
                cluster_id=key['cluster_id'],
                probe_idx=key['probe_idx']
            )

            trial_spike_time = spike_times[spike_ids == itrial*2+1]

            if not len(trial_spike_time):
                trial_spk['trial_spike_times'] = []
            else:
                if event == 'stim on':
                    trial_spk['trial_spike_times'] = \
                        trial_spike_time - trial_stim_on_times[itrial]
                elif event == 'movement':
                    trial_spk['trial_spike_times'] = \
                        trial_spike_time - trial_movement_times[itrial]
                elif event == 'feedback':
                    if trial_feedback_times[itrial]:
                        trial_spk['trial_spike_times'] = \
                            trial_spike_time - trial_feedback_times[itrial]
                    else:
                        continue
                trial_spk['event'] = event
                trial_spks.append(trial_spk.copy())
        self.insert(trial_spks)

@schema
class TrialSpikesLocal(dj.Computed):
    definition = """
    # Spike times of each trial aligned to different events
    -> DefaultCluster
    -> behavior.TrialSet.Trial
    -> Event
    ---
    trial_spike_times=null:   blob@ephys_local     # spike time for each trial, aligned to different event times
    trial_spikes_ts=CURRENT_TIMESTAMP:    timestamp
    """
    key_source = behavior.TrialSet * DefaultCluster * Event & \
        ['event in ("stim on", "feedback")',
         wheel.MovementTimes & 'event="movement"']

    def make(self, key):

        cluster = DefaultCluster() & key
        spike_times = cluster.fetch1('cluster_spikes_times')
        event = (Event & key).fetch1('event')

        if event == 'movement':
            trials = behavior.TrialSet.Trial * wheel.MovementTimes & key
            trial_keys, trial_start_times, trial_end_times, \
                trial_stim_on_times, trial_feedback_times, \
                trial_movement_times = \
                trials.fetch('KEY', 'trial_start_time', 'trial_end_time',
                             'trial_stim_on_time', 'trial_feedback_time',
                             'movement_onset')
        else:
            trials = behavior.TrialSet.Trial & key
            trial_keys, trial_start_times, trial_end_times, \
                trial_stim_on_times, trial_feedback_times = \
                trials.fetch('KEY', 'trial_start_time', 'trial_end_time',
                             'trial_stim_on_time', 'trial_feedback_time')

        # trial idx of each spike
        spike_ids = np.searchsorted(
            np.sort(np.hstack(np.vstack([trial_start_times, trial_end_times]).T)),
            spike_times)

        trial_spks = []
        for itrial, trial_key in enumerate(trial_keys):

            trial_spk = dict(
                **trial_key,
                cluster_id=key['cluster_id'],
                probe_idx=key['probe_idx']
            )

            trial_spike_time = spike_times[spike_ids == itrial*2+1]

            if not len(trial_spike_time):
                trial_spk['trial_spike_times'] = []
            else:
                if event == 'stim on':
                    trial_spk['trial_spike_times'] = \
                        trial_spike_time - trial_stim_on_times[itrial]
                elif event == 'movement':
                    trial_spk['trial_spike_times'] = \
                        trial_spike_time - trial_movement_times[itrial]
                elif event == 'feedback':
                    if trial_feedback_times[itrial]:
                        trial_spk['trial_spike_times'] = \
                            trial_spike_time - trial_feedback_times[itrial]
                    else:
                        continue
                trial_spk['event'] = event
                trial_spks.append(trial_spk.copy())

        self.insert(trial_spks)


if __name__ == '__main__':


    session = acquisition.Session & {'session_uuid': 'f8d5c8b0-b931-4151-b86c-c471e2e80e5d'}
    clusters = (ephys.DefaultCluster & session).fetch('KEY', limit=2)
    tables = [ephys.AlignedTrialSpikes, TrialSpikes, TrialSpikesExternal]
    with dj.config(safemode=False):
        for table in tables:
            (table & clusters).delete()
            start_time = time.time()
            table.populate(clusters, display_progress=True, suppress_errors=True)
            print('Populate time for {}: {}'.format(
                table.__name__, time.time()-start_time))

            start_time = time.time()
            entries = (table & clusters).fetch()
            print('Fetch time for {}: {}'.format(
                table.__name__, time.time()-start_time))
