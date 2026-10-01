# apps/backend/ecommerce/services/checkout/problems.py
"""Checkout problem detection and resolution."""

import logging
from typing import List, Tuple, Dict, Any, Optional
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


class CheckoutProblem:
    """Checkout problem types."""
    
    INSUFFICIENT_STOCK = 'insufficient_stock'
    INVALID_VOUCHER = 'invalid_voucher'
    EXPIRED_VOUCHER = 'expired_voucher'
    MINIMUM_SPEND_NOT_MET = 'minimum_spend_not_met'
    INVALID_SHIPPING = 'invalid_shipping'
    INVALID_ADDRESS = 'invalid_address'
    PAYMENT_FAILED = 'payment_failed'
    PRICE_CHANGED = 'price_changed'
    PRODUCT_UNAVAILABLE = 'product_unavailable'
    
    CHOICES = [
        (INSUFFICIENT_STOCK, 'Insufficient stock'),
        (INVALID_VOUCHER, 'Invalid voucher'),
        (EXPIRED_VOUCHER, 'Expired voucher'),
        (MINIMUM_SPEND_NOT_MET, 'Minimum spend not met'),
        (INVALID_SHIPPING, 'Invalid shipping method'),
        (INVALID_ADDRESS, 'Invalid address'),
        (PAYMENT_FAILED, 'Payment failed'),
        (PRICE_CHANGED, 'Price changed'),
        (PRODUCT_UNAVAILABLE, 'Product unavailable'),
    ]


def detect_checkout_problems(checkout: Any) -> List[Dict[str, Any]]:
    """
    Detect problems with a checkout.
    
    Args:
        checkout: Checkout object
        
    Returns:
        List: List of detected problems
    """
    problems = []
    
    # 1. Check stock
    stock_problems = _check_stock(checkout)
    problems.extend(stock_problems)
    
    # 2. Check voucher
    voucher_problems = _check_voucher(checkout)
    problems.extend(voucher_problems)
    
    # 3. Check shipping
    shipping_problems = _check_shipping(checkout)
    problems.extend(shipping_problems)
    
    # 4. Check address
    address_problems = _check_address(checkout)
    problems.extend(address_problems)
    
    # 5. Check prices
    price_problems = _check_prices(checkout)
    problems.extend(price_problems)
    
    # 6. Check product availability
    availability_problems = _check_product_availability(checkout)
    problems.extend(availability_problems)
    
    return problems


def _check_stock(checkout: Any) -> List[Dict[str, Any]]:
    """Check for insufficient stock problems."""
    problems = []
    
    for line in checkout.lines.all():
        if not line.variant:
            problems.append({
                'type': CheckoutProblem.PRODUCT_UNAVAILABLE,
                'message': f'Product variant not found for line {line.id}',
                'line_id': str(line.id),
                'severity': 'error',
            })
            continue
        
        if hasattr(line.variant, 'track_inventory') and line.variant.track_inventory:
            # Check available stock
            from ecommerce.models.warehouse import Stock
            
            total_stock = Stock.objects.filter(
                variant=line.variant
            ).aggregate(total=models.Sum('quantity'))['total'] or 0
            
            if total_stock < line.quantity:
                problems.append({
                    'type': CheckoutProblem.INSUFFICIENT_STOCK,
                    'message': f'Insufficient stock for {line.variant.name}. Available: {total_stock}',
                    'line_id': str(line.id),
                    'variant_id': str(line.variant.id),
                    'available': total_stock,
                    'requested': line.quantity,
                    'severity': 'error',
                })
    
    return problems


