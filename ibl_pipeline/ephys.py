import datajoint as dj
import numpy as np
from os import path, environ
from . import acquisition, reference, behavior, data
from .ingest import ephys as ephys_ingest
from tqdm import tqdm
import numpy as np
import pandas as pd
from uuid import UUID
import re
import alf.io
from ibl_pipeline.utils import atlas

wheel = dj.create_virtual_module('wheel', 'group_shared_wheel')

try:
    from oneibl.one import ONE
    one = ONE()
except Exception:
    print('ONE not set up')

mode = environ.get('MODE')

if mode == 'update':
    schema = dj.schema('ibl_ephys')
else:
    schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_ephys')

dj.config['safemode'] = False


@schema
class ProbeModel(dj.Lookup):
    definition = """
    # Model of a probe, ingested from the alyx table experiments.probemodel
    probe_name           : varchar(128)
    ---
    probe_uuid           : uuid
    probe_model          : varchar(32)                  # 3A, 3B
    probe_manufacturer   : varchar(32)
    probe_description=null : varchar(2048)
    probe_model_ts=CURRENT_TIMESTAMP : timestamp
    """


@schema
class CompleteClusterSession(dj.Computed):
    definition = """
    # Sessions that are complete with ephys datasets
    -> acquisition.Session
    ---
    complete_cluster_session_ts=CURRENT_TIMESTAMP  :  timestamp
    """
    required_datasets = [
        'clusters.amps.npy',
        'clusters.channels.npy',
        'clusters.depths.npy',
        'clusters.metrics.csv',
        'clusters.peakToTrough.npy',
        'clusters.uuids.csv',
        'clusters.waveforms.npy',
        'clusters.waveformsChannels.npy',
        'spikes.amps.npy',
        'spikes.clusters.npy',
        'spikes.depths.npy',
        'spikes.samples.npy',
        'spikes.templates.npy',
        'spikes.times.npy'
    ]
    key_source = acquisition.Session & \
        'task_protocol like "%ephysChoiceWorld%"' \
        & (data.FileRecord & 'dataset_name="spikes.times.npy"') \
        & (data.FileRecord & 'dataset_name="spikes.clusters.npy"') \
        & (data.FileRecord & 'dataset_name="probes.description.json"')

    def make(self, key):
        datasets = (data.FileRecord & key & 'repo_name LIKE "flatiron_%"' &
                    {'exists': 1}).fetch('dataset_name')
        is_complete = bool(np.all([req_ds in datasets
                                   for req_ds in self.required_datasets]))
        if is_complete:
            self.insert1(key)
            (EphysMissingDataLog & key).delete()
        else:
            for req_ds in self.required_datasets:
                if req_ds not in datasets:
                    EphysMissingDataLog.insert1(
                        dict(**key,
                             missing_data=req_ds),
                        skip_duplicates=True)


