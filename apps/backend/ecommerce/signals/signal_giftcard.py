# ecommerce/signals/signal_giftcard.py

"""
Signal handlers for GiftCard lifecycle events.
"""

import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from ecommerce.models.constants import GiftCardEvents
from ecommerce.models.giftcard import GiftCard, GiftCardEvent


logger = logging.getLogger(__name__)


@receiver(pre_save, sender=GiftCard)
def gift_card_pre_save(sender, instance, **kwargs):
    """Handle gift card pre-save actions."""
    if not instance.pk:
        return

    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    if old.status != instance.status:
        logger.info(
            "Gift card %s status changed from %s to %s",
            instance.code,
            old.status,
            instance.status,
        )


@receiver(post_save, sender=GiftCard)
def gift_card_post_save(sender, instance, created, **kwargs):
    """Handle gift card post-save actions."""
    if not created:
        return

    logger.info(
        "Gift card created: %s (ID: %s)",
        instance.code,
        instance.id,
    )

    try:
        GiftCardEvent.log_event(
            gift_card=instance,
            event_type=GiftCardEvents.ISSUED,
            user=instance.created_by,
            amount=instance.initial_balance_amount,
            previous_balance=0,
            new_balance=instance.initial_balance_amount,
            parameters={
                "created_by_email": instance.created_by_email,
                "currency": instance.currency,
            },
        )
    except Exception:
        logger.exception(
            "Failed to log GiftCardEvent for gift card %s",
            instance.code,
        )