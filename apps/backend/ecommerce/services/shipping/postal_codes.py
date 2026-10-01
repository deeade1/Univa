# apps/backend/ecommerce/services/shipping/postal_codes.py
"""Postal code utilities for shipping."""

import re
from typing import List, Optional, Any, Union
from decimal import Decimal

from django.db import models


def filter_shipping_methods_by_postal_code_rules(
    shipping_methods: List[Any],
    shipping_address: Any,
) -> List[Any]:
    """
    Filter shipping methods based on postal code rules.
    
    Args:
        shipping_methods: List of shipping methods to filter
        shipping_address: Shipping address with postal code
        
    Returns:
        List[Any]: Filtered list of shipping methods
        
    Example:
        >>> methods = ShippingMethod.objects.all()
        >>> address = Order.objects.first().shipping_address
        >>> filtered = filter_shipping_methods_by_postal_code_rules(methods, address)
    """
    if not shipping_methods:
        return []
    
    if not shipping_address or not shipping_address.postal_code:
        # If no postal code, return all methods
        return list(shipping_methods)
    
    postal_code = shipping_address.postal_code.strip().upper()
    filtered_methods = []
    
    for method in shipping_methods:
        # Get postal code rules for this method
        rules = getattr(method, 'postal_code_rules', None)
        if not rules:
            # If no rules, method is valid for all postal codes
            filtered_methods.append(method)
            continue
        
        # Get active rules
        active_rules = rules.filter(is_active=True) if hasattr(rules, 'filter') else rules.all()
        
        if not active_rules.exists():
            # If no active rules, method is valid for all postal codes
            filtered_methods.append(method)
            continue
        
        # Check for exclusion rules
        excluded = False
        for rule in active_rules:
            if rule.inclusion_type == 'exclude':
                if _matches_postal_code(rule, postal_code):
                    excluded = True
                    break
        
        if excluded:
            continue
        
        # Check for inclusion rules
        included = False
        has_inclusion_rules = False
        
        for rule in active_rules:
            if rule.inclusion_type == 'include':
                has_inclusion_rules = True
                if _matches_postal_code(rule, postal_code):
                    included = True
                    break
        
        # If there are inclusion rules and none match, exclude method
        if has_inclusion_rules and not included:
            continue
        
        # Method passed all checks
        filtered_methods.append(method)
    
    return filtered_methods


def _matches_postal_code(rule: Any, postal_code: str) -> bool:
    """
    Check if a postal code matches a rule.
    
    Args:
        rule: Postal code rule object
        postal_code: Postal code to check
        
    Returns:
        bool: True if matches, False otherwise
    """
    start = rule.start.strip().upper() if rule.start else ''
    end = rule.end.strip().upper() if rule.end else None
    
    if not start:
        return False
    
    if end:
        # Range check
        return start <= postal_code <= end
    else:
        # Exact match
        return start == postal_code


def validate_postal_code(postal_code: str, country_code: str = None) -> bool:
    """
    Validate a postal code format for a given country.
    
    Args:
        postal_code: Postal code to validate
        country_code: ISO country code (optional)
        
    Returns:
        bool: True if valid, False otherwise
        
    Example:
        >>> validate_postal_code('90210', 'US')
        True
        >>> validate_postal_code('12345', 'US')
        True
        >>> validate_postal_code('ABC123', 'US')
        False
    """
    if not postal_code:
        return False
    
    # Remove whitespace and convert to uppercase
    postal_code = postal_code.strip().upper()
    
    # Country-specific validation patterns
    patterns = {
        'US': r'^[0-9]{5}(-[0-9]{4})?$',  # 12345 or 12345-6789
        'UK': r'^[A-Z]{1,2}[0-9][A-Z0-9]? [0-9][A-Z]{2}$',  # SW1A 1AA
        'CA': r'^[A-Z][0-9][A-Z] [0-9][A-Z][0-9]$',  # K1A 0A9
        'AU': r'^[0-9]{4}$',  # 2000
        'DE': r'^[0-9]{5}$',  # 10115
        'FR': r'^[0-9]{5}$',  # 75001
        'IT': r'^[0-9]{5}$',  # 00100
        'ES': r'^[0-9]{5}$',  # 28001
        'JP': r'^[0-9]{3}-[0-9]{4}$',  # 100-0001
        'IN': r'^[0-9]{6}$',  # 110001
        'BR': r'^[0-9]{5}-[0-9]{3}$',  # 01000-000
        'RU': r'^[0-9]{6}$',  # 101000
        'ZA': r'^[0-9]{4}$',  # 8001
        'NG': r'^[0-9]{6}$',  # 100001
        'GH': r'^[A-Z]{2}-[0-9]{4}$',  # GA-1234
        'KE': r'^[0-9]{5}$',  # 00100
        'EG': r'^[0-9]{5}$',  # 11511
        'SA': r'^[0-9]{5}$',  # 11564
        'AE': r'^[0-9]{5}$',  # 00000
        'PK': r'^[0-9]{5}$',  # 44000
        'BD': r'^[0-9]{4}$',  # 1000
    }
    
    if country_code and country_code in patterns:
        pattern = patterns[country_code]
        return bool(re.match(pattern, postal_code))
    
    # Generic validation: alphanumeric with spaces, hyphens, and up to 10 characters
    return bool(re.match(r'^[A-Z0-9][A-Z0-9\- ]{0,9}$', postal_code))


