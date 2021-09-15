'''
This script loads the data from alyx postgres database and insert the entries into the alyxraw table.
'''
import os, json, logging, math, datetime, re, django, warnings
from ibl_pipeline.ingest import alyxraw, QueryBuffer
from tqdm import tqdm
import datajoint as dj
import pathlib
import numpy as np


mode = os.getenv('MODE')

django.setup()

# alyx models
import misc, subjects, actions, data, experiments


# logger does not work without this somehow
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

log_file = pathlib.Path(__file__).parent / 'logs/main_ingest.log'
log_file.parent.mkdir(parents=True, exist_ok=True)
log_file.touch(exist_ok=True)

logging.basicConfig(
    format='%(asctime)s - %(message)s',
    handlers=[
        # write info into both the log file and console
        logging.FileHandler(log_file),
        logging.StreamHandler()],
    level=25)

logger = logging.getLogger(__name__)


# Currently I'm not aware of a way to get all ManyToMany fields in a django model,
# so have to pre-know the ManyToMany field names

# TODO: for public database, there are some tables that do not get released
# for a list, check the internal v.s. shared modules

ALYX_MODELS_OF_INTEREST = (
    # misc.models
    misc.models.Lab,
    misc.models.LabLocation,
    misc.models.LabMember,
    misc.models.LabMembership,
    misc.models.CageType,
    misc.models.Enrichment,
    misc.models.Food,
    misc.models.Housing,
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
    data.models.Dataset,       # very big table, usually handled separately
    data.models.FileRecord,    # very big table, usually handled separately
    # experiments.models
    experiments.models.CoordinateSystem,
    experiments.models.ProbeModel,
    experiments.models.ProbeInsertion,
    experiments.models.TrajectoryEstimate
)


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


def get_many_to_many_field_names(alyx_model):
    """Get all ManyToMany field names of an alyx modelinclude

    Args:
        alyx_model (django.model object): alyx model

    Returns:
        [list]: list of ManyToMany field names (property name), including foreign key references
    """
    one_entry = next(alyx_model.objects.iterator())
    many_to_many_field_names = []
    for field_name in dir(one_entry):
        try:
            obj = getattr(one_entry, field_name)
        except:
            pass
        else:
            if obj.__class__.__name__ == 'ManyRelatedManager' and not field_name.endswith('_set'):
                many_to_many_field_names.append(field_name)

    return many_to_many_field_names


def get_tables_with_auto_datetime(tables=None):

    if tables is None:
        tables = ALYX_MODELS_OF_INTEREST

    return([t for t in tables
            if 'auto_datetime' in get_field_names(t)])


