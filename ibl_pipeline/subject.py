import datajoint as dj
from . import reference

schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_dj_subject')


# Actions:
# Refactor questions w/r/t old objs:
#
# - <class 'actions.models.ProcedureType'>: SKIPPED
#   What does this do aside from provide a description?
#   should be inclued for e.g. steps, etc?
# - <class 'actions.models.BaseAction'>: SKIPPED
#   Other than key info, does this provide anything other than 'narritive'?
#   if so, needed?


@schema
class Species(dj.Lookup):
    # <class 'subjects.models.Species'>
    definition = """
    binomial:			    varchar(255)	# binomial
    ---
    species_uuid:           uuid
    species_nickname:		varchar(255)	# nick name
    """


@schema
class Source(dj.Lookup):
    # <class 'subjects.models.Source'>
    definition = """
    source_name:				varchar(255)	# name of source
    ---
    source_uuid:                uuid
    source_description=null:	varchar(255)	# description
    """


@schema
class Strain(dj.Lookup):
    # <class 'subjects.models.Strain'>
    definition = """
    strain_name:		        varchar(255)	# strain name
    ---
    strain_uuid:                uuid
    strain_description=null:    varchar(255)	# description
    """


@schema
class Sequence(dj.Lookup):
    # <class 'subjects.models.Sequence'>
    definition = """
    sequence_name:		        varchar(255)	# informal name
    ---
    sequence_uuid:              uuid
    base_pairs=null:	        varchar(1024)	# base pairs
    sequence_description=null:	varchar(255)	# description
    """


@schema
class Allele(dj.Lookup):
    # <class 'subjects.models.Allele'>
    definition = """
    allele_name:			    varchar(255)    # informal name
    ---
    allele_uuid:                uuid
    standard_name=null:		    varchar(255)	# standard name
    -> [nullable] Source
    allele_source=null:         varchar(255)    # source of the allele
    source_identifier=null:     varchar(255)    # id inside the line provider
    source_url=null:            varchar(255)    # link to the line information
    expression_data_url=null:   varchar(255)    # link to the expression pattern from Allen institute brain atlas
    """


@schema
class AlleleSequence(dj.Lookup):
    definition = """
    -> Allele
    -> Sequence
    """


@schema
class Line(dj.Lookup):
    # <class 'subjects.models.Line'>
    definition = """
    line_name:				varchar(255)	# name
    ---
    -> Species
    -> [nullable] Strain
    line_uuid:              uuid
    line_description=null:	varchar(2048)	# description
    target_phenotype=null:	varchar(255)	# target phenotype
    line_nickname:		    varchar(255)	# nickname
    is_active:				boolean		    # is active
    """


@schema
class LineAllele(dj.Lookup):
    definition = """
    -> Line
    -> Allele
    """


@schema
class Subject(dj.Manual):
    # <class 'subjects.models.Subject'>
    definition = """
    subject_uuid:               uuid
    ---
    subject_nickname:		    varchar(255)		# nickname
    sex:			            enum("M", "F", "U")	# sex
    subject_birth_date=null:	date			    # birth date
    ear_mark=null:			    varchar(255)		# ear mark
    -> [nullable] Line.proj(subject_line="line_name")
    -> [nullable] Source.proj(subject_source='source_name')
    protocol_number:            tinyint         	# protocol number
    subject_description=null:   varchar(1024)
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
    """


@schema
class LitterSubject(dj.Manual):
    # litter subject membership table
    definition = """
    -> Subject
    ---
    -> Litter
    """


@schema
class SubjectProject(dj.Manual):
    definition = """
    -> Subject
    -> reference.Project
    """


@schema
class SubjectUser(dj.Manual):
    definition = """
    -> Subject
    ---
    -> reference.LabMember.proj(responsible_user='user_name')
    """


@schema
class SubjectLab(dj.Manual):
    definition = """
    -> Subject
    ---
    -> reference.Lab
    """


@schema
class Caging(dj.Manual):
    # <class 'subjects.models.Subject'>
    definition = """
    -> Subject
    cage_name:              varchar(255)        # cage name
    ---
    caging_time=null:	    datetime			# cage
    """


@schema
class UserHistory(dj.Manual):
    definition = """
    -> Subject
    -> reference.LabMember
    ---
    user_change_time=null:   datetime      # time when changed to this user
    """


@schema
class Weaning(dj.Manual):
    # <class 'subjects.models.Subject'>
    definition = """
    -> Subject
    ---
    wean_date:			date			# wean date
    """


@schema
class GenotypeTest(dj.Manual):
    # <class 'subjects.models.Subject'>
    # <class 'subjects.models.Zygosity'>
    # genotype = models.ManyToManyField('Allele', through='Zygosity')
    definition = """
    -> Subject
    -> Sequence
    genotype_test_uuid:		    uuid     # genotype test id
    ---
    test_result:		        enum("Present", "Absent")		# test result
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
    zygosity_uuid:      uuid
    zygosity:		    enum("Present", "Absent", "Homozygous", "Heterozygous")  # zygosity
    """


@schema
class Implant(dj.Manual):
    # <class 'subjects.models.Subject'>
    definition = """
    -> Subject
    ---
    implant_weight:		    float			    # implant weight
    protocol_number:        tinyint		        # protocol number
    adverse_effects=null:   varchar(2048)		# adverse effects
    (actual_severity)		-> [nullable] reference.Severity   # actual severity
    """


@schema
class Death(dj.Manual):
    # <class 'subjects.models.Subject'>
    definition = """
    -> Subject
    ---
    death_date:                 date                    # death date
    """
