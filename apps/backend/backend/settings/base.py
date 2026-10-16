# apps/backend/backend/settings/base.py

import datetime
import os
import warnings
from pathlib import Path

import firebase_admin
from decouple import Config, RepositoryEnv
from django.core.cache import CacheKeyWarning
from firebase_admin import credentials
from pytimeparse2 import parse


# ============================================================================
# BASE DIRECTORY
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# The env file lives at the project root (kaz-site/.env), not inside
# the Django backend directory. Resolve it explicitly so `config(...)`
# works regardless of which directory manage.py is invoked from.

_PROJECT_ROOT = BASE_DIR.parent.parent

_ENV_FILE = _PROJECT_ROOT / ".env"

if not _ENV_FILE.exists():
    raise RuntimeError(f"Env file not found: {_ENV_FILE}")

config = Config(RepositoryEnv(str(_ENV_FILE)))

# ============================================================================
# WINDOWS GIS / OSGeo4W
# ============================================================================
#
# Canonical GIS runtime:
#
#   C:\Users\dino\AppData\Local\Programs\OSGeo4W
#
# GDAL:     bin\gdal313.dll
# GEOS:     bin\geos_c.dll
# GDAL data: apps\gdal\share\gdal
# PROJ data: share\proj
# ============================================================================

if os.name == "nt":
    OSGEO4W_ROOT = Path(
        r"C:\Users\dino\AppData\Local\Programs\OSGeo4W"
    )

    OSGEO4W_BIN = OSGEO4W_ROOT / "bin"

    GDAL_LIBRARY_PATH = str(OSGEO4W_BIN / "gdal313.dll")
    GEOS_LIBRARY_PATH = str(OSGEO4W_BIN / "geos_c.dll")
    GDAL_DATA = str(
        OSGEO4W_ROOT / "apps" / "gdal" / "share" / "gdal"
    )
    PROJ_LIB = str(OSGEO4W_ROOT / "share" / "proj")

    if hasattr(os, "add_dll_directory"):
        _OSGEO4W_DLL_DIRECTORY = os.add_dll_directory(
            str(OSGEO4W_BIN)
        )

    current_path = os.environ.get("PATH", "")

    path_entries = [
        entry
        for entry in current_path.split(os.pathsep)
        if entry
        and Path(entry).resolve() != OSGEO4W_BIN.resolve()
    ]

    os.environ["PATH"] = (
        str(OSGEO4W_BIN)
        + os.pathsep
        + os.pathsep.join(path_entries)
    )

    os.environ["GDAL_DATA"] = GDAL_DATA
    os.environ["PROJ_LIB"] = PROJ_LIB


# ============================================================================
# CORE
# ============================================================================

SECRET_KEY = config(
    "DJANGO_SECRET_KEY",
    default=config("SECRET_KEY", default="unsafe-secret"),
)

DEBUG = config("DEBUG", cast=bool, default=False)

ALLOWED_HOSTS = config(
    "DJANGO_ALLOWED_HOSTS",
    default="localhost,127.0.0.1,0.0.0.0",
    cast=lambda v: [s.strip() for s in v.split(",") if s.strip()],
)

# Card encryption key — override in production env.
CARD_ENCRYPTION_KEY = config(
    "CARD_ENCRYPTION_KEY",
    default="GUDndn50gGn1Z0jqEmbrx6VeFjksDlse_uXmAWzPqoU=",
)

# General-purpose encryption key for sensitive data at rest.
ENCRYPTION_KEY = config(
    "ENCRYPTION_KEY",
    default="-T1gt706CYI2F-RJCZWdKmv40r9F0w15iq_w8OYgljc=",
)


# ============================================================================
# REDIS
# ============================================================================

# Use "127.0.0.1" as the default to avoid Windows localhost resolution lag
REDIS_HOST = config("REDIS_HOST", default="127.0.0.1")
REDIS_PORT = config("REDIS_PORT", cast=int, default=6379)



# ============================================================================
# FIREBASE ADMIN SDK
# ============================================================================
#
# NOTE: initialization runs at settings-load time. If the credentials
# file is missing, Firebase silently fails to initialize. Move to an
# AppConfig.ready() when convenient.

if not firebase_admin._apps:
    cred_path = config("GOOGLE_APPLICATION_CREDENTIALS", default="")
    if cred_path and os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)


# ============================================================================
# MOBILE APP
# ============================================================================

