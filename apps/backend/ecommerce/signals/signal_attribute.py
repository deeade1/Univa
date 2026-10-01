
# =============================================================================
# SIGNALS
# =============================================================================

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


@receiver(post_save, sender=Attribute)
def attribute_post_save(sender, instance, created, **kwargs):
    """Handle attribute post-save actions."""
    if created:
        logger.info(f"Attribute created: {instance.name} (ID: {instance.id})")


@receiver(post_delete, sender=Attribute)
def attribute_post_delete(sender, instance, **kwargs):
    """Handle attribute post-delete actions."""
    logger.info(f"Attribute deleted: {instance.name} (ID: {instance.id})")


@receiver(post_save, sender=AttributeValue)
def attribute_value_post_save(sender, instance, created, **kwargs):
    """Handle attribute value post-save actions."""
    if created:
        logger.info(f"Attribute value created: {instance.name} (ID: {instance.id})")