import datajoint as dj
from . import reference
import os

mode = os.environ.get('MODE')

if mode == 'update':
    schema = dj.schema('ibl_subject')
else:
    schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_subject')


@schema
class Species(dj.Lookup):
    # <class 'subjects.models.Species'>
    definition = """
    binomial:			    varchar(255)	# binomial
    ---
    species_uuid:           uuid
    species_nickname:		varchar(255)	# nick name
    species_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class Source(dj.Lookup):
    # <class 'subjects.models.Source'>
    definition = """
    source_name:				    varchar(255)	# name of source
    ---
    source_uuid:                    uuid
    source_description=null:	    varchar(255)	# description
    source_ts=CURRENT_TIMESTAMP:    timestamp
    """


@schema
class Strain(dj.Lookup):
    # <class 'subjects.models.Strain'>
    definition = """
    strain_name:		            varchar(255)	# strain name
    ---
    strain_uuid:                    uuid
    strain_description=null:        varchar(255)	# description
    strain_ts=CURRENT_TIMESTAMP:    timestamp
    """


@schema
class Sequence(dj.Lookup):
    # <class 'subjects.models.Sequence'>
    definition = """
    sequence_name:		            varchar(255)	# informal name
    ---
    sequence_uuid:                  uuid
    base_pairs=null:	            varchar(1024)	# base pairs
    sequence_description=null:	    varchar(255)	# description
    sequence_ts=CURRENT_TIMESTAMP:  timestamp
    """


@schema
class Allele(dj.Lookup):
    # <class 'subjects.models.Allele'>
    definition = """
    allele_name:			        varchar(255)    # informal name
    ---
    allele_uuid:                    uuid
    standard_name=null:		        varchar(255)	# standard name
    -> [nullable] Source
    allele_source=null:             varchar(255)    # source of the allele
    source_identifier=null:         varchar(255)    # id inside the line provider
    source_url=null:                varchar(255)    # link to the line information
    expression_data_url=null:       varchar(255)    # link to the expression pattern from Allen institute brain atlas
    allele_ts=CURRENT_TIMESTAMP:    timestamp
    """


@schema
class AlleleSequence(dj.Lookup):
    definition = """
    -> Allele
    -> Sequence
    ---
    allelesequence_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class Line(dj.Lookup):
    # <class 'subjects.models.Line'>
    definition = """
    line_name:				    varchar(255)	# name
    ---
    -> Species
    -> [nullable] Strain
    line_uuid:                  uuid
    line_description=null:	    varchar(2048)	# description
    target_phenotype=null:	    varchar(255)	# target phenotype
    line_nickname:		        varchar(255)	# nickname
    is_active:				    boolean		    # is active
    line_ts=CURRENT_TIMESTAMP:  timestamp
    """


@schema
class LineAllele(dj.Lookup):
    definition = """
    -> Line
    -> Allele
    ---
    lineallele_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class Subject(dj.Manual):
    # <class 'subjects.models.Subject'>
    definition = """
    subject_uuid:                   uuid
    ---
    subject_nickname:		        varchar(255)		# nickname
    sex:			                enum("M", "F", "U")	# sex
    subject_birth_date=null:	    date			    # birth date
    ear_mark=null:			        varchar(255)		# ear mark
    -> [nullable] Strain.proj(subject_strain="strain_name")
    -> [nullable] Line.proj(subject_line="line_name")
    -> [nullable] Source.proj(subject_source='source_name')
    protocol_number:                tinyint         	# protocol number
    subject_description=null:       varchar(1024)
    subject_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class SubjectCullMethod(dj.Manual):
    definition = """
    -> Subject
    ---
    cull_method:    varchar(255)
    cull_method_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class BreedingPair(dj.Manual):
    # <class 'subjects.models.BreedingPair'>
    definition = """
    bp_name:			    varchar(255)		    # name
    ---
    -> [nullable] Line.proj(bp_line='line_name')
    bp_uuid:                uuid
    bp_description=null:	varchar(2048)		    # description
    bp_start_date=null:	    date		            # start date
    bp_end_date=null:		date			        # end date
    -> [nullable] Subject.proj(father='subject_uuid')    # father
    -> [nullable] Subject.proj(mother1='subject_uuid')   # mother1
    -> [nullable] Subject.proj(mother2='subject_uuid')	 # mother2
    breedingpair_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class Litter(dj.Manual):
    # <class 'subjects.models.Litter'>
    definition = """
    litter_name:                    varchar(255)
    ---
    -> [nullable] BreedingPair
    -> [nullable] Line.proj(litter_line='line_name')
    litter_uuid:			        uuid	    # litter uuid
    litter_descriptive_name=null:	varchar(255)	# descriptive name
    litter_description=null:	    varchar(255)	# description
    litter_birth_date=null:			date		    # birth date
    litter_ts=CURRENT_TIMESTAMP:    timestamp
    """


