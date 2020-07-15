import datajoint as dj
from .. import behavior, ephys
from datetime import datetime
from tqdm import tqdm
import brainbox as bb
import numpy as np

schema = dj.schema(dj.config.get('database.prefix', '') +
                   'ibl_analyses_ephys')

wheel = dj.create_virtual_module('wheel', 'group_shared_wheel')


@schema
class TrialType(dj.Lookup):
    definition = """
    trial_type:       varchar(32)
    """
    contents = zip(['Correct Left Contrast',
                    'Correct Right Contrast',
                    'Incorrect Left Contrast',
                    'Incorrect Right Contrast',
                    'Correct All'])


@schema
class DepthPeth(dj.Computed):
    definition = """
    -> ephys.ProbeInsertion
    -> ephys.Event
    -> TrialType
    ---
    depth_peth          : blob@ephys   # firing rate for each depth bin and time bin
    depth_bin_centers   : longblob     # centers of the depth bins
    time_bin_centers    : longblob     # centers of the time bin
    depth_baseline      : longblob     # baseline for each depth bin, average activity during -0.3 to 0 relative to the event
    depth_peth_ts=CURRENT_TIMESTAMP : timestamp
    """
    key_source = ephys.ProbeInsertion * ephys.Event * \
        (TrialType & 'trial_type="Correct All"') & ephys.DefaultCluster & \
        behavior.TrialSet & wheel.MovementTimes & 'event in ("stim on", "feedback", "movement")'

    def make(self, key):

        clusters_spk_depths, clusters_spk_times, clusters_ids = \
            (ephys.DefaultCluster & key).fetch(
                'cluster_spikes_depths', 'cluster_spikes_times', 'cluster_id')

        spikes_depths = np.hstack(clusters_spk_depths)
        spikes_times = np.hstack(clusters_spk_times)
        spikes_clusters = np.hstack(
            [[cluster_id]*len(cluster_spk_depths)
             for (cluster_id, cluster_spk_depths) in zip(clusters_ids,
                                                         clusters_spk_depths)])

        trials = (behavior.TrialSet.Trial * wheel.MovementTimes & key &
                  'trial_feedback_type=1').fetch()

        bin_size_depth = 80
        min_depth = min(spikes_depths)
        max_depth = max(spikes_depths)
        bin_edges = np.arange(min_depth, max_depth, bin_size_depth)
        spk_bin_ids = np.digitize(spikes_depths, bin_edges)

        edges = np.hstack([bin_edges, [bin_edges[-1]+bin_size_depth]])
        key.update(trial_type='Correct All',
                   depth_bin_centers=(edges[:-1] + edges[1:])/2)

        if key['event'] == 'feedback':
            event_times = trials['trial_feedback_time']
        elif key['event'] == 'stim on':
            event_times = trials['trial_stim_on_time']
        elif key['event'] == 'movement':
            event_times = trials['movement_onset']

        peth_list = []
        baseline_list = []

        for i in tqdm(np.arange(len(bin_edges)) + 1, position=0):
            f = spk_bin_ids == i
            spikes_ibin = spikes_times[f]
            spike_clusters = spikes_clusters[f]
            cluster_ids = np.unique(spike_clusters)

            peths, binned_spikes = bb.singlecell.calculate_peths(
                spikes_ibin, spike_clusters, cluster_ids,
                event_times, pre_time=0.3, post_time=1)
            if len(peths.means):
                time = peths.tscale
                peth = np.sum(peths.means, axis=0)
                baseline = peth[np.logical_and(time > -0.3, time < 0)]
                mean_bsl = np.mean(baseline)

                peth_list.append(peth)
                baseline_list.append(mean_bsl)
            else:
                peth_list.append(np.zeros_like(peths.tscale))
                baseline_list.append(0)

        key.update(depth_peth=np.vstack(peth_list),
                   depth_baseline=np.array(baseline_list),
                   time_bin_centers=peths.tscale)
        self.insert1(key, skip_duplicates=True)


@schema
class NormedDepthPeth(dj.Computed):
    definition = """
    -> DepthPeth
    ---
    normed_peth             : blob@ephys   # normalized peth, with baseline -0.3 to 0 before stim on time
    normed_depth_ts=CURRENT_TIMESTAMP  : timestamp
    """

    def make(self, key):

        depth_peth = (DepthPeth & key).fetch1('depth_peth')

        # fetch the baseline from the
        key_temp = key.copy()
        key_temp.update(event='stim on')
        baseline = (DepthPeth & key_temp).fetch1('depth_baseline')

        key.update(normed_peth=((depth_peth.T - baseline)/(baseline + 1)).T)

        self.insert1(key)
