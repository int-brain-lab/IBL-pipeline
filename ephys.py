import datajoint as dj
import acquisition

schema = dj.schema('ephys')

@schema
class Eye(dj.Imported):
    definition = """
    -> acquisition.Session
    ---
    eye_timestamps:     longblob # Timestamps for pupil tracking timeseries: 2 column array giving sample number and time in seconds
    eye_raw:            longblob # Raw movie data for pupil tracking
    eye_area:           longblob # Area of pupil (pixels^2)
    eye_xy_pos:         longblob # matrix with 2 columns giving x and y position of pupil (in pixels)
    eye_blink:          boolean  # Boolean array saying whether eye was blinking in each frame
    """

@schema
class Wheel(dj.Imported):
    definition = """
    -> acquisition.Session
    ---
    wheel_position:     longblob  # Absolute position of wheel (cm)
    wheel_velocity:     longblob  # Signed velocity of wheel (cm/s) positive = CW
    wheel_timestamp:    longblob  # Timestamps for wheel timeseries
    """
    class WheelMove(dj.Part):
        definition = """
        -> master
        wheel_move_id:          int     # identifier of a wheel movement
        ---
        wheel_move_interval:    blob    # 2 element array with onset and offset times of detected wheel movements in seconds
        wheel_move_type:        enum("CW", "CCW", "Flinch", "Other")  # string array containing classified type of movement
        """
        

@schema
class SparseNoise(dj.Imported):
    definition = """
    -> acquisition.Session
    ---
    sparsenoise_xypos:  longblob				# 2 column array giving x and y coordiates on screen of sparse noise stimulus squares (WHAT UNIT?)
    sparsenoise_times:  longblob				# times of those stimulus squares appeared in universal seconds
    """


@schema
class ExtraRewards(dj.Imported):
    definition = """
    -> acquisition.Session
    ---
    extrarewards_times: longblob 			# times of extra rewards
    """

@schema
class SpontaneousTimes(dj.Imported):
    definition = """
    -> acquisition.Session
    ---
    spontaneous_intervals: longblob 		# times when no other protocol was going on for at least 30 sec or so
    """

@schema
class Lick(dj.Imported):
    definition = """
    -> acquisition.Session
    ---
    lick_times:             longblob  # Times of licks
    lick_piezo_raw:         longblob  # Raw lick trace (1 column array; volts)
    lick_piezo_timestamps:  longblob  # Timestamps for lick trace timeseries: 2 column array giving sample number and time in seconds
    """

@schema
class TrialSet(dj.Imported):
    definition = """
    -> acquisition.Session
    ---
    repitition_num: int     	# the repetition number of the trial, i.e. how many trials have been repeated on this side (counting from 1)
    
    """
    class Trial(dj.Part):
        definition = """
        -> master
        trial_idx:              int           # trial identification number
        ---
        trial_interval:         blob          # 2 element array giving each trial start (i.e. beginning of quiescent period) and stop (i.e. end of iti) times of trials in universal seconds
        trial_included:         boolean	    # boolean suggesting which trials to include in analysis, chosen at experimenter discretion, e.g. by excluding the block of incorrect trials at the end of the session when the mouse has stopped
        trial_go_cue_time:      float         # Time of go cue in choiceworld - in absolute seconds, rather than relative to trial onset
        trial_response_time:    float         # Time of "response" in choiceworld- in absolute seconds, rather than relative to trial onset. This is when one of the three possible choices is registered in software, will not be the same as when the mouse's movement to generate that response begins. 
        trial_choice:           tinyint       # which choice was made in choiceworld: -1 (turn CCW), +1 (turn CW), or 0 (nogo)
        trial_stim_on_time:     float         # Time of stimulus in choiceworld - in absolute seconds, rather than relative to trial onset 
        trial_stim_position:    enum("Left", "Right")	 # position of the stimulus
        trial_stim_contrast:    float         # contrast of the stimulus
        trial_feedback_time:    float         # Time of feedback delivery (reward or not) in choiceworld - in absolute seconds, rather than relative to trial onset 
        trial_feedback_type:    tinyint       # whether feedback is positive or negative in choiceworld (-1 for negative, +1 for positive)
        """

