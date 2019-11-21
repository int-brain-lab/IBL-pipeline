import datajoint as dj
import numpy as np
from os import path, environ
from . import acquisition, reference, behavior, data
import numpy as np
try:
    from oneibl.one import ONE
except:
    pass

mode = environ.get('MODE')

if mode == 'update':
    schema = dj.schema('ibl_ephys')
else:
    schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_ephys')

try:
    one = ONE()
except:
    pass


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
class ProbeInsertion(dj.Imported):
    definition = """
    -> acquisition.Session
    probe_idx:    int    # probe insertion number
    ---
    -> Probe
    """
    key_source = acquisition.Session & behavior.TrialSet & \
        'task_protocol like "%ephysChoiceWorld%"' \
        & (data.FileRecord & 'dataset_name="clusters.probes.npy"') \
        & (data.FileRecord & 'dataset_name="clusters.channels.npy"') \
        & (data.FileRecord & 'dataset_name="clusters.depths.npy"') \
        & (data.FileRecord & 'dataset_name="clusters.amps.npy"') \
        & (data.FileRecord & 'dataset_name="spikes.times.npy"') \
        & (data.FileRecord & 'dataset_name="spikes.clusters.npy"')

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
    defintion = """
    -> ProbeInsertion
    ---
    channel_raw_ids:
    channel_local_coordinates:
    """


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
    -> reference.BrainLocationAcronym   # acronym of the brain location
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
    cluster_revision:               varchar(64)
    cluster_id:                     int
    ---
    cluster_channel:                int             # which channel this cluster is from
    cluster_spike_times:            blob@ephys      # spike times of a particular cluster (seconds)
    cluster_spike_depth:            blob@ephys      # Depth along probe of each spike (µm; computed from waveform center of mass). 0 means deepest site, positive means above this
    cluster_spike_amps:             blob@ephys      # Amplitude of each spike (µV)
    cluster_spike_templates=null:   blob@ephys      # Template ID of each spike (i.e. output of automatic spike sorting prior to manual curation)
    cluster_spike_samples=null:     blob@ephys       # Time of spikes, measured in units of samples in their own electrophysiology binary file.
    cluster_amp:                    float           # Mean amplitude of each cluster (µV)
    cluster_metics=null:            blob            # Quality control metrics at the cluster level
    cluster_waveform=null:          blob@ephys      # Mean unfiltered waveform of spikes in this cluster (but for neuropixels data will have been hardware filtered) nClustersxnSamplesxnChannels
    cluster_template_waveform=null: blob@ephys      # Waveform that was used to detect those spikes in Kilosort, in whitened space (or the most representative such waveform if multiple templates were merged)
    cluster_depth=null:             float           # Depth of mean cluster waveform on probe (µm). 0 means deepest site, positive means above this.
    cluster_peak_to_trough=null:    blob@ephys      # trough to peak time (ms)
    cluster_phy_annotation=null:    tinyint         # 0 = noise, 1 = MUA, 2 = Good, 3 = Unsorted, other number indicates manual quality score (from 4 to 100)
    cluster_phy_id=null:            int             # Original cluster in
    """
    key_source = ProbeInsertion()

    def make(self, key):
        eID = str((acquisition.Session & key).fetch1('session_uuid'))

        clusters_amps_all = one.load(eID, dataset_types=['cluster.amps'])
        clusters_amps = clusters_amps_all[key['probe_idx']]

        clusters_depths_all = one.load(eID, dataset_types=['clusters.depths'])
        clusters_depths = clusters_depths_all[key['probe_idx']]

        clusters_channels = one.load(eID, dataset_types=['clusters.channels'])

        clusters_amps = np.squeeze(clusters_amps)
        clusters_depths = np.squeeze(clusters_depths)
        clusters_peak_channels = np.squeeze(clusters_peak_channels)
        clusters_waveform_duration = np.squeeze(clusters_waveform_duration)

        spikes_amps, \
            spikes_clusters, \
            spikes_depths, \
            spikes_times = \
            one.load(
                eID,
                dataset_types=[
                    'spikes.amps',
                    'spikes.clusters',
                    'spikes.depths',
                    'spikes.times'
                ])
        spikes_amps = np.squeeze(spikes_amps)
        spikes_clusters = np.squeeze(spikes_clusters)
        spikes_depths = np.squeeze(spikes_depths)
        spikes_times = np.squeeze(spikes_times)

        key['cluster_revision'] = 0

        clusters = []
        for icluster, cluster_depth in enumerate(clusters_depths):
            idx = spikes_clusters == icluster
            cluster_amps = list(clusters_amps['Amplitude'])
            clusters.append(
                dict(**key,
                     cluster_id=icluster,
                     cluster_amp=cluster_amps[icluster],
                     cluster_depth=cluster_depth,
                     cluster_waveform_duration=clusters_waveform_duration[icluster],
                     cluster_spike_times=spikes_times[idx],
                     cluster_spike_depth=spikes_depths[idx],
                     cluster_spike_amps=spikes_amps[idx],
                     channel_group_id=0,
                     probe_model_name='Neuropixels phase 3a',
                     channel_id=clusters_peak_channels[icluster]))

        self.insert(clusters)


@schema
class ClusterBrainLocation(dj.Imported):
    definition = """
    -> Cluster
    ---
    -> reference.BrainLocationAcronym    # acronym of the brain location
    cluster_ml_position:      float      # Estimated 3d location of the cell relative to bregma - mediolateral
    cluster_ap_position:      float      # anterior-posterior
    cluster_df_position:      float      # dorsoventral
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
    trial_spike_times=null:   blob@ephys     # spike time for each trial, aligned to go cue time
    """
    key_source = behavior.TrialSet & Cluster()

    def make(self, key):
        trials = behavior.TrialSet.Trial & key
        clusters = Cluster & key

        trial_spks = []
        for icluster in clusters.fetch('KEY'):
            cluster = clusters & icluster
            spike_times = cluster.fetch1('cluster_spike_times')
            for itrial in trials.fetch('KEY'):
                trial = trials & itrial
                trial_spk = dict(
                    **itrial,
                    cluster_id=icluster['cluster_id'],
                    cluster_revision=icluster['cluster_revision'],
                    probe_idx=icluster['probe_idx']
                )
                trial_start, trial_end, \
                    go_cue, stim_on, response, feedback = trial.fetch1(
                        'trial_start_time', 'trial_end_time',
                        'trial_go_cue_time', 'trial_stim_on_time',
                        'trial_response_time', 'trial_feedback_time')
                f = np.logical_and(spike_times < trial_end,
                                   spike_times > trial_start)
                if not np.any(f):
                    continue

                events = Event.fetch('event')
                for event in events:
                    if event == 'go cue':
                        trial_spk['trial_spike_times'] = \
                            spike_times[f] - go_cue
                    elif event == 'stim on':
                        trial_spk['trial_spike_times'] = \
                            spike_times[f] - stim_on
                    elif event == 'response':
                        trial_spk['trial_spike_times'] = \
                            spike_times[f] - (response + trial_start)
                    elif event == 'feedback':
                        trial_spk['trial_spike_times'] = \
                            spike_times[f] - feedback
                    trial_spk['event'] = event
                    trial_spks.append(trial_spk)

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
