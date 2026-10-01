# apps/backend/ecommerce/services/checkout/base_calculations.py
"""Base calculations for checkout processing - shared between preview and final calculations."""

'''from decimal import Decimal
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass

from django.conf import settings
from django.db import models
from core.pricing.money import Money
from core.pricing.money_field import TaxedMoney

from core.taxes import zero_money, zero_taxed_money


@dataclass
class PriceCalculationResult:
    """Result of a price calculation."""
    subtotal: TaxedMoney
    total: TaxedMoney
    shipping_price: TaxedMoney
    discount_amount: Money
    gift_card_amount: Money
    currency: str
    total_without_discount: TaxedMoney
    total_without_gift_cards: TaxedMoney


@dataclass
class LinePriceCalculationResult:
    """Result of a line price calculation."""
    unit_price: TaxedMoney
    total_price: TaxedMoney
    undiscounted_unit_price: TaxedMoney
    undiscounted_total_price: TaxedMoney
    discount_amount: Money
    currency: str


@dataclass
class CheckoutPreview:
    """Preview calculation - safe for frontend display."""
    subtotal: Decimal
    shipping_estimate: Decimal
    discount_estimate: Decimal
    tax_estimate: Decimal
    total_estimate: Decimal
    currency: str
    is_estimated: bool = True
    
    def to_dict(self) -> Dict:
        return {
            'subtotal': str(self.subtotal),
            'shipping': str(self.shipping_estimate),
            'discount': str(self.discount_estimate),
            'tax': str(self.tax_estimate),
            'total': str(self.total_estimate),
            'currency': self.currency,
            'is_estimated': self.is_estimated
        }


@dataclass
class CheckoutFinal:
    """Final calculation - authoritative, from backend only."""
    subtotal: Decimal
    shipping: Decimal
    discount: Decimal
    tax: Decimal
    total: Decimal
    currency: str
    order_id: Optional[str] = None
    is_estimated: bool = False
    
    def to_dict(self) -> Dict:
        return {
            'subtotal': str(self.subtotal),
            'shipping': str(self.shipping),
            'discount': str(self.discount),
            'tax': str(self.tax),
            'total': str(self.total),
            'currency': self.currency,
            'order_id': self.order_id,
            'is_estimated': self.is_estimated
        }


def calculate_subtotal_preview(
    items: List[Dict[str, Any]],
    currency: str,
) -> Decimal:
    """
    Quick preview calculation - for frontend display only.
    
    Args:
        items: List of cart items with price and quantity
        currency: Currency code
        
    Returns:
        Decimal: Subtotal amount
    """
    subtotal = Decimal('0.00')
    
    for item in items:
        price = Decimal(str(item.get('price', 0)))
        quantity = int(item.get('quantity', 0))
        subtotal += price * quantity
    
    return subtotal


def calculate_subtotal_final(
    items: List[Any],
    currency: str,
) -> TaxedMoney:
    """
    Authoritative subtotal calculation - from database objects.
    
    Args:
        items: List of database cart/checkout line objects
        currency: Currency code
        
    Returns:
        TaxedMoney: Subtotal amount
    """
    subtotal = zero_taxed_money(currency)
    
    for item in items:
        if hasattr(item, 'total_price'):
            subtotal += item.total_price
        elif hasattr(item, 'get_total_price'):
            subtotal += item.get_total_price()
        else:
            # Fallback calculation
            unit_price = getattr(item, 'unit_price', zero_taxed_money(currency))
            quantity = getattr(item, 'quantity', 0)
            subtotal += unit_price * quantity
    
    return subtotal


def calculate_shipping_preview(
    shipping_method: Optional[str],
    items: List[Dict[str, Any]],
    country_code: str,
) -> Decimal:
    """
    Quick shipping estimate - for frontend display.
    
    Args:
        shipping_method: Shipping method identifier
        items: Cart items
        country_code: Country code
        
    Returns:
        Decimal: Estimated shipping cost
    """
    # Fast estimation logic - can be simplified for preview
    if not shipping_method:
        return Decimal('0.00')
    
    # Simple estimation based on method
    estimates = {
        'standard': Decimal('5.99'),
        'express': Decimal('15.99'),
        'overnight': Decimal('29.99'),
    }
    
    return estimates.get(shipping_method, Decimal('5.99'))


def calculate_shipping_final(
    shipping_method: Any,
    address: Any,
    currency: str,
) -> TaxedMoney:
    """
    Authoritative shipping calculation - from database.
    
    Args:
        shipping_method: Shipping method database object
        address: Shipping address
        currency: Currency code
        
    Returns:
        TaxedMoney: Shipping price
    """
    if not shipping_method:
        return zero_taxed_money(currency)
    
    # Get actual price from shipping method
    if hasattr(shipping_method, 'get_price'):
        return shipping_method.get_price(address.country_code, currency)
    
    # Fallback: get from channel listing
    if hasattr(shipping_method, 'channel_listings'):
        listing = shipping_method.channel_listings.filter(
            channel__currency_code=currency
        ).first()
        if listing and hasattr(listing, 'price'):
            return TaxedMoney(
                net=listing.price,
                gross=listing.price,
            )
    
    return zero_taxed_money(currency)


def calculate_discount_preview(
    promo_code: Optional[str],
    subtotal: Decimal,
) -> Decimal:
    """
    Quick discount preview - for frontend display.
    
    Args:
        promo_code: Promotion/voucher code
        subtotal: Subtotal amount
        
    Returns:
        Decimal: Estimated discount amount
    """
    if not promo_code:
        return Decimal('0.00')
    
    # Simple estimation - this would be validated on backend
    # This is just for UI preview
    if subtotal > Decimal('100.00'):
        return Decimal('10.00')  # $10 off over $100
    elif subtotal > Decimal('50.00'):
        return Decimal('5.00')   # $5 off over $50
    
    return Decimal('0.00')


def calculate_discount_final(
    promo_code: Optional[str],
    subtotal: TaxedMoney,
    user: Any,
    currency: str,
) -> TaxedMoney:
    """
    Authoritative discount calculation - from database.
    
    Args:
        promo_code: Promotion/voucher code
        subtotal: Subtotal
        user: User object
        currency: Currency code
        
    Returns:
        TaxedMoney: Discount amount
    """
    if not promo_code:
        return zero_taxed_money(currency)
    
    # Validate voucher from database
    from ecommerce.models.discount import Voucher, VoucherCode
    
    try:
        voucher_code = VoucherCode.objects.get(
            code=promo_code.upper(),
            is_active=True
        )
        voucher = voucher_code.voucher
        
        # Validate voucher
        if not voucher.is_active:
            return zero_taxed_money(currency)
        
        # Calculate discount based on voucher type
        if voucher.discount_value_type == 'fixed':
            discount = Money(voucher.discount_value, currency)
        elif voucher.discount_value_type == 'percentage':
            discount = Money(
                (subtotal.net.amount * voucher.discount_value) / Decimal('100'),
                currency
            )
        else:
            return zero_taxed_money(currency)
        
        # Don't exceed subtotal
        if discount > subtotal.net:
            discount = subtotal.net
        
        return TaxedMoney(net=discount, gross=discount)
        
    except (VoucherCode.DoesNotExist, Voucher.DoesNotExist):
        return zero_taxed_money(currency)


def calculate_tax_preview(
    subtotal: Decimal,
    country_code: str,
    items: List[Dict[str, Any]],
) -> Decimal:
    """
    Quick tax estimate - for frontend display.
    
    Args:
        subtotal: Subtotal amount
        country_code: Country code
        items: Cart items
        
    Returns:
        Decimal: Estimated tax amount
    """
    # Simple tax rates by country (for preview only)
    tax_rates = {
        'US': Decimal('0.00'),  # Varies by state - complex
        'UK': Decimal('20.00'),  # 20% VAT
        'NG': Decimal('7.50'),   # 7.5% VAT
        'CA': Decimal('13.00'),  # 13% HST (varies by province)
        'DE': Decimal('19.00'),  # 19% VAT
        'FR': Decimal('20.00'),  # 20% VAT
    }
    
    rate = tax_rates.get(country_code, Decimal('0.00'))
    return (subtotal * rate) / Decimal('100')


def calculate_tax_final(
    subtotal: TaxedMoney,
    shipping: TaxedMoney,
    address: Any,
    tax_class: Any = None,
) -> TaxedMoney:
    """
    Authoritative tax calculation - from tax system.
    
    Args:
        subtotal: Subtotal
        shipping: Shipping cost
        address: Shipping address
        tax_class: Optional tax class
        
    Returns:
        TaxedMoney: Tax amount
    """
    # Get tax rate from tax app or system
    from tax.models import TaxClassCountryRate
    
    country_code = address.country_code
    
    # Try to get tax rate for the country
    try:
        if tax_class:
            rate = TaxClassCountryRate.objects.get(
                tax_class=tax_class,
                country=country_code
            )
        else:
            rate = TaxClassCountryRate.objects.get(
                tax_class=None,
                country=country_code
            )
        tax_rate = rate.rate
    except TaxClassCountryRate.DoesNotExist:
        return zero_taxed_money(subtotal.currency)
    
    # Calculate tax on taxable amount (subtotal + shipping)
    taxable_amount = subtotal.net + shipping.net
    tax_amount = (taxable_amount * tax_rate) / Decimal('100')
    
    return TaxedMoney(net=tax_amount, gross=tax_amount)'''


def get_default_country() -> str:
    """Get the default country from settings."""
    return getattr(settings, 'DEFAULT_COUNTRY', 'US')


def get_default_currency() -> str:
    """Get the default currency from settings."""
    return getattr(settings, 'DEFAULT_CURRENCY', 'USD')


def validate_currency(currency: str) -> bool:
    """Validate if a currency is supported."""
    supported = getattr(settings, 'SUPPORTED_CURRENCIES', ['USD', 'EUR', 'NGN'])
    return currency in supported


def round_price(amount: Decimal, places: int = 2) -> Decimal:
    """Round a price to the specified decimal places."""
    return amount.quantize(Decimal('0.{}'.format('0' * places)))


def zero_money_amount(currency: str) -> Decimal:
    """Return zero money amount for a currency."""
    return Decimal('0.00')