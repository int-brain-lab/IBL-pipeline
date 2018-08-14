import datajoint as dj
import reference


schema = dj.schema(dj.config['names.{}'.format(__name__)])


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
    binomial:			varchar(255)	# binomial
    ---
    display_name:		varchar(255)	# display name
    """


@schema
class Strain(dj.Lookup):
    # <class 'subjects.models.Strain'>
    definition = """
    strain_name:		varchar(255)	# strain name
    ---
    description=null:    		varchar(255)	# description
    """


@schema
class Sequence(dj.Lookup):
    # <class 'subjects.models.Sequence'>
    definition = """
    sequence_name:		varchar(255)	# informal name
    ---
    base_pairs=null:			varchar(255)	# base pairs
    description=null:		varchar(255)	# description
    """


@schema
class Allele(dj.Lookup):
    # <class 'subjects.models.Allele'>
    definition = """
    allele_name:			varchar(255)             # informal name
    ---
    standard_name=null:		varchar(255)	# standard name
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
    -> Species
    -> Strain # this is nullable
    name:				varchar(255)	# name
    ---
    description=null:			varchar(255)	# description
    target_phenotype=null:			varchar(255)	# target phenotype
    auto_names:				varchar(255)	# auto name
    is_active:				boolean		# is active
    """

@schema
class LineAllele(dj.Lookup):
    definition = """
    -> Line
    -> Allele
    """

@schema
class Source(dj.Lookup):
    # <class 'subjects.models.Source'>
    definition = """
    name:				varchar(255)	# name
    ---
    description=null:			varchar(255)	# description
    """


@schema
class SubjectRequest(dj.Manual):
    # <class 'subjects.models.SubjectRequest'>
    definition = """
    -> reference.User
    -> Line
    subject_request_id:         int                  	# subject request id
    ---
    count:                      int 		# count
    date_time:                  date    		# date time
    due_date=null:              date    		# due date
    description=null:           varchar(255)            # description
    """


@schema
class Subject(dj.Manual):
    # <class 'subjects.models.Subject'>
    definition = """
    subject_id:			int                     # subject id
    ---
    nickname=null:			varchar(255)		# nickname
    sex:			enum("M", "F", "U")	# sex
    birth_date:			date			# birth date
    ear_mark=null:			varchar(255)		# ear mark
    (request)                   -> SubjectRequest(subject_request_id)
    -> Source
    (responsible_user)          -> reference.User
    """

@schema
class BreedingPair(dj.Manual):
    # <class 'subjects.models.BreedingPair'>
    definition = """
    -> Line
    name:			varchar(255)		# name
    ---
    description=null:		varchar(255)		# description
    start_date:			date			# start date
    end_date=null:			date			# end date
    (father)			-> Subject		# father
    (mother1) 			-> Subject		# mother1
    (mother2)			-> [nullable] Subject	# mother2
    """
    
@schema
class Litter(dj.Manual):
    # <class 'subjects.models.Litter'>
    definition = """
    -> BreedingPair
    litter_id:			char(32)	# litter id
    ---
    descriptive_name=null:		varchar(255)	# descriptive name
    description=null:			varchar(255)	# description
    birth_date:			date		# birth date
    """

@schema
class LitterSubject(dj.Manual):
    # litter subject membership table
    definition = """
    -> Subject
    -> Litter
    """
    
@schema
class Weighing(dj.Manual):
    # <class 'actions.models.Weighing'>
    definition = """
    -> Subject
    weighing_time:		datetime		# date time
    ---
    weight:			float			# weight
    """


@schema
class WaterAdministration(dj.Manual):
    # <class 'actions.models.WaterAdministration'>
    definition = """
    -> Subject
    administration_time:	datetime		# date time
    ---
    water_administered:		float			# water administered
    hydrogel=NULL:		boolean                 # hydrogel
    """

@schema
class WaterRestriction(dj.Manual):
    # <class 'actions.models.WaterRestriction'>
    definition = """
    -> Subject
    restriction_start_time:     datetime	# start time
    ---
    restriction_end_time:       datetime	# end time
#    -> equipment.LabLocation # equipment removed
    """


@schema
class Caging(dj.Manual):
    # <class 'subjects.models.Subject'>
    definition = """
    -> Subject
    caging_date:                datetime                # caging date
    ---
    lamis_cage:			int			# lamis cage
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
    genotype_test_id:		int     	# genotype test id
    ---
    genotype_test_date:         date            # genotype date
    test_result:		enum("Present", "Absent")		# test result
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
    zygosity:		enum("Present", "Absent", "Homozygous", "Heterozygous") 		# zygosity
    """
    
@schema
class Surgery(dj.Manual):
    # <class 'actions.models.Surgery'>
    definition = """
    -> Subject
    surgery_start_time:		datetime        # surgery start time
    ---
    surgery_end_time:		datetime        # surgery end time
    outcome_type:		varchar(255)	# outcome type
    narrative:			varchar(255)	# narrative
    """


@schema
class Implant(dj.Manual):
    # <class 'subjects.models.Subject'>
    definition = """
    -> Subject
    ---
    implant_weight:		float			# implant weight
    protocol_number:		varchar(255)		# protocol number
    description:		varchar(255)		# description
    adverse_effects:		varchar(255)		# adverse effects
    (actual_severity)		-> reference.Severity   # actual severity
    """


@schema
class VirusInjection(dj.Manual):
    # <class 'actions.models.VirusInjection'>
    # XXX: user was m2m field in django
    definition = """
    -> Subject
    injection_time:		datetime        	# injection time
    ---
    injection_volume:		float   		# injection volume
    rate_of_injection:		float                   # rate of injection
    injection_type:		varchar(255)    	# injection type
    """


@schema
class Culling(dj.Manual):
    # <class 'subjects.models.Subject'>
    definition = """
    -> Subject
    ---
    cull_date:          date                # cull date
    cull_method:		varchar(255)		# cull method
    """


@schema
class Reduction(dj.Manual):
    definition = """
    reduced:			boolean			# reduced
    reduced_date:		date			# reduced date
    """

@schema
class OtherAction(dj.Manual):
    # <class 'actions.models.OtherAction'>
    definition = """
    -> Subject
    other_action_start_time:    datetime	# start time
    ---
    other_action_end_time:      datetime	# end time
    descrption:                 varchar(255)    # description
    # -> equipment.LabLocation # equipment removed
    """


@schema
class Death(dj.Manual):
    # <class 'subjects.models.Subject'>
    definition = """
    -> Subject
    ---
    death_date:                 date                    # death date
    """
