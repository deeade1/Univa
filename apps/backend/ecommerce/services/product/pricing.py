# ecommerce/services/product/pricing.py

"""
Product and variant pricing services.

Resolves the price of a variant in a channel, including applicable
tax based on the customer's country.

Design:

    - Prices live on ProductVariantChannelListing (per variant,
      per channel).
    - A variant with no listing in a channel is not available in
      that channel.
    - Tax is resolved from the TaxClass of the product/product type,
      via the country of the sale.

Prices are returned as:

    - Money: net amount + currency (no tax applied)
    - TaxedMoney: net + gross (tax applied)
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from core.pricing import (
    Money,
    MoneyRange,
    TaxedMoney,
    TaxedMoneyRange,
)
from ecommerce.models.channel import Channel
from ecommerce.models.product import (
    Product,
    ProductChannelListing,
    ProductVariant,
    ProductVariantChannelListing,
)
from tax.calculations import calculate_flat_rate_tax
from tax.models import TaxClass, TaxClassCountryRate


# =====================================================================
# DATACLASSES
# =====================================================================


@dataclass
class VariantAvailability:
    """Variant pricing snapshot for a specific channel and country."""

    on_sale: bool
    price: TaxedMoney
    price_undiscounted: TaxedMoney
    discount: Optional[TaxedMoney] = None


@dataclass
class ProductAvailability:
    """Product pricing snapshot (min/max across variants)."""

    on_sale: bool
    price_range: Optional[TaxedMoneyRange]
    price_range_undiscounted: Optional[TaxedMoneyRange]
    discount: Optional[TaxedMoney] = None


# =====================================================================
# LISTING LOOKUPS
# =====================================================================


def get_variant_listing(
    variant: ProductVariant,
    channel: Channel,
) -> Optional[ProductVariantChannelListing]:
    """Return the variant's listing in the channel, or None."""
    return variant.channel_listings.filter(channel=channel).first()


def get_product_listing(
    product: Product,
    channel: Channel,
) -> Optional[ProductChannelListing]:
    """Return the product's listing in the channel, or None."""
    return product.channel_listings.filter(channel=channel).first()


# =====================================================================
# TAX RESOLUTION
# =====================================================================


def resolve_tax_rate(
    variant: ProductVariant,
    country_code: str,
) -> Decimal:
    """
    Resolve the tax rate percentage for a variant in a country.

    Resolution order:
        1. Product.tax_class
        2. Product.product_type.tax_class
        3. Default rate for the country (TaxClassCountryRate
           with tax_class=NULL)

    Returns the rate as a percentage: 7.5 means 7.5%.
    Returns Decimal("0") if no rate can be resolved.

    The returned value is compatible with
    `tax.calculations.calculate_flat_rate_tax`, which expects
    percentages.
    """
    product = variant.product

    tax_class: Optional[TaxClass] = None

    if product.tax_class_id:
        tax_class = product.tax_class
    elif product.product_type.tax_class_id:
        tax_class = product.product_type.tax_class

    rate = TaxClassCountryRate.resolve(tax_class, country_code)
    if rate is None:
        return Decimal("0")

    return rate.rate


# =====================================================================
# VARIANT PRICING
# =====================================================================


def get_variant_base_price(
    variant: ProductVariant,
    channel: Channel,
) -> Optional[Money]:
    """
    Return the undiscounted net price of a variant in a channel.

    Returns None if the variant has no listing in the channel.
    """
    listing = get_variant_listing(variant, channel)
    if listing is None:
        return None
    return listing.price

def get_variant_price(
    variant: ProductVariant,
    channel: Channel,
) -> Optional[Money]:
    """
    Return the effective net price of a variant in a channel.

    Uses the discounted price if explicitly set, otherwise the
    base price.
    """
    listing = get_variant_listing(variant, channel)
    if listing is None:
        return None
    if listing.discounted_price is not None:
        return listing.discounted_price
    return listing.price

