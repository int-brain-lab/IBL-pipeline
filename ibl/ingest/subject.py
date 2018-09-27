
import datajoint as dj
import json

from . import alyxraw
from . import reference

schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_ingest_subject')


@schema
class Strain(dj.Computed):
     # <class 'subjects.models.Strain'>
    definition = """
    (strain_uuid) -> alyxraw.AlyxRaw
    ---
    strain_name:		        varchar(255)	# strain name
    strain_description=null:    varchar(255)	# description
    """
    key_source = (alyxraw.AlyxRaw & 'model="subjects.strain"').proj(strain_uuid="uuid")

    def make(self, key):
        key_strain = key.copy()
        key['uuid'] = key['strain_uuid']
        key_strain['strain_name'] = (alyxraw.AlyxRaw.Field & key & 'fname="descriptive_name"').fetch1('fvalue')
        
        description = (alyxraw.AlyxRaw.Field & key & 'fname="description"').fetch1('fvalue')
        if description != 'None':
            key_strain['strain_description'] = description
        
        self.insert1(key_strain, skip_duplicates=True)

@schema
class Sequence(dj.Computed):
    # <class 'subjects.models.Sequence'>
    definition = """
    (sequence_uuid) -> alyxraw.AlyxRaw
    ---
    sequence_name:		        varchar(255)	# informal name
    base_pairs=null:	        varchar(255)	# base pairs
    sequence_description=null:	varchar(255)	# description
    """
    key_source = (alyxraw.AlyxRaw & 'model="subjects.sequence"').proj(sequence_uuid="uuid")
    
    def make(self, key):
        key_seq = key.copy()
        key['uuid'] = key['sequence_uuid']
        key_seq['sequence_name'] = (alyxraw.AlyxRaw.Field & key & 'fname="informal_name"').fetch1('fvalue')
        
        base_pairs = (alyxraw.AlyxRaw.Field & key & 'fname="base_pairs"').fetch1('fvalue')
        if base_pairs != 'None':
            key_seq['base_pairs'] = (alyxraw.AlyxRaw.Field & key & 'fname="base_pairs"').fetch1('fvalue')

        description = (alyxraw.AlyxRaw.Field & key & 'fname="description"').fetch1('fvalue')
        if description != 'None':
            key_seq['sequence_description'] = (alyxraw.AlyxRaw.Field & key & 'fname="description"').fetch1('fvalue')
        
        self.insert1(key_seq, skip_duplicates=True)

