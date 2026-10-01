
# ============================================================================
# SIGNALS
# ============================================================================

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Stock)
def stock_post_save(sender, instance, created, **kwargs):
    """Handle stock post-save actions."""
    if created:
        logger.info(f"Stock created: {instance.product_variant.sku} - {instance.warehouse.name}")
    elif instance.quantity <= instance.low_stock_threshold:
        logger.warning(
            f"Low stock alert: {instance.product_variant.sku} "
            f"at {instance.warehouse.name} - {instance.quantity} remaining"
        )


@receiver(post_delete, sender=Stock)
def stock_post_delete(sender, instance, **kwargs):
    """Handle stock post-delete actions."""
    logger.info(f"Stock deleted: {instance.product_variant.sku} - {instance.warehouse.name}")