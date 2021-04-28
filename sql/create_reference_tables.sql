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
  CONSTRAINT `#brain_region_ibfk_1` FOREIGN KEY (`ontology`) REFERENCES `ibl_reference`.`#ontology` (`ontology`) ON UPDATE CASCADE
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
