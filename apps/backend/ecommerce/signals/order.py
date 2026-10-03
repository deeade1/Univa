# ecommerce/signals/order.py

"""
Order event bridge.

When an OrderEvent is created, this module relays it to:

    - the canonical notifications subsystem (user-facing messages)
    - the canonical audit subsystem (compliance / security trail)

Both relays are:

    - idempotent (never emit a duplicate notification for the same
      order + event type combination)
    - exception-safe (a failure in notifications or audit MUST NOT
      affect order processing)
    - opt-in (only events explicitly listed in the mapping tables
      are relayed)

The OrderEvent itself remains the immutable order lifecycle record.
Notifications and audit are derived views of that record.
"""

from __future__ import annotations

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from ecommerce.models.enums import OrderEvents
from ecommerce.models.order import OrderEvent


logger = logging.getLogger(__name__)


# =====================================================================
# MAPPINGS
# =====================================================================


#: OrderEvents type → registered notification event_type.
#:
#: Only include event types that are registered in
#: `notifications.events.registry`. Unregistered event types are
#: rejected by the emitter and would raise NotificationEventError.
ORDER_EVENT_TO_NOTIFICATION = {
    OrderEvents.PLACED: "ORDER.CREATED",
    OrderEvents.CONFIRMED: "ORDER.CONFIRMED",
    OrderEvents.CANCELED: "ORDER.CANCELLED",
    OrderEvents.FULFILLMENT_FULFILLED_ITEMS: "ORDER.DELIVERED",
    OrderEvents.PAYMENT_REFUNDED: "ORDER.REFUNDED",
}


#: OrderEvents type → canonical audit action.
#:
#: Only include events that are compliance/security relevant.
#: Actions must exist in `audit.constants.AuditAction`.
ORDER_EVENT_TO_AUDIT = {
    OrderEvents.PLACED: "ECOMMERCE.ORDER_CREATED",
    OrderEvents.CANCELED: "ECOMMERCE.ORDER_CANCELLED",
    OrderEvents.FULFILLMENT_FULFILLED_ITEMS: "ECOMMERCE.ORDER_COMPLETED",
}


# =====================================================================
# SIGNAL HANDLER
# =====================================================================


@receiver(post_save, sender=OrderEvent)
def relay_order_event(sender, instance: OrderEvent, created: bool, **kwargs) -> None:
    """
    Relay a newly-created OrderEvent to notifications and audit.

    Only fires on creation. Updates to an existing OrderEvent do not
    trigger relays.
    """
    if not created:
        return

    order = instance.order

    _relay_to_notifications(instance, order)
    _relay_to_audit(instance, order)


# =====================================================================
# NOTIFICATIONS
# =====================================================================


def _relay_to_notifications(instance: OrderEvent, order) -> None:
    """Emit a notification if this event type is registered and not yet sent."""
    event_type = ORDER_EVENT_TO_NOTIFICATION.get(instance.type)
    if not event_type:
        return

    if not order.user_id:
        # Guest order — no one to notify.
        return

    try:
        from notifications.events import emit_notification_event
        from notifications.models.event import NotificationEvent
    except ImportError:
        logger.warning(
            "Notification subsystem not available. "
            "Skipped notification for OrderEvent %s",
            instance.pk,
        )
        return

    # Idempotency guard: one notification per (order, event_type).
    # This protects against the signal firing twice for the same event
    # (which can happen if the event row is re-saved after creation).
    if NotificationEvent.objects.filter(
        event_type=event_type,
        object_type="Order",
        object_id=str(order.pk),
    ).exists():
        return

    try:
        emit_notification_event(
            event_type=event_type,
            module="order",
            actor=instance.user,
            object_type="Order",
            object_id=str(order.pk),
            payload={
                "order_id": str(order.pk),
                "order_number": order.number,
                "recipient_id": order.user_id,
            },
        )
    except Exception:
        # Never let a notification failure break order processing.
        logger.exception(
            "Failed to emit notification %s for OrderEvent %s",
            event_type,
            instance.pk,
        )


# =====================================================================
# AUDIT
# =====================================================================


def _relay_to_audit(instance: OrderEvent, order) -> None:
    """Write an audit entry if this event type is audit-relevant."""
    audit_action = ORDER_EVENT_TO_AUDIT.get(instance.type)
    if not audit_action:
        return

    try:
        from audit.services.audit import audit
    except ImportError:
        logger.warning(
            "Audit subsystem not available. "
            "Skipped audit for OrderEvent %s",
            instance.pk,
        )
        return

    try:
        audit(
            action=audit_action,
            actor=instance.user,
            target_user=order.user,
            order_id=str(order.pk),
            order_number=order.number,
            order_event_id=str(instance.pk),
            order_event_type=instance.type,
            parameters=instance.parameters,
        )
    except Exception:
        logger.exception(
            "Failed to write audit %s for OrderEvent %s",
            audit_action,
            instance.pk,
        )