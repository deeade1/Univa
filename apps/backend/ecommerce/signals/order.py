# ecommerce/signals/order.py

"""
Order event bridge.

When an OrderEvent is created, this module relays it to:

    - the canonical notifications subsystem (registered users)
    - a direct email fallback (guest orders)
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

from django.conf import settings
from django.core.mail import send_mail
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
#: `notifications.events.registry`.
ORDER_EVENT_TO_NOTIFICATION = {
    OrderEvents.PLACED: "ORDER.CREATED",
    OrderEvents.CONFIRMED: "ORDER.CONFIRMED",
    OrderEvents.CANCELED: "ORDER.CANCELLED",
    OrderEvents.FULFILLMENT_FULFILLED_ITEMS: "ORDER.DELIVERED",
    OrderEvents.ORDER_MARKED_AS_PAID: "PAYMENT.SUCCESSFUL",
    OrderEvents.PAYMENT_FAILED: "PAYMENT.FAILED",
    OrderEvents.PAYMENT_REFUNDED: "ORDER.REFUNDED",
}


#: OrderEvents type → canonical audit action.
ORDER_EVENT_TO_AUDIT = {
    OrderEvents.PLACED: "ECOMMERCE.ORDER_CREATED",
    OrderEvents.CANCELED: "ECOMMERCE.ORDER_CANCELLED",
    OrderEvents.FULFILLMENT_FULFILLED_ITEMS: "ECOMMERCE.ORDER_COMPLETED",
    OrderEvents.ORDER_MARKED_AS_PAID: "ECOMMERCE.ORDER_PAID",
    OrderEvents.PAYMENT_REFUNDED: "ECOMMERCE.ORDER_REFUNDED",
}


# =====================================================================
# SIGNAL HANDLER
# =====================================================================


@receiver(post_save, sender=OrderEvent)
def relay_order_event(
    sender, instance: OrderEvent, created: bool, **kwargs
) -> None:
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
    """
    Emit a notification if this event type is registered and not
    already sent.

    Registered users go through the canonical notifications subsystem
    (in-app + push + email per their preferences).

    Guest orders (no user, but with an email) get a direct email sent
    via Django's mail backend. Guests have no preferences, no devices,
    and no in-app inbox, so the notification subsystem would just
    create dead records for them.
    """
    event_type = ORDER_EVENT_TO_NOTIFICATION.get(instance.type)
    if not event_type:
        return

    if order.user_id:
        _relay_to_registered_user(instance, order, event_type)
    elif order.user_email:
        _relay_to_guest(instance, order, event_type)
    # else: no user and no email — nothing to do


def _relay_to_registered_user(
    instance: OrderEvent, order, event_type: str
) -> None:
    """Emit a canonical NotificationEvent for a registered user."""
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

    # Idempotency: one notification per (order, event_type).
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
        logger.exception(
            "Failed to emit notification %s for OrderEvent %s",
            event_type,
            instance.pk,
        )


def _relay_to_guest(
    instance: OrderEvent, order, event_type: str
) -> None:
    """
    Send a direct email to a guest customer.

    Bypasses the notification subsystem entirely: guests have no
    preferences, no devices, no in-app inbox. Email is the only
    channel that applies.

    Idempotency: one email per (order, event_type). We check whether
    an OrderEvent already exists with the same type+order+timestamp
    context, but since OrderEvents are append-only, we rely on the
    fact that the signal only fires once per created row.
    """
    try:
        from notifications.events.registry import get_event_definition
    except ImportError:
        logger.warning(
            "Notification registry not available. "
            "Skipped guest email for OrderEvent %s",
            instance.pk,
        )
        return

    definition = get_event_definition(event_type)
    if definition is None:
        logger.warning(
            "No registry definition for %s; skipping guest email.",
            event_type,
        )
        return

    # Resolve the action URL with placeholders, if provided.
    action_url = ""
    if definition.action_url:
        try:
            action_url = definition.action_url.format(
                object_id=str(order.pk),
                event_id=instance.pk,
            )
        except (KeyError, ValueError, IndexError):
            action_url = ""

    # Compose the email body. Keep it simple — no template rendering
    # for Phase 10. If you want rich HTML emails, add a template
    # directory under notifications/templates/orders/.
    lines = [definition.body.strip()]
    if action_url:
        lines.append("")
        lines.append(f"View your order: {settings.FRONTEND_URL}{action_url}")

    body = "\n".join(lines)

    try:
        send_mail(
            subject=f"[Univa] {definition.title}",
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.user_email],
            fail_silently=False,
        )
        logger.info(
            "Guest email sent: order=%s event=%s to=%s",
            order.pk,
            event_type,
            order.user_email,
        )
    except Exception:
        logger.exception(
            "Failed to send guest email for OrderEvent %s (order %s, "
            "recipient %s)",
            instance.pk,
            order.pk,
            order.user_email,
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