MOBILE_APP = {
    "APP_NAME": "Univa",
    "APP_VERSION": "1.0.0",
    "MINIMUM_APP_VERSION": "1.0.0",
    "SUPPORTED_PLATFORMS": ["ios", "android"],
    "API_TIMEOUT": 30,
    "UPLOAD_CHUNK_SIZE": 1024 * 1024,
}


# ============================================================================
# INSTALLED APPS
# ============================================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",

    "daphne",

    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.postgres",
    "django.contrib.gis",
    "django.contrib.sitemaps",

    # Univa apps
    "accounts",
    "blog",
    "banking",
    "chat",
    "social",
    "invoice",
    "investors",
    "transport",
    "payment",
    "realestate",
    "seo",
    "tax",
    "ml",
    "thumbnail",
    "univa_jwt",
    "loyalty",
    "support",
    "ecommerce",
    "biometrics",
    "core",
    "notifications",
    "staff",
    "audit",
    "commissions",
    "earnings",
    "settlements",
    "payment.canonical.apps.PaymentCanonicalConfig",

    # Third-party
    "corsheaders",
    "graphene_gis",
    "graphene_django",
    "django_measurement",
    "adminsortable2",
    "django_celery_beat",
    "mptt",
    "django_countries",
    "django_filters",
    "phonenumber_field",
    "robots",
    "meta",
    "celery",
    "leaflet",
    "channels",
    "pgvector",
    "django_admin_listfilter_dropdown",
]


# ============================================================================
# MIDDLEWARE
# ============================================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "ecommerce.middleware.checkout_session.CheckoutSessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "univa_jwt.middleware.UnivaJWTMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ============================================================================
# URL / ASGI
# ============================================================================

ROOT_URLCONF = "backend.urls"
ASGI_APPLICATION = "backend.asgi.application"
DAPHNE_WS_TIMEOUT = 30


# ============================================================================
# TEMPLATES
# ============================================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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


# ============================================================================
# AUTH
# ============================================================================

AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation."
                "UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation."
                "MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation."
                "CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation."
                "NumericPasswordValidator",
    },
]


# ============================================================================
# MAGIC LINKS
# ============================================================================

MAGIC_LINK_EXPIRY_MINUTES = 15
MAGIC_LINK_SECURE = not DEBUG
MAGIC_LINK_REQUIRE_SAME_IP = False
MAGIC_LINK_REQUIRE_SAME_BROWSER = False
MAGIC_LINK_RESEND_COOLDOWN = 60


# ============================================================================
# RATE LIMITING
# ============================================================================

RATE_LIMITS = {
    "authentication": 10,
    "face_verification": 3,
    "biometric_auth": 3,
    "magic_link": 3,
    "global_per_ip": 100,
}


# ============================================================================
# SECURITY — AUTH LOCKOUT
# ============================================================================

MAX_AUTH_ATTEMPTS_BEFORE_LOCKOUT = 5
AUTH_LOCKOUT_MINUTES = 15


# ============================================================================
# SECURITY — FACE VERIFICATION
# ============================================================================

ENABLE_FACE_VERIFICATION = config(
    "ENABLE_FACE_VERIFICATION", cast=bool, default=True
)

FACE_VERIFICATION_THRESHOLD = 0.9
FACE_VERIFICATION_MAX_ATTEMPTS = 3
FACE_VERIFICATION_COOLDOWN = 300
MAX_FACE_VERIFICATION_ATTEMPTS = 3
FACE_VERIFICATION_LOCKOUT_MINUTES = 30
LIVENESS_THRESHOLD = 0.8

PGVECTOR_DEFAULT_DIM = 512


# ============================================================================
# WEBAUTHN
# ============================================================================

WEBAUTHN_RP_NAME = "Univa Multi-Service Platform"
WEBAUTHN_RP_ID = config("WEBAUTHN_RP_ID", default="yourdomain.com")
WEBAUTHN_ORIGIN = config(
    "WEBAUTHN_ORIGIN", default="http://127.0.0.1:8000"
)


# ============================================================================
# STATIC / MEDIA
# ============================================================================

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# Django 5.1+ storage configuration.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage.CompressedManifestStaticFilesStorage"
        ),
    },
}

# File upload
MAX_UPLOAD_SIZE = 50 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE
FILE_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE
FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755


