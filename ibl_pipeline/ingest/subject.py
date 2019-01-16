import datajoint as dj
import json

from . import alyxraw, reference
from . import get_raw_field as grf

schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_ingest_subject')

@schema
class Species(dj.Computed):
    definition = """
    (species_uuid) -> alyxraw.AlyxRaw
    ---
    binomial:           varchar(255)
    species_nickname:   varchar(255)
    """
    key_source = (alyxraw.AlyxRaw & 'model="subjects.species"').proj(species_uuid="uuid")

    def make(self, key):
        key_species = key.copy()
        key['uuid'] = key['species_uuid']
        key_species['binomial'] = grf(key, 'name')
        key_species['species_nickname'] = grf(key, 'nickname')

        self.insert1(key_species)


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
        key_strain['strain_name'] = grf(key, 'name')

        description = grf(key, 'description')
        if description != 'None':
            key_strain['strain_description'] = description

        self.insert1(key_strain)


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
        key_animal_source = key.copy()
        key['uuid'] = key['source_uuid']
        key_animal_source['source_name'] = grf(key, 'name')

        description = grf(key, 'description')
        if description != 'None':
            key_animal_source['source_description'] = description
        self.insert1(key_animal_source)


@schema
class Sequence(dj.Computed):
    # <class 'subjects.models.Sequence'>
    definition = """
    (sequence_uuid) -> alyxraw.AlyxRaw
    ---
    sequence_name:		        varchar(255)	# informal name
    base_pairs=null:	        varchar(1024)	# base pairs
    sequence_description=null:	varchar(255)	# description
    """
    key_source = (alyxraw.AlyxRaw & 'model="subjects.sequence"').proj(sequence_uuid="uuid")

    def make(self, key):
        key_seq = key.copy()
        key['uuid'] = key['sequence_uuid']
        key_seq['sequence_name'] = grf(key, 'name')

        base_pairs = grf(key, 'base_pairs')
        if base_pairs != 'None':
            key_seq['base_pairs'] = base_pairs

        description = grf(key, 'description')
        if description != 'None':
            key_seq['sequence_description'] = description

        self.insert1(key_seq)


@schema
class Allele(dj.Computed):
    # <class 'subjects.models.Allele'>
    definition = """
    (allele_uuid) -> alyxraw.AlyxRaw
    ---
    allele_name:			    varchar(255)    # informal name
    standard_name=null:		    varchar(255)	# standard name
    allele_source=null:         varchar(255)    # source of the allele
    source_identifier=null:     varchar(255)    # id inside the line provider
    source_url=null:            varchar(255)    # link to the line information
    expression_data_url=null:   varchar(255)    # link to the expression pattern from Allen institute brain atlas
    """
    key_source = (alyxraw.AlyxRaw & 'model="subjects.allele"').proj(allele_uuid='uuid')

    def make(self, key):
        key_allele = key.copy()
        key['uuid'] = key['allele_uuid']
        key_allele['allele_name'] = grf(key, 'nickname')

        standard_name = grf(key, 'name')
        if standard_name != 'None':
            key_allele['standard_name'] = standard_name

        self.insert1(key_allele)


@schema
class AlleleSequence(dj.Computed):
    definition = """
    allele_name:        varchar(255)    # allele name, inherited from Allele
    sequence_name:      varchar(255)    # sequence name, inherited from Sequence
    """


