# ecommerce/services/order/lifecycle.py

"""
Order lifecycle services.

Post-creation operations:

    get_order_by_id        — fetch for display
    get_user_orders        — order history
    confirm_order          — move from unconfirmed to unfulfilled
    mark_order_as_paid     — attach payment reference and update status
    cancel_order           — cancel and release allocated stock

Order creation lives in `ecommerce.services.checkout.complete`.
"""

from __future__ import annotations    
import logging


from typing import Optional

from django.db import transaction
from django.utils import timezone

from ecommerce.models.channel import Channel
from ecommerce.models.enums import OrderEvents, OrderStatus
from ecommerce.models.order import Order, OrderEvent
from ecommerce.services.warehouse.allocation import (
    deallocate_for_order,
)

logger = logging.getLogger(__name__)
# =====================================================================
# ERRORS
# =====================================================================


class OrderNotCancelable(Exception):
    """Raised when an order cannot be cancelled in its current state."""


class OrderNotConfirmable(Exception):
    """Raised when an order cannot be confirmed in its current state."""


# =====================================================================
# LOOKUPS
# =====================================================================


def get_order_by_id(order_id) -> Optional[Order]:
    """
    Fetch an order with the related data a storefront display needs.
    """
    return (
        Order.objects
        .select_related(
            "user",
            "channel",
            "billing_address",
            "shipping_address",
            "shipping_method",
        )
        .prefetch_related(
            "lines__variant__product",
            "lines__allocations",
            "fulfillments__lines",
            "events",
        )
        .filter(pk=order_id)
        .first()
    )


def get_user_orders(user, *, limit: int = 50):
    """
    Return the user's orders, newest first.
    """
    return (
        Order.objects
        .filter(user=user)
        .select_related("channel")
        .prefetch_related("lines")
        .order_by("-created_at")[:limit]
    )


# =====================================================================
# STATE TRANSITIONS
# =====================================================================


@transaction.atomic
def confirm_order(
    order: Order,
    *,
    user=None,
) -> Order:
    """
    Move an order from UNCONFIRMED to UNFULFILLED.

    Idempotent: if the order is already confirmed, this is a no-op.

    Emits an OrderEvent on the transition.
    """
    order = Order.objects.select_for_update(of=("self",)).get(pk=order.pk)

    if order.status == OrderStatus.UNFULFILLED:
        return order

    if order.status != OrderStatus.UNCONFIRMED:
        raise OrderNotConfirmable(
            f"Cannot confirm an order in status {order.status!r}."
        )

    order.status = OrderStatus.UNFULFILLED
    order.save(update_fields=["status", "updated_at"])

    OrderEvent.objects.create(
        order=order,
        type=OrderEvents.CONFIRMED,
        user=user,
    )

    return order


@transaction.atomic
def mark_order_as_paid(
    order: Order,
    *,
    payment_reference: Optional[str] = None,
    user=None,
) -> Order:
    """
    Mark an order as paid.

    Sets `total_charged_amount` to `total_gross_amount`,
    `charge_status` to FULL, and stores the payment reference.

    Idempotent: re-marking a paid order is a no-op.
    """
    order = Order.objects.select_for_update(of=("self",)).get(pk=order.pk)

    if order.charge_status == "full":
        return order

    order.total_charged_amount = order.total_gross_amount
    order.charge_status = "full"
    order.save(
        update_fields=[
            "total_charged_amount",
            "charge_status",
            "updated_at",
        ]
    )

    OrderEvent.objects.create(
        order=order,
        type=OrderEvents.ORDER_MARKED_AS_PAID,
        user=user,
        parameters={"payment_reference": payment_reference} if payment_reference else {},
    )

    return order


@transaction.atomic
def cancel_order(
    order: Order,
    *,
    user=None,
    reason: str = "",
) -> Order:
    """
    Cancel an order.

    Steps:
        1. Lock the order.
        2. Refuse if already in a terminal state.
        3. Deallocate stock for every line.
        4. Restock any already-fulfilled quantities.
        5. Set status to CANCELED.
        6. Emit an OrderEvent.

    Terminal states that cannot be cancelled:
        CANCELED, RETURNED, EXPIRED
    """
    order = Order.objects.select_for_update(of=("self",)).get(pk=order.pk)

    if order.status in {
        OrderStatus.CANCELED,
        OrderStatus.RETURNED,
        OrderStatus.EXPIRED,
    }:
        raise OrderNotCancelable(
            f"Cannot cancel an order in status {order.status!r}."
        )

    # Release any open stock allocations.
    deallocate_for_order(order)

    # If any fulfillment already shipped (stock decremented),
    # restock those units. For MVP, fulfillments don't exist yet,
    # so this loop is empty.
    for fulfillment in order.fulfillments.filter(
        status__in=["fulfilled", "refunded", "returned"]
    ):
        _restock_fulfillment(fulfillment)

    order.status = OrderStatus.CANCELED
    order.save(update_fields=["status", "updated_at"])

    OrderEvent.objects.create(
        order=order,
        type=OrderEvents.CANCELED,
        user=user,
        parameters={"reason": reason} if reason else {},
    )
    # --- Auto-refund if the order was charged -----------------------
    if order.charge_status == "full":
        try:
            from ecommerce.services.order.refund import (
                RefundError,
                create_refund_for_order,
            )
            create_refund_for_order(
                order,
                reason=reason or "Order cancelled",
                user=user,
            )
        except RefundError:
            logger.exception(
                "Auto-refund creation failed for cancelled order %s.",
                order.pk,
            )
        except Exception:
            logger.exception(
                "Unexpected error creating refund for order %s.",
                order.pk,
            ) 
                # Optional: execute immediately.
            from ecommerce.services.order.refund import (
                execute_refund_for_order,
            )
            execute_refund_for_order(
                order,
                provider="paystack",  # or read from channel config
            )
    return order


# =====================================================================
# HELPERS
# =====================================================================


def _restock_fulfillment(fulfillment) -> None:
    """
    Return fulfillment quantities to physical stock.

    Intended for cancel/refund flows. Currently a no-op because
    fulfillments don't yet exist; wired now so cancellation logic
    is complete when they do.
    """
    # Placeholder — will call increase_stock per fulfillment line
    # once we build Phase 5.2.
    return