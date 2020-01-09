import datajoint as dj
import numpy as np
from os import path, environ
from . import acquisition, reference, behavior, data
from tqdm import tqdm
import numpy as np
try:
    from oneibl.one import ONE
    one = ONE()
except:
    print('ONE not set up')

mode = environ.get('MODE')

if mode == 'update':
    schema = dj.schema('ibl_ephys')
else:
    schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_ephys')

dj.config['safemode'] = False


@schema
class Probe(dj.Lookup):
    definition = """
    # Description of a particular model of probe.
    probe_model_name: varchar(128)      # String naming probe model, from probe.description
    ---
    channel_counts: smallint            # number of channels in the probe
    """
    contents = [dict(probe_model_name='Neuropixel 3a',
                     channel_counts=960)]

    class Channel(dj.Part):
        definition = """
        # positional information about every channel on this probe.
        -> master
        channel_id:     smallint         # id of a channel on the probe
        ---
        channel_x_pos=null:  float       # x position relative to the tip of the probe (um), on the width of the shank
        channel_y_pos=null:  float       # y position relative to the tip of the probe (um), the depth where 0 is the deepest site, and positive above this.
        channel_shank=null:  enum(1, 2)  # shank of the channel, 1 or 2
        """


probe = Probe.fetch1('KEY')
Probe.Channel.insert([dict(**probe, channel_id=ichannel+1)
                      for ichannel in range(960)],
                     skip_duplicates=True)