@schema
class LitterSubject(dj.Manual):
    # litter subject membership table
    definition = """
    -> Subject
    ---
    -> Litter
    littersubject_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class SubjectProject(dj.Manual):
    definition = """
    -> Subject
    -> reference.Project.proj(subject_project='project_name')
    ---
    subjectproject_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class SubjectUser(dj.Manual):
    definition = """
    -> Subject
    ---
    -> reference.LabMember.proj(responsible_user='user_name')
    subjectuser_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class SubjectLab(dj.Manual):
    definition = """
    -> Subject
    ---
    -> reference.Lab
    subjectlab_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class Caging(dj.Manual):
    # <class 'subjects.models.Subject'>
    definition = """
    -> Subject
    cage_name:              varchar(255)        # cage name
    ---
    caging_time=null:	    datetime			# cage
    caging_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class UserHistory(dj.Manual):
    definition = """
    -> Subject
    -> reference.LabMember
    ---
    user_change_time=null:              datetime      # time when changed to this user
    userhistory_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class Weaning(dj.Manual):
    # <class 'subjects.models.Subject'>
    definition = """
    -> Subject
    ---
    wean_date:			            date			# wean date
    weaning_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class Food(dj.Lookup):
    definition = """
    food_name:              varchar(255)
    ---
    food_uuid:              uuid
    food_description='':    varchar(255)
    food_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class CageType(dj.Lookup):
    definition = """
    cage_type_name:                     varchar(255)
    ---
    cage_type_uuid:                     uuid
    cage_type_description='':           varchar(255)
    cage_type_ts=CURRENT_TIMESTAMP:     timestamp
    """


@schema
class Enrichment(dj.Lookup):
    definition = """
    enrichment_name:                    varchar(255)
    ---
    enrichment_uuid:                    uuid
    enrichment_description='':          varchar(255)
    enrichment_ts=CURRENT_TIMESTAMP:    timestamp
    """


@schema
class Housing(dj.Manual):
    definition = """
    cage_name:                      varchar(255)
    ---
    housing_uuid:                   uuid
    -> [nullable] Food
    -> [nullable] CageType
    -> [nullable] Enrichment
    cage_cleaning_frequency=null:   int
    light_cycle=null:               int
    housing_description='':         varchar(255)
    housing_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class SubjectHousing(dj.Manual):
    definition = """
    -> Subject
    -> Housing
    ---
    subject_housing_uuid:     uuid
    housing_start_time:       datetime
    housing_end_time=null:    datetime
    subject_housing_ts=CURRENT_TIMESTAMP    :  timestamp
    """


@schema
class GenotypeTest(dj.Manual):
    # <class 'subjects.models.Subject'>
    # <class 'subjects.models.Zygosity'>
    # genotype = models.ManyToManyField('Allele', through='Zygosity')
    definition = """
    -> Subject
    -> Sequence
    genotype_test_uuid:		            uuid     # genotype test id
    ---
    test_result:		                enum("Present", "Absent")		# test result
    genotypetest_ts=CURRENT_TIMESTAMP:  timestamp
    """


@schema
class Zygosity(dj.Manual):
    # <class 'subjects.models.Subject'>
    # <class 'subjects.models.Zygosity'>
    # genotype = models.ManyToManyField('Allele', through='Zygosity')
    definition = """
    -> Subject
    -> Allele
    ---
    zygosity_uuid:                  uuid
    zygosity:		                enum("Present", "Absent", "Homozygous", "Heterozygous")  # zygosity
    zygosity_ts=CURRENT_TIMESTAMP:  timestamp
    """


@schema
class Implant(dj.Manual):
    # <class 'subjects.models.Subject'>
    definition = """
    -> Subject
    ---
    implant_weight:		            float			    # implant weight
    protocol_number:                tinyint		        # protocol number
    adverse_effects=null:           varchar(2048)		# adverse effects
    (actual_severity)		-> [nullable] reference.Severity   # actual severity
    implant_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class Death(dj.Manual):
    # <class 'subjects.models.Subject'>
    definition = """
    -> Subject
    ---
    death_date:                  date       # death date
    death_ts=CURRENT_TIMESTAMP:  timestamp
    """
