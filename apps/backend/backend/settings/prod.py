from decouple import config

from .base import *

DEBUG = False

ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=lambda v: [s.strip() for s in v.split(",")])

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": config("POSTGRES_DB"),
        "USER": config("POSTGRES_USER"),
        "PASSWORD": config("POSTGRES_PASSWORD"),
        "HOST": config("PGHOST"),
        "PORT": config("PGPORT", cast=int, default=5432),
        'CONN_MAX_AGE': 300,  # 5 minutes connection persistence
        'OPTIONS': {
            'application_name': 'transport_app',
            'connect_timeout': 10,
        },
        'TEST': {
            'NAME': 'test_transport_db',
        }
    }
}


# Read replica for read-heavy operations
DATABASES['replica'] = {
    **DATABASES['default'],
    'HOST': os.getenv('DB_REPLICA_HOST', os.getenv('DB_HOST', 'localhost'))
}

# Database router for read/write splitting
class PrimaryReplicaRouter:
    def db_for_read(self, model, **hints):
        return 'replica'
    
    def db_for_write(self, model, **hints):
        return 'default'
    
    def allow_relation(self, obj1, obj2, **hints):
        return True
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return db == 'default'
    
# Production logging (JSON structured logs)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "fmt": "%(asctime)s %(levelname)s %(name)s %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "django.db.backends": {"handlers": ["console"], "level": "ERROR", "propagate": False},
    },
}


