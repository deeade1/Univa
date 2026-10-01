from .base import *


# ============================================================================
# TEST MODE
# ============================================================================

DEBUG = True


# ============================================================================
# DATABASE
# ============================================================================

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": config("POSTGRES_DB"),
        "USER": config("POSTGRES_USER"),
        "PASSWORD": config("POSTGRES_PASSWORD"),
        "HOST": config("PGHOST"),
        "PORT": config("PGPORT"),
        "TEST": {
            "NAME": "test_root",
            "TEMPLATE": "template_extensions",
        },
    }
}


# ============================================================================
# CELERY
# ============================================================================

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True


# ============================================================================
# CACHE
# ============================================================================

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}


# ============================================================================
# CHANNEL LAYERS
# ============================================================================

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}


# ============================================================================
# FIREBASE
# ============================================================================

try:
    import firebase_admin

    if firebase_admin._apps:
        firebase_admin._apps.clear()

except ImportError:
    pass


# ============================================================================
# PASSWORD HASHING
# ============================================================================

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]


# ============================================================================
# TEST DIAGNOSTICS
# ============================================================================

print("✅ Test settings loaded")
print(f"   Installed apps: {len(INSTALLED_APPS)}")
print(f"   Database engine: {DATABASES['default']['ENGINE']}")
print(f"   GDAL_LIBRARY_PATH: {GDAL_LIBRARY_PATH}")
print(f"   GEOS_LIBRARY_PATH: {GEOS_LIBRARY_PATH}")
print(f"   GDAL_DATA: {GDAL_DATA}")
print(f"   PROJ_LIB: {PROJ_LIB}")
