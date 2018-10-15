import datajoint as dj
import json

from ibl.ingest import alyxraw, reference
from ibl.ingest import get_raw_field as grf

schema = dj.schema(dj.config.get('database.prefix', '') + 'ibl_ingest_subject')

@schema
class Species(dj.Computed):
    definition = """
    (species_uuid) -> alyxraw.AlyxRaw
    ---
    binomial:           varchar(255)
    display_name:       varchar(255)         
    """
    key_source = (alyxraw.AlyxRaw & 'model="subjects.species"').proj(species_uuid="uuid")
    
    def make(self, key):
        key_species = key.copy()
        key['uuid'] = key['species_uuid']
        key_species['binomial'] = grf(key, 'binomial')
        key_species['display_name'] = grf(key, 'display_name')
        
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
        key_strain['strain_name'] = grf(key, 'descriptive_name')
        
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
    base_pairs=null:	        varchar(255)	# base pairs
    sequence_description=null:	varchar(255)	# description
    """
    key_source = (alyxraw.AlyxRaw & 'model="subjects.sequence"').proj(sequence_uuid="uuid")
    
    def make(self, key):
        key_seq = key.copy()
        key['uuid'] = key['sequence_uuid']
        key_seq['sequence_name'] = grf(key, 'informal_name')
        
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
        key_allele['allele_name'] = grf(key, 'informal_name')

        standard_name = grf(key, 'standard_name')
        if standard_name != 'None':
            key_allele['standard_name'] = standard_name

        self.insert1(key_allele)

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
        key_line['auto_name'] = grf(key, 'auto_name')
        
        active = grf(key, 'is_active')
        key_line['is_active'] = active=="True"
        
        self.insert1(key_line)

@schema
class LineAllele(dj.Manual):
    definition = """
    binomial:               varchar(255)	# binomial, inherited from Species          
    line_name:				varchar(255)	# name
    allele_name:			varchar(255)             # informal name
    """

@schema
class Subject(dj.Computed):
    # <class 'subjects.models.Subject'>
    definition = """
    (subject_uuid) -> alyxraw.AlyxRaw
    --- 
    lab_name=null:              varchar(255)
    nickname:			        varchar(255)		# nickname
    sex:			            enum("M", "F", "U")	# sex
    subject_birth_date=null:    date			    # birth date
    protocol_number:	        tinyint         	# protocol number
    ear_mark=null:			    varchar(255)		# ear mark
    subject_source=null:        varchar(255)        # source name, inherited from Source
    responsible_user=null:      varchar(255)        # user_name, inherited from reference.LabMember
    subject_description=null:   varchar(1024)
    """
    key_source = (alyxraw.AlyxRaw & 'model = "subjects.subject"').proj(subject_uuid='uuid')

    def make(self, key):

        key_subject = key.copy()
        key['uuid'] = key['subject_uuid']

        nick_name = grf(key, 'nickname')
        if nick_name != 'None':
            key_subject['nickname'] = nick_name
        
        sex = grf(key, 'sex')
        if sex != 'None':
            key_subject['sex'] = sex

        birth_date = grf(key, 'birth_date')
        if birth_date != 'None':
            key_subject['subject_birth_date'] = birth_date
        
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
    line_name=null:         varchar(255)        # line name, inherited from Line
    bp_name:			    varchar(255)		# name
    bp_description=null:	varchar(1024)		# description
    start_date:		        date			    # start date
    end_date=null:		    date			    # end date
    father=null:            varchar(64)         # subject uuid of dad, inherited from subject
    mother1=null:           varchar(64)         # subject uuid of mom, inherited from subject
    mother2=null:		    varchar(64)         # subject uuid of mom2, if has one, inherited from subject
    """
    key_source = (alyxraw.AlyxRaw & 'model="subjects.breedingpair"').proj(bp_uuid='uuid')

    def make(self, key):
        key_bp = key.copy()
        key['uuid'] = key['bp_uuid']
        
        line_uuid = grf(key, 'line')
        if line_uuid != 'None':
            key_bp['line_name'] = (Line & 'line_uuid="{}"'.format(line_uuid)).fetch1('line_name')

        key_bp['bp_name'] = grf(key, 'name')

        description = grf(key, 'description')
        if description != 'None':
            key_bp['bp_description'] = description

        key_bp['start_date'] = grf(key, 'start_date')

        end_date = grf(key, 'end_date')
        if end_date != 'None':
            key_bp['end_date'] = end_date

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
    bp_name:                        varchar(255)    # name of the breedingpair, inherited from BreedingPair
    litter_descriptive_name=null:   varchar(255)	# descriptive name
    litter_description=null:        varchar(255)	# description
    litter_birth_date:		        date		    # birth date
    """
    key_source = (alyxraw.AlyxRaw & 'model="subjects.litter"').proj(litter_uuid='uuid')

    def make(self, key):
        key_litter = key.copy()
        key['uuid'] = key['litter_uuid']
        bp_uuid = grf(key, 'breeding_pair')
        key_litter['bp_name'] = (BreedingPair & 'bp_uuid="{}"'.format(bp_uuid)).fetch1('bp_name')

        descriptive_name = grf(key, 'descriptive_name')
        if descriptive_name != 'None':
            key_litter['litter_descriptive_name'] = descriptive_name
        
        description = grf(key, 'description')
        if description != 'None':
            key_litter['litter_description'] = description

        birth_date = grf(key, 'birth_date')
        key_litter['litter_birth_date'] = birth_date
        self.insert1(key_litter)


@schema
class LitterSubject(dj.Computed):
    definition = """
    bp_name:        varchar(255)
    litter_uuid:    varchar(64)
    subject_uuid:   varchar(64)
    """
    key_source = (alyxraw.AlyxRaw & 'model = "subjects.subject"').proj(subject_uuid='uuid')
    
    def make(self, key):
        key_ls = key.copy()
        key['uuid'] = key['subject_uuid']
        litter = grf(key, 'litter')
        if litter != 'None':
            key_ls['bp_name'], key_ls['litter_uuid'] = (Litter & 'litter_uuid="{}"'.format(litter)).fetch1('bp_name', 'litter_uuid')
            self.insert1(key_ls)

@schema
class SubjectProject(dj.Computed):
    definition = """
    subject_uuid:       varchar(64)
    project_name:       varchar(255)
    """
    key_source = (alyxraw.AlyxRaw & 'model = "subjects.subject"').proj(subject_uuid='uuid')

    def make(self, key):
        key_s = key.copy()
        key['uuid'] = key['subject_uuid']

        proj_uuids = grf(key, 'projects', multiple_entries=True)
        if proj_uuids != 'None':
            for proj_uuid in proj_uuids:
                key_sp = key_s.copy()
                key_sp['project_name'] = (reference.Project & 'project_uuid="{}"'.format(proj_uuid)).fetch1('project_name')
                self.insert1(key_sp)

@schema
class Caging(dj.Computed):
    definition = """
    -> Subject
    lamis_cage:             int
    ---
    caging_date:            datetime
    """

    def make(self, key):
        key_cage = key.copy()
        key['uuid'] = key['subject_uuid']
        cage = grf(key, 'lamis_cage')
        if cage == 'None':
            return
        else:
            key_cage['lamis_cage'] = cage
            json_content = grf(key, 'json')
            if json_content != 'None':
                json_dict = json.loads(json_content)       
                history = json_dict['history']
                if 'lamis_cage' not in history:
                    self.insert1(key_cage)
                else:
                    cages = history['lamis_cage'] 
                    key_cage_i = key_cage.copy()
                    for cage in cages[::-1]:
                        key_cage_i['caging_date'] = cage['date_time']
                        self.insert1(key_cage_i)
                        if cage['value'] != 'None':
                            key_cage_i['lamis_cage'] = cage['value']
                        

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
        
        wean_date = grf(key, 'wean_date')
        if wean_date != 'None':
            key_weaning['wean_date'] = wean_date
            self.insert1(key_weaning)


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
        death_date = grf(key, 'death_date')
        if death_date != 'None':
            key_death['death_date'] = death_date
            self.insert1(key_death)

@schema
class GenotypeTest(dj.Computed):
    # <class 'subjects.models.Subject'>
    # <class 'subjects.models.Zygosity'>
    # genotype = models.ManyToManyField('Allele', through='Zygosity')
    definition = """
    (genotype_test_uuid) -> alyxraw.AlyxRaw
    ---
    subject_uuid:               varchar(64)                     # inherited from Subject
    sequence_name:              varchar(64)                     # inherited from Sequence
    test_result:		        enum("Present", "Absent")		# test result
    """
    key_source = (alyxraw.AlyxRaw & 'model = "subjects.genotypetest"').proj(genotype_test_uuid='uuid')

    def make(self, key):
        key_gt = key.copy()
        key['uuid'] = key['genotype_test_uuid']
        key_gt['subject_uuid'] = grf(key, 'subject')
        
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
    subject_uuid:       varchar(64)             # inherited from Subject
    allele_name:        varchar(255)            # inherited from Allele
    zygosity:           enum("Present", "Absent", "Homozygous", "Heterozygous") 		# zygosity
    """
    key_source = (alyxraw.AlyxRaw & 'model = "subjects.zygosity"').proj(zygosity_uuid='uuid')

    def make(self, key):

        key_zg = key.copy()
        key['uuid'] = key['zygosity_uuid']
        key_zg['subject_uuid'] = grf(key, 'subject')
        
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
class Implant(dj.Computed):
     # <class 'subjects.models.Subject'>
    definition = """
    (subject_uuid) -> alyxraw.AlyxRaw
    ---
    implant_weight:		        float			    # implant weight
    adverse_effects=null:	    varchar(1024)		# adverse effects
    actual_severity=null:       tinyint             # actual severity, inherited from Severity 
    protocol_number:            tinyint      
    """
    key_source = (alyxraw.AlyxRaw & 'model="subjects.subject"' & (alyxraw.AlyxRaw.Field & 'fname = "implant_weight" and fvalue != "None"')).proj(subject_uuid='uuid')
    
    def make(self, key):
        key_implant = key.copy()
        key['uuid'] = key['subject_uuid']
    
        key_implant['implant_weight'] = float(grf(key, 'implant_weight'))
        
        adverse_effects = grf(key, 'adverse_effects')
        if adverse_effects != 'None':
            key_implant['adverse_effects'] = adverse_effects
        
        actual_severity = grf(key, 'actual_severity')
        if actual_severity != 'None':
            key_implant['actual_severity'] = int(actual_severity)

        key_implant['protocol_number'] = int(grf(key, 'protocol_number'))

        self.insert1(key_implant)

    





