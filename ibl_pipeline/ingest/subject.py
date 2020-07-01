import datajoint as dj
import json
import uuid

from . import alyxraw, reference
from . import get_raw_field as grf

schema = dj.schema(dj.config.get('database.prefix', '') +
                   'ibl_ingest_subject')

subjects = alyxraw.AlyxRaw & 'model="subjects.subject"'


@schema
class Species(dj.Computed):
    definition = """
    (species_uuid) -> alyxraw.AlyxRaw
    ---
    binomial:           varchar(255)
    species_nickname:   varchar(255)
    species_ts=CURRENT_TIMESTAMP:   timestamp
    """
    key_source = (alyxraw.AlyxRaw & 'model="subjects.species"').proj(
        species_uuid='uuid')

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
    strain_ts=CURRENT_TIMESTAMP:   timestamp
    """
    key_source = (alyxraw.AlyxRaw & 'model="subjects.strain"').proj(
        strain_uuid='uuid')

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
    source_ts=CURRENT_TIMESTAMP:   timestamp
    """
    key_source = (alyxraw.AlyxRaw & 'model="subjects.source"').proj(
        source_uuid='uuid')

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
    sequence_ts=CURRENT_TIMESTAMP:   timestamp
    """
    key_source = (alyxraw.AlyxRaw & 'model="subjects.sequence"').proj(
        sequence_uuid='uuid')

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
    allele_ts=CURRENT_TIMESTAMP:   timestamp
    """
    key_source = (alyxraw.AlyxRaw & 'model="subjects.allele"').proj(
        allele_uuid='uuid')

    def make(self, key):
        key_allele = key.copy()
        key['uuid'] = key['allele_uuid']
        key_allele['allele_name'] = grf(key, 'nickname')

        standard_name = grf(key, 'name')
        if standard_name != 'None':
            key_allele['standard_name'] = standard_name

        self.insert1(key_allele)


@schema
class AlleleSequence(dj.Manual):
    definition = """
    allele_name:        varchar(255)    # allele name, inherited from Allele
    sequence_name:      varchar(255)    # sequence name, inherited from Sequence
    ---
    allelesequence_ts=CURRENT_TIMESTAMP:   timestamp
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
    line_ts=CURRENT_TIMESTAMP:   timestamp
    """
    key_source = (alyxraw.AlyxRaw & 'model="subjects.line"').proj(
        line_uuid='uuid')

    def make(self, key):

        key_line = key.copy()
        key['uuid'] = key['line_uuid']

        species_uuid = grf(key, 'species')
        key_line['binomial'] = \
            (Species & dict(species_uuid=uuid.UUID(species_uuid))).fetch1(
                'binomial')

        strain_uuid = grf(key, 'strain')
        if strain_uuid != 'None':
            key_line['strain_name'] = (Strain & dict(
                strain_uuid=uuid.UUID(strain_uuid))).fetch1('strain_name')

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
    ---
    lineallele_ts=CURRENT_TIMESTAMP:   timestamp
    """


@schema
class Subject(dj.Computed):
    # <class 'subjects.models.Subject'>
    definition = """
    (subject_uuid) -> alyxraw.AlyxRaw
    ---
    subject_nickname:			varchar(255)		# nickname
    sex:			            enum("M", "F", "U")	# sex
    subject_strain=null:        varchar(255)        # strain of the subject
    subject_birth_date=null:    date			    # birth date
    subject_line=null:          varchar(255)        # line of the subject
    protocol_number:	        tinyint         	# protocol number
    ear_mark=null:			    varchar(255)		# ear mark
    subject_source=null:        varchar(255)        # source name, inherited from Source
    subject_description=null:   varchar(1024)
    subject_ts=CURRENT_TIMESTAMP:   timestamp
    """

    key_source = subjects.proj(subject_uuid='uuid')

    def make(self, key):

        key_subject = key.copy()
        key['uuid'] = key['subject_uuid']

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
            key_subject['subject_line'] = \
                (Line & dict(line_uuid=uuid.UUID(line_uuid))).fetch1(
                    'line_name')

        key_subject['protocol_number'] = grf(key, 'protocol_number')

        ear_mark = grf(key, 'ear_mark')
        if ear_mark != 'None':
            key_subject['ear_mark'] = ear_mark

        source_uuid = grf(key, 'source')
        if source_uuid != 'None':
            key_subject['subject_source'] = \
                (Source & dict(source_uuid=uuid.UUID(source_uuid))).fetch1(
                    'source_name')

        description = grf(key, 'description')
        if description != 'None':
            key_subject['subject_description'] = description

        self.insert1(key_subject)


@schema
class SubjectCullMethod(dj.Computed):
    definition = """
    -> Subject
    ---
    cull_method:       varchar(255)
    cull_method_ts=CURRENT_TIMESTAMP:   timestamp
    """
    subjects_with_cull = alyxraw.AlyxRaw.Field & subjects & \
        'fname="cull_method"' & 'fvalue!="None"'
    key_source = (subjects & subjects_with_cull).proj(
        subject_uuid='uuid')

    def make(self, key):
        key_c = key.copy()
        key['uuid'] = key['subject_uuid']
        self.insert1(dict(
            **key_c, cull_method=grf(key, 'cull_method')))


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
    father=null:            uuid                # subject uuid of dad, inherited from subject
    mother1=null:           uuid                # subject uuid of mom, inherited from subject
    mother2=null:		    uuid                # subject uuid of mom2, if has one, inherited from subject
    breedingpair_ts=CURRENT_TIMESTAMP:   timestamp
    """
    key_source = (alyxraw.AlyxRaw & 'model="subjects.breedingpair"').proj(
        bp_uuid='uuid')

    def make(self, key):
        key_bp = key.copy()
        key['uuid'] = key['bp_uuid']

        line_uuid = grf(key, 'line')
        if line_uuid != 'None':
            key_bp['bp_line'] = \
                (Line & dict(line_uuid=uuid.UUID(line_uuid))).fetch1(
                    'line_name')

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
            key_bp['father'] = uuid.UUID(father)

        mother1 = grf(key, 'mother1')
        if mother1 != 'None':
            key_bp['mother1'] = uuid.UUID(mother1)

        mother2 = grf(key, 'mother2')
        if mother2 != 'None':
            key_bp['mother2'] = uuid.UUID(mother2)

        self.insert1(key_bp)


