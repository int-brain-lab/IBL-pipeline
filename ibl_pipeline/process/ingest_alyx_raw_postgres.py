'''
This script loads the data from alyx postgres database and insert the entries into the alyxraw table.
'''
import os, json, logging, math, datetime, re, django, warnings
from ibl_pipeline.ingest import alyxraw, QueryBuffer
from tqdm import tqdm
import datajoint as dj


mode = os.getenv('MODE')

django.setup()

# alyx models
import misc, subjects, actions, data, experiments


# logger does not work without this somehow
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logging.basicConfig(
    format='%(asctime)s - %(message)s',
    handlers=[
        # write info into both the log file and console
        logging.FileHandler("/src/IBL-pipeline/ibl_pipeline/process/logs/main_ingest.log"),
        logging.StreamHandler()],
    level=25)

logger = logging.getLogger(__name__)


# Currently I'm not aware of a way to get all ManyToMany fields in a django model,
# so have to pre-know the ManyToMany field names

# TODO: for public database, there are some tables that do not get released
# for a list, check the internal v.s. shared modules

TABLES_OF_INTEREST = [
    # misc.models
    {'alyx_model': misc.models.Lab, 'many_to_many_fields': []},
    {'alyx_model': misc.models.LabLocation, 'many_to_many_fields': []},
    {'alyx_model': misc.models.LabMember, 'many_to_many_fields': []},
    {'alyx_model': misc.models.LabMembership, 'many_to_many_fields': []},
    {'alyx_model': misc.models.CageType, 'many_to_many_fields': []},
    {'alyx_model': misc.models.Enrichment, 'many_to_many_fields': []},
    {'alyx_model': misc.models.Food, 'many_to_many_fields': []},
    {'alyx_model': misc.models.Housing, 'many_to_many_fields': ['subjects']},
    # subjects.models
    {'alyx_model': subjects.models.Project, 'many_to_many_fields': ['users']},
    {'alyx_model': subjects.models.Source, 'many_to_many_fields': []},
    {'alyx_model': subjects.models.Species, 'many_to_many_fields': []},
    {'alyx_model': subjects.models.Strain, 'many_to_many_fields': []},
    {'alyx_model': subjects.models.Sequence, 'many_to_many_fields': []},
    {'alyx_model': subjects.models.Allele, 'many_to_many_fields': ['sequences']},
    {'alyx_model': subjects.models.Line, 'many_to_many_fields': ['alleles']},
    {'alyx_model': subjects.models.Subject, 'many_to_many_fields': ['projects']},
    {'alyx_model': subjects.models.BreedingPair, 'many_to_many_fields': []},
    {'alyx_model': subjects.models.Litter, 'many_to_many_fields': []},
    {'alyx_model': subjects.models.GenotypeTest, 'many_to_many_fields': []},
    {'alyx_model': subjects.models.Zygosity, 'many_to_many_fields': []},
    # actions.models
    {'alyx_model': actions.models.ProcedureType, 'many_to_many_fields': []},
    {'alyx_model': actions.models.Surgery, 'many_to_many_fields': []},
    {'alyx_model': actions.models.CullMethod, 'many_to_many_fields': []},
    {'alyx_model': actions.models.CullReason, 'many_to_many_fields': []},
    {'alyx_model': actions.models.Cull, 'many_to_many_fields': []},
    {'alyx_model': actions.models.Weighing, 'many_to_many_fields': []},
    {'alyx_model': actions.models.WaterType, 'many_to_many_fields': []},
    {'alyx_model': actions.models.WaterRestriction, 'many_to_many_fields': ['users', 'procedures']},
    {'alyx_model': actions.models.WaterAdministration, 'many_to_many_fields': []},
    {'alyx_model': actions.models.Session, 'many_to_many_fields': ['users', 'procedures']},
    # data.models
    {'alyx_model': data.models.DataFormat, 'many_to_many_fields': []},
    {'alyx_model': data.models.DataRepositoryType, 'many_to_many_fields': []},
    {'alyx_model': data.models.DataRepository, 'many_to_many_fields': []},
    {'alyx_model': data.models.DatasetType, 'many_to_many_fields': []},
    {'alyx_model': data.models.Dataset, 'many_to_many_fields': []}, # very big table, usually handled separately
    {'alyx_model': data.models.FileRecord, 'many_to_many_fields': []}, # very big table, usually handled separately
    # experiments.models
    {'alyx_model': experiments.models.CoordinateSystem, 'many_to_many_fields': []},
    {'alyx_model': experiments.models.ProbeModel, 'many_to_many_fields': []},
    {'alyx_model': experiments.models.ProbeInsertion, 'many_to_many_fields': []},
    {'alyx_model': experiments.models.TrajectoryEstimate, 'many_to_many_fields': []}
]


