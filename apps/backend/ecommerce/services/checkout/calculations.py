# apps/backend/ecommerce/services/checkout/calculations.py
"""Checkout calculations - combines all calculations for preview and final modes."""

''''from decimal import Decimal
from typing import Optional, List, Dict, Any
import logging

from django.conf import settings
from core.pricing.money import Money
from core.pricing.money_field import TaxedMoney

from .base_calculations import (
    CheckoutPreview, CheckoutFinal,
    calculate_subtotal_preview, calculate_subtotal_final,
    calculate_shipping_preview, calculate_shipping_final,
    calculate_discount_preview, calculate_discount_final,
    calculate_tax_preview, calculate_tax_final,
    get_default_currency, validate_currency,
)


logger = logging.getLogger(__name__)


class CheckoutCalculator:
    """
    Centralized checkout calculator with both preview and final modes.
    
    Preview mode: Fast, lightweight calculations for frontend display.
    Final mode: Authoritative, secure calculations from database.
    """
    
    def __init__(self, request=None, user=None, session=None):
        self.request = request
        self.user = user
        self.session = session
        self.currency = get_default_currency()
    
    def get_preview(
        self,
        items: List[Dict[str, Any]],
        promo_code: Optional[str] = None,
        shipping_method: Optional[str] = None,
        country_code: Optional[str] = None,
    ) -> CheckoutPreview:
        """
        PREVIEW MODE - For frontend display only.
        Fast, lightweight calculations.
        
        Args:
            items: List of cart items with price, quantity
            promo_code: Optional promotion code
            shipping_method: Optional shipping method
            country_code: Optional country code
            
        Returns:
            CheckoutPreview: Preview calculation result
        """
        # Quick calculations from provided data
        subtotal = calculate_subtotal_preview(items, self.currency)
        shipping = calculate_shipping_preview(shipping_method, items, country_code or 'US')
        discount = calculate_discount_preview(promo_code, subtotal)
        tax = calculate_tax_preview(subtotal, country_code or 'US', items)
        total = subtotal + shipping - discount + tax
        
        return CheckoutPreview(
            subtotal=subtotal,
            shipping_estimate=shipping,
            discount_estimate=discount,
            tax_estimate=tax,
            total_estimate=total,
            currency=self.currency,
            is_estimated=True
        )
    
    def get_final(
        self,
        checkout_id: Optional[str] = None,
        items: Optional[List[Any]] = None,
        promo_code: Optional[str] = None,
        shipping_method: Optional[Any] = None,
        address: Optional[Any] = None,
        gift_cards: Optional[List[Any]] = None,
    ) -> CheckoutFinal:
        """
        FINAL MODE - For order creation.
        Authoritative, secure calculations from database.
        
        Args:
            checkout_id: Checkout ID to load from database
            items: List of database checkout line objects
            promo_code: Promotion code (will be validated)
            shipping_method: Shipping method database object
            address: Shipping address
            gift_cards: List of gift card objects
            
        Returns:
            CheckoutFinal: Final calculation result with order ID
        """
        # If checkout_id provided, load from database
        if checkout_id and not items:
            items = self._load_checkout_items(checkout_id)
        
        if not items:
            raise ValueError("No items provided or found")
        
        # RECALCULATE EVERYTHING FROM DATABASE
        subtotal = calculate_subtotal_final(items, self.currency)
        
        shipping = calculate_shipping_final(
            shipping_method, address, self.currency
        )
        
        discount = calculate_discount_final(
            promo_code, subtotal, self.user, self.currency
        )
        
        tax = calculate_tax_final(
            subtotal, shipping, address
        )
        
        # Calculate total
        total = subtotal + shipping - discount + tax
        
        # Apply gift cards
        if gift_cards:
            total = self._apply_gift_cards(total, gift_cards)
        
        # Security check: Compare with frontend estimate
        self._verify_total(checkout_id, total)
        
        # Create order
        order_id = self._create_order(items, total, shipping_method, address)
        
        return CheckoutFinal(
            subtotal=subtotal.net.amount,
            shipping=shipping.net.amount,
            discount=discount.net.amount,
            tax=tax.net.amount,
            total=total.net.amount,
            currency=self.currency,
            order_id=order_id,
            is_estimated=False
        )
    
    def _load_checkout_items(self, checkout_id: str) -> List[Any]:
        """Load checkout items from database."""
        from ecommerce.models.checkout import CheckoutLine
        
        return list(CheckoutLine.objects.filter(
            checkout_id=checkout_id
        ).select_related('variant', 'variant__product'))
    
    def _apply_gift_cards(self, total: TaxedMoney, gift_cards: List[Any]) -> TaxedMoney:
        """Apply gift cards to total."""
        from .base_calculations import calculate_gift_card_usage
        
        used_amount, _ = calculate_gift_card_usage(gift_cards, total, self.currency)
        return total - TaxedMoney(net=used_amount, gross=used_amount)
    
    def _verify_total(self, checkout_id: Optional[str], backend_total: TaxedMoney):
        """
        Security check: verify frontend estimate against backend calculation.
        
        If checkout_id is provided, load the frontend estimate from the checkout.
        """
        if not checkout_id:
            return
        
        from ecommerce.models.checkout import Checkout
        
        try:
            checkout = Checkout.objects.get(pk=checkout_id)
            frontend_total = checkout.total
            
            if frontend_total:
                difference = abs(frontend_total.gross.amount - backend_total.gross.amount)
                if difference > Decimal('0.01'):
                    logger.warning(
                        f"Total mismatch for checkout {checkout_id}: "
                        f"Frontend {frontend_total.gross.amount}, "
                        f"Backend {backend_total.gross.amount}"
                    )
                    # Flag for review
                    checkout.metadata['total_mismatch'] = {
                        'frontend': str(frontend_total.gross.amount),
                        'backend': str(backend_total.gross.amount),
                        'difference': str(difference)
                    }
                    checkout.save(update_fields=['metadata'])
        except Checkout.DoesNotExist:
            pass
    
    def _create_order(
        self,
        items: List[Any],
        total: TaxedMoney,
        shipping_method: Any,
        address: Any
    ) -> str:
        """Create order from checkout items."""
        from ecommerce.models.order import Order, OrderLine
        
        # Create order
        order = Order.objects.create(
            user=self.user,
            total_net_amount=total.net.amount,
            total_gross_amount=total.gross.amount,
            currency=self.currency,
            shipping_address=address,
            shipping_method=shipping_method,
            status='unfulfilled',
        )
        
        # Create order lines
        for item in items:
            OrderLine.objects.create(
                order=order,
                variant=item.variant,
                product_name=item.variant.product.name,
                variant_name=item.variant.name,
                quantity=item.quantity,
                unit_price_net_amount=item.unit_price.net.amount,
                unit_price_gross_amount=item.unit_price.gross.amount,
                total_price_net_amount=item.total_price.net.amount,
                total_price_gross_amount=item.total_price.gross.amount,
                currency=self.currency,
                is_shipping_required=item.variant.is_shipping_required(),
            )
        
        return str(order.id)'''