@schema
class Allele(dj.Computed):
    # <class 'subjects.models.Allele'>
    definition = """
    (allele_uuid) -> alyxraw.AlyxRaw
    ---
    allele_name:			varchar(255)    # informal name
    standard_name=null:		varchar(255)	# standard name
    """
    key_source = (alyxraw.AlyxRaw & 'model="subjects.allele"').proj(allele_uuid='uuid')
    
    def make(self, key):
        key_allele = key.copy()
        key['uuid'] = key['allele_uuid']
        key_allele['allele_name'] = (alyxraw.AlyxRaw.Field & key & 'fname="informal_name"').fetch1('fvalue')
        key_allele['standard_name'] = (alyxraw.AlyxRaw.Field & key & 'fname="standard_name"').fetch1('fvalue')
        self.insert1(key_allele, skip_duplicates=True)

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
    strain_name=null:           varchar(255)    # strain name, inherited from Strain
    line_name:				    varchar(255)	# line name
    line_description=null:		varchar(1024)	# description
    target_phenotype=null:		varchar(255)	# target phenotype
    auto_name:				    varchar(255)	# auto name
    is_active:				    boolean		    # is active
    """
    key_source = (alyxraw.AlyxRaw & 'model="subjects.line"').proj(line_uuid='uuid')

    def make(self, key):

        key_line = key.copy()
        key['uuid'] = key['line_uuid']
        key_line['binomial'] = 'Mus Musculus'
        
        strain_uuid = (alyxraw.AlyxRaw.Field & key & 'fname="strain"').fetch1('fvalue')
        if strain_uuid != 'None':
            key_line['strain_name'] = (Strain & 'strain_uuid="{}"'.format(strain_uuid)).fetch1('strain_name')
        
        key_line['line_name'] = (alyxraw.AlyxRaw.Field & key & 'fname="name"').fetch1('fvalue')

        description = (alyxraw.AlyxRaw.Field & key & 'fname="description"').fetch1('fvalue')
        if description != 'None':
            key_line['line_description'] = description
        key_line['target_phenotype'] = (alyxraw.AlyxRaw.Field & key & 'fname="target_phenotype"').fetch1('fvalue')
        key_line['auto_name'] = (alyxraw.AlyxRaw.Field & key & 'fname="auto_name"').fetch1('fvalue')
        
        active = (alyxraw.AlyxRaw.Field & key & 'fname="is_active"').fetch1('fvalue')
        key_line['is_active'] = True if active=="True" else False
        
        self.insert1(key_line, skip_duplicates=True)

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
    source_description=null:	varchar(255)	# description
    """
    key_source = (alyxraw.AlyxRaw & 'model="subjects.source"').proj(source_uuid='uuid')

    def make(self, key):
        key_strain_source = key.copy()
        key['uuid'] = key['source_uuid']
        key_strain_source['source_name'] = (alyxraw.AlyxRaw.Field & key & 'fname="name"').fetch1('fvalue')
        
        description = (alyxraw.AlyxRaw.Field & key & 'fname="description"').fetch1('fvalue')
        if description != 'None':
            key_strain_source['source_description'] = description
        self.insert1(key_strain_source, skip_duplicates=True)    

@schema
class BreedingPair(dj.Computed):
    # <class 'subjects.models.BreedingPair'>
    definition = """
    (bp_uuid) -> alyxraw.AlyxRaw
    ---
    line_name=null:         varchar(255)        # line name, inherited from Line
    bp_name:			    varchar(255)		# name
    bp_description=null:	varchar(1024)		# description
    start_date=null:		date			    # start date
    end_date=null:		    date			    # end date
    father:                 varchar(36)         # subject uuid of dad, inherited from subject
    mother1:                varchar(36)         # subject uuid of mom, inherited from subject
    mother2=null:		    varchar(36)         # subject uuid of mom2, if has one, inherited from subject
    """
    key_source = (alyxraw.AlyxRaw & 'model="subjects.breedingpair"').proj(bp_uuid='uuid')

    def make(self, key):
        key_bp = key.copy()
        key['uuid'] = key['bp_uuid']
        
        line_uuid = (alyxraw.AlyxRaw.Field & key & 'fname="line"').fetch1('fvalue')
        if line_uuid != 'None':
            key_bp['line_name'] = (Line & 'line_uuid="{}"'.format(line_uuid)).fetch1('line_name')

        key_bp['bp_name'] = (alyxraw.AlyxRaw.Field & key & 'fname="name"').fetch1('fvalue')

        description = (alyxraw.AlyxRaw.Field & key & 'fname="description"').fetch1('fvalue')
        if description != 'None':
            key_bp['bp_description'] = description

        start_date = (alyxraw.AlyxRaw.Field & key & 'fname="start_date"').fetch1('fvalue')
        if start_date != 'None':
            key_bp['start_date'] = start_date

        end_date = (alyxraw.AlyxRaw.Field & key & 'fname="end_date"').fetch1('fvalue')
        if end_date != 'None':
            key_bp['end_date'] = end_date

        key_bp['father'] = (alyxraw.AlyxRaw.Field & key & 'fname="father"').fetch1('fvalue')
        key_bp['mother1'] = (alyxraw.AlyxRaw.Field & key & 'fname="mother1"').fetch1('fvalue')

        mother2 = (alyxraw.AlyxRaw.Field & key & 'fname="mother2"').fetch1('fvalue')
        if mother2 != 'None':
            key_bp['mother2'] = mother2

        self.insert1(key_bp, skip_duplicates=True)

