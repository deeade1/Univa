# apps/backend/check_product_fmap.py
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings.dev")
import django

django.setup()

from django.apps import apps

Product = apps.get_model("ecommerce", "Product")
User = apps.get_model("auth", "User")

for label, model in [("Product", Product), ("User", User)]:
    fmap = model._meta._forward_fields_map
    print(f"=== {label}._forward_fields_map ===")
    print(f"  length: {len(fmap)}")
    print(f"  keys: {sorted(fmap.keys())}")
    print(f"  has created_at: {'created_at' in fmap}")
    print(f"  has updated_at: {'updated_at' in fmap}")
    print()

print("=== Product._meta.get_field('created_at') ===")
try:
    f = Product._meta.get_field("created_at")
    print(f"  OK: {f}")
except Exception as e:
    print(f"  FAILED: {type(e).__name__} - {e}")

print()
print("=== Product._meta.fields_map ===")
print(f"  length: {len(Product._meta.fields_map)}")
print(f"  has created_at: {'created_at' in Product._meta.fields_map}")
print()

# Now clear the cache and rebuild
print("=== Clearing Product's cache and rebuilding ===")
Product._meta.__dict__.pop("_forward_fields_map", None)
Product._meta.__dict__.pop("fields_map", None)
fresh = Product._meta._forward_fields_map
print(f"  length after rebuild: {len(fresh)}")
print(f"  keys after rebuild: {sorted(fresh.keys())}")
print(f"  has created_at: {'created_at' in fresh}")
print(f"  has updated_at: {'updated_at' in fresh}")