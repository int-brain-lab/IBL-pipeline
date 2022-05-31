import datetime
from uuid import UUID

import numpy as np
from tqdm import tqdm

from ibl_pipeline import acquisition, behavior, ephys

events = ephys.Event & 'event in ("feedback", "movement", "response", "stim on")'

trial_sets = behavior.TrialSet & ephys.AlignedTrialSpikes

for trial_set in tqdm(trial_sets):

    clusters = ephys.DefaultCluster & trial_set

    for event in events:

        print("Inserting missing entries for {}...".format(event["event"]))

        if ephys.AlignedTrialSpikes & event & clusters:
            for cluster in tqdm(
                clusters.aggr(
                    ephys.AlignedTrialSpikes & event, n_trials="count(trial_id)"
                )
                & "n_trials < {}".format(len(behavior.TrialSet.Trial & trial_set))
            ):
                trials_missing = (behavior.TrialSet.Trial & cluster) - (
                    ephys.AlignedTrialSpikes & cluster & event
                )
                entries = (
                    ephys.DefaultCluster.proj()
                    * trials_missing.proj()
                    * ephys.Event.proj()
                    & event
                    & cluster
                ).fetch(as_dict=True)

                ephys.AlignedTrialSpikes.insert(
                    [dict(**e, trial_spike_times=np.array([])) for e in entries],
                    skip_duplicates=True,
                    allow_direct_insert=True,
                )
