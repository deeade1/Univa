# ecommerce/services/checkout/calculations.py

"""
Checkout calculations.

Computes the totals of a checkout:

    subtotal        — sum of line totals (taxed)
    shipping_price  — price of the selected shipping method (taxed)
    total           — subtotal + shipping_price

Calculation is deterministic given:
    - the checkout's lines
    - the checkout's channel
    - the checkout's shipping address country
    - the checkout's shipping method

Callers use:

    calculate_checkout_subtotal(checkout, country_code)
    calculate_checkout_shipping(checkout, country_code)
    calculate_checkout_total(checkout, country_code)
    update_checkout_totals(checkout, country_code)

`update_checkout_totals` persists the totals on the Checkout row.
"""


from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from core.pricing import Money, TaxedMoney
from ecommerce.models.channel import Channel
from ecommerce.models.checkout import Checkout, CheckoutLine
from ecommerce.models.shipping import ShippingMethodChannelListing
from ecommerce.services.product.pricing import get_variant_availability


ZERO = Decimal("0")

# =====================================================================
# SUBTOTAL
# =====================================================================


def calculate_checkout_subtotal(
    checkout: Checkout,
    country_code: str,
) -> TaxedMoney:
    """
    Return the taxed subtotal of a checkout.

    The subtotal is the sum of every line's effective price multiplied
    by its quantity, with tax applied based on `country_code`.

    Lines whose variant is no longer available in the channel are
    skipped. Callers should validate availability separately.
    """
    subtotal = _zero_taxed_money(checkout.currency)

    for line in checkout.lines.select_related(
        "variant__product__product_type"
    ):
        line_total = _calculate_line_total(line, checkout, country_code)
        if line_total is not None:
            subtotal = subtotal + line_total

    return subtotal


def calculate_checkout_subtotal_undiscounted(
    checkout: Checkout,
    country_code: str,
) -> TaxedMoney:
    """
    Same as `calculate_checkout_subtotal` but using the undiscounted
    (base) price of each variant.
    """
    subtotal = _zero_taxed_money(checkout.currency)

    for line in checkout.lines.select_related(
        "variant__product__product_type"
    ):
        line_total = _calculate_line_total(
            line, checkout, country_code, use_base_price=True
        )
        if line_total is not None:
            subtotal = subtotal + line_total

    return subtotal


def _calculate_line_total(
    line: CheckoutLine,
    checkout: Checkout,
    country_code: str,
    *,
    use_base_price: bool = False,
) -> TaxedMoney | None:
    """
    Compute the taxed total for a single line.

    Returns None if the variant is not available in the channel.
    """
    variant = line.variant

    availability = get_variant_availability(
        variant, checkout.channel, country_code
    )
    if availability is None:
        return None

    if use_base_price:
        unit_price = availability.price_undiscounted
    else:
        unit_price = availability.price

    # Price override takes precedence — used for ad-hoc lines.
    if line.price_override is not None:
        override_money = Money(line.price_override, checkout.currency)
        unit_price = TaxedMoney(net=override_money, gross=override_money)

    quantity = line.quantity

    return TaxedMoney(
        net=unit_price.net * quantity,
        gross=unit_price.gross * quantity,
    )


# =====================================================================
# SHIPPING
# =====================================================================


def calculate_checkout_shipping(
    checkout: Checkout,
    country_code: str,
) -> TaxedMoney:
    """
    Return the taxed shipping price of a checkout.

    Returns zero if:
        - no shipping method is set
        - the shipping method has no channel listing
        - no line requires shipping

    The shipping price is taken from the shipping method's channel
    listing in the checkout's currency.
    """
    if not _checkout_requires_shipping(checkout):
        return _zero_taxed_money(checkout.currency)

    if checkout.shipping_method_id is None:
        return _zero_taxed_money(checkout.currency)

    listing = _get_shipping_listing(checkout)
    if listing is None:
        return _zero_taxed_money(checkout.currency)

    price = Money(listing.price_amount, listing.currency)
    return TaxedMoney(net=price, gross=price)


def _get_shipping_listing(
    checkout: Checkout,
) -> ShippingMethodChannelListing | None:
    return (
        ShippingMethodChannelListing.objects
        .filter(
            shipping_method=checkout.shipping_method,
            channel=checkout.channel,
            is_active=True,
        )
        .first()
    )


