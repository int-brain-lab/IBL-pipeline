import datajoint as dj
from . import acquisition
from . import reference

schema = dj.schema('ibl_ephys')

@schema
class Ephys(dj.Imported):
    definition = """
    -> acquisition.Session
    ---
    ephys_raw:              longblob     # Raw ephys: array of size nSamples * nChannels. Channels from all probes are included. NOTE: this is huge, and hardly even used. To allow people to load it, we need to add slice capabilities to ONE
    ephys_timestamps:       longblob     # Timestamps for raw ephys timeseries (seconds)
    ephys_start_time:       float        # (seconds)
    ephys_stop_time:       float        # (seconds)
    ephys_duration:         float        # (seconds)
    ephys_sampling_rate:    float        # samples per second
    """

@schema
class ProbeModel(dj.Lookup):
    definition = """
    # Description of a particular model of probe.
    probe_model_name: varchar(128)      # String naming probe model, from probe.description
    ---
    channel_counts: smallint            # number of channels in the probe
    """
    class Channel(dj.Part):
        definition = """
        -> master
        channel_id:         smallint     # id of a channel on the probe
        ---
        channel_x_pos:  float   # x position relative to the tip of the probe (um)
        channel_y_pos:  float   # y position relative to the tip of the probe (um)
        """

@schema
class ProbeSet(dj.Imported):
    definition = """
    -> Ephys
    """
    class Probe(dj.Part):
        definition = """
        -> master
        probe_idx:          tinyint     # probe number in this array
        ---
        -> ProbeModel
        probe_set_raw_filename: varchar(256)      # Name of the raw data file this probe was recorded in
        entry_point_rl:    float
        entry_point_ap:    float
        vertical_angle:    float
        horizontal_angle:  float
        axial_angle:       float
        distance_advanced: float
        """

@schema
class Channel(dj.Imported):
    definition = """
    -> ProbeSet.Probe
    -> ProbeModel.Channel
    ---
    channel_index:          smallint    # position within the data array of recording
    channel_ccf_ap:         float       # anterior posterior CCF coordinate (um)
    channel_ccf_dv:         float       # dorsal ventral CCF coordinate (um)
    channel_ccf_lr:         float       # left right CCF coordinate (um)
    -> reference.BrainLocationAcronym   # acronym of the brain location
    channel_raw_row:        smallint     # Each channel's row in its home file (look up via probes.rawFileName), counting from zero. Note some rows don't have a channel, for example if they were sync pulses
    """
    key_source = Ephys

@schema
class ClusterGroup(dj.Imported):
    definition = """
    -> ProbeSet
    ---
    """
    class Cluster(dj.Part):
        definition = """
        -> master
        cluster_id: smallint
        ---
        cluster_mean_waveform:      longblob      # Mean unfiltered waveform of spikes in this cluster (but for neuropixels data will have been hardware filtered): nClusters*nSamples*nChannels
        cluster_template_waveform:  longblob      # Waveform that was used to detect those spikes in Kilosort, in whitened space (or the most representative such waveform if multiple templates were merged)
        cluster_depth :             float         # Depth of mean cluster waveform on probe (µm). 0 means deepest site, positive means above this.
        cluster_waveform_duration:  float         # trough to peak time (ms)
        cluster_amp:                float         # Mean amplitude of each cluster (µV)
        -> ProbeSet.Probe
        (cluster_peak_channel)  -> Channel(channel_id)
        cluster_phy_annotation:     tinyint       # 0 = noise, 1 = MUA, 2 = Good, 3 = Unsorted, other number indicates manual quality score (from 4 to 100)
        """

@schema
class ClusterSpikes(dj.Imported):
    definition = """
    -> ClusterGroup.Cluster
    ---
    cluster_spike_times:    longblob        # spike times of a particular cluster (seconds)
    cluster_spike_depth:    longblob        # Depth along probe of each spike (µm; computed from waveform center of mass). 0 means deepest site, positive means above this
    cluster_spike_amps:     longblob        # Amplitude of each spike (µV)
    """
    key_source = Ephys

@schema
class LFP(dj.Imported):
    definition = """
    -> ProbeSet
    ---
    lfp_raw:              longblob     # LFP: array of size nSamples * nChannels. Channels from all probes are included
    lfp_timestamps:       longblob     # Timestamps for LFP timeseries in seconds
    lfp_start_time:       float        # (seconds)
    lfp_end_time:         float        # (seconds)
    lfp_duration:         float        # (seconds)
    lfp_sampling_rate:    float        # samples per second
    """
