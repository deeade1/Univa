# ecommerce/services/product/__init__.py

"""
Product services.

Public API:

    from ecommerce.services.product import (
        get_variant_price,
        get_variant_base_price,
        get_variant_availability,
        get_product_price_range,
        get_product_availability,
        resolve_tax_rate,
    )
"""

from ecommerce.services.product.pricing import (
    get_product_availability,
    get_product_price_range,
    get_variant_availability,
    get_variant_base_price,
    get_variant_price,
    resolve_tax_rate,
)

__all__ = [
    "get_variant_price",
    "get_variant_base_price",
    "get_variant_availability",
    "get_product_price_range",
    "get_product_availability",
    "resolve_tax_rate",
]