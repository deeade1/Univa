# apps/backend/check_filter_lookup.py
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings.dev")
import django

django.setup()

# Instrument django_filters.utils.get_field_parts to log every call
import django_filters.utils as df_utils
_orig_get_field_parts = df_utils.get_field_parts

def _traced_get_field_parts(model, field_name):
    result = _orig_get_field_parts(model, field_name)
    if field_name in ("created_at", "updated_at"):
        print(f"[get_field_parts] model={model.__name__!r} field_name={field_name!r} -> {result!r}")
    return result

df_utils.get_field_parts = _traced_get_field_parts

# Now import the schema and see what happens
print("=== Importing backend.schema ===")
try:
    import backend.schema
    print("Schema built OK")
except Exception as e:
    print(f"Schema build FAILED: {type(e).__name__}: {e}")