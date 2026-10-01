# apps/backend/ecommerce/services/checkout/complete_checkout.py
"""Complete checkout process - handles finalizing an order."""

import logging
from decimal import Decimal
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from .calculations import CheckoutCalculator
from .checkout_cleaner import clean_checkout
from .payment_utils import process_payment
from .problems import resolve_checkout_problems

logger = logging.getLogger(__name__)


class CheckoutCompleter:
    """
    Handles the complete checkout process.
    
    This is the authoritative checkout completion service.
    All calculations are performed on the backend.
    """
    
    def __init__(self, checkout_id: str, user=None):
        self.checkout_id = checkout_id
        self.user = user
        self.checkout = None
        self.calculator = None
    
    def complete(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Complete the checkout process.
        
        Returns:
            Tuple: (success, result_data)
        """
        try:
            # 1. Load checkout
            if not self._load_checkout():
                return False, {'error': 'Checkout not found'}
            
            # 2. Lock checkout to prevent concurrent modifications
            with transaction.atomic():
                # 3. Clean and validate checkout
                is_valid, messages = clean_checkout(self.checkout)
                if not is_valid:
                    return False, {'error': 'Invalid checkout', 'messages': messages}
                
                # 4. Check for problems and try to resolve
                problems_resolved, problem_messages = resolve_checkout_problems(self.checkout)
                if not problems_resolved:
                    return False, {'error': 'Checkout has unresolved problems', 'messages': problem_messages}
                
                # 5. Calculate final total (authoritative)
                final_calculation = self._calculate_final_total()
                if not final_calculation:
                    return False, {'error': 'Failed to calculate final total'}
                
                # 6. Process payment
                payment_result = self._process_payment(final_calculation)
                if not payment_result['success']:
                    return False, {'error': 'Payment failed', 'details': payment_result}
                
                # 7. Create order
                order = self._create_order(final_calculation, payment_result)
                if not order:
                    return False, {'error': 'Failed to create order'}
                
                # 8. Complete checkout
                self._complete_checkout(order)
                
                # 9. Send notifications
                self._send_notifications(order)
                
                return True, {
                    'order_id': str(order.id),
                    'order_number': order.number,
                    'total': str(final_calculation.total),
                    'currency': final_calculation.currency,
                    'payment': payment_result,
                }
                
        except Exception as e:
            logger.exception(f"Checkout completion failed for {self.checkout_id}: {str(e)}")
            return False, {'error': str(e)}
    
    def _load_checkout(self) -> bool:
        """Load checkout from database."""
        from ecommerce.models.checkout import Checkout
        
        try:
            self.checkout = Checkout.objects.select_related(
                'user',
                'channel',
                'shipping_address',
                'billing_address',
                'shipping_method',
            ).prefetch_related(
                'lines',
                'lines__variant',
                'lines__variant__product',
            ).get(pk=self.checkout_id)
            
            if self.user and self.checkout.user != self.user:
                logger.warning(f"User mismatch for checkout {self.checkout_id}")
                return False
            
            return True
            
        except Checkout.DoesNotExist:
            logger.error(f"Checkout not found: {self.checkout_id}")
            return False
    
    def _calculate_final_total(self):
        """Calculate the final authoritative total."""
        self.calculator = CheckoutCalculator(
            request=None,
            user=self.checkout.user
        )
        
        return self.calculator.get_final(
            checkout_id=str(self.checkout.id),
            items=list(self.checkout.lines.all()),
            promo_code=self.checkout.voucher_code,
            shipping_method=self.checkout.shipping_method,
            address=self.checkout.shipping_address,
            gift_cards=list(self.checkout.gift_cards.all()) if hasattr(self.checkout, 'gift_cards') else None,
        )
    
    def _process_payment(self, calculation) -> Dict[str, Any]:
        """Process payment for the checkout."""
        return process_payment(
            checkout=self.checkout,
            total=calculation.total,
            currency=calculation.currency,
            user=self.checkout.user,
        )
    
    def _create_order(self, calculation, payment_result) -> Optional[Any]:
        """Create order from checkout."""
        from ecommerce.models.order import Order
        
        with transaction.atomic():
            # Create order
            order = Order.objects.create(
                user=self.checkout.user,
                user_email=self.checkout.get_customer_email(),
                billing_address=self.checkout.billing_address,
                shipping_address=self.checkout.shipping_address,
                channel=self.checkout.channel,
                currency=calculation.currency,
                total_net_amount=calculation.subtotal,
                total_gross_amount=calculation.total,
                shipping_price_net_amount=calculation.shipping,
                shipping_price_gross_amount=calculation.shipping,
                shipping_method=self.checkout.shipping_method,
                voucher_code=self.checkout.voucher_code,
                status='unconfirmed',  # Will be confirmed after payment
                origin='checkout',
                display_gross_prices=True,
            )
            
            # Create order lines
            from ecommerce.models.order import OrderLine
            
            for line in self.checkout.lines.all():
                OrderLine.objects.create(
                    order=order,
                    variant=line.variant,
                    product_name=line.variant.product.name,
                    variant_name=line.variant.name,
                    quantity=line.quantity,
                    unit_price_net_amount=line.total_price_net_amount / line.quantity,
                    unit_price_gross_amount=line.total_price_gross_amount / line.quantity,
                    total_price_net_amount=line.total_price_net_amount,
                    total_price_gross_amount=line.total_price_gross_amount,
                    currency=calculation.currency,
                    is_shipping_required=line.variant.is_shipping_required(),
                )
            
            # Link payment to order
            if payment_result.get('payment_id'):
                from payment.models import Payment
                payment = Payment.objects.get(pk=payment_result['payment_id'])
                payment.order = order
                payment.save(update_fields=['order'])
            
            return order
    
    def _complete_checkout(self, order):
        """Mark checkout as completed."""
        self.checkout.completing_started_at = timezone.now()
        self.checkout.status = 'completed'
        self.checkout.save()
        
        # Update order with checkout token
        order.checkout_token = str(self.checkout.pk)
        order.save(update_fields=['checkout_token'])
    
    def _send_notifications(self, order):
        """Send order confirmation notifications."""
        try:
            from notifications.services.emitter import emit_notification_event
            
            emit_notification_event(
                user=order.user,
                event="ORDER.CONFIRMED",
                module="order",
                payload={
                    "order_id": str(order.id),
                    "order_number": order.number,
                    "total": str(order.total_gross_amount),
                    "currency": order.currency,
                }
            )
        except ImportError:
            logger.warning("Notification system not available")


def complete_checkout(checkout_id: str, user=None) -> Tuple[bool, Dict[str, Any]]:
    """
    Convenience function to complete a checkout.
    
    Args:
        checkout_id: Checkout ID
        user: Optional user for authorization
        
    Returns:
        Tuple: (success, result_data)
    """
    completer = CheckoutCompleter(checkout_id, user)
    return completer.complete()