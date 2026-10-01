from .base import *

DEBUG = True

INSTALLED_APPS += [
    "debug_toolbar",
]

MIDDLEWARE += [
    "debug_toolbar.middleware.DebugToolbarMiddleware",

]



INTERNAL_IPS = ["127.0.0.1"]



DATABASES = {
    'default': {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        'NAME': config('POSTGRES_DB'),
        'USER': config('POSTGRES_USER'),
        'PASSWORD': config('POSTGRES_PASSWORD'),
        'HOST': config('PGHOST'),
        'PORT': config('PGPORT'),
        'TEST': {
            'NAME': 'test_root',
            'TEMPLATE': 'template_extensions',  # Use the template with both extensions
        },
    }
}