@schema
class Litter(dj.Computed):
    # <class 'subjects.models.Litter'>
    definition = """
    (litter_uuid) -> alyxraw.AlyxRaw
    ---
    litter_name:                    varchar(255)    # name of the litter
    bp_name=null:                   varchar(255)    # name of the breedingpair, inherited from BreedingPair
    litter_line=null:               varchar(255)    # line of the litter
    litter_description=null:        varchar(255)	# description
    litter_birth_date=null:		    date		    # birth date
    litter_ts=CURRENT_TIMESTAMP:   timestamp
    """
    key_source = (alyxraw.AlyxRaw & 'model="subjects.litter"').proj(
        litter_uuid='uuid')

    def make(self, key):
        key_litter = key.copy()
        key['uuid'] = key['litter_uuid']

        bp_uuid = grf(key, 'breeding_pair')
        if bp_uuid != 'None':
            key_litter['bp_name'] = \
                (BreedingPair & dict(bp_uuid=uuid.UUID(bp_uuid))).fetch1(
                    'bp_name')

        key_litter['litter_name'] = grf(key, 'name')

        line_uuid = grf(key, 'line')
        if line_uuid != 'None':
            key_litter['litter_line'] = \
                (Line & dict(line_uuid=uuid.UUID(line_uuid))).fetch1(
                    'line_name')

        description = grf(key, 'description')
        if description != 'None':
            key_litter['litter_description'] = description

        birth_date = grf(key, 'birth_date')
        if birth_date != 'None':
            key_litter['litter_birth_date'] = birth_date
        self.insert1(key_litter)


@schema
class LitterSubject(dj.Computed):
    definition = """
    -> Subject
    ---
    litter_name:        varchar(255)
    littersubject_ts=CURRENT_TIMESTAMP:   timestamp
    """

    subjects_with_litter = alyxraw.AlyxRaw.Field & subjects & \
        'fname="litter"' & 'fvalue!="None"'
    key_source = (subjects & subjects_with_litter).proj(
        subject_uuid='uuid')

    def make(self, key):
        key_ls = key.copy()
        key['uuid'] = key['subject_uuid']
        litter = grf(key, 'litter')
        key_ls['litter_name'] = \
            (Litter & dict(litter_uuid=uuid.UUID(litter))).fetch1(
                'litter_name')
        self.insert1(key_ls)


