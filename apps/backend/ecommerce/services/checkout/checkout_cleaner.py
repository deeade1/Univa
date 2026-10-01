# apps/backend/ecommerce/services/checkout/checkout_cleaner.py
"""Checkout cleaning and validation utilities."""

import logging
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal

from django.db import transaction

logger = logging.getLogger(__name__)


def clean_checkout(
    checkout: Any,
    remove_invalid: bool = True,
) -> Tuple[bool, List[str]]:
    """
    Clean and validate a checkout.
    
    Args:
        checkout: Checkout object
        remove_invalid: Whether to remove invalid items
        
    Returns:
        Tuple: (success, list of messages)
    """
    messages = []
    
    # 1. Validate checkout exists
    if not checkout:
        return False, ['Checkout not found']
    
    # 2. Validate user
    if not checkout.user and not checkout.email:
        messages.append('No user or email associated with checkout')
    
    # 3. Validate lines
    line_valid, line_messages = _validate_lines(checkout.lines.all(), remove_invalid)
    messages.extend(line_messages)
    
    # 4. Validate shipping
    shipping_valid, shipping_messages = _validate_shipping(checkout)
    messages.extend(shipping_messages)
    
    # 5. Validate discounts
    discount_valid, discount_messages = _validate_discounts(checkout)
    messages.extend(discount_messages)
    
    # 6. Validate payment
    payment_valid, payment_messages = _validate_payment(checkout)
    messages.extend(payment_messages)
    
    success = all([line_valid, shipping_valid, discount_valid, payment_valid])
    
    # Update checkout status
    if not success and checkout.status != 'invalid':
        checkout.status = 'invalid'
        checkout.save(update_fields=['status'])
    
    return success, messages


def _validate_lines(lines: List[Any], remove_invalid: bool) -> Tuple[bool, List[str]]:
    """Validate checkout lines."""
    messages = []
    success = True
    
    invalid_items = []
    
    for line in lines:
        # Check if variant exists
        if not line.variant:
            messages.append(f'Line {line.id}: Variant not found')
            invalid_items.append(line)
            success = False
            continue
        
        # Check if variant is active
        if hasattr(line.variant, 'is_active') and not line.variant.is_active:
            messages.append(f'Line {line.id}: Variant is not active')
            invalid_items.append(line)
            success = False
            continue
        
        # Check quantity
        if line.quantity <= 0:
            messages.append(f'Line {line.id}: Invalid quantity {line.quantity}')
            invalid_items.append(line)
            success = False
            continue
        
        # Check inventory
        if not _check_inventory(line.variant, line.quantity):
            messages.append(f'Line {line.id}: Insufficient stock')
            invalid_items.append(line)
            success = False
            continue
    
    # Remove invalid items if requested
    if remove_invalid and invalid_items:
        with transaction.atomic():
            for item in invalid_items:
                item.delete()
        messages.append(f'Removed {len(invalid_items)} invalid items')
    
    return success, messages


def _check_inventory(variant: Any, quantity: int) -> bool:
    """Check if there's enough inventory for a variant."""
    if not hasattr(variant, 'track_inventory'):
        return True
    
    if not variant.track_inventory:
        return True
    
    # Check stock
    from ecommerce.models.warehouse import Stock
    
    total_stock = Stock.objects.filter(
        variant=variant
    ).aggregate(total=models.Sum('quantity'))['total'] or 0
    
    return total_stock >= quantity


def _validate_shipping(checkout: Any) -> Tuple[bool, List[str]]:
    """Validate shipping information."""
    messages = []
    
    # Check if shipping is required
    if not checkout.is_shipping_required():
        return True, messages
    
    # Validate shipping address
    if not checkout.shipping_address:
        messages.append('Shipping address is required')
        return False, messages
    
    # Validate shipping method
    if not checkout.shipping_method:
        messages.append('Shipping method is required')
        return False, messages
    
    # Validate address fields
    address = checkout.shipping_address
    required_fields = ['first_name', 'last_name', 'street_address_1', 'city', 'country']
    
    for field in required_fields:
        if not getattr(address, field, None):
            messages.append(f'Shipping address missing {field}')
            return False, messages
    
    return True, messages


def _validate_discounts(checkout: Any) -> Tuple[bool, List[str]]:
    """Validate discounts."""
    messages = []
    
    if not checkout.voucher_code:
        return True, messages
    
    # Validate voucher
    from ecommerce.models.discount import VoucherCode
    
    try:
        voucher_code = VoucherCode.objects.get(
            code=checkout.voucher_code.upper(),
            is_active=True
        )
        voucher = voucher_code.voucher
        
        # Check if voucher is active
        if not voucher.is_active:
            messages.append('Voucher is not active')
            return False, messages
        
        # Check if voucher has expired
        if voucher.end_date and voucher.end_date < timezone.now():
            messages.append('Voucher has expired')
            return False, messages
        
        # Check usage limit
        if voucher.usage_limit:
            used_count = voucher.codes.aggregate(total=models.Sum('used'))['total'] or 0
            if used_count >= voucher.usage_limit:
                messages.append('Voucher has reached usage limit')
                return False, messages
        
        # Check minimum spend
        channel_listing = voucher.channel_listings.filter(
            channel=checkout.channel
        ).first()
        if channel_listing and channel_listing.min_spent:
            if checkout.subtotal.gross < channel_listing.min_spent:
                messages.append(f'Minimum spend of {channel_listing.min_spent} required')
                return False, messages
        
    except VoucherCode.DoesNotExist:
        messages.append('Invalid voucher code')
        return False, messages
    
    return True, messages


def _validate_payment(checkout: Any) -> Tuple[bool, List[str]]:
    """Validate payment information."""
    messages = []
    
    # Check if payment is required
    if checkout.total.gross.amount <= 0:
        return True, messages
    
    # Get active payment
    payment = checkout.get_last_active_payment()
    
    if not payment:
        messages.append('No active payment found')
        return False, messages
    
    # Check if payment is complete
    if payment.charge_status != 'FULLY_CHARGED':
        messages.append(f'Payment not completed: {payment.charge_status}')
        return False, messages
    
    return True, messages


def clear_invalid_checkouts():
    """Clear checkouts that have been marked as invalid for too long."""
    from ecommerce.models.checkout import Checkout
    
    cutoff = timezone.now() - timedelta(hours=24)
    Checkout.objects.filter(
        status='invalid',
        updated_at__lte=cutoff
    ).delete()


def update_checkout_prices(checkout: Any) -> bool:
    """
    Update all prices for a checkout.
    
    Args:
        checkout: Checkout object
        
    Returns:
        bool: True if update was successful
    """
    try:
        from .calculations import CheckoutCalculator
        
        calculator = CheckoutCalculator(request=None, user=checkout.user)
        
        # Get final calculation
        final = calculator.get_final(
            checkout_id=str(checkout.id),
            items=list(checkout.lines.all()),
            promo_code=checkout.voucher_code,
            shipping_method=checkout.shipping_method,
            address=checkout.shipping_address,
        )
        
        # Update checkout
        checkout.subtotal_net_amount = final.subtotal
        checkout.subtotal_gross_amount = final.subtotal
        checkout.shipping_price_net_amount = final.shipping
        checkout.shipping_price_gross_amount = final.shipping
        checkout.total_net_amount = final.total
        checkout.total_gross_amount = final.total
        
        checkout.save()
        return True
        
    except Exception as e:
        logger.error(f"Failed to update checkout prices: {str(e)}")
        return False