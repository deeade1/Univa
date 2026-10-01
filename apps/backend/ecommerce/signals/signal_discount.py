
# =============================================================================
# SIGNALS
# =============================================================================

from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver


@receiver(post_save, sender=Promotion)
def promotion_post_save(sender, instance, created, **kwargs):
    """Handle promotion post-save actions."""
    if created:
        logger.info(f"Promotion created: {instance.name} (ID: {instance.id})")


@receiver(post_delete, sender=Promotion)
def promotion_post_delete(sender, instance, **kwargs):
    """Handle promotion post-delete actions."""
    logger.info(f"Promotion deleted: {instance.name} (ID: {instance.id})")


@receiver(post_save, sender=Voucher)
def voucher_post_save(sender, instance, created, **kwargs):
    """Handle voucher post-save actions."""
    if created:
        logger.info(f"Voucher created: {instance.name or instance.code} (ID: {instance.id})")