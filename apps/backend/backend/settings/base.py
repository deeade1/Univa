import datetime
import os
import platform
import sys
import warnings
from pathlib import Path

import firebase_admin
from decouple import config
from django.core.cache import CacheKeyWarning
from firebase_admin import credentials
from pytimeparse2 import parse


from pathlib import Path
import os


# ============================================================================
# WINDOWS GIS / OSGeo4W
# ============================================================================
#
# Canonical GIS runtime:
#
#   C:\Users\dino\AppData\Local\Programs\OSGeo4W
#
# GDAL:
#   bin\gdal313.dll
#
# GEOS:
#   bin\geos_c.dll
#
# GDAL data:
#   apps\gdal\share\gdal
#
# PROJ data:
#   share\proj
# ============================================================================

if os.name == "nt":
    OSGEO4W_ROOT = Path(
        r"C:\Users\dino\AppData\Local\Programs\OSGeo4W"
    )

    OSGEO4W_BIN = OSGEO4W_ROOT / "bin"

    GDAL_LIBRARY_PATH = str(
        OSGEO4W_BIN / "gdal313.dll"
    )

    GEOS_LIBRARY_PATH = str(
        OSGEO4W_BIN / "geos_c.dll"
    )

    GDAL_DATA = str(
        OSGEO4W_ROOT / "apps" / "gdal" / "share" / "gdal"
    )

    PROJ_LIB = str(
        OSGEO4W_ROOT / "share" / "proj"
    )

    # ------------------------------------------------------------------------
    # Make the OSGeo4W DLL directory available to Windows.
    # ------------------------------------------------------------------------

    if hasattr(os, "add_dll_directory"):
        _OSGEO4W_DLL_DIRECTORY = os.add_dll_directory(
            str(OSGEO4W_BIN)
        )

    # ------------------------------------------------------------------------
    # Make OSGeo4W the first GIS runtime in PATH.
    # ------------------------------------------------------------------------

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

    # ------------------------------------------------------------------------
    # GDAL / PROJ data directories.
    # ------------------------------------------------------------------------

    os.environ["GDAL_DATA"] = GDAL_DATA
    os.environ["PROJ_LIB"] = PROJ_LIB
  
BASE_DIR = Path(__file__).resolve().parent.parent.parent


# Core settings
SECRET_KEY = config("DJANGO_SECRET_KEY", default="unsafe-secret")
# apps/backend/backend/settings/base.py

import os

# Card encryption key - store in environment variables in production!
CARD_ENCRYPTION_KEY = config('CARD_ENCRYPTION_KEY', default="GUDndn50gGn1Z0jqEmbrx6VeFjksDlse_uXmAWzPqoU=")
DEBUG = config("DEBUG", cast=bool, default=False)

ALLOWED_HOSTS = config(
    "DJANGO_ALLOWED_HOSTS",
    default="localhost,127.0.0.1,0.0.0.0",
    cast=lambda v: [s.strip() for s in v.split(",") if s.strip()],
)



REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))


# Firebase Admin SDK
if not firebase_admin._apps:
    cred_path = config("GOOGLE_APPLICATION_CREDENTIALS")
    if cred_path and os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)

# Mobile App Settings
MOBILE_APP = {
    "APP_NAME": "Univa",
    "APP_VERSION": "1.0.0",
    "MINIMUM_APP_VERSION": "1.0.0",
    "SUPPORTED_PLATFORMS": ["ios", "android"],
    "API_TIMEOUT": 30,
    "UPLOAD_CHUNK_SIZE": 1024 * 1024,  # 1MB chunks for mobile uploads
}


# Installed apps
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

    # Your apps
    "accounts",  "blog", "banking", "chat", "social",   
    "invoice", "transport", "payment", "realestate",  
    "seo", "tax", "ml", "thumbnail", "univa_jwt", 
    "loyalty", "support", "ecommerce", "biometrics",
    "core", "notifications", "staff", "audit", "commissions",
    "earnings", "settlements", "payment.canonical.apps.PaymentCanonicalConfig",

    # Third-party apps
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

# Middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",

    "django.contrib.auth.middleware.AuthenticationMiddleware",

    "univa_jwt.middleware.UnivaJWTMiddleware",

    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    
]

# URL and WSGI
ROOT_URLCONF = "backend.urls"
ASGI_APPLICATION = "backend.asgi.application"
DAPHNE_WS_TIMEOUT = 30 
#WSGI_APPLICATION = "backend.wsgi.application"

# Templates
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


AUTH_USER_MODEL = "accounts.User"


AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    # Add any custom backends here if needed
]


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Magic link settings
MAGIC_LINK_EXPIRY_MINUTES = 15
MAGIC_LINK_SECURE = not DEBUG
MAGIC_LINK_REQUIRE_SAME_IP = False
MAGIC_LINK_REQUIRE_SAME_BROWSER = False
MAGIC_LINK_RESEND_COOLDOWN = 60

# Rate limiting settings
RATE_LIMITS = {
    'authentication': 10,  # attempts per 15 minutes
    'face_verification': 3,  # attempts per 5 minutes  
    'biometric_auth': 3,  # attempts per 5 minutes
    'magic_link': 3,  # attempts per hour
    'global_per_ip': 100,  # total auth attempts per hour per IP
}



# Security settings
MAX_FACE_VERIFICATION_ATTEMPTS = 3
FACE_VERIFICATION_LOCKOUT_MINUTES = 30
MAX_AUTH_ATTEMPTS_BEFORE_LOCKOUT = 5
AUTH_LOCKOUT_MINUTES = 15
# Face verification settings
ENABLE_FACE_VERIFICATION = config("ENABLE_FACE_VERIFICATION", cast=bool, default=True)
FACE_VERIFICATION_THRESHOLD = 0.9
FACE_VERIFICATION_MAX_ATTEMPTS = 3
FACE_VERIFICATION_COOLDOWN = 300
LIVENESS_THRESHOLD = 0.8
MAX_FACE_VERIFICATION_ATTEMPTS = 3
FACE_VERIFICATION_LOCKOUT_MINUTES = 5
PGVECTOR_DEFAULT_DIM = 512

# WebAuthn settings
WEBAUTHN_RP_NAME = "Univa Multi-Service Platform"
WEBAUTHN_RP_ID = config("WEBAUTHN_RP_ID", "yourdomain.com")
WEBAUTHN_ORIGIN = config("WEBAUTHN_ORIGIN", "http://127.0.0.1:8000")

# Static and Media files
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# File upload settings for mobile
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE
FILE_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE
FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Lagos"
USE_I18N = True
USE_L10N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# GraphQL Configuration

# GraphQL Configuration
# =============================================================================
# GraphQL Configuration
# =============================================================================

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


    
# JWT settings

UNIVA_JWT = {
    "ALGORITHM": config(
        "UNIVA_JWT_ALGORITHM",
        default="HS256",
    ),

    "SIGNING_KEY": config(
        "UNIVA_JWT_SIGNING_KEY",
    ),

    "ISSUER": config(
        "UNIVA_JWT_ISSUER",
        default="univa-backend",
    ),

    "AUDIENCE": config(
        "UNIVA_JWT_AUDIENCE",
        default="univa-client",
    ),

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

    "LEEWAY": config(
        "UNIVA_JWT_LEEWAY",
        cast=int,
        default=5,
    ),
}



# CORS & CSRF Configuration for Mobile App
CORS_ALLOW_ALL_ORIGINS = config("CORS_ALLOW_ALL_ORIGINS", cast=bool, default=DEBUG)
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000,http://127.0.0.1:3000,"
            "http://localhost:8081,http://127.0.0.1:8081,"
            "http://localhost:19006,http://127.0.0.1:19006,"
            "http://kaz-backend:8000,http://kaz-nginx,http://10.69.240.93:8000",
    cast=lambda v: [s.strip() for s in v.split(",") if s.strip()],
)

# Expo and mobile development origins
EXPO_ORIGINS = [
    "https://*.exp.host",
    "https://*.expo.dev",
    "exp://*.expo.dev",
    "exp://192.168.*.*:8081",
    "exp://localhost:8081",
]
if DEBUG:
    # merge but dedupe
    CORS_ALLOWED_ORIGINS = list(dict.fromkeys(CORS_ALLOWED_ORIGINS + EXPO_ORIGINS))


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
    *[o if o.startswith("http") else f"http://{o}" for o in CORS_ALLOWED_ORIGINS],
    # Backwards-compatible extras
    "http://kaz-backend:8000",
    "http://10.69.240.93:8000",
]

# SEO Settings
SITE_ID = 1
SITE_URL = config('SITE_URL', 'http://127.0.0.1:8000')
ROBOTS_SITEMAP_URLS = [f'{SITE_URL}/sitemap.xml']

# Redis Caching
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'redis://{REDIS_HOST}:{REDIS_PORT}/1',
        'TIMEOUT': 60 * 15,  # 15 minutes
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'IGNORE_EXCEPTIONS': True,
        }
    },
    'mobile_sessions': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'redis://{REDIS_HOST}:{REDIS_PORT}/2',
        'TIMEOUT': 60 * 60 * 24 * 7,  # 1 week for mobile sessions
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Ignore Django Redis warnings
warnings.filterwarnings("ignore", category=CacheKeyWarning)

