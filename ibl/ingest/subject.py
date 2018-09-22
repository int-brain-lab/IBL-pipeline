
import datajoint as dj

from . import alyxraw
from . import reference

schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_ingest_subject')


@schema
class Species(dj.Computed):
    # <class 'subjects.models.Species'>
    definition = """
    binomial:			varchar(255)	# binomial
    ---
    display_name:		varchar(255)	# display name
    """


@schema
class Strain(dj.Computed):
     # <class 'subjects.models.Strain'>
    definition = """
    (strain_uuid) -> alyxraw.AlyxRaw
    ---
    strain_name:		varchar(255)	# strain name
    description=null:   varchar(255)	# description
    """
    key_source = alyxraw.AlyxRaw & 'model="subjects.strain"'
    
    def make(self, key):   
        key['strain_name'] = (alyxraw.AlyxRaw.Field & key & 'fname="descriptive_name"').fetch1('fvalue')
        key['description'] = (alyxraw.AlyxRaw.Field & key & 'fname="description"').fetch1('fvalue')
        self.insert1(key, skip_duplicates=True)

@schema
class Sequence(dj.Computed):
    # <class 'subjects.models.Sequence'>
    definition = """
    (sequence_uuid) -> alyxraw.AlyxRaw
    ---
    sequence_name:		varchar(255)	# informal name
    base_pairs=null:	varchar(255)	# base pairs
    description=null:	varchar(255)	# description
    """
    key_source = alyxraw.AlyxRaw & 'model="subjects.sequence"'
    
    def make(self, key):
        key['sequence_name'] = (alyxraw.AlyxRaw.Field & key & 'fname="informal_name"').fetch1('fvalue')
        key['base_pairs'] = (alyxraw.AlyxRaw.Field & key & 'fname="base_pairs"').fetch1('fvalue')
        key['description'] = (alyxraw.AlyxRaw.Field & key & 'fname="description"').fetch1('fvalue')
        self.insert1(key, skip_duplicates=True)

@schema
class Allele(dj.Computed):
    # <class 'subjects.models.Allele'>
    definition = """
    (allele_uuid) -> alyxraw.AlyxRaw
    ---
    allele_name:			varchar(255)    # informal name
    standard_name=null:		varchar(255)	# standard name
    """
    key_source = alyxraw.AlyxRaw & 'model="subjects.allele"'
    
    def make(self, key):
        key['allele_name'] = (alyxraw.AlyxRaw.Field & key & 'fname="informal_name"').fetch1('fvalue')
        key['standard_name'] = (alyxraw.AlyxRaw.Field & key & 'fname="standard_name"').fetch1('fvalue')
        self.insert1(key, skip_duplicates=True)

#@schema
#class AlleleSequence(dj.Computed):
#    definition = ds_subject.AlleleSequence.definition


@schema
class Line(dj.Computed):
    # <class 'subjects.models.Line'>
    definition = """
    (line_uuid) -> alyxraw.AlyxRaw
    ---
    binomial:                   varchar(255)	# binomial, inherited from Species          
    strain_name:                varchar(255)    # strain name, inherited from Strain
    line_name:				    varchar(255)	# line name
    description=null:			varchar(255)	# description
    target_phenotype=null:		varchar(255)	# target phenotype
    auto_name:				    varchar(255)	# auto name
    is_active:				    boolean		    # is active
    """
    key_source = alyxraw.AlyxRaw & 'model="subjects.line"'

    def make(self, key):
        key['binomial'] = 'Mus Musculus'
        
        strain_uuid = (alyxraw.AlyxRaw.Field & key & 'fname="strain"').fetch1('fvalue')
        key['strain_name'] = (Strain & 'strain_uuid="{}"'.format(strain_uuid)).fetch1('strain_name')
        
        key['line_name'] = (alyxraw.AlyxRaw.Field & key & 'fname="name"').fetch1('fvalue')
        key['description'] = (alyxraw.AlyxRaw.Field & key & 'fname="description"').fetch1('fvalue')
        key['target_phenotype'] = (alyxraw.AlyxRaw.Field & key & 'fname="target_phenotype"').fetch1('fvalue')
        key['auto_name'] = (alyxraw.AlyxRaw.Field & key & 'fname="auto_name"').fetch1('fvalue')
        
        active = (alyxraw.AlyxRaw.Field & key & 'fname="is_active"').fetch1('fvalue')
        key['is_active'] = True if active=="True" else False
        
        self.insert1(key, skip_duplicates=True)
        # TODO: uuid of sequence referenced in subjects.models.line