def get_variant_availability(
    variant: ProductVariant,
    channel: Channel,
    country_code: str,
) -> Optional[VariantAvailability]:
    """
    Return the taxed availability for a variant.

    Returns None if the variant is not listed in the channel.
    """
    listing = get_variant_listing(variant, channel)
    if listing is None:
        return None

    base_price = listing.price
    if base_price is None:
        return None

    effective_price = (
        listing.discounted_price
        if listing.discounted_price is not None
        else base_price
    )

    tax_rate = resolve_tax_rate(variant, country_code)

    price_taxed = calculate_flat_rate_tax(
        effective_price,
        tax_rate,
        prices_entered_with_tax=False,
    )
    base_price_taxed = calculate_flat_rate_tax(
        base_price,
        tax_rate,
        prices_entered_with_tax=False,
    )

    discount = None
    if base_price_taxed.gross > price_taxed.gross:
        discount = base_price_taxed - price_taxed

    return VariantAvailability(
        on_sale=discount is not None,
        price=price_taxed,
        price_undiscounted=base_price_taxed,
        discount=discount,
    )


# =====================================================================
# PRODUCT PRICING (across variants)
# =====================================================================


def get_product_price_range(
    product: Product,
    channel: Channel,
    country_code: str,
) -> Optional[TaxedMoneyRange]:
    """
    Return the taxed price range across the product's listed variants.

    Returns None if the product has no listed variants in the channel.
    """
    variant_listings = ProductVariantChannelListing.objects.filter(
        variant__product=product,
        channel=channel,
        price_amount__isnull=False,
    ).select_related("variant__product", "variant__product__product_type")

    if not variant_listings.exists():
        return None

    rates: dict[int, Decimal] = {}
    prices: list[TaxedMoney] = []

    for listing in variant_listings:
        variant = listing.variant
        if variant.pk not in rates:
            rates[variant.pk] = resolve_tax_rate(variant, country_code)
        rate = rates[variant.pk]

        listing_price = (
            listing.discounted_price
            if listing.discounted_price is not None
            else listing.price
        )
        if listing_price is None:
            continue

        taxed = calculate_flat_rate_tax(
            listing_price,
            rate,
            prices_entered_with_tax=False,
        )
        prices.append(taxed)

    if not prices:
        return None

    return TaxedMoneyRange(start=min(prices), stop=max(prices))


def get_product_availability(
    product: Product,
    channel: Channel,
    country_code: str,
) -> ProductAvailability:
    """
    Return the taxed availability snapshot for a product.
    """
    product_listing = get_product_listing(product, channel)

    price_range = get_product_price_range(product, channel, country_code)

    # Undiscounted variant prices
    variant_listings = ProductVariantChannelListing.objects.filter(
        variant__product=product,
        channel=channel,
        price_amount__isnull=False,
    ).select_related("variant__product", "variant__product__product_type")

    undiscounted_prices: list[TaxedMoney] = []
    for listing in variant_listings:
        if listing.price is None:
            continue
        rate = resolve_tax_rate(listing.variant, country_code)
        taxed = calculate_flat_rate_tax(
            listing.price,
            rate,
            prices_entered_with_tax=False,
        )
        undiscounted_prices.append(taxed)

    undiscounted_range = None
    if undiscounted_prices:
        undiscounted_range = TaxedMoneyRange(
            start=min(undiscounted_prices),
            stop=max(undiscounted_prices),
        )

    discount = None
    if price_range and undiscounted_range:
        if undiscounted_range.start > price_range.start:
            discount = undiscounted_range.start - price_range.start

    is_visible = (
        product_listing is not None
        and product_listing.visible_in_listings
    )
    is_on_sale = is_visible and discount is not None

    return ProductAvailability(
        on_sale=is_on_sale,
        price_range=price_range,
        price_range_undiscounted=undiscounted_range,
        discount=discount,
    )