@schema
class CompleteClusterSession(dj.Computed):
    definition = """
    # sessions that are complete with ephys datasets
    -> acquisition.Session
    ---
    complete_cluster_session=CURRENT_TIMESTAMP  :  timestamp
    """
    required_datasets = [
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


@schemaa
class EphysMissingDataLog(dj.Manual):
    definition = """
    # Keep record of the missing data
    -> acquisition.Session
    missing_data: varchar(255)
    ---
    missing_data_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class ProbeInsertion(dj.Imported):
    definition = """
    -> acquisition.Session
    probe_idx:    int    # probe insertion number (0 corresponds to probe00, 1 corresponds to probe01)
    ---
    -> Probe
    """
    key_source = CompleteClusterSession

    def make(self, key):
        eID = str((acquisition.Session & key).fetch1('session_uuid'))
        clusters_probes = one.load(
            eID, dataset_types=['clusters.probes'])
        probe_ids = np.unique(clusters_probes)
        probe = Probe.fetch1('KEY')
        for idx in probe_ids:
            key.update(probe_idx=idx,
                       probe_model_name=probe['probe_model_name'])
            self.insert1(key)


@schema
class ChannelGroup(dj.Imported):
    definition = """
    -> ProbeInsertion
    ---
    channel_raw_inds:             blob  # Array of integers saying which index in the raw recording file (of its home probe) that the channel corresponds to (counting from zero).
    channel_local_coordinates:    blob  # Location of each channel relative to probe coordinate system (µm): x (first) dimension is on the width of the shank; (y) is the depth where 0 is the deepest site, and positive above this.
    """

    key_source = acquisition.Session & ProbeInsertion \
        & (data.FileRecord & 'dataset_name="channels.rawInd.npy"') \
        & (data.FileRecord & 'dataset_name="channels.localCoordinates.npy"')

    def make(self, key):
        eID = str((acquisition.Session & key).fetch1('session_uuid'))

        channels_rawInd = one.load(
            eID, dataset_types=['channels.rawInd'])
        channels_local_coordinates = one.load(
            eID, dataset_types=['channels.localCoordinates'])

        probe_ids = (ProbeInsertion & key).fetch('probe_idx')

        self.insert(
            [dict(**key,
                  probe_idx=probe_idx,
                  channel_raw_inds=channels_rawInd[probe_idx],
                  channel_local_coordinates=channels_local_coordinates[probe_idx])
                for probe_idx in probe_ids])


@schema
class ProbeInsertionLocation(dj.Imported):
    definition = """
    # data imported from probes.trajectory
    -> ProbeInsertion
    ---
    probe_set_raw_filename: varchar(256)      # Name of the raw data file this probe was recorded in
    entry_point_rl:     float
    entry_point_ap:     float
    entry_point_dv:     float
    tip_point_rl:       float
    tip_point_ap:       float
    tip_point_dv:       float
    axial_angle:        float
    """


# needs to be further adjusted by adding channels.mlapdvIntended
@schema
class ChannelBrainLocation(dj.Imported):
    definition = """
    -> ProbeInsertion
    -> Probe.Channel
    -> reference.Atlas
    histology_revision: varchar(64)
    ---
    # from channels.brainlocation
    version_time:       datetime
    channel_ap:         float           # anterior posterior CCF coordinate (um)
    channel_dv:         float           # dorsal ventral CCF coordinate (um)
    channel_lr:         float           # left right CCF coordinate (um)
    -> reference.BrainLocationAcronym.proj(channel_brain_location='acronym')   # acronym of the brain location
    channel_raw_row:        smallint    # Each channel's row in its home file (look up via probes.rawFileName), counting from zero. Note some rows don't have a channel, for example if they were sync pulses
    """


@schema
class Template(dj.Imported):
    definition = """
    template_id:                        int
    ---
    template_waveform=null:             blob@ephys      #  Waveform of automatic spike sorting templates (stored as a sparse array, only for a subset of channels with large waveforms)
    template_waveform_channels=null:    blob@ephys      #  Channels of original recording that are stored for each template
    """


@schema
class Cluster(dj.Imported):
    definition = """
    -> ProbeInsertion
    cluster_revision='0':           varchar(64)
    cluster_id:                     int
    ---
    cluster_channel:                int             # which channel this cluster is from
    cluster_spike_times:            blob@ephys      # spike times of a particular cluster (seconds)
    cluster_spike_depths:           blob@ephys      # Depth along probe of each spike (µm; computed from waveform center of mass). 0 means deepest site, positive means above this
    cluster_spike_amps:             blob@ephys      # Amplitude of each spike (µV)
    cluster_spike_templates=null:   blob@ephys      # Template ID of each spike (i.e. output of automatic spike sorting prior to manual curation)
    cluster_spike_samples=null:     blob@ephys       # Time of spikes, measured in units of samples in their own electrophysiology binary file.
    cluster_amp=null:               float           # Mean amplitude of each cluster (µV)
    cluster_metrics=null:           blob            # Quality control metrics at the cluster level
    cluster_waveform=null:          blob@ephys      # Mean unfiltered waveform of spikes in this cluster (but for neuropixels data will have been hardware filtered) nClustersxnSamplesxnChannels
    cluster_template_waveform=null: blob@ephys      # Waveform that was used to detect those spikes in Kilosort, in whitened space (or the most representative such waveform if multiple templates were merged)
    cluster_depth=null:             float           # Depth of mean cluster waveform on probe (µm). 0 means deepest site, positive means above this.
    cluster_peak_to_trough=null:    blob@ephys      # trough to peak time (ms)
    cluster_phy_annotation=null:    tinyint         # 0 = noise, 1 = MUA, 2 = Good, 3 = Unsorted, other number indicates manual quality score (from 4 to 100)
    cluster_phy_id=null:            int             # Original cluster in
    """
    key_source = acquisition.Session & ProbeInsertion

    def make(self, key):
        eID = str((acquisition.Session & key).fetch1('session_uuid'))

        clusters_datasets = ['clusters.amps',
                             'clusters.channels',
                             'clusters.depths',
                             'clusters.peakToTrough']

        clusters_data = [
            one.load(eID, dataset_types=[dataset])
            for dataset in clusters_datasets
        ]

        spikes_datasets = ['spikes.amps',
                           'spikes.clusters',
                           'spikes.depths',
                           'spikes.times']

        spikes_data = [
            one.load(eID, dataset_types=[dataset])
            for dataset in spikes_datasets
        ]

        cluster_lengths = [
            [len(subdata) for subdata in data]
            if np.any(data) else None for data in clusters_data]
        spikes_lengths = [
            [len(subdata) for subdata in data]
            for data in spikes_data]

        # spikes_data[1] is spikes.clusters, match the spikes
        # with clusters by this dataset.
        max_cluster = [max(data)+1 for data in spikes_data[1]]

        standard_order_cluster = cluster_lengths[0]
        idx_clusters = [
            [cluster_length.index(x) for x in standard_order_cluster]
            if cluster_length else None for cluster_length in cluster_lengths]

        idx_cluster_spikes = [max_cluster.index(x)
                              for x in standard_order_cluster]
        standard_order_spikes = [spikes_lengths[1][idx]
                                 for idx in idx_cluster_spikes]
        idx_spikes = [[spikes_length.index(x) for x in standard_order_spikes]
                      for spikes_length in spikes_lengths]

        clusters = []
        for probe_idx in [0, 1]:

            clusters_data_probe = []
            for idata, data in enumerate(clusters_data):
                print(idata)
                if idx_clusters[idata]:
                    print(idx_clusters)
                    idx = idx_clusters[idata][probe_idx]
                    clusters_data_probe.append(data[idx])
                else:
                    clusters_data_probe.append(None)

            clusters_amps = clusters_data_probe[0]
            clusters_channels = clusters_data_probe[1]
            clusters_depths = clusters_data_probe[2]

            clusters_peak_to_trough = clusters_data_probe[3]

            spikes_data_probe = []

            for idata, data in enumerate(spikes_data):
                idx = idx_spikes[idata][probe_idx]
                spikes_data_probe.append(data[idx])

            spikes_amps = spikes_data_probe[0]
            spikes_clusters = spikes_data_probe[1]
            spikes_depths = spikes_data_probe[2]
            spikes_times = spikes_data_probe[3]

            for icluster, cluster_depth in enumerate(clusters_depths):
                idx = spikes_clusters == icluster
                cluster_amps = clusters_amps[icluster]
                cluster = dict(
                    **key,
                    probe_idx=probe_idx,
                    cluster_id=icluster,
                    cluster_amp=clusters_amps[icluster],
                    cluster_depth=cluster_depth,
                    cluster_channel=clusters_channels[icluster],
                    cluster_spike_times=spikes_times[idx],
                    cluster_spike_depths=spikes_depths[idx],
                    cluster_spike_amps=spikes_amps[idx])
                if clusters_peak_to_trough:
                    cluster.update(
                        cluster_peak_to_trough=clusters_peak_to_trough[icluster])
                clusters.append(cluster)

        self.insert(clusters)


@schema
class ClusterBrainLocation(dj.Imported):
    definition = """
    -> Cluster
    ---
    -> reference.BrainLocationAcronym    # acronym of the brain location
    cluster_ml_position:      float      # Estimated 3d location of the cell relative to bregma - mediolateral
    cluster_ap_position:      float      # anterior-posterior
    cluster_dv_position:      float      # dorsoventral
    """


@schema
class Event(dj.Lookup):
    definition = """
    event:       varchar(32)
    """
    contents = zip(['go cue', 'stim on', 'response', 'feedback'])


@schema
class TrialSpikes(dj.Computed):
    definition = """
    -> Cluster
    -> behavior.TrialSet.Trial
    -> Event
    ---
    trial_spike_times=null:   longblob     # spike time for each trial, aligned to different event times
    """
    key_source = behavior.TrialSet * Cluster

    def make(self, key):
        trials = behavior.TrialSet.Trial & key
        trial_spks = []
        cluster = Cluster() & key
        spike_times = cluster.fetch1('cluster_spike_times')

        for trial, itrial in tqdm(zip(trials.fetch(as_dict=True), trials.fetch('KEY'))):
            trial_spk = dict(
                **itrial,
                cluster_id=key['cluster_id'],
                cluster_revision=key['cluster_revision'],
                probe_idx=key['probe_idx']
            )
            f = np.logical_and(spike_times < trial['trial_end_time'],
                               spike_times > trial['trial_start_time'])

            events = (Event & 'event!="go cue"').fetch('event')
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

        self.insert(trial_spks)


@schema
class LFP(dj.Imported):
    definition = """
    -> ProbeInsertion
    ---
    lfp_timestamps:       blob@ephys    # Timestamps for LFP timeseries in seconds
    lfp_start_time:       float         # (seconds)
    lfp_end_time:         float         # (seconds)
    lfp_duration:         float         # (seconds)
    lfp_sampling_rate:    float         # samples per second
    """

    class Channel(dj.Part):
        definition = """
        -> master
        -> Probe.Channel
        ---
        lfp: blob@ephys           # recorded lfp on this channel
        """
