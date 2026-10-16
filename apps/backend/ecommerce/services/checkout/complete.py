# ecommerce/services/checkout/complete.py

"""
Checkout completion.

Converts a Checkout into an Order:

    - Validates the checkout is completable
    - Recomputes totals (authoritative — never trusts the client)
    - Creates the Order and OrderLine rows
    - Allocates stock for each order line
    - Releases checkout reservations
    - Emits an OrderEvent (which triggers notifications + audit)
    - Deletes the checkout

The whole flow runs inside a single transaction: either every step
succeeds and the order exists, or nothing happens.
"""

from __future__ import annotations
import logging
from decimal import Decimal
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.exceptions import InsufficientStock
from ecommerce.models.checkout import Checkout, CheckoutLine
from ecommerce.models.enums import OrderEvents, OrderOrigin, OrderStatus
from ecommerce.models.order import Order, OrderEvent, OrderLine
from ecommerce.services.checkout.calculations import (
    calculate_checkout_shipping,
    calculate_checkout_subtotal,
    calculate_checkout_total,
)
from ecommerce.services.product.pricing import get_variant_availability
from ecommerce.services.warehouse.allocation import (
    allocate_for_order_line,
    release_reservations_for_checkout_line,
)
from ecommerce.services.order.payment import create_payment_for_order

logger = logging.getLogger(__name__)

ZERO = Decimal("0")


# =====================================================================
# ERRORS
# =====================================================================


class CheckoutNotReady(ValidationError):
    """Raised when a checkout cannot be completed."""


# =====================================================================
# VALIDATION
# =====================================================================


def validate_checkout_for_completion(checkout: Checkout) -> None:
    """
    Raise CheckoutNotReady if the checkout cannot be completed.

    Rules:
        - must have at least one line
        - must have an email (either on checkout or its user)
        - must have billing_address and shipping_address if shipping
          is required
        - must have a shipping_method if shipping is required
        - every line's variant must be available in the channel
    """
    if not checkout.lines.exists():
        raise CheckoutNotReady("Checkout has no lines.")

    email = checkout.get_customer_email()
    if not email:
        raise CheckoutNotReady("Checkout has no contact email.")

    if _checkout_requires_shipping(checkout):
        if checkout.shipping_address_id is None:
            raise CheckoutNotReady("Shipping address is required.")
        if checkout.billing_address_id is None:
            raise CheckoutNotReady("Billing address is required.")
        if checkout.shipping_method_id is None:
            raise CheckoutNotReady("Shipping method is required.")

    country_code = checkout.get_country()
    for line in checkout.lines.select_related(
        "variant__product__product_type"
    ):
        availability = get_variant_availability(
            line.variant, checkout.channel, country_code
        )
        if availability is None:
            raise CheckoutNotReady(
                f"Variant {line.variant} is no longer available."
            )


def _checkout_requires_shipping(checkout: Checkout) -> bool:
    return any(
        line.variant.is_shipping_required()
        for line in checkout.lines.select_related(
            "variant__product__product_type"
        )
    )


# =====================================================================
# COMPLETION
# =====================================================================