@schema
class SubjectProject(dj.Computed):
    definition = """
    -> Subject
    subject_project:           varchar(255)
    ---
    subjectproject_ts=CURRENT_TIMESTAMP:   timestamp
    """

    subjects_with_projects = alyxraw.AlyxRaw.Field & subjects & \
        'fname="projects"' & 'fvalue!="None"'
    key_source = (subjects & subjects_with_projects).proj(
        subject_uuid='uuid')

    def make(self, key):
        key_s = key.copy()
        key['uuid'] = key['subject_uuid']

        proj_uuids = grf(key, 'projects', multiple_entries=True)
        for proj_uuid in proj_uuids:
            key_sp = key_s.copy()
            try:
                key_sp['subject_project'] = \
                    (reference.Project &
                        dict(project_uuid=uuid.UUID(proj_uuid))).fetch1(
                            'project_name')
                self.insert1(key_sp)
            except Exception:
                print(key['subject_uuid'])


@schema
class SubjectUser(dj.Computed):
    definition = """
    -> Subject
    ---
    responsible_user:       varchar(255)
    subjectuser_ts=CURRENT_TIMESTAMP:   timestamp
    """

    subjects_with_user = alyxraw.AlyxRaw.Field & subjects & \
        'fname="responsible_user"' & 'fvalue!="None"'

    key_source = (subjects & subjects_with_user).proj(
        subject_uuid='uuid')

    def make(self, key):
        key_su = key.copy()
        key['uuid'] = key['subject_uuid']

        user = grf(key, 'responsible_user')
        key_su['responsible_user'] = \
            (reference.LabMember &
                dict(user_uuid=uuid.UUID(user))).fetch1('user_name')
        self.insert1(key_su)


@schema
class SubjectLab(dj.Computed):
    definition = """
    -> Subject
    ---
    lab_name:       varchar(255)
    subjectlab_ts=CURRENT_TIMESTAMP:   timestamp
    """

    def make(self, key):
        key_sl = key.copy()
        key['uuid'] = key['subject_uuid']
        lab = grf(key, 'lab')
        key_sl['lab_name'] = \
            (reference.Lab &
                dict(lab_uuid=uuid.UUID(lab))).fetch1('lab_name')
        self.insert1(key_sl)


@schema
class Caging(dj.Computed):
    definition = """
    -> Subject
    cage_name:              varchar(255)
    ---
    caging_time=null:       datetime    # time when changed to this cage
    caging_ts=CURRENT_TIMESTAMP:   timestamp
    """
    key_source = subjects.proj(subject_uuid='uuid')

    def make(self, key):
        key_cage = key.copy()
        key['uuid'] = key['subject_uuid']

        key_cage['cage_name'] = grf(key, 'cage')
        json_content = grf(key, 'json')
        if json_content != 'None':
            json_dict = json.loads(json_content)
            history = json_dict['history']
            if 'cage' not in history:
                self.insert1(key_cage, skip_duplicates=True)
            else:
                cages = history['cage']
                key_cage_i = key_cage.copy()
                for cage in cages[::-1]:
                    cage_time = cage['date_time']
                    key_cage_i['caging_time'] = cage_time[:-6]
                    self.insert1(key_cage_i, skip_duplicates=True)
                    if cage['value'] != 'None':
                        key_cage_i['cage_name'] = cage['value']


@schema
class UserHistory(dj.Computed):
    definition = """
    -> Subject
    user_name:              varchar(255)  # username
    ---
    user_change_time=null:  datetime      # time when changed to this user
    userhistory_ts=CURRENT_TIMESTAMP:   timestamp
    """

    key_source = subjects.proj(subject_uuid='uuid')

    def make(self, key):
        key_user = key.copy()
        key['uuid'] = key['subject_uuid']

        user = grf(key, 'responsible_user', model='subjects.subject')
        key_user['user_name'] = \
            (reference.LabMember &
             dict(user_uuid=uuid.UUID(user))).fetch1('user_name')

        json_content = grf(key, 'json', model='subjects.subject')
        if json_content != 'None':
            json_content = json_content.replace("\'", "\"")
            json_dict = json.loads(json_content)
            history = json_dict['history']
            if 'reponsible_user' not in history:
                self.insert1(key_user)
            else:
                users = history['responsible_user']
                key_user_i = key_user.copy()
                for user in users[::-1]:
                    user_change_time = user['date_time']
                    key_user_i['user_change_time'] = user_change_time[:-6]
                    self.insert1(key_user_i)
                    if user['value'] != 'None':
                        user_uuid = user['value']
                        key_user_i['user_name'] = \
                            (reference.LabMember &
                             dict(user_uuid=uuid.UUID(user_uuid))).fetch1(
                                 'user_name')
        else:
            self.insert1(key_user)


