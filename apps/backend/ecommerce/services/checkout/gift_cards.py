# apps/backend/ecommerce/services/checkout/gift_cards.py

"""
Gift card application and removal.

Applying a gift card creates a CheckoutGiftCard row that records
the intent to deduct. The balance is deducted at
`complete_checkout`, not at application, so an abandoned
checkout does not consume the balance.

Multiple gift cards can be applied to a single checkout.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from ecommerce.models.checkout import Checkout, CheckoutGiftCard
from ecommerce.models.giftcard import GiftCard
from ecommerce.services.checkout.calculations import (
    calculate_checkout_total,
    update_checkout_totals,
)


class GiftCardNotFound(ValidationError):
    """Raised when no gift card matches the given code."""


class GiftCardNotUsable(ValidationError):
    """Raised when the gift card is expired, inactive, or empty."""


# =====================================================================
# APPLY
# =====================================================================


@transaction.atomic
def apply_gift_card(
    checkout: Checkout,
    code: str,
    *,
    amount: Decimal | None = None,
) -> Checkout:
    """
    Apply a gift card to a checkout.

    `amount` is optional: if omitted, the maximum usable amount
    (min of card balance and remaining total) is applied.

    Idempotent per card: re-applying the same card updates the
    amount rather than creating a duplicate row.

    Raises:
        GiftCardNotFound — if the code does not resolve.
        GiftCardNotUsable — if the card is not usable.
    """
    code = (code or "").strip()
    if not code:
        raise GiftCardNotFound("Gift card code is required.")

    gift_card = GiftCard.objects.filter(code=code).first()
    if gift_card is None:
        raise GiftCardNotFound(f"Unknown gift card: {code}")

    if gift_card.currency != checkout.currency:
        raise GiftCardNotUsable(
            "Gift card currency does not match checkout currency."
        )

    if not gift_card.is_usable:
        raise GiftCardNotUsable(
            "Gift card is not usable (expired, inactive, or empty)."
        )

    # Compute the maximum this card can contribute.
    country_code = checkout.get_country()
    current_total = calculate_checkout_total(checkout, country_code)

    existing_applications = CheckoutGiftCard.objects.filter(
        checkout=checkout,
    ).exclude(gift_card=gift_card)

    already_applied = sum(
        (a.amount_applied for a in existing_applications),
        Decimal("0"),
    )

    remaining = current_total.gross.amount - already_applied
    if remaining <= Decimal("0"):
        raise GiftCardNotUsable(
            "The checkout total is already covered."
        )

    max_usable = min(gift_card.current_balance_amount, remaining)
    requested = Decimal(str(amount)) if amount is not None else max_usable

    if requested <= Decimal("0"):
        raise GiftCardNotUsable(
            "Gift card amount must be greater than zero."
        )
    if requested > gift_card.current_balance_amount:
        raise GiftCardNotUsable(
            f"Gift card balance is {gift_card.current_balance_amount}, "
            f"requested {requested}."
        )
    if requested > remaining:
        raise GiftCardNotUsable(
            f"Checkout has {remaining} remaining; "
            f"requested {requested}."
        )

    CheckoutGiftCard.objects.update_or_create(
        checkout=checkout,
        gift_card=gift_card,
        defaults={"amount_applied": requested},
    )

    update_checkout_totals(checkout, country_code)
    checkout.refresh_from_db()
    return checkout


# =====================================================================
# REMOVE
# =====================================================================


@transaction.atomic
def remove_gift_card(
    checkout: Checkout,
    gift_card: GiftCard,
) -> Checkout:
    """
    Remove a gift card from a checkout. Idempotent.
    """
    deleted, _ = CheckoutGiftCard.objects.filter(
        checkout=checkout,
        gift_card=gift_card,
    ).delete()

    if deleted:
        country_code = checkout.get_country()
        update_checkout_totals(checkout, country_code)
        checkout.refresh_from_db()

    return checkout