# ============================================================================
# INTERNATIONALIZATION
# ============================================================================

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Lagos"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ============================================================================
# GRAPHQL (Graphene)
# ============================================================================

GRAPHENE = {
    "SCHEMA": "backend.schema.schema",
    "SCHEMA_OUTPUT": "backend/schema.graphql",
    "SCHEMA_INDENT": 2,

    "RELAY_CONNECTION_ENFORCE_FIRST_OR_LAST": True,
    "RELAY_CONNECTION_MAX_LIMIT": 100,

    "ATOMIC_MUTATIONS": True,

    "MIDDLEWARE": [
        "univa_jwt.schema.middleware.JWTAuthMiddleware",
    ],
}

if DEBUG:
    GRAPHENE["MIDDLEWARE"].insert(
        0,
        "graphene_django.debug.DjangoDebugMiddleware",
    )


# ============================================================================
# JWT (Univa)
# ============================================================================

UNIVA_JWT = {
    "ALGORITHM": config("UNIVA_JWT_ALGORITHM", default="HS256"),
    "SIGNING_KEY": config("UNIVA_JWT_SIGNING_KEY"),
    "ISSUER": config("UNIVA_JWT_ISSUER", default="univa-backend"),
    "AUDIENCE": config("UNIVA_JWT_AUDIENCE", default="univa-client"),

    "ACCESS_TOKEN_LIFETIME_MINUTES": config(
        "UNIVA_JWT_ACCESS_TOKEN_MINUTES",
        cast=int,
        default=30,
    ),
    "REFRESH_TOKEN_LIFETIME_DAYS": config(
        "UNIVA_JWT_REFRESH_TOKEN_DAYS",
        cast=int,
        default=7,
    ),

    "ROTATE_REFRESH_TOKENS": config(
        "UNIVA_JWT_ROTATE_REFRESH_TOKENS",
        cast=bool,
        default=True,
    ),
    "REVOKE_REFRESH_ON_ROTATION": config(
        "UNIVA_JWT_REVOKE_REFRESH_ON_ROTATION",
        cast=bool,
        default=True,
    ),
    "REQUIRE_REFRESH_TOKEN_REVOCATION_CHECK": config(
        "UNIVA_JWT_REQUIRE_REVOCATION_CHECK",
        cast=bool,
        default=True,
    ),

    "VERIFY_EXPIRATION": True,
    "VERIFY_ISSUER": True,
    "VERIFY_AUDIENCE": True,

    "AUTH_HEADER_PREFIX": config(
        "UNIVA_JWT_AUTH_HEADER_PREFIX",
        default="Bearer",
    ),

    "USER_ID_CLAIM": "sub",
    "TOKEN_TYPE_CLAIM": "token_type",
    "JTI_CLAIM": "jti",
    "REQUIRE_JTI": True,
    "REQUIRE_TOKEN_TYPE": True,

    "LEEWAY": config("UNIVA_JWT_LEEWAY", cast=int, default=5),
}


# ============================================================================
# CORS / CSRF
# ============================================================================

CORS_ALLOW_ALL_ORIGINS = config(
    "CORS_ALLOW_ALL_ORIGINS", cast=bool, default=DEBUG
)
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default=(
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:8081,http://127.0.0.1:8081,"
        "http://localhost:19006,http://127.0.0.1:19006,"
        "http://kaz-backend:8000,http://kaz-nginx,"
        "http://10.69.240.93:8000"
    ),
    cast=lambda v: [s.strip() for s in v.split(",") if s.strip()],
)

EXPO_ORIGINS = [
    "https://*.exp.host",
    "https://*.expo.dev",
    "exp://*.expo.dev",
    "exp://192.168.*.*:8081",
    "exp://localhost:8081",
]

if DEBUG:
    CORS_ALLOWED_ORIGINS = list(
        dict.fromkeys(CORS_ALLOWED_ORIGINS + EXPO_ORIGINS)
    )

CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "x-app-version",
    "x-device-id",
    "x-platform",
    "x-device-type",
    "x-app-build",
]

CORS_EXPOSE_HEADERS = [
    "x-app-version",
    "x-platform",
    "x-api-version",
]

CSRF_TRUSTED_ORIGINS = [
    *[
        o if o.startswith("http") else f"http://{o}"
        for o in CORS_ALLOWED_ORIGINS
    ],
    "http://kaz-backend:8000",
    "http://10.69.240.93:8000",
]


# ============================================================================
# SEO
# ============================================================================