@schema
class Litter(dj.Computed):
     # <class 'subjects.models.Litter'>
    definition = """
    (litter_uuid) -> alyxraw.AlyxRaw
    ---
    bp_name=null:               varchar(255)    # name of the breedingpair, inherited from BreedingPair
    descriptive_name=null:		varchar(255)	# descriptive name
    litter_description=null:    varchar(255)	# description
    litter_birth_date=null:		date		    # birth date
    """
    key_source = (alyxraw.AlyxRaw & 'model="subjects.litter"').proj(litter_uuid='uuid')

    def make(self, key):
        key_litter = key.copy()
        key['uuid'] = key['litter_uuid']
        bp_uuid = (alyxraw.AlyxRaw.Field & key & 'fname="breeding_pair"').fetch1('fvalue')
        if bp_uuid != 'None':
            key_litter['bp_name'] = (BreedingPair & 'bp_uuid="{}"'.format(bp_uuid)).fetch1('bp_name')

        descriptive_name = (alyxraw.AlyxRaw.Field & key & 'fname="descriptive_name"').fetch1('fvalue')
        if descriptive_name != 'None':
            key_litter['descriptive_name'] = descriptive_name
        
        description = (alyxraw.AlyxRaw.Field & key & 'fname="description"').fetch1('fvalue')
        if description != 'None':
            key_litter['litter_description'] = description

        birth_date = (alyxraw.AlyxRaw.Field & key & 'fname="birth_date"').fetch1('fvalue')
        if birth_date != 'None':
            key_litter['litter_birth_date'] = birth_date
        self.insert1(key_litter, skip_duplicates=True)

@schema
class Subject(dj.Computed):
    # <class 'subjects.models.Subject'>
    definition = """
    (subject_uuid) -> alyxraw.AlyxRaw
    --- 
    nickname=null:			    varchar(255)		# nickname
    sex=null:			            enum("M", "F", "U")	# sex
    subject_birth_date=null:    date			    # birth date
    ear_mark=null:			    varchar(255)		# ear mark
    source_name=null:           varchar(255)        # source name, inherited from Source
    litter_uuid=null:           varchar(36)
    responsible_user=null:      varchar(255)        # user_name, inherited from reference.LabMember
    """
    key_source = (alyxraw.AlyxRaw & 'model = "subjects.subject"').proj(subject_uuid='uuid')

    def make(self, key):

        key_subject = key.copy()
        key['uuid'] = key['subject_uuid']

        nick_name = (alyxraw.AlyxRaw.Field & key & 'fname="nickname"').fetch1('fvalue')
        if nick_name != 'None':
            key_subject['nickname'] = nick_name
        
        sex = (alyxraw.AlyxRaw.Field & key & 'fname="sex"').fetch1('fvalue')
        if sex != 'None':
            key_subject['sex'] = sex

        birth_date = (alyxraw.AlyxRaw.Field & key & 'fname="birth_date"').fetch1('fvalue')
        if birth_date != 'None':
            key_subject['subject_birth_date'] = birth_date
        
        ear_mark = (alyxraw.AlyxRaw.Field & key & 'fname="ear_mark"').fetch1('fvalue')
        if ear_mark != 'None':
            key_subject['ear_mark'] = ear_mark
        
        source_uuid = (alyxraw.AlyxRaw.Field & key & 'fname="source"').fetch1('fvalue')
        if source_uuid != 'None':
            key_subject['source_name'] = (Source & 'source_uuid="{}"'.format(source_uuid)).fetch1('source_name')

        user_uuid = (alyxraw.AlyxRaw.Field & key & 'fname="responsible_user"').fetch1('fvalue')
        if user_uuid != 'None':
            key_subject['responsible_user'] = (reference.LabMember & 'user_uuid="{}"'.format(user_uuid)).fetch1('username')

        litter_uuid = (alyxraw.AlyxRaw.Field & key & 'fname="litter"').fetch1('fvalue')
        if litter_uuid != 'None':
            key_subject['litter_uuid'] = litter_uuid

        self.insert1(key_subject, skip_duplicates=True)

