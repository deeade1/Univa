# apps/backend/ecommerce/services/shipping/__init__.py
"""Shipping services for the ecommerce app."""

from .postal_codes import (
    filter_shipping_methods_by_postal_code_rules,
    validate_postal_code,
    normalize_postal_code,
    extract_postal_code_from_address,
    get_postal_code_rules_for_method,
    is_postal_code_allowed,
    get_allowed_postal_codes,
    get_excluded_postal_codes,
)

__all__ = [
    'filter_shipping_methods_by_postal_code_rules',
    'validate_postal_code',
    'normalize_postal_code',
    'extract_postal_code_from_address',
    'get_postal_code_rules_for_method',
    'is_postal_code_allowed',
    'get_allowed_postal_codes',
    'get_excluded_postal_codes',
]