#@schema
#class LineAllele(dj.Computed):
    #definition = ds_subject.LineAllele.definition


@schema
class Source(dj.Computed):
    # <class 'subjects.models.Source'>
    definition = """
    (source_uuid) -> alyxraw.AlyxRaw
    ---
    source_name:				varchar(255)	# name of source
    description=null:			varchar(255)	# description
    """
    key_source = alyxraw.AlyxRaw & 'model="subjects.source"'

    def make(self, key):
        key['source_name'] = (alyxraw.AlyxRaw.Field & key & 'fname="name"').fetch1('fvalue')
        key['description'] = (alyxraw.AlyxRaw.Field & key & 'fname="description"').fetch1('fvalue')


@schema
class Subject(dj.Computed):
    # <class 'subjects.models.Subject'>
    definition = """
    (subject_uuid) -> alyxraw.AlyxRaw
    --- 
    nickname=null:			varchar(255)		# nickname
    sex:			        enum("M", "F", "U")	# sex
    birth_date:			    date			    # birth date
    ear_mark=null:			varchar(255)		# ear mark
    source_name:            varchar(255)        # source name, inherited from Source
    responsible_user:       varchar(255)        # user_name, inherited from reference.LabMember
    """
    key_source = alyxraw.AlyxRaw & 'model = subjects.subject'

    def make(self, key):

        key['nick_name'] = (alyxraw.AlyxRaw.Field & key & 'fname="nickname"').fetch1('fvalue')
        key['sex'] = (alyxraw.AlyxRaw.Field & key & 'fname="sex"').fetch1('fvalue')
        key['birth_date'] = (alyxraw.AlyxRaw.Field & key & 'fname="birth_date"').fetch1('fvalue')
        key['ear_mark'] = (alyxraw.AlyxRaw.Field & key & 'fname="ear_mark"').fetch1('fvalue')
        
        source_uuid = (alyxraw.AlyxRaw.Field & key & 'fname="source"').fetch1('fvalue')
        key['source_name'] = (Source & 'source_uuid="{}"'.format(source_uuid)).fetch1('source_name')

        user_uuid = (alyxraw.AlyxRaw.Field & key & 'fname="responsible_user"').fetch1('fvalue')
        key['reponsible_user'] = (reference.LabMember & 'user_uuid="{}"'.format(user_uuid)).fetch1('user_name')

        self.insert1(key, skip_duplicates=True)

@schema
class Caging(dj.Computed):
    definition = """
    -> Subject
    ---
    lamis_cage:         int
    """
    key_source = alyxraw.AlyxRaw & 'model = subjects.subject'

    def make(self, key):
        key['lamis_cage'] = (alyxraw.AlyxRaw.Field & key & 'fname="lamis_cage"').fetch1('fvalue')
        self.insert1(key, skip_duplicates=True)
##TODO: caging history might be in the json field of subject

@schema
class Weaning(dj.Computed):
    definition = """
    -> Subject
    ---
    wean_date:			date			# wean date
    """
    key_source = alyxraw.AlyxRaw & 'model = subjects.subject'

    def make(self, key):
        key['wean_date'] = (alyxraw.AlyxRaw.Field & key & 'fname="wean_date"').fetch1('fvalue')
        self.insert1(key, skip_duplicates=True)

@schema
class Culling(dj.Computed):
    # need to be parsed when ingesting into the real table
    definition = """
    -> master
    ---
    to_be_culled:       boolean       
    cull_method=null:   varchar(255)   # like a discription
    """
    key_source = alyxraw.AlyxRaw & 'model = subjects.subject'

    def make(self, key):
        key['to_be_culled'] = (alyxraw.AlyxRaw.Field & key & 'fname="to_be_culled"').fetch1('fvalue')
        key['cull_method'] = (alyxraw.AlyxRaw.Field & key & 'fname="cull_method"').fetch1('fvalue')
        self.insert1(key, skip_duplicates=True)