@schema
class Line(dj.Computed):
    # <class 'subjects.models.Line'>
    definition = """
    (line_uuid) -> alyxraw.AlyxRaw
    ---
    binomial:                   varchar(255)	# binomial, inherited from Species          
    strain_name=null:           varchar(255)    # strain name, inherited from Strain
    line_name:				    varchar(255)	# line name
    line_description=null:		varchar(2048)	# description
    target_phenotype=null:		varchar(255)	# target phenotype
    line_nickname:				varchar(255)	# auto name
    is_active:				    boolean		    # is active
    """
    key_source = (alyxraw.AlyxRaw & 'model="subjects.line"').proj(line_uuid='uuid')

    def make(self, key):

        key_line = key.copy()
        key['uuid'] = key['line_uuid']

        species_uuid = grf(key, 'species')
        key_line['binomial'] = (Species & 'species_uuid="{}"'.format(species_uuid)).fetch1('binomial')

        strain_uuid = grf(key, 'strain')
        if strain_uuid != 'None':
            key_line['strain_name'] = (Strain & 'strain_uuid="{}"'.format(strain_uuid)).fetch1('strain_name')

        key_line['line_name'] = grf(key, 'name')

        description = grf(key, 'description')
        if description != 'None':
            key_line['line_description'] = description
        key_line['target_phenotype'] = grf(key, 'target_phenotype')
        key_line['line_nickname'] = grf(key, 'nickname')

        active = grf(key, 'is_active')
        key_line['is_active'] = active == "True"

        self.insert1(key_line)


@schema
class LineAllele(dj.Manual):
    definition = """
    line_name:				varchar(255)	# name
    allele_name:			varchar(255)    # informal name
    """


@schema
class Subject(dj.Computed):
    # <class 'subjects.models.Subject'>
    definition = """
    (subject_uuid) -> alyxraw.AlyxRaw
    ---
    lab_name:                   varchar(255)
    subject_nickname:			varchar(255)		# nickname
    sex:			            enum("M", "F", "U")	# sex
    subject_birth_date=null:    date			    # birth date
    subject_line=null:          varchar(255)        # line of the subject
    protocol_number:	        tinyint         	# protocol number
    ear_mark=null:			    varchar(255)		# ear mark
    subject_source=null:        varchar(255)        # source name, inherited from Source
    responsible_user=null:      varchar(255)        # user_name, inherited from reference.LabMember
    subject_description=null:   varchar(1024)
    """
    
    subjects = alyxraw.AlyxRaw.Field & 'model="subjects.subject"' & 'fname="lab"' & 'fvalue!="None"'
    key_source = (alyxraw.AlyxRaw & subjects).proj(subject_uuid='uuid')

    def make(self, key):

        key_subject = key.copy()
        key['uuid'] = key['subject_uuid']

        lab_uuid = grf(key, 'lab')
        key_subject['lab_name'] = (reference.Lab & 'lab_uuid="{}"'.format(lab_uuid)).fetch1('lab_name')

        nickname = grf(key, 'nickname')
        if nickname != 'None':
            key_subject['subject_nickname'] = nickname

        sex = grf(key, 'sex')
        if sex != 'None':
            key_subject['sex'] = sex

        birth_date = grf(key, 'birth_date')
        if birth_date != 'None':
            key_subject['subject_birth_date'] = birth_date
        
        line_uuid = grf(key, 'line')
        if line_uuid != 'None':
            key_subject['subject_line'] = (Line & 'line_uuid="{}"'.format(line_uuid)).fetch1('line_name')

        key_subject['protocol_number'] = grf(key, 'protocol_number')

        ear_mark = grf(key, 'ear_mark')
        if ear_mark != 'None':
            key_subject['ear_mark'] = ear_mark

        source_uuid = grf(key, 'source')
        if source_uuid != 'None':
            key_subject['subject_source'] = (Source & 'source_uuid="{}"'.format(source_uuid)).fetch1('source_name')

        user_uuid = grf(key, 'responsible_user')
        if user_uuid != 'None':
            key_subject['responsible_user'] = (reference.LabMember & 'user_uuid="{}"'.format(user_uuid)).fetch1('user_name')

        description = grf(key, 'description')
        if description != 'None':
            key_subject['subject_description'] = description

        self.insert1(key_subject)