SITE_ID = 1
SITE_URL = config("SITE_URL", default="http://127.0.0.1:8000")
ROBOTS_SITEMAP_URLS = [f"{SITE_URL}/sitemap.xml"]


# ============================================================================
# CACHING
# ============================================================================

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/1",
        "TIMEOUT": 60 * 15,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
            "IGNORE_EXCEPTIONS": True,
        },
    },
    "mobile_sessions": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/2",
        "TIMEOUT": 60 * 60 * 24 * 7,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    },
}

warnings.filterwarnings("ignore", category=CacheKeyWarning)


# ============================================================================
# INTERNAL / ADMIN
# ============================================================================

INTERNAL_IPS = ["127.0.0.1", "localhost", "10.0.2.2"]

ADMIN_SITE_HEADER = "Univa Admin"
ADMIN_SITE_TITLE = "Univa Administration"
ADMIN_INDEX_TITLE = "Welcome to Univa Admin Portal"
LIST_PER_PAGE = 50


# ============================================================================
# CELERY
# ============================================================================
#
# The authoritative Celery configuration lives in:
#
#     backend/celery.py       (task routes, serializers, timezone)
#     backend/celerybeat.py   (beat schedule)
#
# These settings are the minimum required for `config_from_object`
# to pick up the broker and result backend.

CELERY_BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
CELERY_RESULT_BACKEND = f"redis://{REDIS_HOST}:{REDIS_PORT}/1"

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

CELERY_TIMEZONE = "Africa/Lagos"
CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TASK_CREATE_MISSING_QUEUES = True


# ============================================================================
# CHANNELS
# ============================================================================
#
# NOTE: InMemoryChannelLayer works only for a single-process dev server.
# Migrate to channels_redis before any multi-worker deployment — WebSocket
# subscriptions silently break across processes with the in-memory backend.

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}


# ============================================================================
# EMAIL
# ============================================================================

EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = config("EMAIL_HOST", default="")
EMAIL_PORT = config("EMAIL_PORT", cast=int, default=587)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", cast=bool, default=True)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config(
    "DEFAULT_FROM_EMAIL", default="noreply@univa.com"
)
SERVER_EMAIL = config("SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)


# ============================================================================
# SMS (Twilio)
# ============================================================================

TWILIO_ACCOUNT_SID = config("TWILIO_ACCOUNT_SID", default="")
TWILIO_AUTH_TOKEN = config("TWILIO_AUTH_TOKEN", default="")
TWILIO_PHONE_NUMBER = config("TWILIO_PHONE_NUMBER", default="")
TWILIO_WHATSAPP_FROM = config("TWILIO_WHATSAPP_FROM", default="")


# ============================================================================
# LOCALE / CURRENCY DEFAULTS
# ============================================================================

DEFAULT_PHONE_REGION = "NG"
DEFAULT_CURRENCY = "NGN"
DEFAULT_COUNTRY = "NG"

DEFAULT_DECIMAL_PLACES = 3
DEFAULT_MAX_DIGITS = 12
DEFAULT_CURRENCY_CODE_LENGTH = 3

COUNTRIES_OVERRIDE = {"EU": "European Union"}


# ============================================================================
# LIMITS / RULES
# ============================================================================

DATABASE_CONNECTION_DEFAULT_NAME = "default"

MAX_USER_ADDRESSES = config(
    "MAX_USER_ADDRESSES", cast=int, default=100
)
ORDER_RULES_LIMIT = config("ORDER_RULES_LIMIT", cast=int, default=100)
GIFTS_LIMIT_PER_RULE = config(
    "GIFTS_LIMIT_PER_RULE", cast=int, default=500
)
INDEX_MAXIMUM_EXPR_COUNT = 100


# ============================================================================
# CHECKOUT / FILE CLEANUP
# ============================================================================

ANONYMOUS_CHECKOUTS_TIMEDELTA = datetime.timedelta(
    seconds=parse(
        config("ANONYMOUS_CHECKOUTS_TIMEDELTA", default="30 days")
    )
)

USER_CHECKOUTS_TIMEDELTA = datetime.timedelta(
    seconds=parse(
        config("USER_CHECKOUTS_TIMEDELTA", default="90 days")
    )
)

EMPTY_CHECKOUTS_TIMEDELTA = datetime.timedelta(
    seconds=parse(
        config("EMPTY_CHECKOUTS_TIMEDELTA", default="6 hours")
    )
)

EXPORT_FILES_TIMEDELTA = datetime.timedelta(
    seconds=parse(config("EXPORT_FILES_TIMEDELTA", default="30 days"))
)


# ============================================================================
# PREDEFINED DATA
# ============================================================================

DEFAULT_MENUS = {
    "top_menu_name": "navbar",
    "bottom_menu_name": "footer",
}
DEFAULT_CHANNEL_SLUG = config(
    "DEFAULT_CHANNEL_SLUG", default="default-channel"
)
POPULATE_DEFAULTS = config(
    "POPULATE_DEFAULTS", cast=bool, default=True
)


# ============================================================================
# FRONTEND / MOBILE
# ============================================================================

FRONTEND_URL = config(
    "FRONTEND_URL", default="http://localhost:8081"
).rstrip("/")

MOBILE_APP_DEEP_LINK = config(
    "MOBILE_APP_DEEP_LINK", default="univa://"
)


# ============================================================================
# BRANDING
# ============================================================================

MARKET_NAME = "Univa Multi-Service Platform"
MARKET_LOGO_URL = f"{SITE_URL}/static/images/univa.png"
MARKET_ADDRESS = "123 Market St, Lagos, Nigeria"
MARKET_PHONE = "+234 800 000 0000"


# ============================================================================
# PRODUCT / PRICING
# ============================================================================

PRODUCT_MAX_INDEXED_VARIANTS = 50
PRODUCT_MAX_INDEXED_ATTRIBUTES = 10
PRODUCT_MAX_INDEXED_ATTRIBUTE_VALUES = 20

DEFAULT_VAT_RATE = 0.075
DEFAULT_DISCOUNT = 0.00


# ============================================================================
# LOGGING
# ============================================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "pretty": {
            "format": (
                "\033[92m[%(levelname)s]\033[0m %(asctime)s "
                "| %(name)s | %(message)s"
            ),
            "datefmt": "%H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "pretty",
        },
    },
    "loggers": {
        "auth.middleware": {
            "handlers": ["console"],
            "level": "INFO",
        },
    },
}