# Internal IPs
INTERNAL_IPS = ["127.0.0.1", "localhost", "10.0.2.2"]

# Admin UI Customization
ADMIN_SITE_HEADER = "Univa Admin"
ADMIN_SITE_TITLE = "Univa Administration"
ADMIN_INDEX_TITLE = "Welcome to Univa Admin Portal"
LIST_PER_PAGE = 50

SIMPLEUI_CONFIG = {
    'system_keep': False,
    'menu_display': ['Authentication', 'Accounts', 'Ecommerce', 'Banking', 'Transport', 'Real Estate', 'Chat', 'Social', 'Blog'],
    'dynamic': True,
    'menus': [
        {
            'name': 'Authentication',
            'icon': 'fa fa-user',
            'models': [
                {'name': 'Users', 'icon': 'fa fa-user', 'url': 'auth/user/'},
                {'name': 'Groups', 'icon': 'fa fa-users', 'url': 'auth/group/'}
            ]
        },
    ]
}

# Celery Configuration
CELERY_BROKER_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/0'
CELERY_RESULT_BACKEND = f'redis://{REDIS_HOST}:{REDIS_PORT}/1'
CELERY_ACCEPT_CONTENT = ['json', 'pickle']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Africa/Lagos'
CELERY_TASK_DEFAULT_QUEUE = 'default'
CELERY_TASK_CREATE_MISSING_QUEUES = True
CELERY_TASK_ROUTES = {
    "accounts.tasks.*": {"queue": "accounts"},
    "chat.tasks.*": {"queue": "chat"},
    "transport.tasks.*": {"queue": "transport"},
    "notifications.tasks.*": {"queue": "notifications"},
}

CELERY_BEAT_SCHEDULE = {
    'cleanup-expired-sessions': {
        'task': 'accounts.tasks.cleanup_expired_sessions',
        'schedule': datetime.timedelta(hours=24),
    },
    
}



CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
        # For production, use Redis:
        # 'BACKEND': 'channels_redis.core.RedisChannelLayer',
        # 'CONFIG': {
        #     "hosts": [('127.0.0.1', 6379)],
        # },
    },
}


# Email Configuration
EMAIL_BACKEND = config('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', '')
EMAIL_PORT = config('EMAIL_PORT', cast=int, default=587)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', cast=bool, default=True)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', 'noreply@univa.com')
SERVER_EMAIL = config('SERVER_EMAIL', DEFAULT_FROM_EMAIL)

# SMS Configuration (Twilio)
TWILIO_ACCOUNT_SID = config('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = config('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = config('TWILIO_PHONE_NUMBER', '')
TWILIO_WHATSAPP_FROM = config('TWILIO_WHATSAPP_FROM', '')

# Phone and country defaults
DEFAULT_PHONE_REGION = 'NG'
DEFAULT_COUNTRY = os.getenv("DEFAULT_COUNTRY", "NG")
DEFAULT_DECIMAL_PLACES = 3
DEFAULT_MAX_DIGITS = 12
DEFAULT_CURRENCY_CODE_LENGTH = 3
COUNTRIES_OVERRIDE = {"EU": "European Union"}

# Limits and rules
DATABASE_CONNECTION_DEFAULT_NAME = "default"
MAX_USER_ADDRESSES = int(os.getenv("MAX_USER_ADDRESSES", 100))
ORDER_RULES_LIMIT = os.getenv("ORDER_RULES_LIMIT", 100)
GIFTS_LIMIT_PER_RULE = os.getenv("GIFTS_LIMIT_PER_RULE", 500)
INDEX_MAXIMUM_EXPR_COUNT = 100

# Checkout cleanup rules
ANONYMOUS_CHECKOUTS_TIMEDELTA = datetime.timedelta(
    seconds=parse(os.getenv("ANONYMOUS_CHECKOUTS_TIMEDELTA", "30 days"))
)
USER_CHECKOUTS_TIMEDELTA = datetime.timedelta(
    seconds=parse(os.getenv("USER_CHECKOUTS_TIMEDELTA", "90 days"))
)
EMPTY_CHECKOUTS_TIMEDELTA = datetime.timedelta(
    seconds=parse(os.getenv("EMPTY_CHECKOUTS_TIMEDELTA", "6 hours"))
)

# File cleanup
EXPORT_FILES_TIMEDELTA = datetime.timedelta(
    seconds=parse(os.getenv("EXPORT_FILES_TIMEDELTA", "30 days"))
)

# Predefined data
DEFAULT_MENUS = {"top_menu_name": "navbar", "bottom_menu_name": "footer"}
DEFAULT_CHANNEL_SLUG = os.getenv("DEFAULT_CHANNEL_SLUG", "default-channel")
POPULATE_DEFAULTS = os.getenv("POPULATE_DEFAULTS", "true").lower() in ("true", "1")

# Frontend URL

FRONTEND_URL = config(
    "FRONTEND_URL",
    default="http://localhost:8081",
).rstrip("/")

MOBILE_APP_DEEP_LINK = config("MOBILE_APP_DEEP_LINK", "univa://")

# Seller / branding
MARKET_NAME = "Univa Multi-Service Platform"
MARKET_LOGO_URL = f"{SITE_URL}/static/images/univa.png"
MARKET_ADDRESS = "123 Market St, Lagos, Nigeria"
MARKET_PHONE = "+234 800 000 0000"

PRODUCT_MAX_INDEXED_VARIANTS = 50
PRODUCT_MAX_INDEXED_ATTRIBUTES = 10
PRODUCT_MAX_INDEXED_ATTRIBUTE_VALUES = 20
# Default VAT, discount
DEFAULT_VAT_RATE = 0.075  # 7.5%
DEFAULT_DISCOUNT = 0.00


# Logging Configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "pretty": {
            "format": "\033[92m[%(levelname)s]\033[0m %(asctime)s | %(name)s | %(message)s",
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
            "level": "INFO"
        },
    },
}

SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Banking settings
BANKING_CONFIG = {
    'MAX_DAILY_TRANSFER': 5000.00,
    'MAX_TRANSACTION_AMOUNT': 1000.00,
    'OTP_EXPIRY_MINUTES': 10,
    'SUPPORTED_BANKS': ['OPAY', 'PALMPAY', 'MONIEPOINT'],
    'TRANSACTION_FEE_PERCENTAGE': 0.015,
    'MINIMUM_BALANCE': 0.00,
    'DAILY_WITHDRAWAL_LIMIT': 500.00,
    'DAILY_TRANSFER_LIMIT': 1000.00,
}

# Security settings
PIN_HASH_ITERATIONS = 100000
WEBHOOK_TIMEOUT = 10
APPEND_SLASH = True

# settings.py (add these)
# Virtual Account Providers
DEFAULT_VIRTUAL_ACCOUNT_PROVIDER = "paystack"  # paystack, monnify, flutterwave
DEFAULT_TRANSFER_PROVIDER = "paystack"

# Paystack
'''PAYSTACK_SECRET_KEY = config("PAYSTACK_SECRET_KEY")
PAYSTACK_PUBLIC_KEY = config("PAYSTACK_PUBLIC_KEY")

# Monnify
MONNIFY_API_KEY = config("MONNIFY_API_KEY")
MONNIFY_SECRET_KEY = config("MONNIFY_SECRET_KEY")
MONNIFY_CONTRACT_CODE = config("MONNIFY_CONTRACT_CODE")
MONNIFY_BASE_URL = "https://api.monnify.com"

# Flutterwave
FLUTTERWAVE_SECRET_KEY = config("FLUTTERWAVE_SECRET_KEY")
FLUTTERWAVE_PUBLIC_KEY = config("FLUTTERWAVE_PUBLIC_KEY")

# BVN Providers
BVN_PROVIDER = "verifyme"  # verifyme, prembly, nibss
VERIFYME_API_KEY = config("VERIFYME_API_KEY")
PREMBLY_API_KEY = config("PREMBLY_API_KEY")
NIBSS_API_KEY = config("NIBSS_API_KEY")

# KYC Tier Limits
KYC_TIER_LIMITS = {
    'TIER_1': {
        'daily': 50000,      # ₦50,000
        'monthly': 300000,   # ₦300,000
        'per_transaction': 50000,
    },
    'TIER_2': {
        'daily': 200000,     # ₦200,000
        'monthly': 1000000,  # ₦1,000,000
        'per_transaction': 200000,
    },
    'TIER_3': {
        'daily': 1000000,    # ₦1,000,000
        'monthly': 5000000,  # ₦5,000,000
        'per_transaction': 1000000,
    }
}

# Encryption key for sensitive data
ENCRYPTION_KEY = config("ENCRYPTION_KEY")'''

ENCRYPTION_KEY = config(
    "ENCRYPTION_KEY",
    default="-T1gt706CYI2F-RJCZWdKmv40r9F0w15iq_w8OYgljc=",
)

# For production, consider using cloud storage
# DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

