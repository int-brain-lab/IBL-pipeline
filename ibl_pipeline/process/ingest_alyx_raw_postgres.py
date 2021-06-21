'''
This script loads the data from alyx postgres database and insert the entries into the alyxraw table.
'''
import os, json, logging, math, datetime, re, django
from ibl_pipeline.ingest import alyxraw, QueryBuffer
from tqdm import tqdm
import numpy as np

django.setup()

import misc, subjects, actions, data, experiments


# logger does not work without this somehow
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logging.basicConfig(
    format='%(asctime)s - %(message)s',
    handlers=[
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


def get_field_names(alyx_model):
    return [field.name for field in alyx_model._meta.fields]


def get_tables_with_auto_datetime(tables=None):

    if not tables:
        tables = TABLES_OF_INTEREST

    return([t for t in tables
            if 'auto_datetime' in get_field_names(t)])


def insert_alyx_entries_model(alyx_model, backtrack_days=None):
    """Insert alyx entries for a particular alyx model

    Args:
        alyx_model (django.model object): alyx model
        backtrack_days (int, optional): number of days the data are within to backtrack and ingest.
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
    model_name = alyx_model._meta.db_table.replace('_', '.')
    pk_list = entries.values_list('id', flat=True)

    alyxraw.AlyxRaw.insert(
        [dict(uuid=s, model=model_name) for s in pk_list],
        skip_duplicates=True)

    # ingest into part table
    ib_part = QueryBuffer(alyxraw.AlyxRaw.Field)
    for r in tqdm(entries.values()):
        try:
            field_entry = dict(uuid=r['id'])
            for field_name, field_value in r.items():
                if field_name == 'id':
                    continue
                field_entry['fname'] = field_name
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
                elif type(field_value) is list and \
                        (type(field_value[0]) is dict or type(field_value[0]) is str):
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


def main(backtrack_days=3):

    for t in TABLES_OF_INTEREST:
        logger.log(25, 'Ingesting alyx table {} into datajoint alyxraw...'.format(t._meta.db_table))
        insert_alyx_entries_model(t, backtrack_days=backtrack_days)


if __name__ == '__main__':
    main()
