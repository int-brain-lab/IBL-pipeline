'''
This script loads the data from alyx postgres database and insert the entries into the alyxraw table.
'''
from ibl_pipeline.acquisition_internal import WaterAdministrationSession
from ibl_pipeline.action_internal import WaterAdministration
import os, json, logging, math, datetime, re, django, warnings
from ibl_pipeline.ingest import alyxraw, QueryBuffer
from tqdm import tqdm
import numpy as np
import datajoint as dj


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


TABLES_OF_INTEREST = [
    # misc.models
    misc.models.Lab,
    misc.models.LabLocation,
    misc.models.LabMember,
    misc.models.LabMembership,
    misc.models.CageType,
    misc.models.Enrichment,
    # subjects.models
    subjects.models.Project,
    subjects.models.Source,
    subjects.models.Species,
    subjects.models.Strain,
    subjects.models.Sequence,
    subjects.models.Allele,
    subjects.models.Line,
    subjects.models.Subject,
    subjects.models.BreedingPair,
    subjects.models.Litter,
    subjects.models.GenotypeTest,
    subjects.models.Zygosity,
    # actions.models
    actions.models.ProcedureType,
    actions.models.Surgery,
    actions.models.CullMethod,
    actions.models.CullReason,
    actions.models.Cull,
    actions.models.Weighing,
    actions.models.WaterType,
    actions.models.WaterRestriction,
    actions.models.WaterAdministration,
    actions.models.Session,
    # data.models
    data.models.DataFormat,
    data.models.DataRepositoryType,
    data.models.DataRepository,
    data.models.DatasetType,
    data.models.Dataset,
    data.models.FileRecord,
    # experiments.models
    experiments.models.CoordinateSystem,
    experiments.models.ProbeModel,
    experiments.models.ProbeInsertion,
    experiments.models.TrajectoryEstimate,
]


def get_alyx_model_name(alyx_model):
    """get alyx model name ("model" field in alyxraw.AlyxRaw) from an alyx model object

    Args:
        alyx_model (alyx model object): alyx model object, e.g. misc.models.Lab

    Returns:
        [str]: "model" field in alyxraw.AlyxRaw, e.g. misc.lab
    """
    # return alyx_model.__module__.split('.')[0] + '.' + alyx_model.__name__.lower()
    return alyx_model._meta.db_table.replace('_', '.')

def get_field_names(alyx_model):
    return [field.name for field in alyx_model._meta.fields]


def get_tables_with_auto_datetime(tables=None):

    if not tables:
        tables = TABLES_OF_INTEREST

    return([t for t in tables
            if 'auto_datetime' in get_field_names(t)])


def insert_alyx_entries_model(
        alyx_model,
        alyxraw_dj_module=alyxraw,
        backtrack_days=None):
    """Insert alyx entries into alyxraw tables for a particular alyx model

    Args:
        alyx_model (django.model object): alyx model
        alyxraw_dj_module (datajoint module): datajoint module containing AlyxRaw tables, either alyxraw or alyxraw update
        backtrack_days (int, optional): number of days the data are within to backtrack and ingest,
            just applicable to tables with auto_datetime field
    """
    if backtrack_days:
        # only ingest the latest data
        date_cut = datetime.datetime.strptime(
                os.getenv('ALYX_DL_DATE'), '%Y-%m-%d').date() - \
            datetime.timedelta(days=backtrack_days)
        if alyx_model in get_tables_with_auto_datetime():
            entries = alyx_model.objects.filter(
                auto_datetime__date__gte=date_cut)
        elif alyx_model == data.models.FileRecord:
            entries = alyx_model.objects.filter(
                dataset__auto_datetime__date__gte=date_cut, exists=True)
        else:
            entries = alyx_model.objects.all()
    elif alyx_model == data.models.FileRecord:
        entries = alyx_model.objects.filter(exists=True)
    else:
        entries = alyx_model.objects.all()

    # ingest into main table
    model_name = get_alyx_model_name(alyx_model)
    pk_list = entries.values_list('id', flat=True)

    # This is not very slow, if too slow, use QueryBuffer instead
    alyxraw_dj_module.AlyxRaw.insert(
        [dict(uuid=s, model=model_name) for s in pk_list],
        skip_duplicates=True)

    # ingest into part table
    ib_part = QueryBuffer(alyxraw_dj_module.AlyxRaw.Field)
    for r in tqdm(entries.values()):
        try:

            for field_name, field_value in r.items():
                field_entry = dict(uuid=r['id'])
                if field_name == 'id':
                    continue
                field_entry['fname'] = field_name

                # in alyxmodel, all foreign key references ends with `_id`,
                # remove `_id` in the fname to be compatible with previous json dump convention
                if field_name.endswith('_id'):
                    field_name = field_name.split('_id')[0]

                # dump the json field
                if field_name == 'json' and field_value:
                    field_entry['value_idx'] = 0
                    field_entry['fvalue'] = json.dumps(field_value)
                    if len(field_entry['fvalue']) < 10000:
                        ib_part.add_to_queue1(field_entry)
                    else:
                        continue
                elif field_name == 'narrative' and field_value is not None:
                    # filter out emoji
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
                elif (not field_value) or \
                        (isinstance(field_value, float) and math.isnan(field_value)):
                    field_entry['value_idx'] = 0
                    field_entry['fvalue'] = 'None'
                    ib_part.add_to_queue1(field_entry)
                elif isinstance(field_value, list) and \
                        (isinstance(field_value[0], dict) or isinstance(field_value[0], str)):
                    for value_idx, value in enumerate(field_value):
                        field_entry['value_idx'] = value_idx
                        field_entry['fvalue'] = str(value)
                        ib_part.add_to_queue1(field_entry)
                else:
                    field_entry['value_idx'] = 0
                    field_entry['fvalue'] = str(field_value)
                    ib_part.add_to_queue1(field_entry)

                if ib_part.flush_insert(skip_duplicates=True, chunksz=10000):
                    logger.log(25, 'Inserted 10000 raw field tuples')

        except Exception as e:
            logger.log(25, 'Problematic entry {} of model {} with error {}'.format(
                r['id'], model_name, str(e)))

    if ib_part.flush_insert(skip_duplicates=True):
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
            print('Deleting alyxraw update...')
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
        if model not in [data.models.Dataset, data.models.FileRecord]:
            logger.log(25, 'Ingesting alyx table {} into datajoint update_alyxraw...'.format(get_alyx_model_name(model)))
            insert_alyx_entries_model(
                model, alyxraw_dj_module=alyxraw_update)


def main(backtrack_days=3):

    for t in TABLES_OF_INTEREST:
        logger.log(25, 'Ingesting alyx table {} into datajoint alyxraw...'.format(get_alyx_model_name(model)))
        insert_alyx_entries_model(t, backtrack_days=backtrack_days)


if __name__ == '__main__':
    main()