# ============================================================================
# SECURITY (transport, cookies)
# ============================================================================

SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False


# ============================================================================
# BANKING
# ============================================================================

BANKING_CONFIG = {
    "MAX_DAILY_TRANSFER": 5000.00,
    "MAX_TRANSACTION_AMOUNT": 1000.00,
    "OTP_EXPIRY_MINUTES": 10,
    "SUPPORTED_BANKS": ["OPAY", "PALMPAY", "MONIEPOINT"],
    "TRANSACTION_FEE_PERCENTAGE": 0.015,
    "MINIMUM_BALANCE": 0.00,
    "DAILY_WITHDRAWAL_LIMIT": 500.00,
    "DAILY_TRANSFER_LIMIT": 1000.00,
}

PIN_HASH_ITERATIONS = 100000
WEBHOOK_TIMEOUT = 10
APPEND_SLASH = True

DEFAULT_VIRTUAL_ACCOUNT_PROVIDER = config(
    "DEFAULT_VIRTUAL_ACCOUNT_PROVIDER", default="paystack"
)
DEFAULT_TRANSFER_PROVIDER = config(
    "DEFAULT_TRANSFER_PROVIDER", default="paystack"
)


# ============================================================================
# PAYSTACK (canonical payment provider)
# ============================================================================

PAYSTACK_SECRET_KEY = config(
    "PAYSTACK_SECRET_KEY",
    default="",
)

PAYSTACK_PUBLIC_KEY = config(
    "PAYSTACK_PUBLIC_KEY",
    default="",
)

# Paystack signs webhooks with HMAC-SHA512 keyed by the secret key.
# Keep this as a separate setting so it can be rotated independently
# and so sandbox vs. live environments can use distinct secrets.
PAYSTACK_WEBHOOK_SECRET = config(
    "PAYSTACK_WEBHOOK_SECRET",
    default=PAYSTACK_SECRET_KEY,
)

PAYSTACK_BASE_URL = config(
    "PAYSTACK_BASE_URL",
    default="https://api.paystack.co",
)

PAYSTACK_TIMEOUT_SECONDS = config(
    "PAYSTACK_TIMEOUT_SECONDS",
    cast=int,
    default=15,
)


# ============================================================================
# REGIONS
# ============================================================================

REGION_AUTO_CREATE = True