@schema
class Reduction(dj.Computed):
    # need to be parsed when ingesting into the real table
    definition = """
    -> master
    ---
    reduced:            boolean
    reduce_date:        date
    """
    key_source = alyxraw.AlyxRaw & 'model = subjects.subject'
    
    def make(self, key):
        key['reduced'] = (alyxraw.AlyxRaw.Field & key & 'fname="reduced"').fetch1('fvalue')
        key['reduce_date'] = (alyxraw.AlyxRaw.Field & key & 'fname="reduce_date"').fetch1('fvalue')
        self.insert1(key, skip_duplicates=True)

@schema
class Death(dj.Computed):
    definition = """
    -> master
    ---
    death_date:         date
    """
    key_source = alyxraw.AlyxRaw & 'model = subjects.subject'

    def make(self, key):
        key['death_date'] = (alyxraw.AlyxRaw.Field & key & 'fname="death_date"').fetch1('fvalue')
        self.insert1(key, skip_duplicates=True)


@schema
class BreedingPair(dj.Computed):
    # <class 'subjects.models.BreedingPair'>
    definition = """
    (bp_uuid) -> alyxraw.AlyxRaw
    ---
    line_name:          varchar(255)        # line name, inherited from Line
    bp_name:			varchar(255)		# name
    description=null:	varchar(255)		# description
    start_date:			date			    # start date
    end_date=null:		date			    # end date
    father:             varchar(36)         # subject uuid of dad, inherited from subject
    mother1:            varchar(36)         # subject uuid of mom, inherited from subject
    mother2=null		varchar(36)         # subject uuid of mom2, if has one, inherited from subject
    """
    key_source = alyxraw.AlyxRaw & 'model="subjects.breedingpair"'

    def make(self, key):
        line_uuid = (alyxraw.AlyxRaw & key & 'fname="line"').fetch1('fvalue')
        key['line_name'] = (Line & 'line_uuid="{}"'.format(line_uuid)).fetch1('line_name')

        key['bp_name'] = (alyxraw.AlyxRaw.Field & key & 'fname="name"').fetch1('fvalue')
        key['description'] = (alyxraw.AlyxRaw.Field & key & 'fname="description"').fetch1('fvalue')
        key['start_date'] = (alyxraw.AlyxRaw.Field & key & 'fname="start_date"').fetch1('fvalue')
        key['end_date'] = (alyxraw.AlyxRaw.Field & key & 'fname="end_date"').fetch1('fvalue')
        key['father'] = (alyxraw.AlyxRaw.Field & key & 'fname="father"').fetch1('fvalue')
        key['mother'] = (alyxraw.AlyxRaw.Field & key & 'fname="mother1"').fetch1('fvalue')
        key['mother2'] = (alyxraw.AlyxRaw.Field & key & 'fname="mother2"').fetch1('fvalue')

        self.insert1(key, skip_duplicates=True)

@schema
class Litter(dj.Computed):
     # <class 'subjects.models.Litter'>
    definition = """
    (litter_uuid) -> alyxraw.AlyxRaw
    ---
    bp_name:                    varchar(255)    # name of the breedingpair, inherited from BreedingPair
    descriptive_name=null:		varchar(255)	# descriptive name
    description=null:			varchar(255)	# description
    birth_date:			        date		    # birth date
    """
    key_source = alyxraw.AlyxRaw & 'model="subjects.litter"'

    def make(self, key):
        bp_uuid = (alyxraw.AlyxRaw & key & 'fname="breeding_pair"').fetch1('fvalue')
        key['bp_name'] = (BreedingPair & 'bp_uuid="{}"'.format(bp_uuid)).fetch1('bp_name')
        key['descriptive_name'] = (alyxraw.AlyxRaw.Field & key & 'fname="descriptive_name"').fetch1('fvalue')
        key['description'] = (alyxraw.AlyxRaw.Field & key & 'fname="description"').fetch1('fvalue')
        key['birth_date'] = (alyxraw.AlyxRaw.Field & key & 'fname="birth_date"').fetch1('fvalue')
        self.insert1(key, skip_duplicates=True)


