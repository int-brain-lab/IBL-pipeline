import itertools
import os
import re
import sys

import django
from django.apps import apps
from django.conf import settings

if not settings.configured:
    try:
        from alyx import settings as alyx_settings
    except ImportError:
        print(
            "Could not import alyx settings. Check DJANGO_SETTINGS_MODULE and PYTHONPATH"
        )
        sys.path.insert(0, os.getenv("ALYX_SRC_PATH", "/var/www/alyx/alyx"))
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "alyx.settings")

if not apps.ready:
    django.setup()


MODEL_ORDER = [
    'misc.lab',
    'misc.lablocation',
    'misc.labmember',
    'misc.labmembership',
    'misc.cagetype',
    'misc.enrichment',
    'misc.food',
    'misc.housing',
    'subjects.project',
    'subjects.source',
    'subjects.species',
    'subjects.strain',
    'subjects.sequence',
    'subjects.allele',
    'subjects.line',
    'subjects.subject',
    'subjects.breedingpair',
    'subjects.litter',
    'subjects.genotypetest',
    'subjects.zygosity',
    'actions.proceduretype',
    'actions.surgery',
    'actions.cullmethod',
    'actions.cullreason',
    'actions.cull',
    'actions.weighing',
    'actions.watertype',
    'actions.waterrestriction',
    'actions.wateradministration',
    'actions.session',
    'data.dataformat',
    'data.datarepositorytype',
    'data.datarepository',
    'data.datasettype',
    'data.dataset',
    'data.filerecord',
    'experiments.coordinatesystem',
    'experiments.probemodel',
    'experiments.probeinsertion',
    'experiments.trajectoryestimate',
    'experiments.channel',
]

def get_django_model_name(model):
    return model._meta.db_table.replace("_", ".")


def get_django_field_names(model):
    """Get all field names of an django model, ManyToMany fields are not included

    Args:
        model (django.model object): django model

    Returns:
        [list]: list of field names (property name), including foreign key references, not ManyToMany fields
    """
    return [field.name for field in model._meta.fields]


def get_django_many_to_many_field_names(model):
    """Get all ManyToMany field names of an django modelinclude

    Args:
        model (django.model object): django model

    Returns:
        [list]: list of ManyToMany field names (property name), including foreign key references
    """
    many_to_many_field_names = []
    try:
        one_entry = next(model.objects.iterator())
    except StopIteration:
        return many_to_many_field_names
    for field_name in dir(one_entry):
        try:
            obj = getattr(one_entry, field_name)
        except:
            pass
        else:
            if (
                obj.__class__.__name__ == "ManyRelatedManager"
                and not field_name.endswith("_set")
            ):
                many_to_many_field_names.append(field_name)

    return many_to_many_field_names

def get_django_models(exclude=None):
    models = {
        get_django_model_name(model): {
            "django_model": model,
            "django_name": model.__name__,
            "django_module": get_django_model_name(model),
            "django_fields": tuple(field.name for field in model._meta.fields),
        }
        for model in apps.get_models()
        if not model._meta.proxy
    }
    first_set = {m: models[m] for m in MODEL_ORDER if m in models}
    second_set = {m: models[m] for m in models if m not in MODEL_ORDER}
    models = {**first_set, **second_set}

    if not exclude:
        return models

    if not isinstance(exclude, (list, tuple)):
        exclude = [exclude]

    exclusions = r"(?=(" + "|".join(exclude) + r"))"
    return {k: v for k, v in models.items() if not re.findall(exclusions, k)}


def extract_models_entry(models, *entries):
    if not entries:
        return tuple()

    return [tuple(v[e] for e in entries if e in v) for v in models.values()]



def alyx_models(as_dict=False):
    models = get_django_models(exclude=["^django", "^reversion", "^auth", "^jobs"])

    if as_dict:
        return dict(extract_models_entry(models, "django_module", "django_model"))
    return tuple(
        itertools.chain.from_iterable(extract_models_entry(models, "django_model"))
    )