@schema
class BreedingPair(dj.Computed):
    # <class 'subjects.models.BreedingPair'>
    definition = """
    (bp_uuid) -> alyxraw.AlyxRaw
    ---
    bp_line=null:           varchar(255)        # line name, inherited from Line
    bp_name:			    varchar(255)		# name of the breeding pair
    bp_description=null:	varchar(2048)		# description
    bp_start_date=null:		date			    # start date
    bp_end_date=null:		date			    # end date
    father=null:            varchar(64)         # subject nickname of dad, inherited from subject
    mother1=null:           varchar(64)         # subject nickname of mom, inherited from subject
    mother2=null:		    varchar(64)         # subject nickname of mom2, if has one, inherited from subject
    """
    key_source = (alyxraw.AlyxRaw & 'model="subjects.breedingpair"').proj(bp_uuid='uuid')

    def make(self, key):
        key_bp = key.copy()
        key['uuid'] = key['bp_uuid']

        line_uuid = grf(key, 'line')
        if line_uuid != 'None':
            key_bp['bp_line'] = (Line & 'line_uuid="{}"'.format(line_uuid)).fetch1('line_name')

        key_bp['bp_name'] = grf(key, 'name')

        description = grf(key, 'description')
        if description != 'None':
            key_bp['bp_description'] = description

        start_date = grf(key, 'start_date')
        if start_date != 'None':
            key_bp['bp_start_date'] = grf(key, 'start_date')

        end_date = grf(key, 'end_date')
        if end_date != 'None':
            key_bp['bp_end_date'] = end_date

        father = grf(key, 'father')
        if father != 'None':
            key_bp['father'] = father

        mother1 = grf(key, 'mother1')
        if mother1 != 'None':
            key_bp['mother1'] = mother1

        mother2 = grf(key, 'mother2')
        if mother2 != 'None':
            key_bp['mother2'] = mother2

        self.insert1(key_bp)


@schema
class Litter(dj.Computed):
    # <class 'subjects.models.Litter'>
    definition = """
    (litter_uuid) -> alyxraw.AlyxRaw
    ---
    litter_name:                    varchar(255)    # name of the litter
    bp_name=null:                   varchar(255)    # name of the breedingpair, inherited from BreedingPair
    litter_line:                    varchar(255)    # line of the litter
    litter_description=null:        varchar(255)	# description
    litter_birth_date=null:		    date		    # birth date
    """
    key_source = (alyxraw.AlyxRaw & 'model="subjects.litter"').proj(litter_uuid='uuid')

    def make(self, key):
        key_litter = key.copy()
        key['uuid'] = key['litter_uuid']
        
        bp_uuid = grf(key, 'breeding_pair')
        if bp_uuid != 'None':
            key_litter['bp_name'] = (BreedingPair & 'bp_uuid="{}"'.format(bp_uuid)).fetch1('bp_name')

        key_litter['litter_name'] = grf(key, 'name')

        line_uuid = grf(key, 'line')
        key_litter['litter_line'] = (Line & 'line_uuid="{}"'.format(line_uuid)).fetch1('line_name')

        description = grf(key, 'description')
        if description != 'None':
            key_litter['litter_description'] = description

        birth_date = grf(key, 'birth_date')
        if birth_date != 'None':
            key_litter['litter_birth_date'] = birth_date
        self.insert1(key_litter)


@schema
class LitterSubject(dj.Manual):
    definition = """
    lab_name:           varchar(255)
    subject_nickname:   varchar(255)
    ---
    litter_name:        varchar(255)
    """


@schema
class SubjectProject(dj.Manual):
    definition = """
    lab_name:               varchar(255)
    subject_nickname:       varchar(255)
    project_name:           varchar(255)
    """

@schema
class SubjectUser(dj.Manual):
    definition = """
    lab_name:               varchar(255)
    subject_nickname:       varchar(255)
    ---
    responsible_user:       varchar(255)
    """
    

@schema
class Caging(dj.Manual):
    definition = """
    lab_name:               varchar(255)
    subject_nickname:       varchar(255)
    cage_name:              varchar(255)
    ---
    caging_time=null:       datetime    # time when changed to this cage
    """