@transaction.atomic
def complete_checkout(
    checkout: Checkout,
    *,
    user=None,
    payment_reference: Optional[str] = None,
) -> Order:
    """
    Convert a checkout into an order.

    Steps:
        1. Lock the checkout row.
        2. Validate it.
        3. Recompute totals.
        4. Create the order.
        5. Create order lines.
        6. Allocate stock.
        7. Release reservations.
        8. Emit an OrderEvent.
        9. Delete the checkout.

    Returns the new Order.

    Raises:
        CheckoutNotReady — if the checkout is not completable.
        InsufficientStock — if any line cannot be allocated.
    """
    # --- 1. Lock the checkout ----------------------------------------
    # Lock only the Checkout row. `select_related` on nullable FKs
    # (user, shipping_address, billing_address) would produce a
    # LEFT OUTER JOIN, and Postgres rejects FOR UPDATE on the nullable
    # side of an outer join.
    checkout = (
        Checkout.objects
        .select_for_update(of=("self",))
        .get(pk=checkout.pk)
    )

    if checkout.completing_started_at is not None:
        raise CheckoutNotReady(
            "Checkout is already being completed."
        )

    checkout.completing_started_at = timezone.now()
    checkout.save(update_fields=["completing_started_at", "last_change"])

    # --- 2. Validate -------------------------------------------------
    validate_checkout_for_completion(checkout)

    # --- 3. Recompute totals -----------------------------------------
    country_code = checkout.get_country()
    subtotal = calculate_checkout_subtotal(checkout, country_code)
    shipping = calculate_checkout_shipping(checkout, country_code)
    total = calculate_checkout_total(checkout, country_code)

    # --- 4. Create order ---------------------------------------------
    order = Order.objects.create(
        channel=checkout.channel,
        currency=checkout.currency,
        user=checkout.user,
        user_email=checkout.get_customer_email(),
        language_code=checkout.language_code,
        billing_address=checkout.billing_address,
        shipping_address=checkout.shipping_address,
        shipping_method=checkout.shipping_method,
        collection_point=checkout.collection_point,
        shipping_method_name=(
            checkout.shipping_method.name
            if checkout.shipping_method
            else None
        ),
        origin=OrderOrigin.CHECKOUT,
        status=OrderStatus.UNFULFILLED,
        authorize_status="none",
        charge_status="none",
        display_gross_prices=True,
        customer_note=checkout.note,
        checkout_token=str(checkout.pk),
        # Totals (taxed)
        subtotal_net_amount=subtotal.net.amount,
        subtotal_gross_amount=subtotal.gross.amount,
        shipping_price_net_amount=shipping.net.amount,
        shipping_price_gross_amount=shipping.gross.amount,
        total_net_amount=total.net.amount,
        total_gross_amount=total.gross.amount,
        undiscounted_total_net_amount=total.net.amount,
        undiscounted_total_gross_amount=total.gross.amount,
        # Shipping undiscounted
        base_shipping_price_amount=shipping.net.amount,
        undiscounted_base_shipping_price_amount=shipping.net.amount,
    )

    # --- 5. Create order lines ---------------------------------------
    order_lines = _create_order_lines_from_checkout(
        checkout, order, country_code
    )
    
    # --- 6b. Consume voucher and gift cards --------------------------
    _consume_voucher(checkout, order)
    _consume_gift_cards(checkout, order)
    
    # --- 6. Allocate stock for each line -----------------------------
    for order_line in order_lines:
        try:
            allocate_for_order_line(order_line, checkout.channel)
        except InsufficientStock:
            # The transaction will roll back — the order and every
            # allocation created so far disappears.
            raise

    # --- 7. Release checkout reservations ----------------------------
    for checkout_line in checkout.lines.all():
        release_reservations_for_checkout_line(checkout_line)

    # --- 8. Emit OrderEvent (triggers notifications + audit) ---------
    OrderEvent.objects.create(
        order=order,
        type=OrderEvents.PLACED,
        user=user or checkout.user,
        parameters={
            "checkout_token": str(checkout.pk),
            "payment_reference": payment_reference,
        },
    )
    # --- Create the canonical Payment for this order ---------------
    # Best-effort: if the payment layer fails, the order still exists
    # and can be retried by staff. Do not fail the checkout on
    # payment-layer availability.
    try:
        create_payment_for_order(order)
    except Exception:
        logger.exception(
            "Failed to create Payment for order %s.",
            order.pk,
        )
    # --- 9. Delete the checkout --------------------------------------
    checkout.lines.all().delete()
    
    checkout.delete()

    return order


# =====================================================================
# HELPERS
# =====================================================================