@schema
class Weaning(dj.Computed):
    definition = """
    -> Subject
    ---
    wean_date=null:			date			# wean date
    weaning_ts=CURRENT_TIMESTAMP:   timestamp
    """

    subjects_with_wean = alyxraw.AlyxRaw.Field & subjects & \
        'fname="wean_date"' & 'fvalue!="None"'
    key_source = (subjects & subjects_with_wean).proj(
        subject_uuid='uuid')

    def make(self, key):
        key_weaning = key.copy()
        key['uuid'] = key['subject_uuid']

        key_weaning['wean_date'] = grf(key, 'wean_date')
        self.insert1(key_weaning)


@schema
class Death(dj.Computed):
    definition = """
    -> Subject
    ---
    death_date=null:         date
    death_ts=CURRENT_TIMESTAMP:   timestamp
    """
    subjects_with_death = alyxraw.AlyxRaw.Field & subjects & \
        'fname="death_date"' & 'fvalue!="None"'
    key_source = (subjects & subjects_with_death).proj(
        subject_uuid='uuid')

    def make(self, key):
        key_death = key.copy()
        key['uuid'] = key['subject_uuid']
        key_death['death_date'] = grf(key, 'death_date')
        self.insert1(key_death)


@schema
class Food(dj.Computed):
    definition = """
    (food_uuid) -> alyxraw.AlyxRaw
    ---
    food_name:              varchar(255)
    food_description='':    varchar(255)
    food_ts=CURRENT_TIMESTAMP:   timestamp
    """
    key_source = (alyxraw.AlyxRaw & 'model="misc.food"').proj(
        food_uuid='uuid')

    def make(self, key):
        key_food = key.copy()
        key['uuid'] = key['food_uuid']
        key_food['food_name'] = grf(key, 'name')

        description = grf(key, 'description')
        if description != 'None':
            key_food['food_description'] = description

        self.insert1(key_food)


@schema
class CageType(dj.Computed):
    definition = """
    (cage_type_uuid) -> alyxraw.AlyxRaw
    ---
    cage_type_name:                     varchar(255)
    cage_type_description='':           varchar(255)
    cage_type_ts=CURRENT_TIMESTAMP:     timestamp
    """
    key_source = (alyxraw.AlyxRaw & 'model="misc.cagetype"').proj(
        cage_type_uuid='uuid')

    def make(self, key):
        key_cage_type = key.copy()
        key['uuid'] = key['cage_type_uuid']
        key_cage_type['cage_type_name'] = grf(key, 'name')

        description = grf(key, 'description')
        if description != 'None':
            key_cage_type['cage_type_description'] = description

        self.insert1(key_cage_type)


@schema
class Enrichment(dj.Computed):
    definition = """
    (enrichment_uuid) -> alyxraw.AlyxRaw
    ---
    enrichment_name:                    varchar(255)
    enrichment_description='':           varchar(255)
    enrichment_ts=CURRENT_TIMESTAMP:    timestamp
    """
    key_source = (alyxraw.AlyxRaw & 'model="misc.enrichment"').proj(
        enrichment_uuid='uuid')

    def make(self, key):
        key_enrichment = key.copy()
        key['uuid'] = key['enrichment_uuid']
        key_enrichment['enrichment_name'] = grf(key, 'name')

        description = grf(key, 'description')
        if description != 'None':
            key_enrichment['enrichment_description'] = description

        self.insert1(key_enrichment)


@schema
class Housing(dj.Computed):
    definition = """
    (housing_uuid) -> alyxraw.AlyxRaw
    ---
    cage_name:                      varchar(255)
    food_name=null:                 varchar(255)
    cage_type_name=null:            varchar(255)
    enrichment_name=null:           varchar(255)
    cage_cleaning_frequency=null:   int
    light_cycle=null:               int
    housing_description='':         varchar(255)
    housing_ts=CURRENT_TIMESTAMP:   timestamp
    """
    key_source = (alyxraw.AlyxRaw & 'model="misc.housing"').proj(
        housing_uuid='uuid')

    def make(self, key):
        key_housing = key.copy()
        key['uuid'] = key['housing_uuid']
        key_housing['cage_name'] = grf(key, 'cage_name')

        food_uuid = grf(key, 'food')
        if food_uuid != 'None':
            key_housing['food_name'] = \
                (Food & dict(food_uuid=uuid.UUID(food_uuid))).fetch1(
                    'food_name')

        enrichment_uuid = grf(key, 'enrichment')
        if enrichment_uuid != 'None':
            key_housing['enrichment_name'] = \
                (Enrichment &
                 dict(enrichment_uuid=uuid.UUID(enrichment_uuid))).fetch1(
                    'enrichment_name')

        cage_type_uuid = grf(key, 'cage_type')
        if cage_type_uuid != 'None':
            key_housing['cage_type_name'] = \
                (CageType &
                 dict(cage_type_uuid=uuid.UUID(cage_type_uuid))).fetch1(
                    'cage_type_name')

        frequency = grf(key, 'cage_cleaning_frequency_days')
        if frequency != 'None':
            key_housing['cage_cleaning_frequency'] = frequency

        light_cycle = grf(key, 'light_cycle')
        if light_cycle != 'None':
            key_housing['light_cycle'] = light_cycle

        description = grf(key, 'description')
        if description != 'None':
            key_housing['housing_description'] = description

        self.insert1(key_housing)