def _checkout_requires_shipping(checkout: Checkout) -> bool:
    """True if any line in the checkout requires shipping."""
    return any(
        line.variant.is_shipping_required()
        for line in checkout.lines.select_related(
            "variant__product__product_type"
        )
    )


# =====================================================================
# TOTAL
# =====================================================================


def calculate_checkout_total(
    checkout: Checkout,
    country_code: str,
) -> TaxedMoney:
    """
    Return the taxed grand total of a checkout, after gift cards.

    Gift cards reduce the gross amount the customer must pay.
    The net amount is also reduced, proportionally — gift cards
    are treated as a payment method, not a discount, so the
    subtotal is unchanged.

    The total is floored at zero: a gift card cannot over-apply.
    """
    subtotal = calculate_checkout_subtotal(checkout, country_code)
    shipping = calculate_checkout_shipping(checkout, country_code)
    gross_total = subtotal + shipping

    gift_card_amount = _sum_applied_gift_cards(checkout)
    if gift_card_amount <= ZERO:
        return gross_total

    # Apply gift cards to gross, then reduce net proportionally.
    new_gross = max(
        gross_total.gross.amount - gift_card_amount,
        ZERO,
    )
    if gross_total.gross.amount == ZERO:
        ratio = Decimal("0")
    else:
        ratio = new_gross / gross_total.gross.amount
    new_net = (gross_total.net.amount * ratio).quantize(Decimal("0.01"))

    return TaxedMoney(
        net=Money(new_net, checkout.currency),
        gross=Money(new_gross, checkout.currency),
    )


def _sum_applied_gift_cards(checkout: Checkout) -> Decimal:
    """Sum the amount_applied on all CheckoutGiftCard rows."""
    from ecommerce.models.checkout import CheckoutGiftCard

    total = (
        CheckoutGiftCard.objects
        .filter(checkout=checkout)
        .aggregate(total=Sum("amount_applied"))["total"]
    )
    return total or ZERO


def calculate_checkout_total_undiscounted(
    checkout: Checkout,
    country_code: str,
) -> TaxedMoney:
    """Undiscounted subtotal + shipping."""
    subtotal = calculate_checkout_subtotal_undiscounted(checkout, country_code)
    shipping = calculate_checkout_shipping(checkout, country_code)
    return subtotal + shipping


# =====================================================================
# PERSISTENCE
# =====================================================================


@transaction.atomic
def update_checkout_totals(
    checkout: Checkout,
    country_code: str | None = None,
) -> Checkout:
    """
    Compute and persist the checkout's totals.

    Writes:
        subtotal_net_amount, subtotal_gross_amount
        shipping_price_net_amount, shipping_price_gross_amount
        total_net_amount, total_gross_amount
        base_subtotal_amount, base_total_amount

    Returns the same checkout instance, updated.
    """
    if country_code is None:
        country_code = checkout.get_country()

    subtotal = calculate_checkout_subtotal(checkout, country_code)
    subtotal_undiscounted = calculate_checkout_subtotal_undiscounted(
        checkout, country_code
    )
    shipping = calculate_checkout_shipping(checkout, country_code)
    total = calculate_checkout_total(checkout, country_code)
    total_undiscounted = subtotal_undiscounted + shipping

    checkout.subtotal_net_amount = subtotal.net.amount
    checkout.subtotal_gross_amount = subtotal.gross.amount
    checkout.base_subtotal_amount = subtotal_undiscounted.net.amount

    checkout.shipping_price_net_amount = shipping.net.amount
    checkout.shipping_price_gross_amount = shipping.gross.amount

    checkout.total_net_amount = total.net.amount
    checkout.total_gross_amount = total.gross.amount
    checkout.base_total_amount = total_undiscounted.net.amount

    checkout.price_expiration = timezone.now()
    checkout.last_change = timezone.now()

    checkout.save(update_fields=[
        "subtotal_net_amount",
        "subtotal_gross_amount",
        "base_subtotal_amount",
        "shipping_price_net_amount",
        "shipping_price_gross_amount",
        "total_net_amount",
        "total_gross_amount",
        "base_total_amount",
        "price_expiration",
        "last_change",
    ])

    return checkout


# =====================================================================
# HELPERS
# =====================================================================


def _zero_taxed_money(currency: str) -> TaxedMoney:
    zero = Money(ZERO, currency)
    return TaxedMoney(net=zero, gross=zero)