@schema
class UserHistory(dj.Manual):
    definition = """
    lab_name:               varchar(255)
    subject_nickname:       varchar(255)
    user_name:              varchar(255)  # username 
    ---
    user_change_time=null:   datetime      # time when changed to this user
    """


@schema
class Weaning(dj.Manual):
    definition = """
    lab_name:               varchar(255)
    subject_nickname:       varchar(255)
    ---
    wean_date=null:			date			# wean date
    """


@schema
class Death(dj.Manual):
    definition = """
    lab_name:               varchar(255)
    subject_nickname:        varchar(255)
    ---
    death_date=null:         date
    """


@schema
class GenotypeTest(dj.Computed):
    # <class 'subjects.models.Subject'>
    # <class 'subjects.models.Zygosity'>
    # genotype = models.ManyToManyField('Allele', through='Zygosity')
    definition = """
    (genotype_test_uuid) -> alyxraw.AlyxRaw
    ---
    lab_name:                   varchar(255)
    subject_nickname:           varchar(64)                     # inherited from Subject
    sequence_name:              varchar(64)                     # inherited from Sequence
    test_result:		        enum("Present", "Absent")		# test result
    """
    key_source = (alyxraw.AlyxRaw & 'model = "subjects.genotypetest"').proj(genotype_test_uuid='uuid')

    def make(self, key):
        key_gt = key.copy()
        key['uuid'] = key['genotype_test_uuid']
        subject_uuid = grf(key, 'subject')
        key_gt['lab_name'], key_gt['subject_nickname'] = (Subject & 'subject_uuid="{}"'.format(subject_uuid)).fetch1('lab_name', 'subject_nickname')

        sequence_uuid = grf(key, 'sequence')
        key_gt['sequence_name'] = (Sequence & 'sequence_uuid="{}"'.format(sequence_uuid)).fetch1('sequence_name')

        test_result = grf(key, 'test_result')
        key_gt['test_result'] = 'Present' if test_result else 'Absent'
        self.insert1(key_gt)


@schema
class Zygosity(dj.Computed):
    # <class 'subjects.models.Subject'>
    # <class 'subjects.models.Zygosity'>
    # genotype = models.ManyToManyField('Allele', through='Zygosity')
    definition = """
    (zygosity_uuid) -> alyxraw.AlyxRaw
    ---
    lab_name:           varchar(255)            # inherited from Subject
    subject_nickname:   varchar(64)             # inherited from Subject
    allele_name:        varchar(255)            # inherited from Allele
    zygosity:           enum("Present", "Absent", "Homozygous", "Heterozygous") 		# zygosity
    """
    key_source = (alyxraw.AlyxRaw & 'model = "subjects.zygosity"').proj(zygosity_uuid='uuid')

    def make(self, key):

        key_zg = key.copy()
        key['uuid'] = key['zygosity_uuid']
        subject_uuid = grf(key, 'subject')
        key_zg['lab_name'], key_zg['subject_nickname'] = (Subject & 'subject_uuid="{}"'.format(subject_uuid)).fetch1('lab_name', 'subject_nickname')

        allele_uuid = grf(key, 'allele')
        key_zg['allele_name'] = (Allele & 'allele_uuid="{}"'.format(allele_uuid)).fetch1('allele_name')

        zygosity = grf(key, 'zygosity')    
        zygosity_types = {
            '0': 'Absent',
            '1': 'Heterozygous',
            '2': 'Homozygous',
            '3': 'Present'
        }
        key_zg['zygosity'] = zygosity_types[zygosity]

        self.insert1(key_zg)


@schema
class Implant(dj.Manual):
    # <class 'subjects.models.Subject'>
    definition = """
    lab_name:                   varchar(255)        # inherited from Subject
    subject_nickname:           varchar(255)        # inherited from Subject
    ---
    implant_weight:		        float			    # implant weight
    adverse_effects=null:	    varchar(2048)		# adverse effects
    actual_severity=null:       tinyint             # actual severity, inherited from Severity 
    protocol_number:            tinyint
    """