def _check_voucher(checkout: Any) -> List[Dict[str, Any]]:
    """Check for voucher problems."""
    problems = []
    
    if not checkout.voucher_code:
        return problems
    
    from ecommerce.models.discount import VoucherCode
    
    try:
        voucher_code = VoucherCode.objects.get(
            code=checkout.voucher_code.upper(),
            is_active=True
        )
        voucher = voucher_code.voucher
        
        # Check if voucher is active
        if not voucher.is_active:
            problems.append({
                'type': CheckoutProblem.INVALID_VOUCHER,
                'message': 'Voucher is not active',
                'voucher_code': checkout.voucher_code,
                'severity': 'error',
            })
            return problems
        
        # Check if voucher has expired
        if voucher.end_date and voucher.end_date < timezone.now():
            problems.append({
                'type': CheckoutProblem.EXPIRED_VOUCHER,
                'message': 'Voucher has expired',
                'voucher_code': checkout.voucher_code,
                'expired_at': str(voucher.end_date),
                'severity': 'error',
            })
            return problems
        
        # Check usage limit
        if voucher.usage_limit:
            used_count = voucher.codes.aggregate(total=models.Sum('used'))['total'] or 0
            if used_count >= voucher.usage_limit:
                problems.append({
                    'type': CheckoutProblem.INVALID_VOUCHER,
                    'message': 'Voucher has reached usage limit',
                    'voucher_code': checkout.voucher_code,
                    'severity': 'error',
                })
                return problems
        
        # Check minimum spend
        channel_listing = voucher.channel_listings.filter(
            channel=checkout.channel
        ).first()
        if channel_listing and channel_listing.min_spent:
            if checkout.subtotal.gross < channel_listing.min_spent:
                problems.append({
                    'type': CheckoutProblem.MINIMUM_SPEND_NOT_MET,
                    'message': f'Minimum spend of {channel_listing.min_spent} required',
                    'voucher_code': checkout.voucher_code,
                    'min_spent': str(channel_listing.min_spent.amount),
                    'current_subtotal': str(checkout.subtotal.gross.amount),
                    'severity': 'warning',
                })
        
    except VoucherCode.DoesNotExist:
        problems.append({
            'type': CheckoutProblem.INVALID_VOUCHER,
            'message': 'Invalid voucher code',
            'voucher_code': checkout.voucher_code,
            'severity': 'error',
        })
    
    return problems


def _check_shipping(checkout: Any) -> List[Dict[str, Any]]:
    """Check for shipping problems."""
    problems = []
    
    if not checkout.is_shipping_required():
        return problems
    
    if not checkout.shipping_method:
        problems.append({
            'type': CheckoutProblem.INVALID_SHIPPING,
            'message': 'No shipping method selected',
            'severity': 'error',
        })
        return problems
    
    # Check if shipping method is still valid
    if not checkout.shipping_method.is_active:
        problems.append({
            'type': CheckoutProblem.INVALID_SHIPPING,
            'message': 'Selected shipping method is no longer available',
            'shipping_method': checkout.shipping_method.name,
            'severity': 'error',
        })
    
    return problems


def _check_address(checkout: Any) -> List[Dict[str, Any]]:
    """Check for address problems."""
    problems = []
    
    if not checkout.is_shipping_required():
        return problems
    
    if not checkout.shipping_address:
        problems.append({
            'type': CheckoutProblem.INVALID_ADDRESS,
            'message': 'No shipping address provided',
            'severity': 'error',
        })
        return problems
    
    address = checkout.shipping_address
    
    # Check required fields
    required_fields = ['first_name', 'last_name', 'street_address_1', 'city', 'country']
    
    for field in required_fields:
        if not getattr(address, field, None):
            problems.append({
                'type': CheckoutProblem.INVALID_ADDRESS,
                'message': f'Missing {field} in shipping address',
                'field': field,
                'severity': 'error',
            })
    
    # Check if country is supported
    if address.country:
        from django_countries import countries
        if address.country.code not in [c.code for c in countries]:
            problems.append({
                'type': CheckoutProblem.INVALID_ADDRESS,
                'message': f'Unsupported country: {address.country.name}',
                'field': 'country',
                'severity': 'warning',
            })
    
    return problems


def _check_prices(checkout: Any) -> List[Dict[str, Any]]:
    """Check for price changes."""
    problems = []
    
    for line in checkout.lines.all():
        if not line.variant:
            continue
        
        # Get current price from channel listing
        listing = line.variant.channel_listings.filter(
            channel=checkout.channel
        ).first()
        
        if listing and listing.price:
            current_price = listing.price.amount
            stored_price = line.total_price.net.amount / line.quantity if line.quantity > 0 else 0
            
            if abs(current_price - stored_price) > Decimal('0.01'):
                problems.append({
                    'type': CheckoutProblem.PRICE_CHANGED,
                    'message': f'Price changed for {line.variant.name}',
                    'line_id': str(line.id),
                    'old_price': str(stored_price),
                    'new_price': str(current_price),
                    'severity': 'warning',
                })
    
    return problems


