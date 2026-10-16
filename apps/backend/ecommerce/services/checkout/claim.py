# ecommerce/services/checkout/claim.py

"""
Checkout claim services.

Transfers ownership of an anonymous checkout to an authenticated
user:

    claim_checkout(checkout, user) -> Checkout

Merge rules
-----------

    * No existing user cart on the same channel:
        The guest checkout is simply assigned to the user.

    * Existing user cart on the same channel, guest cart empty:
        Discard the guest cart; keep the user cart.

    * Existing user cart on the same channel, guest cart non-empty:
        Merge guest cart lines into the user cart:
            - same variant -> quantities sum
            - new variant  -> added to the user cart
        Then delete the guest cart.

    * Existing user cart on a different channel:
        Raise CHANNEL_MISMATCH.

    * Checkout already claimed by a different user:
        Raise ALREADY_CLAIMED.

    * Checkout completion in progress (completing_started_at set):
        Raise LOCKED.

    * Checkout is a session cart whose owner is the same user:
        Idempotent no-op, returns the checkout unchanged.

This module does not:
    - modify line prices or the price_expiration
    - perform order completion
    - touch the accounts app
"""

from __future__ import annotations

import logging
from typing import Optional

from django.db import transaction
from django.utils import timezone

from ecommerce.models.checkout import Checkout, CheckoutLine
from ecommerce.models.enums.errors import ClaimErrorCode

logger = logging.getLogger(__name__)


# =====================================================================
# ERRORS
# =====================================================================


class ClaimError(Exception):
    """
    Raised when a checkout cannot be claimed.

    `code` is a ClaimErrorCode value, exposed to GraphQL clients.
    """

    default_code = ClaimErrorCode.INVALID

    def __init__(self, message, *, code=None):
        super().__init__(message)
        self.code = code if code is not None else self.default_code


# =====================================================================
# PUBLIC API
# =====================================================================


@transaction.atomic
def claim_checkout(
    checkout: Checkout,
    user,
    *,
    merge: bool = True,
) -> Checkout:
    """
    Assign a guest checkout to a user, merging lines if the user
    already has an active cart on the same channel.

    Returns the checkout the caller should treat as the user's
    active cart (either the claimed guest cart, or the user's
    existing cart when the guest cart was merged into it).

    Parameters
    ----------
    checkout:
        The guest checkout to claim. Must be persisted.
    user:
        The authenticated user who will own the cart.
    merge:
        If True (default), merge a non-empty guest cart into the
        user's existing cart. If False, do a plain ownership
        transfer; the user may end up with multiple active carts.
    """
    _validate_checkout(checkout)
    _validate_user(user)

    # Idempotent: already this user's.
    if checkout.user_id == user.pk:
        return checkout

    # Belongs to a different user.
    if checkout.user_id is not None and checkout.user_id != user.pk:
        raise ClaimError(
            "This checkout is already claimed by another user.",
            code=ClaimErrorCode.ALREADY_CLAIMED,
        )

    # Refuse if completion is in progress.
    if checkout.completing_started_at is not None:
        raise ClaimError(
            "Cannot claim a checkout whose completion has started.",
            code=ClaimErrorCode.LOCKED,
        )

    # Look for the user's existing cart on the same channel.
    existing_user_cart = _get_existing_user_cart(user, checkout)

    # No existing cart: simple ownership transfer.
    if existing_user_cart is None:
        return _assign_owner(checkout, user)

    # Channel mismatch: refuse.
    if existing_user_cart.channel_id != checkout.channel_id:
        raise ClaimError(
            "Cannot claim a checkout on a different channel than "
            "the user's existing cart.",
            code=ClaimErrorCode.CHANNEL_MISMATCH,
        )

    # Empty guest cart: discard, keep user cart.
    if not checkout.lines.exists():
        _discard_empty_guest_cart(checkout)
        return existing_user_cart

    # Non-empty guest cart: merge into the user's cart.
    if merge:
        _merge_into_user_cart(guest=checkout, target=existing_user_cart)
        return existing_user_cart

    # merge=False: both become user carts.
    return _assign_owner(checkout, user)


def get_user_active_cart(user, channel) -> Optional[Checkout]:
    """
    Return the user's most recent active checkout on the given channel.

    "Active" = not currently being completed.
    """
    return (
        Checkout.objects
        .filter(
            user=user,
            channel=channel,
            completing_started_at__isnull=True,
        )
        .order_by("-last_change")
        .first()
    )


# =====================================================================
# INTERNALS
# =====================================================================

def _get_existing_user_cart(user, checkout: Checkout) -> Optional[Checkout]:
    """
    Return the user's most recent active cart, regardless of channel.

    The caller decides how to handle channel mismatches:
    same channel merges; different channel refuses with
    ClaimErrorCode.CHANNEL_MISMATCH.
    """
    return (
        Checkout.objects
        .filter(
            user=user,
            completing_started_at__isnull=True,
        )
        .exclude(pk=checkout.pk)
        .order_by("-last_change")
        .first()
    )
    
    
def _assign_owner(checkout: Checkout, user) -> Checkout:
    """
    Attach the user to the checkout, filling in email if missing.
    """
    checkout.user = user

    update_fields = ["user", "last_change"]

    if not checkout.email and user.email:
        checkout.email = user.email
        update_fields.append("email")

    checkout.last_change = timezone.now()
    checkout.save(update_fields=update_fields)

    return checkout


def _discard_empty_guest_cart(guest: Checkout) -> None:
    """Delete an empty guest cart."""
    guest.delete()


def _merge_into_user_cart(*, guest: Checkout, target: Checkout) -> None:
    """
    Merge guest cart lines into the target cart, then delete the
    guest cart.

    Line merging delegates to `add_variant_to_checkout`, which
    handles stock reservation, unique-constraint-safe upserts, and
    price invalidation.
    """
    from ecommerce.services.checkout.lifecycle import (
        add_variant_to_checkout,
    )

    for guest_line in guest.lines.select_related("variant").all():
        add_variant_to_checkout(
            target,
            guest_line.variant,
            guest_line.quantity,
            replace=False,
        )

    # Inherit guest email if the target has none.
    if not target.email and guest.email:
        target.email = guest.email
        target.save(update_fields=["email", "last_change"])

    guest.delete()


def _validate_checkout(checkout: Checkout) -> None:
    if checkout is None:
        raise ClaimError(
            "Checkout is required.",
            code=ClaimErrorCode.INVALID,
        )
    if not isinstance(checkout, Checkout):
        raise ClaimError(
            "A valid Checkout instance is required.",
            code=ClaimErrorCode.INVALID,
        )
    if checkout._state.adding:
        raise ClaimError(
            "Checkout must be persisted before it can be claimed.",
            code=ClaimErrorCode.NOT_FOUND,
        )


def _validate_user(user) -> None:
    if user is None:
        raise ClaimError(
            "User is required.",
            code=ClaimErrorCode.INVALID,
        )
    if not getattr(user, "is_authenticated", False):
        raise ClaimError(
            "An authenticated user is required.",
            code=ClaimErrorCode.INVALID,
        )


__all__ = [
    "ClaimError",
    "claim_checkout",
    "get_user_active_cart",
]