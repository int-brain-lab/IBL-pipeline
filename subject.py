import datajoint as dj

import reference
import equipment

schema = dj.schema(dj.config['names.%s' % __name__], locals())


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
class Species(dj.Manual):
    # <class 'subjects.models.Species'>
    definition = """
    binomial:			varchar(255)	# binomial
    ---
    display_name:		varchar(255)	# display name
    """


@schema
class Strain(dj.Manual):
    # <class 'subjects.models.Strain'>
    definition = """
    strain_name:		varchar(255)	# strain name
    ---
    description:    		varchar(255)	# description
    """


@schema
class Sequence(dj.Manual):
    # <class 'subjects.models.Sequence'>
    definition = """
    sequence_name:		varchar(255)	# informal name
    ---
    base_pairs:			varchar(255)	# base pairs
    description:		varchar(255)	# description
    """


@schema
class Allele(dj.Manual):
    # <class 'subjects.models.Allele'>
    definition = """
    allele_id:			int             # allele id
    ---
    standard_name:		varchar(255)	# standard name
    informal_name:		varchar(255)	# informal name
    """


@schema
class Line(dj.Manual):
    # <class 'subjects.models.Line'>
    definition = """
    -> Species
    -> Strain
    -> Sequence
    line_id:				int             # line id
    ---
    name:				varchar(255)	# name
    description:			varchar(255)	# description
    target_phenotype:			varchar(255)	# target phenotype
    auto_name:				varchar(255)	# auto name
    is_active:				boolean		# is active
    """


@schema
class Source(dj.Manual):
    # <class 'subjects.models.Source'>
    definition = """
    source_id:				int             # source id
    ---
    name:				varchar(255)	# name
    description:			varchar(255)	# description
    """


@schema
class SubjectRequest(dj.Manual):
    # <class 'subjects.models.SubjectRequest'>
    definition = """
    -> reference.User
    -> Line
    subject_request_id:         int                  	# subject request id
    ---
    count:                      integer 		# count
    date_time:                  date    		# date time
    due_date:                   date    		# due date
    description:                varchar(255)            # description
    """


@schema
class Subject(dj.Manual):
    # <class 'subjects.models.Subject'>
    definition = """
    subject_id:			int                     # subject id
    ---
    nickname:			varchar(255)		# nickname
    sex:			enum("M", "F", "U")	# sex
    birth_date:			date			# birth date
    ear_mark:			varchar(255)		# ear mark
    (request)                   -> SubjectRequest(subject_request_id)
    -> Source
    -> Line
    (responsible_user)          -> reference.User
    """


@schema
class Birth(dj.Manual):
    # <class 'subjects.models.BreedingPair'>
    # <class 'subjects.models.Litter'>
    definition = """
    -> Subject
    ---
    (father)			-> Subject		# father
    (mother1) 			-> Subject		# mother1
    # XXX: explain? (mother2)	-> [nullable] Subject	# mother2
    """


@schema
class Weighing(dj.Manual):
    # <class 'actions.models.Weighing'>
    definition = """
    -> Subject
    weighing_time:		datetime		# date time
    ---
    weight:			float			# weight
    -> equipment.WeighingScale
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
    -> equipment.LabLocation
    """


@schema
class Caging(dj.Manual):
    # <class 'subjects.models.Subject'>
    definition = """
    -> Subject
    caging_date:                datetime                # caging date
    ---
    lamis_cage:			integer			# lamis cage
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
    # <class 'subjects.models.GenotypeTest'>
    definition = """
    -> Subject
    -> Sequence
    genotype_test_id:		int     	# genotype test id
    ---
    genotype_test_date:         date            # genotype date
    test_result:		integer		# test result
    """


@schema
class Genotype(dj.Manual):
    # <class 'subjects.models.Subject'>
    # <class 'subjects.models.Zygosity'>
    # genotype = models.ManyToManyField('Allele', through='Zygosity')
    definition = """
    -> Subject
    -> Allele
    ---
    zygosity:		integer 		# zygosity
    """


@schema
class Surgery(dj.Manual):
    # <class 'actions.models.Surgery'>
    definition = """
    -> Subject
    -> reference.BrainLocation
    surgery_start_time:		datetime        # surgery start time
    ---
    surgery_end_time:		datetime        # surgery end time
    outcome_type:		varchar(255)	# outcome type
    narrative:			varchar(255)	# narrative
    -> equipment.LabLocation
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
    -> equipment.VirusBatch
    injection_time:		datetime        	# injection time
    ---
    injection_volume:		float   		# injection volume
    rate_of_injection:		float                   # rate of injection
    injection_type:		varchar(255)    	# injection type
    -> equipment.LabLocation
    """


@schema
class Culling(dj.Manual):
    # <class 'subjects.models.Subject'>
    definition = """
    -> Subject
    ---
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
    -> equipment.LabLocation
    """


@schema
class Death(dj.Manual):
    # <class 'subjects.models.Subject'>
    definition = """
    -> Subject
    ---
    death_date:                 date                    # death date
    """
