CREATE TABLE `ibl_reference`.`#coordinate_system` (
  `coordinate_system_name` varchar(64) NOT NULL,
  `coordinate_system_uuid` binary(16) NOT NULL COMMENT ':uuid:',
  `coordinate_system_description` varchar(2048) DEFAULT NULL,
  PRIMARY KEY (`coordinate_system_name`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;


CREATE TABLE `ibl_reference`.`#ontology` (
  `ontology` varchar(32) NOT NULL,
  PRIMARY KEY (`ontology`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;


CREATE TABLE `ibl_reference`.`#brain_region` (
  `ontology` varchar(32) NOT NULL,
  `acronym` varchar(32) CHARACTER SET latin1 COLLATE latin1_general_cs NOT NULL,
  `brain_region_name` varchar(128) NOT NULL,
  `brain_region_pk` int(11) NOT NULL,
  `brain_region_level` tinyint(4) DEFAULT NULL,
  `graph_order` smallint(5) unsigned DEFAULT NULL,
  `parent` int(11) DEFAULT NULL,
  PRIMARY KEY (`ontology`,`acronym`),
  CONSTRAINT `#brain_region_ibfk_1` FOREIGN KEY (`ontology`) REFERENCES `#ontology` (`ontology`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;


CREATE TABLE `ibl_reference`.`_parent_region` (
  `ontology` varchar(32) NOT NULL,
  `acronym` varchar(32) CHARACTER SET latin1 COLLATE latin1_general_cs NOT NULL,
  `parent` varchar(32) CHARACTER SET latin1 COLLATE latin1_general_cs NOT NULL,
  PRIMARY KEY (`ontology`,`acronym`),
  KEY `ontology` (`ontology`,`parent`),
  CONSTRAINT `_parent_region_ibfk_1` FOREIGN KEY (`ontology`, `acronym`) REFERENCES `ibl_reference`.`#brain_region` (`ontology`, `acronym`) ON UPDATE CASCADE,
  CONSTRAINT `_parent_region_ibfk_2` FOREIGN KEY (`ontology`, `parent`) REFERENCES `ibl_reference`.`#brain_region` (`ontology`, `acronym`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;


CREATE TABLE `ibl_histology`.`#provenance` (
  `provenance` tinyint(3) unsigned NOT NULL COMMENT 'provenance code',
  `provenance_description` varchar(128) NOT NULL COMMENT 'type of trajectory',
  PRIMARY KEY (`provenance`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COMMENT='Method to estimate the probe trajectory, including Ephys aligned histology track, Histology track, Micro-manipulator, and Planned';


CREATE TABLE `ibl_histology`.`_probe_trajectory` (
  `subject_uuid` binary(16) NOT NULL COMMENT ':uuid:',
  `session_start_time` datetime NOT NULL COMMENT 'start time',
  `probe_idx` int(11) NOT NULL COMMENT 'probe insertion number (0 corresponds to probe00, 1 corresponds to probe01)',
  `coordinate_system_name` varchar(64) DEFAULT NULL,
  `x` float NOT NULL COMMENT '(um) medio-lateral coordinate relative to Bregma, left negative',
  `y` float NOT NULL COMMENT '(um) antero-posterior coordinate relative to Bregma, back negative',
  `z` float NOT NULL COMMENT '(um) dorso-ventral coordinate relative to Bregma, ventral negative',
  `phi` float NOT NULL COMMENT '(degrees)[-180 180] azimuth',
  `theta` float NOT NULL COMMENT '(degrees)[0 180] polar angle',
  `depth` float NOT NULL COMMENT '(um) insertion depth',
  `roll` float DEFAULT NULL COMMENT '(degrees) roll angle of the probe',
  `trajectory_ts` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `probe_trajectory_uuid` binary(16) DEFAULT NULL COMMENT ':uuid:',
  PRIMARY KEY (`subject_uuid`,`session_start_time`,`probe_idx`),
  KEY `coordinate_system_name` (`coordinate_system_name`),
  CONSTRAINT `_probe_trajectory_ibfk_1` FOREIGN KEY (`subject_uuid`, `session_start_time`, `probe_idx`) REFERENCES `ibl_ephys`.`_probe_insertion` (`subject_uuid`, `session_start_time`, `probe_idx`) ON UPDATE CASCADE,
  CONSTRAINT `_probe_trajectory_ibfk_2` FOREIGN KEY (`coordinate_system_name`) REFERENCES `ibl_reference`.`#coordinate_system` (`coordinate_system_name`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COMMENT='Probe Trajectory resolved by 3 users, ingested from ALF dataset probes.trajectory';


CREATE TABLE `ibl_histology`.`_channel_brain_location` (
  `subject_uuid` binary(16) NOT NULL COMMENT ':uuid:',
  `session_start_time` datetime NOT NULL COMMENT 'start time',
  `probe_idx` int(11) NOT NULL COMMENT 'probe insertion number (0 corresponds to probe00, 1 corresponds to probe01)',
  `channel_idx` int(11) NOT NULL,
  `channel_ml` decimal(6,1) NOT NULL,
  `channel_ap` decimal(6,1) NOT NULL,
  `channel_dv` decimal(6,1) NOT NULL,
  `ontology` varchar(32) NOT NULL,
  `acronym` varchar(32) CHARACTER SET latin1 COLLATE latin1_general_cs NOT NULL,
  PRIMARY KEY (`subject_uuid`,`session_start_time`,`probe_idx`,`channel_idx`),
  KEY `ontology` (`ontology`,`acronym`),
  CONSTRAINT `_channel_brain_location_ibfk_1` FOREIGN KEY (`subject_uuid`, `session_start_time`, `probe_idx`) REFERENCES `ibl_histoloy`.`_probe_trajectory` (`subject_uuid`, `session_start_time`, `probe_idx`) ON UPDATE CASCADE,
  CONSTRAINT `_channel_brain_location_ibfk_2` FOREIGN KEY (`ontology`, `acronym`) REFERENCES `ibl_reference`.`#brain_region` (`ontology`, `acronym`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;


CREATE TABLE `ibl_histology`.`_cluster_brain_region` (
  `subject_uuid` binary(16) NOT NULL COMMENT ':uuid:',
  `session_start_time` datetime NOT NULL COMMENT 'start time',
  `probe_idx` int(11) NOT NULL COMMENT 'probe insertion number (0 corresponds to probe00, 1 corresponds to probe01)',
  `cluster_id` int(11) NOT NULL,
  `cluster_ml` decimal(6,1) NOT NULL,
  `cluster_ap` decimal(6,1) NOT NULL,
  `cluster_dv` decimal(6,1) NOT NULL,
  `ontology` varchar(32) NOT NULL,
  `acronym` varchar(32) CHARACTER SET latin1 COLLATE latin1_general_cs NOT NULL,
  PRIMARY KEY (`subject_uuid`,`session_start_time`,`probe_idx`,`cluster_id`),
  KEY `subject_uuid` (`subject_uuid`,`session_start_time`,`probe_idx`),
  KEY `ontology` (`ontology`,`acronym`),
  CONSTRAINT `_cluster_brain_region_ibfk_1` FOREIGN KEY (`subject_uuid`, `session_start_time`, `probe_idx`, `cluster_id`) REFERENCES `ibl_ephys`.`_default_cluster` (`subject_uuid`, `session_start_time`, `probe_idx`, `cluster_id`) ON UPDATE CASCADE,
  CONSTRAINT `_cluster_brain_region_ibfk_2` FOREIGN KEY (`subject_uuid`, `session_start_time`, `probe_idx`) REFERENCES `ibl_histology`.`_probe_trajectory` (`subject_uuid`, `session_start_time`, `probe_idx`) ON UPDATE CASCADE,
  CONSTRAINT `_cluster_brain_region_temp_ibfk_3` FOREIGN KEY (`ontology`, `acronym`) REFERENCES `ibl_reference`.`#brain_region` (`ontology`, `acronym`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COMMENT='Brain region assignment to each cluster';



CREATE TABLE `ibl_histology`.`__probe_brain_region` (
  `subject_uuid` binary(16) NOT NULL COMMENT ':uuid:',
  `session_start_time` datetime NOT NULL COMMENT 'start time',
  `probe_idx` int(11) NOT NULL COMMENT 'probe insertion number (0 corresponds to probe00, 1 corresponds to probe01)',
  `ontology` varchar(32) NOT NULL,
 `acronym` varchar(32) CHARACTER SET latin1 COLLATE latin1_general_cs NOT NULL,
  PRIMARY KEY (`subject_uuid`,`session_start_time`,`probe_idx`,`ontology`,`acronym`),
  KEY `ontology` (`ontology`,`acronym`),
  CONSTRAINT `__probe_brain_region_ibfk_1` FOREIGN KEY (`subject_uuid`, `session_start_time`, `probe_idx`) REFERENCES `ibl_histology`.`_probe_trajectory` (`subject_uuid`, `session_start_time`, `probe_idx`) ON UPDATE CASCADE,
  CONSTRAINT `__probe_brain_region_ibfk_2` FOREIGN KEY (`ontology`, `acronym`) REFERENCES  `ibl_reference`.`#brain_region` (`ontology`, `acronym`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COMMENT='Brain regions assignment to each probe insertion';


CREATE TABLE `ibl_histology`.`__depth_brain_region` (
  `subject_uuid` binary(16) NOT NULL COMMENT ':uuid:',
  `session_start_time` datetime NOT NULL COMMENT 'start time',
  `probe_idx` int(11) NOT NULL COMMENT 'probe insertion number (0 corresponds to probe00, 1 corresponds to probe01)',
  `region_boundaries` blob NOT NULL,
  `region_label` blob NOT NULL,
  `region_color` blob NOT NULL,
  `region_id` blob NOT NULL,
  PRIMARY KEY (`subject_uuid`,`session_start_time`,`probe_idx`),
  CONSTRAINT `__depth_brain_region_ibfk_1` FOREIGN KEY (`subject_uuid`, `session_start_time`, `probe_idx`) REFERENCES `ibl_histology`.`_probe_trajectory` (`subject_uuid`, `session_start_time`, `probe_idx`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COMMENT='For each ProbeTrajectory, assign depth boundaries relative to the probe tip to each brain region covered by the trajectory';