def _create_order_lines_from_checkout(
    checkout: Checkout,
    order: Order,
    country_code: str,
) -> list[OrderLine]:
    """
    Create OrderLine rows from the checkout's lines.

    Prices come from `get_variant_availability` (tax-aware).
    Quantity unit comes from the variant, so the order preserves
    the sale unit (kg, unit, bunch, etc.).
    """
    order_lines: list[OrderLine] = []

    for checkout_line in checkout.lines.select_related(
        "variant__product__product_type", "variant__product"
    ):
        variant = checkout_line.variant
        product = variant.product

        availability = get_variant_availability(
            variant, checkout.channel, country_code
        )
        # Already checked in validate_checkout_for_completion, but
        # defensive recheck in case of a concurrent change.
        if availability is None:
            raise CheckoutNotReady(
                f"Variant {variant} is no longer available."
            )

        unit_price = availability.price
        quantity = checkout_line.quantity

        order_line = OrderLine.objects.create(
            order=order,
            variant=variant,
            product_name=product.name,
            variant_name=variant.name or "",
            product_sku=variant.sku,
            quantity=quantity,
            quantity_unit=checkout_line.quantity_unit,
            is_shipping_required=variant.is_shipping_required(),
            is_gift_card=variant.is_gift_card(),
            currency=order.currency,
            # Unit prices
            unit_price_net_amount=unit_price.net.amount,
            unit_price_gross_amount=unit_price.gross.amount,
            undiscounted_unit_price_net_amount=availability.price_undiscounted.net.amount,
            undiscounted_unit_price_gross_amount=availability.price_undiscounted.gross.amount,
            # Total prices
            total_price_net_amount=unit_price.net.amount * quantity,
            total_price_gross_amount=unit_price.gross.amount * quantity,
            undiscounted_total_price_net_amount=availability.price_undiscounted.net.amount * quantity,
            undiscounted_total_price_gross_amount=availability.price_undiscounted.gross.amount * quantity,
            # Base prices
            base_unit_price_amount=unit_price.net.amount,
            undiscounted_base_unit_price_amount=availability.price_undiscounted.net.amount,
        )

        order_lines.append(order_line)

    return order_lines

def _consume_voucher(
    checkout: Checkout,
    order: Order,
) -> None:
    """
    Transfer the checkout's voucher discount to the order and
    increment the voucher code's usage counter.

    No-op if no voucher discount is present.
    """
    from ecommerce.models.discount import (
        CheckoutDiscount,
        DiscountType,
        OrderDiscount,
        VoucherCode,
    )

    checkout_discount = CheckoutDiscount.objects.filter(
        checkout=checkout,
        type=DiscountType.VOUCHER,
    ).first()

    if checkout_discount is None:
        return

    # Copy the discount to the order.
    OrderDiscount.objects.create(
        order=order,
        type=checkout_discount.type,
        value_type=checkout_discount.value_type,
        value=checkout_discount.value,
        amount_value=checkout_discount.amount_value,
        currency=checkout_discount.currency,
        name=checkout_discount.name,
        voucher=checkout_discount.voucher,
        voucher_code=checkout_discount.voucher_code,
        reason="Applied at checkout",
    )

    # Increment the usage counter on the code.
    if checkout_discount.voucher_code:
        VoucherCode.objects.filter(
            code=checkout_discount.voucher_code,
        ).update(used=models.F("used") + 1)


def _consume_gift_cards(
    checkout: Checkout,
    order: Order,
) -> None:
    """
    Deduct each applied gift card's balance and log an event.

    The amount deducted is recomputed against the order total
    to handle the (unusual) case where the total changed between
    application and completion. Cards are consumed in order.
    """
    from ecommerce.models.checkout import CheckoutGiftCard
    from ecommerce.models.giftcard import GiftCardEvent
    from ecommerce.models.enums import GiftCardEvents

    applications = (
        CheckoutGiftCard.objects
        .filter(checkout=checkout)
        .select_related("gift_card")
        .order_by("created_at")
    )

    remaining = order.total_gross_amount

    for application in applications:
        if remaining <= ZERO:
            break

        deduct = min(application.amount_applied, remaining)
        if deduct <= ZERO:
            continue

        gift_card = application.gift_card

        # Re-check usability at the moment of consumption; the
        # card may have expired or been used elsewhere since
        # application.
        
        if not gift_card.is_usable:
            raise CheckoutNotReady(
                f"Gift card {gift_card.display_code} is no longer "
                f"usable. Remove it and try again."
            )

        previous_balance = gift_card.current_balance_amount
        gift_card.use_balance(deduct)

        GiftCardEvent.log_event(
            gift_card=gift_card,
            event_type=GiftCardEvents.USED,
            order=order,
            amount=deduct,
            previous_balance=previous_balance,
            new_balance=gift_card.current_balance_amount,
            parameters={
                "order_id": str(order.pk),
                "checkout_token": str(checkout.pk),
            },
        )

        remaining -= deduct



