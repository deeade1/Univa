# ecommerce/services/order/refund.py

"""
Refund flow for ecommerce orders.

A refund is a canonical Payment with direction=DISBURSE. The bridge:

    Order
        ↓
    OrderGrantedRefund (ecommerce intent)
        ↓
    Payment (canonical, direction=DISBURSE)
        ↓
    PaymentExecution + Celery task
        ↓
    [async] ExecutionOrchestrator.execute()
        ↓
    [signal] PaymentExecution COMPLETED → OrderGrantedRefund.status=SUCCESS

Architectural boundary
----------------------

Ecommerce owns refund *intent*. Payment owns refund *execution*.
No payment-side code knows about OrderGrantedRefund.
"""

from __future__ import annotations

import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from django.db import transaction
from django.utils import timezone

from ecommerce.models.enums import (
    OrderEvents,
    OrderGrantedRefundStatus,
)
from ecommerce.models.order import (
    Order,
    OrderEvent,
    OrderGrantedRefund,
)
from payment.canonical.models import Payment


logger = logging.getLogger(__name__)


# =====================================================================
# ERRORS
# =====================================================================


class RefundError(Exception):
    """Base error for refund operations."""


class OrderNotRefundable(RefundError):
    """Raised when an order cannot be refunded in its current state."""


class RefundAmountInvalid(RefundError):
    """Raised when a requested refund amount is out of bounds."""


# =====================================================================
# PRECISION
# =====================================================================


def _quantize(amount: Decimal) -> Decimal:
    """Normalize to currency precision (2 dp) — same rule as payments."""
    return Decimal(amount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


# =====================================================================
# CREATE REFUND
# =====================================================================


@transaction.atomic
def create_refund_for_order(
    order: Order,
    *,
    amount: Optional[Decimal] = None,
    reason: str = "",
    user=None,
) -> OrderGrantedRefund:
    """
    Create an OrderGrantedRefund and its backing canonical Payment.

    Idempotent per order for full refunds: if a pending or successful
    refund already exists, returns it.

    Steps:
        1. Lock the order.
        2. Validate: order must have been charged.
        3. Compute refund amount (default = total_charged_amount).
        4. Create OrderGrantedRefund (status=PENDING).
        5. Create canonical Payment (direction=DISBURSE).
        6. Link Payment via OrderGrantedRefund.payment_id.
        7. Emit OrderEvent.

    PaymentExecution creation is a separate step, triggered by
    `execute_refund_for_order` (or automatically by `orderCancel`).
    """
    order = Order.objects.select_for_update(of=("self",)).get(pk=order.pk)

    _validate_refundable(order)

    # Idempotent: don't create a second refund for a fully refunded order.
    existing = (
        OrderGrantedRefund.objects
        .filter(
            order=order,
            status__in=[
                OrderGrantedRefundStatus.PENDING,
                OrderGrantedRefundStatus.SUCCESS,
            ],
        )
        .first()
    )
    if existing is not None:
        return existing

    refund_amount = _resolve_refund_amount(order, amount)

    refund = OrderGrantedRefund.objects.create(
        order=order,
        amount_value=refund_amount,
        currency=order.currency,
        reason=reason or "",
        user=user,
        status=OrderGrantedRefundStatus.PENDING,
    )

    # Create the canonical Payment.
    from payment.canonical.services.service import PaymentService

    payment = PaymentService.create_payment(
        direction=Payment.Direction.DISBURSE,
        purpose=Payment.Purpose.REFUND,
        source_type="refund",
        source_id=str(refund.pk),
        source_reference=f"Refund for Order #{order.number}",
        payer=None,
        beneficiary=None,   # refund routes back through original instrument
        amount=refund_amount,
        currency=order.currency,
        idempotency_key=f"refund:{refund.pk}:payment",
        metadata={
            "order_id": str(order.pk),
            "order_number": order.number,
            "original_payment_id": (
                str(order.payment_id) if order.payment_id else None
            ),
            "refund_id": str(refund.pk),
        },
    )

    # Link refund → payment for lookup.
    refund.payment_id = payment.pk
    refund.save(update_fields=["payment_id", "updated_at"])

    OrderEvent.objects.create(
        order=order,
        type=OrderEvents.ORDER_REFUND_REQUESTED,
        user=user,
        parameters={
            "refund_id": str(refund.pk),
            "amount": str(refund_amount),
            "currency": order.currency,
        },
    )

    return refund


# =====================================================================
# EXECUTE REFUND
# =====================================================================


@transaction.atomic
def execute_refund_for_order(
    order: Order,
    *,
    provider: str,
    route_type: str = "univa_internal",
    idempotency_key: Optional[str] = None,
) -> Payment:
    """
    Create and enqueue a PaymentExecution for the order's refund Payment.

    Assumes `create_refund_for_order` has already been called.
    """
    refund = _get_active_refund(order)
    if refund is None:
        raise RefundError(
            f"Order {order.pk} has no refund to execute."
        )

    payment = _get_refund_payment(refund)
    if payment is None:
        raise RefundError(
            f"Refund {refund.pk} has no canonical Payment."
        )

    from payment.canonical.services.execution import (
        PaymentExecutionService,
    )

    execution = PaymentExecutionService.create_execution(
        payment=payment,
        route_type=route_type,
        provider=provider,
        idempotency_key=(
            idempotency_key
            or f"refund:{refund.pk}:execution:{timezone.now().timestamp()}"
        ),
        metadata={
            "order_id": str(order.pk),
            "refund_id": str(refund.pk),
        },
    )

    from ecommerce.tasks.payment import execute_order_payment_task

    execute_order_payment_task.delay(str(execution.pk))

    return payment


# =====================================================================
# LOOKUP HELPERS
# =====================================================================


def _get_active_refund(order: Order) -> Optional[OrderGrantedRefund]:
    return (
        OrderGrantedRefund.objects
        .filter(
            order=order,
            status=OrderGrantedRefundStatus.PENDING,
        )
        .order_by("-created_at")
        .first()
    )


def _get_refund_payment(
    refund: OrderGrantedRefund,
) -> Optional[Payment]:
    if not refund.payment_id:
        return None
    return Payment.objects.filter(pk=refund.payment_id).first()


# =====================================================================
# VALIDATION
# =====================================================================


def _validate_refundable(order: Order) -> None:
    if order.charge_status != "full":
        raise OrderNotRefundable(
            f"Cannot refund an order with charge_status="
            f"{order.charge_status!r}."
        )

    if order.total_charged_amount <= Decimal("0"):
        raise OrderNotRefundable(
            "Order has no charged amount to refund."
        )


def _resolve_refund_amount(
    order: Order,
    amount: Optional[Decimal],
) -> Decimal:
    max_refundable = _quantize(order.total_charged_amount)

    if amount is None:
        return max_refundable

    requested = _quantize(amount)

    if requested <= Decimal("0"):
        raise RefundAmountInvalid("Refund amount must be positive.")

    if requested > max_refundable:
        raise RefundAmountInvalid(
            f"Refund amount {requested} exceeds charged amount "
            f"{max_refundable}."
        )

    return requested


__all__ = [
    "RefundError",
    "OrderNotRefundable",
    "RefundAmountInvalid",
    "create_refund_for_order",
    "execute_refund_for_order",
]