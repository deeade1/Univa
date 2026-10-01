# apps/backend/check_product.py
"""
Diagnose which Product class ProductNode is bound to.
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

# --- 1. Django's app registry view of Product -----------------------------
from django.apps import apps

registry_product = apps.get_model("ecommerce", "Product")
print("=== App registry Product ===")
print(f"  module : {registry_product.__module__}")
print(f"  name   : {registry_product.__name__}")
print(f"  id     : {id(registry_product)}")
print(f"  file   : {registry_product.__module__.replace('.', '/')}.py")
print("  fields :")
for f in registry_product._meta.get_fields():
    print(f"      - {f.name} ({type(f).__name__})")

# --- 2. Direct import from the model module ------------------------------
print()
print("=== Direct import from ecommerce.models.product ===")
from ecommerce.models.product import Product as DirectProduct
print(f"  module : {DirectProduct.__module__}")
print(f"  name   : {DirectProduct.__name__}")
print(f"  id     : {id(DirectProduct)}")
print(f"  same as registry? {DirectProduct is registry_product}")

# --- 3. Import from ecommerce.models (in case of re-export) --------------
print()
print("=== Import from ecommerce.models (package) ===")
try:
    from ecommerce.models import Product as PackageProduct
    print(f"  module : {PackageProduct.__module__}")
    print(f"  name   : {PackageProduct.__name__}")
    print(f"  id     : {id(PackageProduct)}")
    print(f"  same as registry? {PackageProduct is registry_product}")
    print(f"  same as direct?   {PackageProduct is DirectProduct}")
except Exception as e:
    print(f"  FAILED: {e}")

# --- 4. What ProductNode is actually bound to ----------------------------
print()
print("=== ProductNode._meta.model ===")
try:
    from graphq.ecommerce.types.product import ProductNode
    NodeProduct = ProductNode._meta.model
    print(f"  module : {NodeProduct.__module__}")
    print(f"  name   : {NodeProduct.__name__}")
    print(f"  id     : {id(NodeProduct)}")
    print(f"  same as registry? {NodeProduct is registry_product}")
    print(f"  same as direct?   {NodeProduct is DirectProduct}")
    print(f"  has created_at? {any(f.name == 'created_at' for f in NodeProduct._meta.get_fields())}")
    print(f"  has updated_at? {any(f.name == 'updated_at' for f in NodeProduct._meta.get_fields())}")
except Exception as e:
    print(f"  FAILED: {e}")

# --- 5. Where ProductNode.Meta.filter_fields actually lives --------------
print()
print("=== ProductNode.Meta ===")
try:
    print(f"  filter_fields: {dict(ProductNode._meta.filter_fields)}")
    print(f"  ordering: {ProductNode._meta.ordering}")
except Exception as e:
    print(f"  FAILED: {e}")

# --- 6. Look for a shadowing Product class --------------------------------
print()
print("=== Any other class named 'Product' in the app registry? ===")
for app_config in apps.get_app_configs():
    for model in app_config.get_models():
        if model.__name__ == "Product":
            print(f"  {app_config.label}.{model.__name__} -> {model.__module__} (id={id(model)})")