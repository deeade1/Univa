# ecommerce/services/order/payment.py

"""
Bridge between the ecommerce Order and the canonical Payment primitive.

Architectural boundary
----------------------

Ecommerce depends on payment_canonical. Payment does not know about
ecommerce.

This module:

    - creates a canonical Payment for an Order
    - creates PaymentExecution records for provider attempts
    - enqueues async execution via Celery

This module does NOT:

    - implement provider-specific logic
    - call ProviderAdapter.initiate() directly
    - mutate PaymentExecution state
    - perform reconciliation
    - import Payment internals beyond the public model API

Execution is owned by ExecutionOrchestrator in payment_canonical.
The signal-based bridge back to Order state lives in
`ecommerce/signals/payment.py`.
"""

from __future__ import annotations

import logging

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from django.db import transaction
from django.utils import timezone

from ecommerce.models.order import Order
from payment.canonical.models import (
    Payment,
    PaymentExecution,
)


logger = logging.getLogger(__name__)


# =====================================================================
# ERRORS
# =====================================================================



class OrderPaymentError(Exception):
    """Base error for order payment operations."""


class PaymentAlreadyExists(OrderPaymentError):
    """Raised when attempting to create a payment for an order that has one."""


# =====================================================================
# CREATE PAYMENT
# =====================================================================
# =====================================================================
# PRECISION CONVERSION
# =====================================================================


def _quantize_for_payment(amount: Decimal) -> Decimal:
    """
    Normalize an ecommerce money amount to payment precision (2 dp).

    Ecommerce uses DEFAULT_DECIMAL_PLACES (typically 3) to support
    weighted quantities like "2.5 kg of beef". The canonical Payment
    uses 2 dp — standard currency precision.

    This conversion happens ONLY at the ecommerce → payment boundary.
    Inside ecommerce, amounts stay at their native precision. Inside
    payment, amounts stay at currency precision. The bridge translates.
    """
    if amount is None:
        return None
    return Decimal(amount).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

@transaction.atomic
def create_payment_for_order(
    order: Order,
    *,
    source_reference: Optional[str] = None,
) -> Payment:
    """
    Create a canonical Payment linked to this order.

    Idempotent: if the order already has a payment (payment_id set),
    returns the existing Payment.

    The Payment is created in PENDING state. Execution happens later,
    asynchronously.

    The Payment's idempotency_key is derived from the order number
    so a retried checkoutComplete for the same order produces the
    same Payment.
    """
    from payment.canonical.services.service import PaymentService

    # Idempotent: return existing if present.
    if order.payment_id:
        existing = Payment.objects.filter(pk=order.payment_id).first()
        if existing is not None:
            return existing

    idempotency_key = f"order:{order.pk}:payment"

    payment = PaymentService.create_payment(
        direction=Payment.Direction.RECEIVE,
        purpose=Payment.Purpose.CHECKOUT,
        source_type="order",
        source_id=str(order.pk),
        source_reference=source_reference or f"Order #{order.number}",
        payer=order.user,
        beneficiary=None,
        amount=_quantize_for_payment(order.total_gross_amount),
        currency=order.currency,
        idempotency_key=idempotency_key,
        metadata={
            "order_id": str(order.pk),
            "order_number": order.number,
            "channel_slug": order.channel.slug if order.channel_id else None,
            "user_email": order.user_email,
        },
    )

    order.payment_id = payment.pk
    order.save(update_fields=["payment_id", "updated_at"])

    return payment


# =====================================================================
# CREATE EXECUTION
# =====================================================================


@transaction.atomic
def create_execution_for_order_payment(
    order: Order,
    *,
    provider: str,
    route_type: str,
    instrument=None,
    idempotency_key: Optional[str] = None,
) -> PaymentExecution:
    """
    Create a PaymentExecution for the order's Payment and enqueue
    its async provider execution.

    Assumes `create_payment_for_order` has already run.
    """
    from payment.canonical.services.execution import (
        PaymentExecutionService,
    )

    payment = get_order_payment(order)
    if payment is None:
        raise OrderPaymentError(
            f"Order {order.pk} has no payment to execute against."
        )

    exec_idempotency_key = (
        idempotency_key
        or f"order:{order.pk}:execution:{timezone.now().timestamp()}"
    )

    execution = PaymentExecutionService.create_execution(
        payment=payment,
        route_type=route_type,
        provider=provider,
        idempotency_key=exec_idempotency_key,
        instrument=instrument,
        metadata={
            "order_id": str(order.pk),
            "order_number": order.number,
        },
    )

    # Enqueue the provider call. The orchestrator owns the actual
    # ExecutionOrchestrator.execute() invocation.
    from ecommerce.tasks.payment import execute_order_payment_task

    execute_order_payment_task.delay(str(execution.pk))

    return execution


# =====================================================================
# LOOKUP HELPERS
# =====================================================================


def get_order_payment(order: Order) -> Optional[Payment]:
    """
    Return the canonical Payment attached to this order, or None.
    """
    if not order.payment_id:
        return None

    return Payment.objects.filter(pk=order.payment_id).first()


def get_order_payment_executions(order: Order):
    """
    Return all PaymentExecution records for the order's Payment.
    """
    payment = get_order_payment(order)
    if payment is None:
        return PaymentExecution.objects.none()

    return PaymentExecution.objects.filter(payment=payment)


__all__ = [
    "OrderPaymentError",
    "PaymentAlreadyExists",
    "create_payment_for_order",
    "create_execution_for_order_payment",
    "get_order_payment",
    "get_order_payment_executions",
]