def get_alyx_model_name(alyx_model):
    """get alyx model name ("model" field in alyxraw.AlyxRaw) from an alyx model object

    Args:
        alyx_model (alyx model object): alyx model object, e.g. misc.models.Lab

    Returns:
        [str]: "model" field in alyxraw.AlyxRaw, e.g. misc.lab
    """
    return alyx_model._meta.db_table.replace('_', '.')


def get_field_names(alyx_model):
    """Get all field names of an alyx model, ManyToMany fields are not included

    Args:
        alyx_model (django.model object): alyx model

    Returns:
        [list]: list of field names (property name), including foreign key references, not ManyToMany fields
    """
    return [field.name for field in alyx_model._meta.fields]


def get_tables_with_auto_datetime(tables=None):

    if not tables:
        tables = [t['alyx_model'] for t in TABLES_OF_INTEREST]

    return([t for t in tables
            if 'auto_datetime' in get_field_names(t)])


def insert_alyx_entries_model(
        alyx_model, many_to_many_fields=[],
        alyxraw_dj_module=alyxraw,
        backtrack_days=None):
    """Insert alyx entries into alyxraw tables for a particular alyx model

    Args:
        alyx_model (django.model object): alyx model
        many_to_many_fields (list): list of str for many to many fields that need to be ingested into datajoint tables.
        alyxraw_dj_module (datajoint module): datajoint module containing AlyxRaw tables, either alyxraw or alyxraw update
        backtrack_days (int, optional): number of days the data are within to backtrack and ingest,
            just applicable to tables with auto_datetime field
    """
    if backtrack_days:
        # filtering the alyx table - get more recent entries within the backtrack_days
        # only applicable to alyx models having "auto_datetime" and FileRecord alyx model
        date_cut = datetime.datetime.strptime(
                os.getenv('ALYX_DL_DATE'), '%Y-%m-%d').date() - \
            datetime.timedelta(days=backtrack_days)
        if alyx_model in get_tables_with_auto_datetime():
            # actions.models.Session, data.models.Dataset, experiments.models.ProbeInsertion
            entries = alyx_model.objects.filter(
                auto_datetime__date__gte=date_cut)
        elif alyx_model == data.models.FileRecord:
            entries = alyx_model.objects.filter(
                dataset__auto_datetime__date__gte=date_cut, exists=True)
        else:
            entries = alyx_model.objects.all()
    elif alyx_model == data.models.FileRecord:
        # for FileRecord alyx model, restrict to only the entries where the file does exist
        entries = alyx_model.objects.filter(exists=True)
    else:
        entries = alyx_model.objects.all()

    # ingest into main table
    model_name = get_alyx_model_name(alyx_model)

    # This is not very slow, if too slow, use QueryBuffer instead
    alyxraw_dj_module.AlyxRaw.insert(
        [dict(uuid=s, model=model_name) for s in entries.values_list('id', flat=True)],
        skip_duplicates=True)

    # ingest into part table AlyxRaw.Field
    alyxraw_field_buffer = QueryBuffer(alyxraw_dj_module.AlyxRaw.Field)

    # ingest fields and single foreign key references in alyxraw.AlyxRaw.Field
    field_names = get_field_names(alyx_model)

    for r in tqdm(entries):
        # e.g. for table subjects.models.Subject, each r is a subject queryset
        # for one subject
        try:
            for field_name in field_names:
                if field_name == 'id':
                    continue

                field_entry = dict(uuid=r.id)
                field_entry['fname'] = field_name
                field_value = getattr(r, field_name)

                if field_name == 'json' and field_value:
                    # handles the 'json' field - store the json dump
                    field_entry['fvalue'] = json.dumps(field_value)
                    if len(field_entry['fvalue']) < 10000:
                        # if the json dump is too large, skip
                        field_entry['value_idx'] = 0
                        alyxraw_field_buffer.add_to_queue1(field_entry)
                    else:
                        continue
                elif field_name == 'narrative' and field_value is not None:
                    # handles 'narrative' field with emoji - filter out emoji
                    emoji_pattern = re.compile(
                        "["
                        u"\U0001F600-\U0001F64F"  # emoticons
                        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                        u"\U0001F680-\U0001F6FF"  # transport & map symbols
                        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                        u"\U00002702-\U000027B0"
                        u"\U000024C2-\U0001F251"
                        "]+", flags=re.UNICODE)

                    field_entry['value_idx'] = 0
                    field_entry['fvalue'] = emoji_pattern.sub(r'', field_value)
                    alyxraw_field_buffer.add_to_queue1(field_entry)
                elif (not isinstance(field_value, (float, int)) and not field_value) or \
                        (isinstance(field_value, (float, int)) and math.isnan(field_value)):
                    # handle "falsy" field value - store as string 'None'
                    field_entry['value_idx'] = 0
                    field_entry['fvalue'] = 'None'
                    alyxraw_field_buffer.add_to_queue1(field_entry)
                elif isinstance(field_value, str):
                    field_entry['value_idx'] = 0
                    field_entry['fvalue'] = field_value
                    alyxraw_field_buffer.add_to_queue1(field_entry)
                elif isinstance(field_value, (bool, float, int,
                                              datetime.datetime, datetime.date)):
                    field_entry['value_idx'] = 0
                    field_entry['fvalue'] = str(field_value)
                    alyxraw_field_buffer.add_to_queue1(field_entry)
                else:
                    # special handling for foreign key object
                    field_entry['value_idx'] = 0
                    fk_id = field_name + '_id'
                    if hasattr(r, fk_id):
                        field_entry['fvalue'] = str(getattr(r, fk_id))
                        alyxraw_field_buffer.add_to_queue1(field_entry)

                if alyxraw_field_buffer.flush_insert(skip_duplicates=True, chunksz=10000):
                    logger.log(25, 'Inserted 10000 raw field tuples')

            # ingest many to many fields into alyxraw.AlyxRaw.Field
            for field_name in many_to_many_fields:
                for obj_idx, obj in enumerate(getattr(r, field_name).all()):
                    alyxraw_field_buffer.add_to_queue1(
                        dict(uuid=r.id, fname=field_name,
                             value_idx=obj_idx, fvalue=str(obj.id)))
                    if alyxraw_field_buffer.flush_insert(skip_duplicates=True, chunksz=10000):
                        logger.log(25, 'Inserted 10000 AlyxRaw.Field entries')

        except Exception as e:
            logger.log(25, 'Problematic entry {} of model {} with error {}'.format(
                r.id, model_name, str(e)))

    if alyxraw_field_buffer.flush_insert(skip_duplicates=True):
        logger.log(25, 'Inserted all remaining raw field tuples')


