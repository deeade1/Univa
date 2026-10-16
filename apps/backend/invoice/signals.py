# apps/backend/invoice/signals.py

"""
Signal bridges for InvoiceEvent.

Notifications do not live on the Invoice model. Instead, a
post_save receiver picks up InvoiceEvent rows and dispatches
to the notification system.

This mirrors the OrderEvent bridge in ecommerce.
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from notifications.events import constants as notification_constants
from notifications.events.emitter import emit_notification_event

from invoice.enums import InvoiceEventType
from invoice.models import InvoiceEvent


logger = logging.getLogger(__name__)


# Mapping of InvoiceEventType -> registered notification event
# identifier. Each identifier must be present in both
# notifications.events.constants.ALL_EVENT_TYPES and
# notifications.events.registry.EVENT_REGISTRY.
_NOTIFICATION_EVENT_MAP = {
    InvoiceEventType.SENT: notification_constants.INVOICE_SENT,
    InvoiceEventType.PAID: notification_constants.INVOICE_PAID,
    InvoiceEventType.OVERDUE: notification_constants.INVOICE_OVERDUE,
    InvoiceEventType.CANCELLED: notification_constants.INVOICE_CANCELLED,
    InvoiceEventType.VOIDED: notification_constants.INVOICE_VOIDED,
    InvoiceEventType.REFUNDED: notification_constants.INVOICE_REFUNDED,
}


@receiver(
    post_save,
    sender=InvoiceEvent,
    dispatch_uid="invoice.event_notification_bridge",
)
def invoice_event_notification_bridge(sender, instance, created, **kwargs):
    if not created:
        return

    notification_event_type = _NOTIFICATION_EVENT_MAP.get(instance.type)
    if notification_event_type is None:
        return

    invoice = instance.invoice

    try:
        emit_notification_event(
            event_type=notification_event_type,
            module="invoice",
            actor=instance.actor,
            object_type="Invoice",
            object_id=str(invoice.pk),
            payload={
                "invoice_id": str(invoice.pk),
                "invoice_number": invoice.number,
                "recipient_id": str(invoice.recipient_id),
                "recipient_name": invoice.recipient.name,
                "recipient_email": invoice.recipient.email,
                "total_amount": str(invoice.total_amount),
                "balance_due": str(invoice.balance_due),
                "currency": invoice.currency,
                "status": invoice.status,
                "due_date": (
                    str(invoice.due_date) if invoice.due_date else None
                ),
                **(instance.parameters or {}),
            },
        )
    except Exception:
        logger.exception(
            "Failed to dispatch notification for invoice event %s",
            instance.pk,
        )