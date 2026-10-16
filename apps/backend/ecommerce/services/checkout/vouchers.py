# apps/backend/ecommerce/services/checkout/vouchers.py

"""
Voucher application and removal.

A voucher is applied to a checkout by creating a CheckoutDiscount
row with type=VOUCHER. The voucher's usage counter is incremented
at checkout completion, not at application — so an abandoned
checkout does not consume a voucher code.

At most one voucher discount can exist per checkout. Enforced by
the `unique_checkout_single_manual_discount` partial unique
constraint on CheckoutDiscount (promotion_rule IS NULL).
"""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from core.pricing import Money
from ecommerce.models.channel import Channel
from ecommerce.models.checkout import Checkout
from ecommerce.models.discount import (
    CheckoutDiscount,
    DiscountType,
    DiscountValueType,
    NotApplicable,
    Voucher,
    VoucherCode,
)
from ecommerce.services.checkout.calculations import (
    calculate_checkout_subtotal,
    update_checkout_totals,
)


class VoucherNotFound(ValidationError):
    """Raised when no active voucher matches the given code."""


# =====================================================================
# APPLY
# =====================================================================


@transaction.atomic
def apply_voucher(
    checkout: Checkout,
    code: str,
) -> Checkout:
    """
    Apply a voucher code to a checkout.

    Validates the voucher, creates a CheckoutDiscount row, and
    recalculates totals.

    If a voucher is already applied, it is replaced (the previous
    CheckoutDiscount row is deleted first).

    Raises:
        VoucherNotFound — if the code does not resolve.
        NotApplicable   — if the voucher does not apply.
    """
    code = (code or "").strip()
    if not code:
        raise VoucherNotFound("Voucher code is required.")

    voucher_code = (
        VoucherCode.objects
        .select_related("voucher")
        .filter(code=code, is_active=True)
        .first()
    )
    if voucher_code is None:
        raise VoucherNotFound(f"Unknown voucher code: {code}")

    voucher = voucher_code.voucher

    _validate_voucher_for_checkout(voucher, checkout)

    # Replace any existing voucher discount on this checkout.
    CheckoutDiscount.objects.filter(
        checkout=checkout,
        promotion_rule__isnull=True,
    ).delete()

    # Compute the discount amount against the current subtotal.
    country_code = checkout.get_country()
    subtotal = calculate_checkout_subtotal(checkout, country_code)

    discount_amount = _compute_discount_amount(
        voucher, checkout, subtotal,
    )

    CheckoutDiscount.objects.create(
        checkout=checkout,
        type=DiscountType.VOUCHER,
        value_type=voucher.discount_value_type,
        value=_get_channel_listing_value(voucher, checkout.channel),
        amount_value=discount_amount,
        currency=checkout.currency,
        name=voucher.name or voucher_code.code,
        voucher=voucher,
        voucher_code=voucher_code.code,
    )

    checkout.voucher_code = voucher_code.code
    checkout.save(update_fields=["voucher_code", "last_change"])

    update_checkout_totals(checkout, country_code)
    checkout.refresh_from_db()
    return checkout


# =====================================================================
# REMOVE
# =====================================================================


@transaction.atomic
def remove_voucher(checkout: Checkout) -> Checkout:
    """
    Remove any voucher discount from a checkout.

    Idempotent: no-op if no voucher is applied.
    """
    deleted, _ = CheckoutDiscount.objects.filter(
        checkout=checkout,
        promotion_rule__isnull=True,
        type=DiscountType.VOUCHER,
    ).delete()

    if deleted:
        checkout.voucher_code = None
        checkout.save(update_fields=["voucher_code", "last_change"])

        country_code = checkout.get_country()
        update_checkout_totals(checkout, country_code)
        checkout.refresh_from_db()

    return checkout


# =====================================================================
# VALIDATION
# =====================================================================


def _validate_voucher_for_checkout(
    voucher: Voucher,
    checkout: Checkout,
) -> None:
    """
    Raise NotApplicable if the voucher cannot be applied.

    Order of checks matches the message order in the UI:
    staff, channel, dates, minimums, customer limits, country.
    """
    country_code = checkout.get_country()
    customer_email = checkout.get_customer_email()

    # Staff-only
    user = checkout.user
    voucher.validate_only_for_staff(user)

    # Channel listing
    channel_listing = voucher.channel_listings.filter(
        channel=checkout.channel,
        is_active=True,
    ).first()
    if channel_listing is None:
        raise NotApplicable(
            "This voucher is not available in the current channel."
        )

    # Country restriction
    if voucher.countries and country_code not in voucher.countries:
        raise NotApplicable(
            "This voucher is not available in your country."
        )

    # Minimum spend (needs subtotal)
    subtotal = calculate_checkout_subtotal(checkout, country_code)
    voucher.validate_min_spent(subtotal.gross, checkout.channel)

    # Minimum items
    total_quantity = sum(
        (line.quantity for line in checkout.lines.all()),
        Decimal("0"),
    )
    voucher.validate_min_checkout_items_quantity(total_quantity)

    # Once-per-customer
    if voucher.apply_once_per_customer and customer_email:
        voucher.validate_once_per_customer(customer_email)

    # Product/variant/collection/category restriction
    if not _voucher_applies_to_any_line(voucher, checkout):
        raise NotApplicable(
            "This voucher does not apply to any item in your cart."
        )


def _voucher_applies_to_any_line(
    voucher: Voucher,
    checkout: Checkout,
) -> bool:
    """
    Return True if the voucher has at least one applicable line.

    If the voucher has no product/variant/collection/category
    restrictions, it applies to the whole cart.
    """
    has_product_restrictions = (
        voucher.products.exists()
        or voucher.variants.exists()
        or voucher.collections.exists()
        or voucher.categories.exists()
    )
    if not has_product_restrictions:
        return True

    for line in checkout.lines.select_related(
        "variant__product__category"
    ):
        variant = line.variant

        if voucher.variants.filter(pk=variant.pk).exists():
            return True
        if voucher.products.filter(pk=variant.product_id).exists():
            return True

        # Collection match
        if voucher.collections.filter(
            products=variant.product,
        ).exists():
            return True

        # Category match (mptt: check ancestors too)
        category = variant.product.category
        if category is not None:
            if voucher.categories.filter(pk=category.pk).exists():
                return True

    return False


# =====================================================================
# DISCOUNT MATH
# =====================================================================


def _get_channel_listing_value(
    voucher: Voucher,
    channel: Channel,
) -> Decimal:
    """Return the raw discount value from the channel listing."""
    listing = voucher.channel_listings.filter(channel=channel).first()
    return listing.discount_value if listing else Decimal("0")


def _compute_discount_amount(
    voucher: Voucher,
    checkout: Checkout,
    subtotal,
) -> Decimal:
    """
    Return the discount amount in the checkout's currency.

    Percentage vouchers apply to the subtotal. Fixed vouchers
    apply their channel-listing value directly, capped at the
    subtotal (no negative total).
    """
    channel_listing = voucher.channel_listings.filter(
        channel=checkout.channel,
    ).first()
    if channel_listing is None:
        return Decimal("0")

    value = channel_listing.discount_value

    if voucher.discount_value_type == DiscountValueType.PERCENTAGE:
        discount = (
            subtotal.gross.amount * value / Decimal("100")
        )
    else:
        discount = value

    # Cap at subtotal, floor at zero.
    return max(min(discount, subtotal.gross.amount), Decimal("0"))