def insert_alyx_entries_model(
        alyx_model,
        AlyxRawTable=alyxraw.AlyxRaw,
        backtrack_days=None,
        skip_existing_alyxraw=False):
    """Insert alyx entries into alyxraw tables for a particular alyx model

    Args:
        alyx_model (django.model object): alyx model
        AlyxRawTable (datajoint module): datajoint module containing AlyxRaw tables, either alyxraw or alyxraw update
        backtrack_days (int, optional): number of days the data are within to backtrack and ingest,
            just applicable to tables with auto_datetime field
        skip_existing_alyxraw: if True, skip over the entries already existed in the AlyxRaw table,
            else, load and insert everything again (but still with `skip_duplicates=True`)
    """
    model_name = get_alyx_model_name(alyx_model)
    field_names = get_field_names(alyx_model)
    many_to_many_field_names = get_many_to_many_field_names(alyx_model)

    if model_name == 'actions.session':
        backtrack_days = backtrack_days or 30

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

    # Ingest into main table
    if skip_existing_alyxraw:
        existing_uuids = (AlyxRawTable & {'model': model_name}).fetch('uuid')
        new_uuids = np.setxor1d(list(entries.values_list('id', flat=True)), existing_uuids)
        entries = [e for e in entries if e.id in new_uuids]
    else:
        new_uuids = list(entries.values_list('id', flat=True))

    if not len(new_uuids):
        return

    # using QueryBuffer, ingest into table AlyxRaw
    alyxraw_buffer = QueryBuffer(AlyxRawTable & {'model': model_name}, verbose=False)
    # using QueryBuffer, ingest into part table AlyxRaw.Field
    alyxraw_field_buffer = QueryBuffer(AlyxRawTable.Field, verbose=True)
    # cancel on-going transaction, if any
    AlyxRawTable.connection.cancel_transaction()

    # ingest fields and single foreign key references in alyxraw.AlyxRaw.Field
    for r in tqdm(entries):
        alyxraw_buffer.add_to_queue1({'uuid': r.id, 'model': model_name})
        # e.g. for table subjects.models.Subject, each r is a subject queryset
        # for one subject
        try:
            field_entries = []
            for field_name in field_names:
                if field_name == 'id':
                    continue

                field_entry = {'uuid': r.id, 'fname': field_name}
                field_value = getattr(r, field_name)

                if field_name == 'json' and field_value:
                    # handles the 'json' field - store the json dump
                    field_entry['value_idx'] = 0
                    field_entry['fvalue'] = json.dumps(field_value)
                    if len(field_entry['fvalue']) >= 10000:
                        # if the json dump is too large, store fvalue as null
                        field_entry.pop('fvalue')
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
                elif (not isinstance(field_value, (float, int)) and not field_value) or \
                        (isinstance(field_value, (float, int)) and math.isnan(field_value)):
                    # handle "falsy" field value - store as string 'None'
                    field_entry['value_idx'] = 0
                    field_entry['fvalue'] = 'None'
                elif isinstance(field_value, str):
                    field_entry['value_idx'] = 0
                    field_entry['fvalue'] = field_value
                elif isinstance(field_value, (bool, float, int,
                                              datetime.datetime, datetime.date)):
                    field_entry['value_idx'] = 0
                    field_entry['fvalue'] = str(field_value)
                else:
                    # special handling for foreign key object
                    field_entry['value_idx'] = 0
                    fk_id = field_name + '_id'
                    if hasattr(r, fk_id):
                        field_entry['fvalue'] = str(getattr(r, fk_id))

                field_entries.append(field_entry)
            # ingest many to many fields into alyxraw.AlyxRaw.Field
            for field_name in many_to_many_field_names:
                many_to_many_entries = getattr(r, field_name).all()
                if len(many_to_many_entries) > 200:
                    print(f'\tmany-to-many field {field_name} with {len(many_to_many_entries)} entries - skipping...')
                    continue
                field_entries.extend([
                    dict(uuid=r.id, fname=field_name,
                         value_idx=obj_idx, fvalue=str(obj.id))
                    for obj_idx, obj in enumerate(many_to_many_entries)])

            alyxraw_field_buffer.add_to_queue(field_entries)
            dj.conn().ping()
            del field_entries  # to be cleaned by garbage collector, improve memory management

        except Exception as e:
            logger.log(25, 'Problematic entry {} of model {} with error {}'.format(
                r.id, model_name, str(e)))

        if len(alyxraw_field_buffer._queue) >= 7500:
            with AlyxRawTable.connection.transaction:
                alyxraw_buffer.flush_insert(skip_duplicates=True)
                alyxraw_field_buffer.flush_insert(skip_duplicates=True, chunksz=7500)

    with AlyxRawTable.connection.transaction:
        alyxraw_buffer.flush_insert(skip_duplicates=True)
        alyxraw_field_buffer.flush_insert(skip_duplicates=True)


def insert_to_update_alyxraw_postgres(alyx_models=None, excluded_models=[],
                                      delete_UpdateAlyxRaw_first=False,
                                      skip_existing_alyxraw=False):

    """Ingest entries into update_ibl_alyxraw from postgres alyx instance

    Args:
        alyx_models (list of alyx model django objects): list of alyx django models
        delete_UpdateAlyxRaw_first (bool, optional): whether to delete the update module alyx raw tables first. Defaults to False.
    """
    if not alyx_models:
        alyx_models = ALYX_MODELS_OF_INTEREST

    if delete_UpdateAlyxRaw_first:
        with dj.config(safemode=False):
            logger.log(25, 'Deleting update ibl alyxraw tables...')
            models_res = [{'model': get_alyx_model_name(m) for m in alyx_models}]
            (alyxraw.UpdateAlyxRaw.Field & models_res).delete_quick()
            (alyxraw.UpdateAlyxRaw & models_res).delete_quick()

    for alyx_model in alyx_models:
        if alyx_model.__name__ in excluded_models:
            continue
        logger.log(25, 'Ingesting alyx table {} into datajoint UpdateAlyxRaw...'.format(get_alyx_model_name(alyx_model)))
        insert_alyx_entries_model(alyx_model, AlyxRawTable=alyxraw.UpdateAlyxRaw,
                                  skip_existing_alyxraw=skip_existing_alyxraw)


def main(backtrack_days=3, skip_existing_alyxraw=False):
    for alyx_model in ALYX_MODELS_OF_INTEREST:
        logger.log(25, 'Ingesting alyx table {} into datajoint alyxraw...'.format(get_alyx_model_name(alyx_model)))
        if get_alyx_model_name(alyx_model) == 'actions.session':
            skip_existing_alyxraw = False
        insert_alyx_entries_model(alyx_model, AlyxRawTable=alyxraw.AlyxRaw,
                                  backtrack_days=backtrack_days,
                                  skip_existing_alyxraw=skip_existing_alyxraw)


if __name__ == '__main__':
    main()