@schema
class Caging(dj.Computed):
    definition = """
    -> Subject
    caging_date:            varchar(255)
    ---
    lamis_cage=null:        int
    """

    def make(self, key):
        key_cage = key.copy()
        key['uuid'] = key['subject_uuid']
        json_content = (alyxraw.AlyxRaw.Field & key & 'fname="json"').fetch1('fvalue')
        if json_content != 'None':
            json_dict = json.loads(json_content)       
            history = json_dict['history']

            if 'lamis_cage' in history.keys(): 
                cages = history['lamis_cage'] 
                for cage in cages:
                    key_cage_i = key_cage.copy()
                    key_cage_i['caging_date'] = cage['date_time']
                    if cage['value'] != 'None':
                        key_cage_i['lamis_cage'] = cage['value']
                    self.insert1(key_cage_i, skip_duplicates=True)

@schema
class Weaning(dj.Computed):
    definition = """
    -> Subject
    ---
    wean_date=null:			date			# wean date
    """
    def make(self, key):
        key_weaning = key.copy()
        key['uuid'] = key['subject_uuid']
        
        wean_date = (alyxraw.AlyxRaw.Field & key & 'fname="wean_date"').fetch1('fvalue')
        if wean_date != 'None':
            key_weaning['wean_date'] = wean_date

        self.insert1(key_weaning, skip_duplicates=True)

@schema
class Culling(dj.Computed):
    # need to be parsed when ingesting into the real table
    definition = """
    -> Subject
    ---
    to_be_culled:       boolean       
    cull_method=null:   varchar(255)   # like a description
    """

    def make(self, key):
        key_cull = key.copy()
        key['uuid'] = key['subject_uuid']
        to_be_culled = (alyxraw.AlyxRaw.Field & key & 'fname="to_be_culled"').fetch1('fvalue')
        key_cull['to_be_culled'] = True if to_be_culled == 'True' else False
        key_cull['cull_method'] = (alyxraw.AlyxRaw.Field & key & 'fname="cull_method"').fetch1('fvalue')
        self.insert1(key_cull, skip_duplicates=True)

@schema
class Reduction(dj.Computed):
    # need to be parsed when ingesting into the real table
    definition = """
    -> Subject
    ---
    reduced:                boolean
    reduce_date=null:       date
    """
    
    def make(self, key):
        key_reduction = key.copy()
        key['uuid'] = key['subject_uuid']

        reduced = (alyxraw.AlyxRaw.Field & key & 'fname="reduced"').fetch1('fvalue')
        key_reduction['reduced'] = True if reduced == 'True' else False
        
        reduced_date = (alyxraw.AlyxRaw.Field & key & 'fname="reduced_date"').fetch1('fvalue')
        if reduced_date != 'None':
            key_reduction['reduce_date'] = reduced_date

        self.insert1(key_reduction, skip_duplicates=True)

@schema
class Death(dj.Computed):
    definition = """
    -> Subject
    ---
    death_date=null:         date
    """

    def make(self, key):
        key_death = key.copy()
        key['uuid'] = key['subject_uuid']
        death_date = (alyxraw.AlyxRaw.Field & key & 'fname="death_date"').fetch1('fvalue')
        if death_date != 'None':
            key_death['death_date'] = death_date
            self.insert1(key_death, skip_duplicates=True)

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
    key_source = (alyxraw.AlyxRaw & 'model = "subjects.genotypetest"').proj(genotype_test_uuid='uuid')

    def make(self, key):
        key_gt = key.copy()
        key['uuid'] = key['genotype_test_uuid']
        key_gt['subject_uuid'] = (alyxraw.AlyxRaw.Field & key & 'fname="subject"').fetch1('fvalue')
        key_gt['sequence_uuid'] = (alyxraw.AlyxRaw.Field & key & 'fname="sequence"').fetch1('fvalue')
        test_result = (alyxraw.AlyxRaw.Field & key & 'fname="test_result"').fetch1('fvalue')
        key_gt['test_result'] = 'Present' if test_result else 'Absent'
        self.insert1(key_gt, skip_duplicates=True)