def _check_product_availability(checkout: Any) -> List[Dict[str, Any]]:
    """Check if products are still available."""
    problems = []
    
    for line in checkout.lines.all():
        if not line.variant:
            continue
        
        # Check if product is published
        if hasattr(line.variant.product, 'is_published'):
            if not line.variant.product.is_published:
                problems.append({
                    'type': CheckoutProblem.PRODUCT_UNAVAILABLE,
                    'message': f'Product {line.variant.product.name} is no longer available',
                    'line_id': str(line.id),
                    'product_id': str(line.variant.product.id),
                    'severity': 'error',
                })
        
        # Check if variant is active
        if hasattr(line.variant, 'is_active') and not line.variant.is_active:
            problems.append({
                'type': CheckoutProblem.PRODUCT_UNAVAILABLE,
                'message': f'Variant {line.variant.name} is no longer available',
                'line_id': str(line.id),
                'variant_id': str(line.variant.id),
                'severity': 'error',
            })
    
    return problems


def resolve_checkout_problems(checkout: Any) -> Tuple[bool, List[str]]:
    """
    Attempt to resolve checkout problems.
    
    Args:
        checkout: Checkout object
        
    Returns:
        Tuple: (success, list of resolution messages)
    """
    problems = detect_checkout_problems(checkout)
    messages = []
    
    if not problems:
        return True, ['No problems found']
    
    with transaction.atomic():
        for problem in problems:
            if problem['type'] == CheckoutProblem.INSUFFICIENT_STOCK:
                # Try to reduce quantity or remove item
                resolved = _resolve_stock_problem(checkout, problem)
                if resolved:
                    messages.append(f"Stock issue resolved for line {problem.get('line_id')}")
                else:
                    messages.append(f"Could not resolve stock issue for line {problem.get('line_id')}")
                    
            elif problem['type'] == CheckoutProblem.INVALID_VOUCHER:
                # Remove invalid voucher
                checkout.voucher_code = None
                checkout.save(update_fields=['voucher_code'])
                messages.append(f"Removed invalid voucher {problem.get('voucher_code')}")
                
            elif problem['type'] == CheckoutProblem.EXPIRED_VOUCHER:
                # Remove expired voucher
                checkout.voucher_code = None
                checkout.save(update_fields=['voucher_code'])
                messages.append(f"Removed expired voucher {problem.get('voucher_code')}")
                
            elif problem['type'] == CheckoutProblem.PRICE_CHANGED:
                # Update prices
                from .calculations import CheckoutCalculator
                calculator = CheckoutCalculator(request=None, user=checkout.user)
                calculator._calculate_final_total()
                messages.append("Prices updated")
                
            elif problem['type'] == CheckoutProblem.PRODUCT_UNAVAILABLE:
                # Remove unavailable product
                if problem.get('line_id'):
                    from ecommerce.models.checkout import CheckoutLine
                    CheckoutLine.objects.filter(id=problem['line_id']).delete()
                    messages.append(f"Removed unavailable product line {problem.get('line_id')}")
    
    # Check if there are still error-level problems
    remaining_problems = detect_checkout_problems(checkout)
    critical_problems = [p for p in remaining_problems if p.get('severity') == 'error']
    
    if critical_problems:
        return False, messages + [f"Critical problems remain: {len(critical_problems)}"]
    
    return True, messages


def _resolve_stock_problem(checkout: Any, problem: Dict[str, Any]) -> bool:
    """Resolve a stock problem by reducing quantity."""
    line_id = problem.get('line_id')
    if not line_id:
        return False
    
    from ecommerce.models.checkout import CheckoutLine
    
    try:
        line = CheckoutLine.objects.get(id=line_id, checkout=checkout)
        available = problem.get('available', 0)
        
        if available > 0:
            # Reduce quantity to available stock
            line.quantity = available
            line.save(update_fields=['quantity'])
            return True
        else:
            # Remove the line completely
            line.delete()
            return True
            
    except CheckoutLine.DoesNotExist:
        return False