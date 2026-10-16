# ecommerce/services/order/fulfillment.py

"""
Order fulfillment services.

A Fulfillment represents a shipment of one or more order lines.

Lifecycle:

    create_fulfillment()   — record shipment, decrement physical stock
    complete_fulfillment() — mark shipped (no-op for our flow)
    cancel_fulfillment()   — reverse shipment, restock

Design:

    - One fulfillment per order for MVP (multi-shipment is Phase 7+).
    - Each FulfillmentLine references the OrderLine it fulfills and
      the Stock it came from.
    - Creating a fulfillment decrements Stock.quantity (physical stock
      leaves the warehouse).
    - OrderLine.quantity_fulfilled is incremented.
    - Order.status is updated based on total quantity fulfilled.
    - Every state change emits an OrderEvent, which triggers
      notifications and audit.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Iterable, Optional
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone

from ecommerce.models.enums import (
    FulfillmentStatus,
    OrderEvents,
    OrderStatus,
)
from ecommerce.models.inventory import Stock
from ecommerce.models.order import (
    Fulfillment,
    FulfillmentLine,
    Order,
    OrderEvent,
    OrderLine,
)


ZERO = Decimal("0")


# =====================================================================
# ERRORS
# =====================================================================


class FulfillmentError(ValidationError):
    """Base error for fulfillment operations."""


class FulfillmentNotPossible(FulfillmentError):
    """Raised when an order cannot be fulfilled in its current state."""


# =====================================================================
# DATA SHAPES
# =====================================================================


class FulfillmentLineInput:
    """
    Simple value object for fulfillment line input.

    Pass a list of these to `create_fulfillment`.
    """

    __slots__ = ("order_line", "quantity", "stock")

    def __init__(
        self,
        order_line: OrderLine,
        quantity: Decimal,
        stock: Optional[Stock] = None,
    ):
        self.order_line = order_line
        self.quantity = Decimal(str(quantity))
        self.stock = stock


# =====================================================================
# LOOKUPS
# =====================================================================


def get_fulfillment_by_id(
    fulfillment_id: UUID | int,
) -> Optional[Fulfillment]:
    """Fetch a fulfillment with prefetched lines."""
    return (
        Fulfillment.objects
        .select_related("order")
        .prefetch_related("lines__order_line__variant")
        .filter(pk=fulfillment_id)
        .first()
    )


# =====================================================================
# CREATE
# =====================================================================


@transaction.atomic
def create_fulfillment(
    order: Order,
    lines_data: Iterable[FulfillmentLineInput],
    *,
    tracking_number: str = "",
    user=None,
) -> Fulfillment:
    """
    Record a shipment for an order.

    For each line:
        - validates the quantity is available to fulfill
        - decrements Stock.quantity (goods leave the warehouse)
        - increments OrderLine.quantity_fulfilled

    Then:
        - updates Order.status
        - emits FULFILLMENT_FULFILLED_ITEMS event

    Raises:
        FulfillmentNotPossible — if the order is not in a
            fulfillable state.
        FulfillmentError — if a line's quantity exceeds the
            unfulfilled amount.
    """
    order = Order.objects.select_for_update(of=("self",)).get(pk=order.pk)

    if order.status not in {
        OrderStatus.UNFULFILLED,
        OrderStatus.PARTIALLY_FULFILLED,
    }:
        raise FulfillmentNotPossible(
            f"Cannot fulfill an order in status {order.status!r}."
        )

    lines_data = list(lines_data)
    if not lines_data:
        raise FulfillmentError("A fulfillment must have at least one line.")

    # Create the fulfillment header. `fulfillment_order` is set in
    # Fulfillment.save(), so we don't need to compute it here.
    fulfillment = Fulfillment.objects.create(
        order=order,
        status=FulfillmentStatus.FULFILLED,
        tracking_number=tracking_number,
    )

    # Process each line.
    for line_input in lines_data:
        _add_fulfillment_line(fulfillment, line_input)

    # Update order status.
    _update_order_status_from_fulfillments(order)

    # Emit event.
    OrderEvent.objects.create(
        order=order,
        type=OrderEvents.FULFILLMENT_FULFILLED_ITEMS,
        user=user,
        parameters={
            "fulfillment_id": fulfillment.pk,
            "fulfillment_order": fulfillment.fulfillment_order,
            "line_count": len(lines_data),
        },
    )

    return fulfillment


def _add_fulfillment_line(
    fulfillment: Fulfillment,
    line_input: FulfillmentLineInput,
) -> FulfillmentLine:
    """
    Add a single line to a fulfillment.

    Validates quantity, decrements stock, and updates the order line.
    """
    order_line = line_input.order_line
    quantity = line_input.quantity

    if quantity <= ZERO:
        raise FulfillmentError("Fulfillment quantity must be positive.")

    # Reload the order line with a lock to check quantity_fulfilled safely.
    order_line = (
        OrderLine.objects
        .select_for_update(of=("self",))
        .get(pk=order_line.pk)
    )

    remaining = order_line.quantity - order_line.quantity_fulfilled
    if quantity > remaining:
        raise FulfillmentError(
            f"Cannot fulfill {quantity}: "
            f"only {remaining} unfulfilled on order line {order_line.pk}."
        )

    # Decrement physical stock if this is a tracked variant.
    stock = line_input.stock
    if stock is None:
        stock = _find_stock_for_variant(
            order_line.variant, fulfillment.order
        )

    if stock is not None and order_line.variant.track_inventory:
        stock.decrease_stock(
            quantity,
            commit=True,
            reason=f"Fulfillment #{fulfillment.pk}",
            user=None,
        )

    # Create the fulfillment line.
    fulfillment_line = FulfillmentLine.objects.create(
        fulfillment=fulfillment,
        order_line=order_line,
        quantity=quantity,
        stock=stock,
    )

    # Update the order line's fulfilled quantity.
    order_line.quantity_fulfilled = F(("quantity_fulfilled")) + quantity
    order_line.save(update_fields=["quantity_fulfilled"])

    return fulfillment_line


def _find_stock_for_variant(variant, order) -> Optional[Stock]:
    """
    Pick a Stock for a variant, preferring the order's allocated
    warehouse.

    Returns None if the variant doesn't track inventory.
    """
    if not variant.track_inventory:
        return None

    # Prefer a stock from the order line's allocated warehouse
    # (set during checkout), fall back to any stock in the channel.
    stock = (
        Stock.objects
        .filter(
            product_variant=variant,
            warehouse__channelwarehouse__channel=order.channel,
        )
        .order_by("-quantity")
        .first()
    )
    return stock


# =====================================================================
# CANCEL
# =====================================================================


@transaction.atomic
def cancel_fulfillment(
    fulfillment: Fulfillment,
    *,
    user=None,
    reason: str = "",
) -> Fulfillment:
    """
    Cancel a fulfillment and return its quantities to stock.

    Steps:
        1. Lock the fulfillment.
        2. Refuse if already terminal (CANCELED, RETURNED).
        3. Restock each line.
        4. Decrement OrderLine.quantity_fulfilled.
        5. Update Order.status.
        6. Emit FULFILLMENT_CANCELED event.
    """
    fulfillment = (
        Fulfillment.objects
        .select_for_update(of=("self",))
        .get(pk=fulfillment.pk)
    )

    if fulfillment.status in {
        FulfillmentStatus.CANCELED,
        FulfillmentStatus.RETURNED,
    }:
        raise FulfillmentError(
            f"Cannot cancel a fulfillment in status {fulfillment.status!r}."
        )

    for line in fulfillment.lines.select_related(
        "order_line__variant", "stock"
    ):
        _restock_fulfillment_line(line, reason=reason)

    fulfillment.status = FulfillmentStatus.CANCELED
    fulfillment.save(update_fields=["status"])

    _update_order_status_from_fulfillments(fulfillment.order)

    OrderEvent.objects.create(
        order=fulfillment.order,
        type=OrderEvents.FULFILLMENT_CANCELED,
        user=user,
        parameters={
            "fulfillment_id": fulfillment.pk,
            "reason": reason,
        },
    )

    return fulfillment


def _restock_fulfillment_line(
    line: FulfillmentLine,
    *,
    reason: str = "",
) -> None:
    """
    Return a fulfillment line's quantity to physical stock and
    decrement the order line's fulfilled quantity.
    """
    order_line = line.order_line
    quantity = line.quantity

    if order_line.variant.track_inventory and line.stock is not None:
        line.stock.increase_stock(
            quantity,
            commit=True,
            reason=reason or f"Cancel fulfillment line #{line.pk}",
            user=None,
        )

    # Decrement the order line's fulfilled quantity.
    order_line.quantity_fulfilled = F("quantity_fulfilled") - quantity
    order_line.save(update_fields=["quantity_fulfilled"])


# =====================================================================
# STATUS RECOMPUTATION
# =====================================================================


def _update_order_status_from_fulfillments(order: Order) -> None:
    """
    Recompute Order.status based on the total fulfilled quantity
    across all non-canceled fulfillment lines.

    Rules:
        - No fulfilled quantity → UNFULFILLED
        - Some fulfilled → PARTIALLY_FULFILLED
        - All fulfilled → FULFILLED
    """
    order_lines = order.lines.all()
    total_quantity = sum(
        (line.quantity for line in order_lines),
        ZERO,
    )
    if total_quantity == ZERO:
        return

    fulfilled_quantity = sum(
        (line.quantity_fulfilled for line in order_lines),
        ZERO,
    )

    if fulfilled_quantity >= total_quantity:
        new_status = OrderStatus.FULFILLED
    elif fulfilled_quantity > ZERO:
        new_status = OrderStatus.PARTIALLY_FULFILLED
    else:
        new_status = OrderStatus.UNFULFILLED

    if order.status != new_status:
        order.status = new_status
        order.save(update_fields=["status", "updated_at"])