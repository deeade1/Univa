# ecommerce/signals/payment.py

"""
Order ↔ Payment synchronization.

Subscribes to PaymentExecution state changes and updates the linked
Order's charge_status. Payment does not know about ecommerce; it
just emits standard Django save signals.
"""

from __future__ import annotations

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver


logger = logging.getLogger(__name__)


@receiver(post_save, sender="payment_canonical.PaymentExecution")
def sync_order_charge_status_from_execution(
    sender, instance, created, **kwargs
):
    """
    When a PaymentExecution reaches COMPLETED, propagate to Order.
    """
    from payment.canonical.models import PaymentExecution

    if instance.status != PaymentExecution.Status.COMPLETED:
        return

    payment = instance.payment
    if payment is None:
        return

    from ecommerce.models.order import Order
    order = Order.objects.filter(payment_id=payment.pk).first()
    if order is None:
        return

    if order.charge_status == "full":
        return

    from ecommerce.services.order.lifecycle import mark_order_as_paid

    try:
        mark_order_as_paid(
            order,
            payment_reference=payment.reference,
            user=None,
        )
    except Exception:
        logger.exception(
            "Failed to mark Order %s as paid after PaymentExecution %s.",
            order.pk,
            instance.pk,
        )
        
@receiver(post_save, sender="payment_canonical.PaymentExecution")
def notify_on_payment_execution_failure(
    sender, instance, created, **kwargs
):
    """
    When a payment execution fails, write an OrderEvent(PAYMENT_FAILED)
    so the order history and notifications both reflect it.

    Only fires for order-source payments. Refund-source payments are
    handled in ecommerce/signals/refund.py.
    """
    from payment.canonical.models import PaymentExecution
    from ecommerce.models.enums import OrderEvents
    from ecommerce.models.order import Order, OrderEvent

    if instance.status != PaymentExecution.Status.FAILED:
        return

    payment = instance.payment
    if payment is None:
        return

    if payment.source_type != "order":
        return

    order = Order.objects.filter(payment_id=payment.pk).first()
    if order is None:
        return

    # Idempotency: one PAYMENT_FAILED event per execution.
    if OrderEvent.objects.filter(
        order=order,
        type=OrderEvents.PAYMENT_FAILED,
        parameters__execution_id=str(instance.pk),
    ).exists():
        return

    OrderEvent.objects.create(
        order=order,
        type=OrderEvents.PAYMENT_FAILED,
        parameters={
            "execution_id": str(instance.pk),
            "failure_code": instance.failure_code or "",
            "failure_reason": instance.failure_reason or "",
        },
    )