def normalize_postal_code(postal_code: str, country_code: str = None) -> str:
    """
    Normalize a postal code for consistent storage and comparison.
    
    Args:
        postal_code: Postal code to normalize
        country_code: ISO country code (optional)
        
    Returns:
        str: Normalized postal code
        
    Example:
        >>> normalize_postal_code('90210', 'US')
        '90210'
        >>> normalize_postal_code('SW1A 1AA', 'UK')
        'SW1A 1AA'
    """
    if not postal_code:
        return ''
    
    # Remove extra whitespace and convert to uppercase
    normalized = postal_code.strip().upper()
    
    # Country-specific normalization
    if country_code:
        if country_code == 'US':
            # Remove spaces from US zip+4
            normalized = normalized.replace(' ', '')
        elif country_code == 'CA':
            # Ensure space between postal code parts
            if len(normalized) == 6 and not normalized[3].isspace():
                normalized = normalized[:3] + ' ' + normalized[3:]
    
    return normalized


def extract_postal_code_from_address(address: Any) -> Optional[str]:
    """
    Extract postal code from an address object.
    
    Args:
        address: Address object with postal_code attribute
        
    Returns:
        Optional[str]: Postal code or None
    """
    if not address:
        return None
    
    postal_code = getattr(address, 'postal_code', None)
    if postal_code:
        return normalize_postal_code(postal_code)
    
    return None


def get_postal_code_rules_for_method(shipping_method: Any) -> List[Any]:
    """
    Get all postal code rules for a shipping method.
    
    Args:
        shipping_method: Shipping method object
        
    Returns:
        List[Any]: List of postal code rules
    """
    if not shipping_method:
        return []
    
    rules = getattr(shipping_method, 'postal_code_rules', None)
    if not rules:
        return []
    
    return list(rules.filter(is_active=True))


def is_postal_code_allowed(
    shipping_method: Any,
    postal_code: str,
) -> bool:
    """
    Check if a postal code is allowed for a shipping method.
    
    Args:
        shipping_method: Shipping method object
        postal_code: Postal code to check
        
    Returns:
        bool: True if allowed, False otherwise
        
    Example:
        >>> method = ShippingMethod.objects.first()
        >>> is_postal_code_allowed(method, '90210')
        True
    """
    if not shipping_method or not postal_code:
        return False
    
    rules = get_postal_code_rules_for_method(shipping_method)
    if not rules:
        return True
    
    postal_code = normalize_postal_code(postal_code)
    
    # Check for exclusions
    for rule in rules:
        if rule.inclusion_type == 'exclude':
            if _matches_postal_code(rule, postal_code):
                return False
    
    # Check for inclusions
    has_inclusion = any(rule.inclusion_type == 'include' for rule in rules)
    if has_inclusion:
        for rule in rules:
            if rule.inclusion_type == 'include':
                if _matches_postal_code(rule, postal_code):
                    return True
        return False
    
    return True


def get_allowed_postal_codes(shipping_method: Any) -> List[str]:
    """
    Get all allowed postal codes for a shipping method.
    
    Args:
        shipping_method: Shipping method object
        
    Returns:
        List[str]: List of allowed postal codes
    """
    if not shipping_method:
        return []
    
    rules = get_postal_code_rules_for_method(shipping_method)
    if not rules:
        return []
    
    allowed_codes = []
    for rule in rules:
        if rule.inclusion_type == 'include':
            if rule.end:
                # Range - expand or just store the range
                allowed_codes.append(f"{rule.start}-{rule.end}")
            else:
                allowed_codes.append(rule.start)
    
    return allowed_codes


def get_excluded_postal_codes(shipping_method: Any) -> List[str]:
    """
    Get all excluded postal codes for a shipping method.
    
    Args:
        shipping_method: Shipping method object
        
    Returns:
        List[str]: List of excluded postal codes
    """
    if not shipping_method:
        return []
    
    rules = get_postal_code_rules_for_method(shipping_method)
    if not rules:
        return []
    
    excluded_codes = []
    for rule in rules:
        if rule.inclusion_type == 'exclude':
            if rule.end:
                excluded_codes.append(f"{rule.start}-{rule.end}")
            else:
                excluded_codes.append(rule.start)
    
    return excluded_codes