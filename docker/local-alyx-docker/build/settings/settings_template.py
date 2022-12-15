# DO NOT EDIT ! --- Template SETTINGS for autogenerating Django configuration
import os
from textwrap import dedent

from django.conf.locale.en import formats as en_formats

# settings_secret.py -------------------------------------------------------------------

SECRET_KEY = "%DJANGO_SECRET_KEY%"
S3_ACCESS = {}
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": "%PGDATABASE%",
        "USER": "%PGUSER%",
        "PASSWORD": "%PGPASSWORD%",
        "HOST": "%PGHOST%",
        "PORT": "5432",
        "OPTIONS": {"options": "-c default_transaction_read_only=%PGREADONLY%"},
    }
}
EMAIL_HOST = "mail.superserver.net"
EMAIL_HOST_USER = "alyx@awesomedomain.org"
EMAIL_HOST_PASSWORD = "UnbreakablePassword"
EMAIL_PORT = 587
EMAIL_USE_TLS = True

# settings_lab.py ----------------------------------------------------------------------

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "host.docker.internal", "%ALYX_NETWORK%"]
LANGUAGE_CODE = "en-us"
TIME_ZONE = "GB"
GLOBUS_CLIENT_ID = "525cc543-8ccb-4d11-8036-af332da5eafd"
SUBJECT_REQUEST_EMAIL_FROM = "alyx@internationalbrainlab.org"
DEFAULT_SOURCE = "IBL"
DEFAULT_PROTOCOL = "1"
SUPERUSERS = ("%PGUSER%", "root")
STOCK_MANAGERS = ("%PGUSER%", "root")
WEIGHT_THRESHOLD = 0.75
DEFAULT_LAB_NAME = "defaultlab"
WATER_RESTRICTIONS_EDITABLE = False
DEFAULT_LAB_PK = "4027da48-7be3-43ec-a222-f75dffe36872"
SESSION_REPO_URL = (
    "http://ibl.flatironinstitute.org/{lab}/Subjects/{subject}/{date}/{number:03d}/"
)
NARRATIVE_TEMPLATES = {
    "Headplate implant": dedent(
        """
    == General ==

    Start time (hh:mm):   ___:___
    End time (hh:mm):    ___:___

    Bregma-Lambda :   _______  (mm)

    == Drugs == (copy paste as many times as needed; select IV, SC or IP)
    __________________( IV / SC / IP ) Admin. time (hh:mm)  ___:___

    == Coordinates ==  (copy paste as many times as needed; select B or L)
    (B / L) - Region: AP:  _______  ML:  ______  (mm)
    Region: _____________________________

    == Notes ==
    <write your notes here>
        """
    ),
}

# settings.py --------------------------------------------------------------------------

en_formats.DATETIME_FORMAT = "d/m/Y H:i"
DATE_INPUT_FORMATS = ("%d/%m/%Y",)
USE_DEPRECATED_PYTZ = True
AUTH_USER_MODEL = "misc.LabMember"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
DEBUG = "%ALYX_INSTANCE%" != "prod"
if not DEBUG:
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = "DENY"
    SESSION_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = 30
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
INSTALLED_APPS = (
    # 'dal',
    # 'dal_select2',
    "django_admin_listfilter_dropdown",
    "django_filters",
    "django.contrib.admin",
    "django.contrib.admindocs",
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "mptt",
    "polymorphic",
    "rangefilter",
    "rest_framework",
    "rest_framework.authtoken",
    "rest_framework_docs",
    "reversion",
    "test_without_migrations",
    # alyx-apps
    "actions",
    "data",
    "misc",
    "experiments",
    "jobs",
    "subjects",
    "django_cleanup.apps.CleanupConfig",  # needs to be last in the list
)
MIDDLEWARE = (
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "alyx.base.QueryPrintingMiddleware",
    "django_structlog.middlewares.RequestMiddleware",
)
ROOT_URLCONF = "alyx.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
TEMPLATE_LOADERS = (
    (
        "django.template.loaders.cached.Loader",
        (
            "django.template.loaders.filesystem.Loader",
            "django.template.loaders.app_directories.Loader",
        ),
    ),
)
WSGI_APPLICATION = "alyx.wsgi.application"
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ),
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "STRICT_JSON": False,
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    # 'DEFAULT_RENDERER_CLASSES': (
    #     'rest_framework.renderers.JSONRenderer',
    # ),
    "EXCEPTION_HANDLER": "alyx.base.rest_filters_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "rest_framework.schemas.coreapi.AutoSchema",
    "PAGE_SIZE": 250,
}
USE_I18N = False
USE_L10N = False
USE_TZ = False
STATIC_ROOT = os.path.join(BASE_DIR, "static/")
STATIC_URL = "/static/"
MEDIA_ROOT = "/backups/uploaded/"
MEDIA_URL = "/uploaded/"
TABLES_ROOT = "/backups/tables/"
UPLOADED_IMAGE_WIDTH = 800
