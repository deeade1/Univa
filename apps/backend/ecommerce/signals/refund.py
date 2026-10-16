# ecommerce/signals/refund.py — full file

"""
Refund ↔ Payment synchronization.

Subscribes to PaymentExecution state changes for refund Payments and
updates the linked OrderGrantedRefund.status.

The payment app has no knowledge of refunds. It emits PaymentExecution
save signals. This module interprets them.
"""

from __future__ import annotations

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver


logger = logging.getLogger(__name__)


@receiver(post_save, sender="payment_canonical.PaymentExecution")
def sync_refund_from_payment_execution(
    sender, instance, created, **kwargs
):
    """
    When a refund's PaymentExecution reaches a terminal state, update
    the OrderGrantedRefund.status accordingly.
    """
    from payment.canonical.models import PaymentExecution
    from ecommerce.models.enums import OrderGrantedRefundStatus
    from ecommerce.models.order import OrderGrantedRefund

    payment = instance.payment
    if payment is None:
        return

    if payment.source_type != "refund":
        return

    # `Payment.source_id` is a CharField; OrderGrantedRefund.pk is an
    # integer. Coerce explicitly and bail on malformed values so a bad
    # row can never crash the PaymentExecution save path.
    try:
        refund_id = int(payment.source_id)
    except (TypeError, ValueError):
        logger.warning(
            "Refund Payment %s has non-numeric source_id=%r; "
            "skipping refund status sync.",
            payment.pk,
            payment.source_id,
        )
        return

    refund = OrderGrantedRefund.objects.filter(pk=refund_id).first()
    if refund is None:
        return

    new_status = None

    if instance.status == PaymentExecution.Status.COMPLETED:
        new_status = OrderGrantedRefundStatus.SUCCESS
    elif instance.status == PaymentExecution.Status.FAILED:
        new_status = OrderGrantedRefundStatus.FAILURE
    elif instance.status == PaymentExecution.Status.PENDING:
        new_status = OrderGrantedRefundStatus.PENDING

    if new_status is None:
        return

    if refund.status == new_status:
        return

    refund.status = new_status
    refund.save(update_fields=["status", "updated_at"])

    # ------------------------------------------------------------------
    # Emit a customer-facing order event on successful refund.
    #
    # This is what the notifications bridge maps to ORDER.REFUNDED.
    # We emit an OrderEvent (the immutable order-history record) rather
    # than calling the notification emitter directly, so audit + admin
    # views also see the refund.
    # ------------------------------------------------------------------

    if new_status == OrderGrantedRefundStatus.SUCCESS:
        _emit_refund_completed_order_event(refund)


def _emit_refund_completed_order_event(refund) -> None:
    """
    Write an OrderEvent(PAYMENT_REFUNDED) for the completed refund.

    Idempotent: refuses to write a duplicate PAYMENT_REFUNDED event
    for the same refund.
    """
    from ecommerce.models.enums import OrderEvents
    from ecommerce.models.order import OrderEvent

    # Idempotency: only one PAYMENT_REFUNDED event per refund_id.
    existing = OrderEvent.objects.filter(
        order=refund.order,
        type=OrderEvents.PAYMENT_REFUNDED,
        parameters__refund_id=str(refund.pk),
    ).exists()
    if existing:
        return

    OrderEvent.objects.create(
        order=refund.order,
        type=OrderEvents.PAYMENT_REFUNDED,
        parameters={
            "refund_id": str(refund.pk),
            "amount": str(refund.amount_value),
            "currency": refund.currency,
        },
    )