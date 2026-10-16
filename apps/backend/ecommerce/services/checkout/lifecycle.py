# ecommerce/services/checkout/lifecycle.py

"""
Checkout lifecycle services.

Owns the creation, mutation, and destruction of checkouts and
checkout lines:

    - create_checkout
    - add_variant_to_checkout
    - update_checkout_line_quantity
    - remove_checkout_line
    - set_checkout_shipping_address
    - set_checkout_billing_address
    - set_checkout_shipping_method
    - clear_checkout

Stock reservation is delegated to
`ecommerce.services.warehouse.allocation`.

Prices and totals are computed by
`ecommerce.services.checkout.calculations`.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.utils import timezone

from core.exceptions import InsufficientStock
from ecommerce.models.channel import Channel
from ecommerce.models.checkout import Checkout, CheckoutLine
from ecommerce.models.product import ProductVariant
from ecommerce.models.shipping import ShippingMethod
from ecommerce.services.warehouse.allocation import (
    reserve_for_checkout_line,
    release_reservations_for_checkout_line,
)


ZERO = Decimal("0")


# =====================================================================
# CREATE
# =====================================================================


@transaction.atomic
def create_checkout(
    channel: Channel,
    *,
    user=None,
    email: Optional[str] = None,
    currency: Optional[str] = None,
) -> Checkout:
    """
    Create a new empty checkout on a channel.

    If `user` is provided, the checkout is attached to them.
    If `email` is provided (guest), it's stored on the checkout.

    `currency` defaults to the channel's currency.
    """
    return Checkout.objects.create(
        channel=channel,
        user=user,
        email=email or (user.email if user else None),
        currency=currency or channel.currency_code,
        country=channel.default_country,
    )


def get_checkout_by_token(token) -> Optional[Checkout]:
    """Fetch a checkout by its UUID token."""
    return (
        Checkout.objects
        .select_related("user", "channel", "shipping_address", "billing_address")
        .prefetch_related("lines__variant__product")
        .filter(pk=token)
        .first()
    )


def get_user_active_checkout(user, channel: Channel) -> Optional[Checkout]:
    """
    Return the user's most recent checkout on a channel, or None.

    "Active" = not yet marked as completing.
    """
    return (
        Checkout.objects
        .filter(user=user, channel=channel, completing_started_at__isnull=True)
        .order_by("-last_change")
        .first()
    )


def claim_checkout_for_user(checkout: Checkout, user) -> Checkout:
    """
    Attach an anonymous checkout to a user after they log in.
    """
    if checkout.user_id == user.pk:
        return checkout

    checkout.user = user
    if not checkout.email:
        checkout.email = user.email
    checkout.save(update_fields=["user", "email", "last_change"])
    return checkout


# =====================================================================
# LINES
# =====================================================================


@transaction.atomic
def add_variant_to_checkout(
    checkout: Checkout,
    variant: ProductVariant,
    quantity: Decimal,
    *,
    replace: bool = False,
) -> CheckoutLine:
    """
    Add a variant to a checkout, or update its quantity if it's
    already present.

    Reserves stock for the new quantity.

    Raises InsufficientStock if the variant is not available.

    `replace=True` sets the quantity instead of adding to it.
    """
    quantity = Decimal(str(quantity))

    if quantity <= ZERO:
        raise ValueError("Quantity must be greater than zero.")

    # Idempotent: releasing reservations before re-reserving means
    # the caller's own hold doesn't count against them.
    existing_line = checkout.lines.filter(variant=variant).first()

    if existing_line is not None and replace:
        new_quantity = quantity
    else:
        new_quantity = (existing_line.quantity if existing_line else ZERO) + quantity

    # Update or create the line
    if existing_line is None:
        existing_line = CheckoutLine.objects.create(
            checkout=checkout,
            variant=variant,
            quantity=new_quantity,
            currency=checkout.currency,
            quantity_unit=variant.quantity_unit,
        )
    else:
        existing_line.quantity = new_quantity
        existing_line.save(update_fields=["quantity"])

    # Reserve stock
    try:
        reserve_for_checkout_line(existing_line, checkout.channel)
    except InsufficientStock:
        # Roll back the line change if reservation fails.
        transaction.set_rollback(True)
        raise

    # Invalidate prices
    checkout.last_change = timezone.now()
    checkout.price_expiration = timezone.now()
    checkout.save(update_fields=["last_change", "price_expiration"])

    return existing_line


@transaction.atomic
def update_checkout_line_quantity(
    checkout: Checkout,
    line: CheckoutLine,
    quantity: Decimal,
) -> Optional[CheckoutLine]:
    """
    Set a line's quantity to `quantity`.

    If `quantity` is zero or negative, the line is deleted and its
    reservation released.

    Raises InsufficientStock if the new quantity isn't available.
    """
    quantity = Decimal(str(quantity))

    if quantity <= ZERO:
        remove_checkout_line(checkout, line)
        return None

    line.quantity = quantity
    line.save(update_fields=["quantity"])

    try:
        reserve_for_checkout_line(line, checkout.channel)
    except InsufficientStock:
        transaction.set_rollback(True)
        raise

    checkout.last_change = timezone.now()
    checkout.price_expiration = timezone.now()
    checkout.save(update_fields=["last_change", "price_expiration"])

    return line


@transaction.atomic
def remove_checkout_line(checkout: Checkout, line: CheckoutLine) -> None:
    """Delete a line and release its reservation."""
    release_reservations_for_checkout_line(line)
    line.delete()

    checkout.last_change = timezone.now()
    checkout.price_expiration = timezone.now()
    checkout.save(update_fields=["last_change", "price_expiration"])


# =====================================================================
# ADDRESSES
# =====================================================================


def set_checkout_shipping_address(checkout: Checkout, address) -> Checkout:
    """Attach a shipping address to the checkout."""
    if checkout.shipping_address_id == getattr(address, "pk", None):
        return checkout

    checkout.shipping_address = address
    checkout.last_change = timezone.now()
    checkout.price_expiration = timezone.now()
    checkout.save(
        update_fields=[
            "shipping_address",
            "last_change",
            "price_expiration",
        ]
    )
    return checkout


def set_checkout_billing_address(checkout: Checkout, address) -> Checkout:
    """Attach a billing address to the checkout."""
    if checkout.billing_address_id == getattr(address, "pk", None):
        return checkout

    checkout.billing_address = address
    checkout.last_change = timezone.now()
    checkout.save(
        update_fields=["billing_address", "last_change"]
    )
    return checkout


def set_checkout_email(checkout: Checkout, email: str) -> Checkout:
    """Set the checkout's contact email."""
    checkout.email = email
    checkout.save(update_fields=["email", "last_change"])
    return checkout


# =====================================================================
# SHIPPING METHOD
# =====================================================================


def set_checkout_shipping_method(
    checkout: Checkout,
    shipping_method: Optional[ShippingMethod],
) -> Checkout:
    """Attach a shipping method to the checkout, or clear it."""
    checkout.shipping_method = shipping_method
    checkout.last_change = timezone.now()
    checkout.price_expiration = timezone.now()
    checkout.save(
        update_fields=[
            "shipping_method",
            "last_change",
            "price_expiration",
        ]
    )
    return checkout


# =====================================================================
# CLEAR
# =====================================================================


@transaction.atomic
def clear_checkout(checkout: Checkout) -> None:
    """
    Remove all lines and reservations from a checkout.

    Keeps the checkout itself (so the token remains valid).
    """
    for line in checkout.lines.all():
        release_reservations_for_checkout_line(line)
    checkout.lines.all().delete()

    checkout.last_change = timezone.now()
    checkout.price_expiration = timezone.now()
    checkout.save(update_fields=["last_change", "price_expiration"])