#@schema
#class LitterSubject(dj.Computed):
#    definition = ds_subject.LitterSubject.definition


@schema
class GenotypeTest(dj.Computed):
    # <class 'subjects.models.Subject'>
    # <class 'subjects.models.Zygosity'>
    # genotype = models.ManyToManyField('Allele', through='Zygosity')
    definition = """
    (genotype_test_uuid) -> alyxraw.AlyxRaw
    ---
    subject_uuid:               varchar(36)                     # inherited from Subject
    sequence_uuid:              varchar(36)                     # inherited from Sequence
    genotype_test_date=null:    date                            # genotype date
    test_result:		        enum("Present", "Absent")		# test result
    """
    key_source = alyxraw.AlyxRaw & 'model = subjects.genotypetest'

    def make(self, key):
        key['subject_uuid'] = (alyxraw.AlyxRaw.Field & key & 'fname="subject"').fetch1('fvalue')
        key['sequence_uuid'] = (alyxraw.AlyxRaw.Field & key & 'fname="sequence"').fetch1('fvalue')
        test_result = (alyxraw.AlyxRaw.Field & key & 'fname="test_result"').fetch1('fvalue')
        key['test_result'] = 'Present' if test_result else 'Absent'
        self.insert1(key, skip_duplicates=True)

@schema
class Zygosity(dj.Computed):
    # <class 'subjects.models.Subject'>
    # <class 'subjects.models.Zygosity'>
    # genotype = models.ManyToManyField('Allele', through='Zygosity')
    definition = """
    (zygosity_uuid) -> alyxraw.AlyxRaw    
    ---
    subject_uuid:   varchar(36)             # inherited from Subject
    allele_name:    varchar(255)            # inherited from Allele
    zygosity:		enum("Present", "Absent", "Homozygous", "Heterozygous") 		# zygosity
    """
    key_source = alyxraw.AlyxRaw & 'model = "subjects.zygosity"'

    def make(self, key):
        key['subject_uuid'] = (alyxraw.AlyxRaw.Field & key & 'fname="subject"').fetch1('fvalue')
        
        allele_uuid = (alyxraw.AlyxRaw.Field & key & 'fname="allele"').fetch1('fvalue')
        key['allele_name'] = (Allele & 'allele_uuid="{}"'.format(allele_uuid)).fetch1('allele_name')

        zygosity = (alyxraw.AlyxRaw.Field & key & 'fname="zygosity"').fetch1('fvalue') 
        zygosity_types = {
            0: 'Absent',
            1: 'Heterozygous',
            2: 'Homozygous',
            3: 'Present'
        }
        key['zygosity'] = zygosity_types[zygosity]
        
        self.insert1(key, skip_duplicates=True)


@schema
class Implant(dj.Computed):
     # <class 'subjects.models.Subject'>
    definition = """
    (implant_uuid) -> alyxraw.AlyxRaw
    ---
    subject_uuid:       varchar(36)         # inherited from Subject
    implant_weight:		float			    # implant weight
    protocol_number:	varchar(255)		# protocol number
    description:		varchar(255)		# description
    adverse_effects:	varchar(255)		# adverse effects
    actual_severity:    tinyint             # actual severity, inherited from Severity
    """
    key_source = alyxraw.AlyxRaw & 'model = "subjects.subject"'
    
    def make(self, key):
        key['subject_uuid'] = (alyxraw.AlyxRaw.Field & key & 'fname="uuid"').fetch1('fvalue')
        key['implant_weight'] = (alyxraw.AlyxRaw.Field & key & 'fname="implant_weight"').fetch1('fvalue')
        key['protocol_number'] = (alyxraw.AlyxRaw.Field & key & 'fname="protocol_number"').fetch1('fvalue')
        key['description'] = (alyxraw.AlyxRaw.Field & key & 'fname="description"').fetch1('fvalue')
        key['adverse_effects'] = (alyxraw.AlyxRaw.Field & key & 'fname="adverse_effects"').fetch1('fvalue')
        self.insert1(key, skip_duplicates=True)