@schema
class PassiveTrial(dj.Imported):
    # it is possible to be a part table of TrialSet if the repitition number could be inferred from the data,
    # Are passive trials interleaved with real trials?
    definition = """
    -> acquisition.Session
    ---
    passive_trial_included:     boolean		# suggesting whether this trial to include in analysis, chosen at experimenter discretion, e.g. by excluding the block of incorrect trials at the end of the session when the mouse has stopped
    passive_trial_stim_on_time: float	    # Time of stimuli in choiceworld - in absolute seconds, rather than relative to trial onset 
    passive_trial_stim_position:    enum("Left", "Right")	 # position of the stimulus
    passive_trial_contrast:         float                    # contrast of the stimulus				    
    passive_valve_click_time:       float 		             # Time of valve opening during passive trial presentation
    passive_beep_time:              float         		     # Time of the beep, equivilent to the go cue during the choice world task
    passive_white_noise_time:       float		             # Time of white noise bursts, equivilent to the negative feedback sound during the choice world task
    passive_noise_interval:         blob   	                 # 2 element array giving each passive noise trial's start (i.e. beginning of quiescent period) and stop (i.e. end of iti) times of trials in universal seconds
    """

@schema
class Ephys(dj.Imported):
    definition = """
    -> acquisition.Session
    ---
    ephys_raw:              longblob     # Raw ephys: array of size nSamples * nChannels. Channels from all probes are included. NOTE: this is huge, and hardly even used. To allow people to load it, we need to add slice capabilities to ONE
    ephys_sample_id:        longblob
    ephys_timestamps:       longblob     # Timestamps for raw ephys timeseries in seconds
    """

@schema
class LFP(dj.Imported):
    definition = """
    -> Ephys
    ---
    lfp_raw:        longblob   # LFP: array of size nSamples * nChannels. Channels from all probes are included
    lfp_sample_id:  longblob 
    lfp_timestamps: longblob   # Timestamps for LFP timeseries in seconds
    """


@schema
class ProbeModel(dj.Lookup):
    definition = """
    probe_model_name: varchar(128)     # String naming probe model
    ---
    probes_site_positions: longblob     # json file: one entry per probe, each containing nSites by 2 array of site positions in local  coordinates. Probe tip is at the origin. Note that there is an entry for all sites, even if they were not recorded in this experiment. This allows you to use the same probes.sitePositions file for all recordings with a single probe model, even if different channel subsets are recorded on different experiments
    """

    
@schema
class ProbeArray(dj.Imported):
    definition = """
    -> Ephys
    ---
    -> ProbeModel
    probe_array_raw_filename: varchar(256)      # Name of the raw data file this probe was recorded in
    """
    class Probe(dj.Part):
        definition = """
        -> master
        probe_idx:          tinyint     # probe number in this array
        ---
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
    -> ProbeArray.Probe
    channel_idx:    tinyint    # channel identifier
    ---
    channel_site:           tinyint    # integer saying which site on that probe the channel corresponds to (counting from zero). Note that not all sites need to be recorded - so there can be "gaps" in this file
    channel_brain_location: blob       # ccf_ap, ccf_dv, ccf_lr, ccf_acronym
    channel_raw_row:        tinyint    # Each channel's row in its home file (look up via probes.rawFileName), counting from zero. Note some rows don't have a channel, for example if they were sync pulses
    channel_site_position:  blob       # 2 element array site positions of the channel in local  coordinates. Probe tip is at the origin. 
    """

@schema
class ClusterGroup(dj.Imported):
    definition = """
    -> Ephys
    ---
    cluster_phy_annotation: tinyint       # 0 = noise, 1 = MUA, 2 = Good, 3 = Unsorted, other number indicates manual quality score (from 4 to 100)
    """
    class Cluster(dj.Part):
        definition = """
        -> master
        cluster_idx: tinyint #
        ---
        cluster_mean_waveform:      longblob      # Mean unfiltered waveform of spikes in this cluster (but for neuropixels data will have been hardware filtered): nClusters*nSamples*nChannels
        cluster_template_waveform:  longblob      # Waveform that was used to detect those spikes in Kilosort, in whitened space (or the most representative such waveform if multiple templates were merged)
        cluster_depth :             float         # Depth of mean cluster waveform on probe (µm). 0 means deepest site, positive means above this.
        cluster_waveform_duration:  float         # trough to peak time, ms
        cluster_amp:                float         # Mean amplitude of each cluster (µV)
        -> ProbeArray.Probe
        (cluster_peak_channel)  -> Channel(channel_idx)
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