@schema
class Zygosity(dj.Computed):
    # <class 'subjects.models.Subject'>
    # <class 'subjects.models.Zygosity'>
    # genotype = models.ManyToManyField('Allele', through='Zygosity')
    definition = """
    (zygosity_uuid) -> alyxraw.AlyxRaw    
    ---
    subject_uuid:       varchar(36)             # inherited from Subject
    allele_name:        varchar(255)            # inherited from Allele
    zygosity=null:      enum("Present", "Absent", "Homozygous", "Heterozygous") 		# zygosity
    """
    key_source = (alyxraw.AlyxRaw & 'model = "subjects.zygosity"').proj(zygosity_uuid='uuid')

    def make(self, key):

        key_zg = key.copy()
        key['uuid'] = key['zygosity_uuid']
        key_zg['subject_uuid'] = (alyxraw.AlyxRaw.Field & key & 'fname="subject"').fetch1('fvalue')
        
        allele_uuid = (alyxraw.AlyxRaw.Field & key & 'fname="allele"').fetch1('fvalue')
        key_zg['allele_name'] = (Allele & 'allele_uuid="{}"'.format(allele_uuid)).fetch1('allele_name')

        zygosity = (alyxraw.AlyxRaw.Field & key & 'fname="zygosity"').fetch1('fvalue') 
        if zygosity != 'None':
            zygosity_types = {
                '0': 'Absent',
                '1': 'Heterozygous',
                '2': 'Homozygous',
                '3': 'Present'
            }
            key_zg['zygosity'] = zygosity_types[zygosity]
        
        self.insert1(key_zg, skip_duplicates=True)


@schema
class Implant(dj.Computed):
     # <class 'subjects.models.Subject'>
    definition = """
    -> Subject
    ---
    subject_uuid:               varchar(36)         # inherited from Subject
    implant_weight=null:		float			    # implant weight
    protocol_number:	        tinyint         	# protocol number
    implant_description=null:	varchar(1024)		# description
    adverse_effects=null:	    varchar(1024)		# adverse effects
    actual_severity=null:       tinyint             # actual severity, inherited from Severity
    """
    
    def make(self, key):
        key_implant = key.copy()
        key['uuid'] = key['subject_uuid']
    
        implant_weight = (alyxraw.AlyxRaw.Field & key & 'fname="implant_weight"').fetch1('fvalue')
        if implant_weight != 'None':
            key_implant['implant_weight'] = float(implant_weight)
        
        key_implant['protocol_number'] = int((alyxraw.AlyxRaw.Field & key & 'fname="protocol_number"').fetch1('fvalue'))
        
        description = (alyxraw.AlyxRaw.Field & key & 'fname="description"').fetch1('fvalue')
        if description != 'None':
            key_implant['implant_description'] = description
        
        adverse_effects = (alyxraw.AlyxRaw.Field & key & 'fname="adverse_effects"').fetch1('fvalue')
        if adverse_effects != 'None':
            key_implant['adverse_effects'] = adverse_effects
        
        actual_severity = (alyxraw.AlyxRaw.Field & key & 'fname="actual_severity"').fetch1('fvalue')
        if actual_severity != 'None':
            key_implant['actual_severity'] = int(actual_severity)

        self.insert1(key_implant, skip_duplicates=True)