@schema
class EphysMissingDataLog(dj.Manual):
    definition = """
    # Keep record of the missing data
    -> acquisition.Session
    missing_data: varchar(255)
    ---
    missing_data_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class ProblematicDataSet(dj.Manual):
    definition = """
    # Data sets that are known to be old or have a problem
    -> acquisition.Session
    """


@schema
class ProbeInsertion(dj.Imported):
    definition = """
    # Probe insertion of a session, ingested from the alyx table experiments.probeinsertion
    -> acquisition.Session
    probe_idx                   : int           # probe insertion number (0 corresponds to probe00, 1 corresponds to probe01)
    ---
    probe_label=null            : varchar(32)   # name in alyx table experiments.probeinsertion
    probe_insertion_uuid=null   : uuid          # probe insertion uuid
    -> [nullable] ProbeModel
    probe_insertion_ts=CURRENT_TIMESTAMP  :  timestamp
    """


@schema
class ChannelGroup(dj.Imported):
    definition = """
    # Raw index and local coordinates of each channel group, ingested from channels.rawInd and localCoordinates
    -> ProbeInsertion
    ---
    channel_raw_inds:             blob  # Array of integers saying which index in the raw recording file (of its home probe) that the channel corresponds to (counting from zero)
    channel_local_coordinates:    blob  # Location of each channel relative to probe coordinate system (µm): x (first) dimension is on the width of the shank; (y) is the depth where 0 is the deepest site, and positive above this
    channel_group_ts=CURRENT_TIMESTAMP  :  timestamp
    """

    key_source = ProbeInsertion \
        & (data.FileRecord & 'dataset_name="channels.rawInd.npy"') \
        & (data.FileRecord & 'dataset_name="channels.localCoordinates.npy"')

    def make(self, key):

        eID = str((acquisition.Session & key).fetch1('session_uuid'))
        dtypes = [
            'channels.rawInd',
            'channels.localCoordinates'
        ]

        files = one.load(eID, dataset_types=dtypes, download_only=True,
                         clobber=True)
        ses_path = alf.io.get_session_path(files[0])

        probe_name = (ProbeInsertion & key).fetch1('probe_label')
        channels = alf.io.load_object(
            ses_path.joinpath('alf', probe_name), 'channels')

        self.insert1(
            dict(**key,
                 channel_raw_inds=channels.rawInd,
                 channel_local_coordinates=channels.localCoordinates))


@schema
class ClusteringMethod(dj.Lookup):
    definition = """
    clustering_method:   varchar(32)   # clustering method
    """
    contents = [['ks2']]


@schema
class DefaultCluster(dj.Imported):
    definition = """
    # Cluster properties achieved from the default clustering method, ingested from alf files clusters.*
    -> ProbeInsertion
    cluster_id:                 int
    ---
    cluster_uuid:                    uuid            # uuid of this cluster
    cluster_channel:                 int             # which channel this cluster is from
    cluster_amp=null:                float           # Mean amplitude of each cluster (µV)
    cluster_waveforms=null:          blob@ephys      # Waveform from spike sorting templates (stored as a sparse array, only for a subset of channels closest to the peak channel)
    cluster_waveforms_channels=null: blob@ephys      # Index of channels that are stored for each cluster waveform. Sorted by increasing distance from the maximum amplitude channel.
    cluster_depth=null:              float           # Depth of mean cluster waveform on probe (µm). 0 means deepest site, positive means above this.
    cluster_peak_to_trough=null:     blob@ephys      # trough to peak time (ms)
    cluster_spikes_times:            blob@ephys      # spike times of a particular cluster (seconds)
    cluster_spikes_depths:           blob@ephys      # Depth along probe of each spike (µm; computed from waveform center of mass). 0 means deepest site, positive means above this
    cluster_spikes_amps:             blob@ephys      # Amplitude of each spike (µV)
    cluster_spikes_templates=null:   blob@ephys      # Template ID of each spike (i.e. output of automatic spike sorting prior to manual curation)
    cluster_spikes_samples=null:     blob@ephys      # Time of spikes, measured in units of samples in their own electrophysiology binary file.
    cluster_ts=CURRENT_TIMESTAMP  :  timestamp
    """
    key_source = ProbeInsertion & (CompleteClusterSession - ProblematicDataSet)

    def make(self, key):
        eID = str((acquisition.Session & key).fetch1('session_uuid'))

        dtypes = [
            'clusters.amps',
            'clusters.channels',
            'clusters.depths',
            'clusters.metrics',
            'clusters.peakToTrough',
            'clusters.uuids',
            'clusters.waveforms',
            'clusters.waveformsChannels',
            'spikes.amps',
            'spikes.clusters',
            'spikes.depths',
            'spikes.samples',
            'spikes.templates',
            'spikes.times'
        ]

        files = one.load(eID, dataset_types=dtypes, download_only=True,
                         clobber=True)
        ses_path = alf.io.get_session_path(files[0])

        probe_name = (ProbeInsertion & key).fetch1('probe_label')

        clusters = alf.io.load_object(
            ses_path.joinpath('alf', probe_name), 'clusters')
        spikes = alf.io.load_object(
            ses_path.joinpath('alf', probe_name), 'spikes')

        max_spike_time = spikes.times[-1]

        for icluster, cluster_uuid in tqdm(enumerate(clusters.uuids['uuids']),
                                           position=0):

            idx = spikes.clusters == icluster
            cluster = dict(
                **key,
                cluster_id=icluster,
                cluster_uuid=cluster_uuid,
                cluster_channel=clusters.channels[icluster],
                cluster_amp=clusters.amps[icluster],
                cluster_waveforms=clusters.waveforms[icluster],
                cluster_waveforms_channels=clusters.waveformsChannels[icluster],
                cluster_depth=clusters.depths[icluster],
                cluster_peak_to_trough=clusters.peakToTrough[icluster],
                cluster_spikes_times=spikes.times[idx],
                cluster_spikes_depths=spikes.depths[idx],
                cluster_spikes_amps=spikes.amps[idx],
                cluster_spikes_templates=spikes.templates[idx],
                cluster_spikes_samples=spikes.samples[idx])

            self.insert1(cluster)

            num_spikes = len(cluster['cluster_spikes_times'])
            firing_rate = num_spikes/max_spike_time

            metrics = clusters.metrics.iloc[icluster]

            self.Metrics.insert1(
                dict(
                    **key,
                    cluster_id=icluster,
                    num_spikes=num_spikes,
                    firing_rate=firing_rate,
                    metrics=metrics.to_dict()))

            if metrics.ks2_label and (not pd.isnull(metrics.ks2_label)):
                self.Ks2Label.insert1(
                    dict(**key, cluster_id=icluster,
                         ks2_label=metrics.ks2_label))

            self.Metric.insert(
                [dict(**key, cluster_id=icluster,
                      metric_name=name, metric_value=value)
                 for name, value in metrics.to_dict().items()
                 if name != 'ks2_label' and not np.isnan(value)]
            )

    class Metric(dj.Part):
        definition = """
        # Individual quality metric, ingested from clusters.metrics
        -> master
        metric_name: varchar(32)
        ---
        metric_value: float
        """

    class Metrics(dj.Part):
        definition = """
        # Quality metrics as a dictionary, ingested from cluster.metrics
        -> master
        ---
        num_spikes:                 int         # total spike number
        firing_rate:                float       # firing rate of the cluster
        metrics:                    longblob    # a dictionary with fields of metrics, depend on the clustering method
        """

    class Ks2Label(dj.Part):
        definition = """
        # Quality label given by kilosort2, ‘good’ or ‘mua’
        -> master
        ---
        ks2_label       : enum('good', 'mua')
        """


@schema
class GoodClusterCriterion(dj.Lookup):
    definition = """
    # Criterion to identify whether a cluster is good.
    criterion_id:               int
    ---
    criterion_description:      varchar(255)
    """
    contents = [[1, 'firing rate greater than 0.2']]


@schema
class GoodCluster(dj.Computed):
    definition = """
    # Whether a cluster is good based on the criterion defined in GoodClusterCriterion
    -> DefaultCluster
    -> GoodClusterCriterion
    ---
    is_good=0:       bool      # whether the unit is good
    """
    def make(self, key):

        firing_rate = (DefaultCluster.Metrics & key).fetch1('firing_rate')
        if key['criterion_id'] == 1:
            if firing_rate > 0.2:
                key['is_good'] = True

        self.insert1(key)


@schema
class Event(dj.Lookup):
    definition = """
    # Different behavioral events, including 'go cue', 'stim on', 'response', 'feedback', and 'movement'
    event:       varchar(32)
    """
    contents = zip(['go cue', 'stim on', 'response', 'feedback', 'movement'])


@schema
class AlignedTrialSpikes(dj.Computed):
    definition = """
    # Spike times of each trial aligned to different events
    -> DefaultCluster
    -> behavior.TrialSet.Trial
    -> Event
    ---
    trial_spike_times=null:   longblob     # spike time for each trial, aligned to different event times
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