def insert_to_update_alyxraw_postgres(
        alyx_models=None, delete_update_tables_first=False):

    """Ingest entries into update_ibl_alyxraw from postgres alyx instance

    Args:
        alyx_models (list of alyx model django objects): list of alyx django models
        delete_update_tables_first (bool, optional): whether to delete the update module alyx raw tables first. Defaults to False.
    """
    if not alyx_models:
        alyx_models = TABLES_OF_INTEREST

    alyxraw_schema_name = dj.config.get('database.prefix', '') + 'update_ibl_alyxraw'

    with dj.config(safemode=False):

        if delete_update_tables_first:
            logger.log(25, 'Deleting update ibl alyxraw tables...')
            # check existence of update_alyxraw
            if alyxraw_schema_name in dj.list_schemas():
                alyxraw_update = dj.create_virtual_module(
                    'alyxraw', alyxraw_schema_name)
                if hasattr(alyxraw_update, 'AlyxRaw') and alyxraw_update.AlyxRaw:
                    alyxraw_update.AlyxRaw.Field.delete_quick()
                    alyxraw_update.AlyxRaw.delete_quick()
            else:
                warnings.warn(f'{alyxraw_schema_name} does not exist, create alyxraw_module')

    schema = dj.schema(alyxraw_schema_name)

    @schema
    class AlyxRaw(dj.Manual):
        definition = '''
        uuid: uuid  # pk field (uuid string repr)
        ---
        model: varchar(255)  # alyx 'model'
        '''

        class Field(dj.Part):
            definition = '''
            -> master
            fname: varchar(255)  # field name
            value_idx: tinyint
            ---
            fvalue=null: varchar(40000)  # field value in the position of value_idx
            index (fname)
            '''
    alyxraw_update = dj.create_virtual_module('alyx_raw', alyxraw_schema_name)

    for model in alyx_models:
        # skip big tables DataSet and FileRecord for updates
        if model['alyx_model'] not in [data.models.Dataset, data.models.FileRecord]:
            logger.log(25, 'Ingesting alyx table {} into datajoint update_alyxraw...'.format(get_alyx_model_name(model['alyx_model'])))
            insert_alyx_entries_model(model['alyx_model'],
                                      model['many_to_many_fields'],
                                      alyxraw_dj_module=alyxraw_update)


def main(backtrack_days=3):

    for t in TABLES_OF_INTEREST:
        logger.log(25, 'Ingesting alyx table {} into datajoint alyxraw...'.format(get_alyx_model_name(t['alyx_model'])))
        insert_alyx_entries_model(t['alyx_model'], t['many_to_many_fields'], backtrack_days=backtrack_days)


if __name__ == '__main__':
    main()
