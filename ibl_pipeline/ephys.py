import datajoint as dj
import numpy as np
from os import path
from . import acquisition
from . import reference
import numpy as np

schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_ephys')


@schema
class Ephys(dj.Imported):
    definition = """
    -> acquisition.Session
    ---
    ephys_raw_dir:              varchar(256) # Path of Raw ephys file: array of size nSamples * nChannels. Channels from all probes are included. NOTE: this is huge, and hardly even used. To allow people to load it, we need to add slice capabilities to ONE
    ephys_timestamps=null:      longblob     # Timestamps for raw ephys timeseries (seconds)
    ephys_start_time=null:      float        # (seconds)
    ephys_stop_time=null:       float        # (seconds)
    ephys_duration=null:        float        # (seconds)
    ephys_sampling_rate=null:   float        # samples per second
    """

    def make(self, key):
        datapath = path.join(path.sep,'data', '{subject_id}-{session_start_time}'.format(**key)).replace(':', '_')
        ephys_raw_dir = path.join(datapath,'ephys.raw.npy')
        ephys_timestamps = np.load(path.join(datapath,'ephys.timestamps.npy'))[:, 1]

        key['ephys_raw_dir'] = ephys_raw_dir
        key['ephys_timestamps'] = ephys_timestamps
        key['ephys_start_time'] = ephys_timestamps[0]
        key['ephys_stop_time'] = ephys_timestamps[-1]
        key['ephys_duration'] = key['ephys_stop_time'] - key['ephys_start_time']
        key['ephys_sampling_rate'] = 1 / np.median(np.diff(ephys_timestamps))

        self.insert1(key)


@schema
class Probe(dj.Lookup):
    definition = """
    # Description of a particular model of probe.
    probe_model_name: varchar(128)      # String naming probe model, from probe.description
    ---
    channel_counts: smallint            # number of channels in the probe
    """

    class Channel(dj.Part):
        definition = """
        # positional information about every channel on this probe.
        -> master
        channel_id:     smallint    # id of a channel on the probe
        ---
        channel_x_pos=null:  float   # x position relative to the tip of the probe (um)
        channel_y_pos=null:  float   # y position relative to the tip of the probe (um)
        channel_z_pos=0:     float   # z position
        """


@schema
class ChannelGroup(dj.Lookup):
    definition = """
    # group of channel on a particular probe model for clustering analyses
    -> Probe
    channel_group_id:         smallint     # id of a channel on the probe
    ---
    channel_group_name=null:  varchar(32)  # user friendly name
    """

    class Channel(dj.Part):
        definition = """
        # membership table for channel group and channel
        -> master
        -> Probe.Channel
        """


@schema
class ProbeInsertion(dj.Imported):
    definition = """
    -> Ephys
    probe_idx:    int    # probe insertion number
    ---
    -> Probe
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
    -> ChannelGroup.Channel
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
class ClusterGroup(dj.Imported):
    definition = """
    -> ProbeInsertion
    cluster_revision:               varchar(64)
    """

    def make(self, key):
        eID = str((acquisition.Session & key).fetch1('session_uuid'))
        clusters_amps, \
            clusters_depths, \
            clusters_peak_channels, \
            clusters_waveform_duration = \
            ONE().load(
                eID,
                datasets=[
                    'clusters.amps',
                    'clusters.depths',
                    'clusters.peakChannel',
                    'clusters.waveformDuration'
                ])

        for icluster, cluster_amps in enumerate(clusters_amps):
            cluster = cluster


    class Cluster(dj.Part):
        definition = """
        -> master
        cluster_id:                     smallint
        ---
        -> ChannelGroup.Channel                     # peak channel for the cluster
        cluster_mean_waveform=null:     longblob    # Mean unfiltered waveform of spikes in this cluster (but for neuropixels data will have been hardware filtered): nClusters*nSamples*nChannels
        cluster_template_waveform=null: longblob    # Waveform that was used to detect those spikes in Kilosort, in whitened space (or the most representative such waveform if multiple templates were merged)
        cluster_depth:                  float       # Depth of mean cluster waveform on probe (µm). 0 means deepest site, positive means above this.
        cluster_waveform_duration:      float       # trough to peak time (ms)
        cluster_amp:                    float       # Mean amplitude of each cluster (µV)
        cluster_phy_annotation:         tinyint     # 0 = noise, 1 = MUA, 2 = Good, 3 = Unsorted, other number indicates manual quality score (from 4 to 100)
        cluster_spike_times:            longblob    # spike times of a particular cluster (seconds)
        cluster_spike_depth:            longblob    # Depth along probe of each spike (µm; computed from waveform center of mass). 0 means deepest site, positive means above this
        cluster_spike_amps:             longblob    # Amplitude of each spike (µV)
        """


@schema
class LFP(dj.Imported):
    definition = """
    -> ProbeInsertion
    ---
    lfp_timestamps:       longblob     # Timestamps for LFP timeseries in seconds
    lfp_start_time:       float        # (seconds)
    lfp_end_time:         float        # (seconds)
    lfp_duration:         float        # (seconds)
    lfp_sampling_rate:    float        # samples per second
    """

    class Channel(dj.Part):
        definition = """
        -> master
        -> ChannelGroup.Channel
        ---
        lfp: longblob           # recorded lfp on this channel
        """
