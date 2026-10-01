# apps/backend/ecommerce/services/checkout/__init__.py
"""Checkout services for the ecommerce app.

This module provides comprehensive checkout functionality including:
- Preview calculations (fast, frontend-friendly)
- Final calculations (authoritative, backend-only)
- Checkout cleaning and validation
- Complete checkout workflow
- Payment processing
- Problem detection and resolution

Usage:
    # Get a preview for frontend display
    from ecommerce.services.checkout import get_checkout_preview
    preview = get_checkout_preview(items, promo_code, shipping_method)

    # Complete a checkout (authoritative)
    from ecommerce.services.checkout import complete_checkout
    success, result = complete_checkout(checkout_id, user)

    # Clean and validate a checkout
    from ecommerce.services.checkout import clean_checkout
    is_valid, messages = clean_checkout(checkout)

    # Detect and resolve problems
    from ecommerce.services.checkout import detect_checkout_problems, resolve_checkout_problems
    problems = detect_checkout_problems(checkout)
    resolved, messages = resolve_checkout_problems(checkout)
"""

'''from .base_calculations import (
    PriceCalculationResult,
    LinePriceCalculationResult,
    CheckoutPreview,
    CheckoutFinal,
    calculate_subtotal_preview,
    calculate_subtotal_final,
    calculate_shipping_preview,
    calculate_shipping_final,
    calculate_discount_preview,
    calculate_discount_final,
    calculate_tax_preview,
    calculate_tax_final,
    get_default_country,
    get_default_currency,
    validate_currency,
    round_price,
    zero_money_amount,
)

from .calculations import (
    CheckoutCalculator,
)

from .checkout_cleaner import (
    clean_checkout,
    clear_invalid_checkouts,
    update_checkout_prices,
)

from .complete_checkout import (
    complete_checkout,
    CheckoutCompleter,
)

from .payment_utils import (
    process_payment,
)

from .problems import (
    CheckoutProblem,
    detect_checkout_problems,
    resolve_checkout_problems,
)


# =============================================================================
# Convenience Functions
# =============================================================================

def get_checkout_preview(
    items,
    promo_code: str = None,
    shipping_method: str = None,
    country_code: str = None,
    currency: str = None,
):
    """
    Get a preview calculation for frontend display.
    
    This is a fast, lightweight calculation that should be used for UI previews only.
    Never use this for final order totals.
    
    Args:
        items: List of cart items (dicts with price and quantity)
        promo_code: Optional promotion code
        shipping_method: Optional shipping method identifier
        country_code: Optional country code
        currency: Optional currency code
        
    Returns:
        CheckoutPreview: Preview calculation result
        
    Example:
        >>> preview = get_checkout_preview(
        ...     items=[{'price': '10.00', 'quantity': 2}],
        ...     promo_code='SAVE10',
        ...     country_code='US'
        ... )
        >>> print(preview.total_estimate)
        18.00
    """
    from django.utils import timezone
    
    if not currency:
        currency = get_default_currency()
    
    # Convert items to dict if they're model objects
    item_data = []
    for item in items:
        if hasattr(item, 'price') and hasattr(item, 'quantity'):
            item_data.append({
                'price': float(item.price),
                'quantity': int(item.quantity),
            })
        elif isinstance(item, dict):
            item_data.append({
                'price': float(item.get('price', 0)),
                'quantity': int(item.get('quantity', 0)),
            })
        else:
            # Try to extract price and quantity from object
            price = getattr(item, 'price', None) or getattr(item, 'unit_price', 0)
            quantity = getattr(item, 'quantity', 1)
            item_data.append({
                'price': float(price),
                'quantity': int(quantity),
            })
    
    calculator = CheckoutCalculator()
    return calculator.get_preview(
        items=item_data,
        promo_code=promo_code,
        shipping_method=shipping_method,
        country_code=country_code,
    )


def get_checkout_final(
    checkout_id: str,
    user=None,
):
    """
    Get the authoritative final calculation for a checkout.
    
    This should be used when placing an order. All calculations are done
    from database data and are considered authoritative.
    
    Args:
        checkout_id: ID of the checkout
        user: Optional user for authorization
        
    Returns:
        CheckoutFinal: Final calculation result
        
    Example:
        >>> final = get_checkout_final('abc-123', user=request.user)
        >>> print(final.total)
        19.99
    """
    from ecommerce.models.checkout import Checkout
    
    try:
        checkout = Checkout.objects.get(pk=checkout_id)
        
        if user and checkout.user != user:
            raise ValueError("User does not own this checkout")
        
        calculator = CheckoutCalculator(request=None, user=checkout.user)
        return calculator.get_final(
            checkout_id=str(checkout.id),
            items=list(checkout.lines.all()),
            promo_code=checkout.voucher_code,
            shipping_method=checkout.shipping_method,
            address=checkout.shipping_address,
            gift_cards=list(checkout.gift_cards.all()) if hasattr(checkout, 'gift_cards') else None,
        )
        
    except Checkout.DoesNotExist:
        raise ValueError(f"Checkout {checkout_id} not found")


def validate_checkout(checkout_id: str, user=None):
    """
    Validate a checkout without completing it.
    
    Args:
        checkout_id: ID of the checkout
        user: Optional user for authorization
        
    Returns:
        Tuple[bool, List[str]]: (is_valid, messages)
    """
    from ecommerce.models.checkout import Checkout
    from typing import Tuple, List
    
    try:
        checkout = Checkout.objects.get(pk=checkout_id)
        
        if user and checkout.user != user:
            return False, ["User does not own this checkout"]
        
        return clean_checkout(checkout)
        
    except Checkout.DoesNotExist:
        return False, [f"Checkout {checkout_id} not found"]


def get_checkout_total(checkout_id: str, user=None):
    """
    Get the total amount for a checkout.
    
    This is a convenience function that returns just the total amount.
    
    Args:
        checkout_id: ID of the checkout
        user: Optional user for authorization
        
    Returns:
        Decimal: Total amount, or None if not found
    """
    from decimal import Decimal
    from typing import Optional
    
    try:
        final = get_checkout_final(checkout_id, user)
        return final.total
    except (ValueError, Exception):
        return None


def estimate_shipping_cost(
    items,
    shipping_method: str = None,
    country_code: str = None,
):
    """
    Estimate shipping cost for items.
    
    Args:
        items: List of cart items
        shipping_method: Shipping method identifier
        country_code: Country code
        
    Returns:
        Decimal: Estimated shipping cost
    """
    from decimal import Decimal
    
    if not country_code:
        country_code = get_default_country()
    
    preview = get_checkout_preview(
        items=items,
        shipping_method=shipping_method,
        country_code=country_code,
    )
    return preview.shipping_estimate


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Base Calculations
    'PriceCalculationResult',
    'LinePriceCalculationResult',
    'CheckoutPreview',
    'CheckoutFinal',
    'calculate_subtotal_preview',
    'calculate_subtotal_final',
    'calculate_shipping_preview',
    'calculate_shipping_final',
    'calculate_discount_preview',
    'calculate_discount_final',
    'calculate_tax_preview',
    'calculate_tax_final',
    'get_default_country',
    'get_default_currency',
    'validate_currency',
    'round_price',
    'zero_money_amount',
    
    # Calculations
    'CheckoutCalculator',
    
    # Cleaner
    'clean_checkout',
    'clear_invalid_checkouts',
    'update_checkout_prices',
    
    # Complete Checkout
    'complete_checkout',
    'CheckoutCompleter',
    
    # Payment
    'process_payment',
    
    # Problems
    'CheckoutProblem',
    'detect_checkout_problems',
    'resolve_checkout_problems',
    
    # Convenience Functions
    'get_checkout_preview',
    'get_checkout_final',
    'validate_checkout',
    'get_checkout_total',
    'estimate_shipping_cost',
]'''


# =============================================================================
# Module Documentation
# =============================================================================

__doc__ = """
Checkout Services
=================

This module provides comprehensive checkout functionality for the ecommerce app.

Quick Start
-----------

1. Get a preview for the frontend:
    >>> from ecommerce.services.checkout import get_checkout_preview
    >>> preview = get_checkout_preview(items, promo_code='SAVE10')
    >>> frontend_data = preview.to_dict()

2. Complete a checkout (authoritative):
    >>> from ecommerce.services.checkout import complete_checkout
    >>> success, result = complete_checkout(checkout_id, user=request.user)
    >>> if success:
    ...     order_id = result['order_id']

3. Validate a checkout:
    >>> from ecommerce.services.checkout import validate_checkout
    >>> is_valid, messages = validate_checkout(checkout_id, user=request.user)

4. Detect problems:
    >>> from ecommerce.services.checkout import detect_checkout_problems
    >>> problems = detect_checkout_problems(checkout)

Security Note
-------------
Never trust frontend calculations for final amounts. Always use backend calculations
for order creation. The preview calculations are for UI display only.

Performance Note
----------------
Preview calculations are optimized for speed and can be called frequently.
Final calculations are more expensive and should only be called during checkout
completion.
"""