@schema
class SubjectHousing(dj.Computed):
    definition = """
    (subject_housing_uuid) -> alyxraw.AlyxRaw
    ---
    housing_start_time:       datetime
    housing_end_time=null:    datetime
    cage_name:                varchar(255)
    subject_uuid:             uuid
    subject_housing_ts=CURRENT_TIMESTAMP    :  timestamp
    """
    key_source = (alyxraw.AlyxRaw & 'model="misc.housingsubject"').proj(
        subject_housing_uuid='uuid')

    def make(self, key):

        key_subj_housing = key.copy()
        key['uuid'] = key['subject_housing_uuid']

        key_subj_housing['housing_start_time'] = grf(key, 'start_datetime')

        end_time = grf(key, 'end_datetime')
        if end_time != 'None':
            key_subj_housing['housing_end_time'] = end_time

        key_subj_housing['subject_uuid'] = grf(key, 'subject')

        housing = grf(key, 'housing')
        if housing == 'None':
            return
        key_subj_housing['cage_name'] = \
            (Housing & dict(housing_uuid=uuid.UUID(housing))).fetch1(
                'cage_name')

        self.insert1(key_subj_housing)


@schema
class GenotypeTest(dj.Computed):
    # <class 'subjects.models.Subject'>
    # <class 'subjects.models.Zygosity'>
    # genotype = models.ManyToManyField('Allele', through='Zygosity')
    definition = """
    (genotype_test_uuid) -> alyxraw.AlyxRaw
    ---
    subject_uuid:       uuid
    sequence_name:      varchar(255)              # inherited from Sequence
    test_result:		enum("Present", "Absent") # test result
    genotypetest_ts=CURRENT_TIMESTAMP:   timestamp
    """
    key_source = (alyxraw.AlyxRaw & 'model = "subjects.genotypetest"').proj(
        genotype_test_uuid='uuid')

    def make(self, key):
        key_gt = key.copy()
        key['uuid'] = key['genotype_test_uuid']
        key_gt['subject_uuid'] = uuid.UUID(grf(key, 'subject'))

        sequence_uuid = grf(key, 'sequence')
        key_gt['sequence_name'] = \
            (Sequence & dict(sequence_uuid=uuid.UUID(sequence_uuid))).fetch1(
                'sequence_name')

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
    subject_uuid:       uuid
    allele_name:        varchar(255)            # inherited from Allele
    zygosity:           enum("Present", "Absent", "Homozygous", "Heterozygous") # zygosity
    zygosity_ts=CURRENT_TIMESTAMP:   timestamp
    """
    key_source = (alyxraw.AlyxRaw & 'model = "subjects.zygosity"').proj(
        zygosity_uuid='uuid')

    def make(self, key):

        key_zg = key.copy()
        key['uuid'] = key['zygosity_uuid']
        key_zg['subject_uuid'] = uuid.UUID(grf(key, 'subject'))

        if not len(Subject & key_zg):
            return

        allele_uuid = grf(key, 'allele')
        key_zg['allele_name'] = \
            (Allele & dict(allele_uuid=uuid.UUID(allele_uuid))).fetch1(
                'allele_name')

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
    -> Subject
    ---
    implant_weight:		        float			    # implant weight
    adverse_effects=null:	    varchar(2048)		# adverse effects
    actual_severity=null:       tinyint             # actual severity, inherited from Severity
    protocol_number:            tinyint
    implant_ts=CURRENT_TIMESTAMP:   timestamp
    """
    subjects_with_implant = alyxraw.AlyxRaw.Field & subjects & \
        'fname="implant_weight"' & 'fvalue!="None"'
    key_source = (subjects & subjects_with_implant).proj(
        subject_uuid='uuid')

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
