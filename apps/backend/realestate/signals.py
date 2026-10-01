# apps/backend/realestate/signals.py

"""
Real-estate domain signals.

Signals in this module are responsible for lightweight domain-side
reactions to model lifecycle events.

Important:
    Real-estate application relationships use domain entities such as
    Client and Agent rather than accounts.UserProfile.

    PropertyProximity.buyer -> realestate.Client
"""

from django.core.cache import cache
from django.db.models import Avg
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import (
    Listing,
    PropertyProximity,
    PropertyRating,
)


# ---------------------------------------------------------------------------
# Property Rating
# ---------------------------------------------------------------------------

@receiver(post_save, sender=PropertyRating)
@receiver(post_delete, sender=PropertyRating)
def update_property_avg_rating(sender, instance, **kwargs):
    """
    Recalculate the property's average rating whenever a rating is
    created, updated, or deleted.
    """

    average = (
        PropertyRating.objects
        .filter(property=instance.property)
        .aggregate(avg=Avg("rating"))
        .get("avg")
    )

    if average is not None:
        instance.property.average_rating = round(average, 2)
    else:
        instance.property.average_rating = None

    instance.property.save(
        update_fields=["average_rating"],
    )


# ---------------------------------------------------------------------------
# Property Proximity
# ---------------------------------------------------------------------------

@receiver(post_save, sender=PropertyProximity)
def update_proximity_cache(sender, instance, created, **kwargs):
    """
    Invalidate cached recommendations when a newly calculated proximity
    falls inside the buyer's preferred location.

    PropertyProximity.buyer is a realestate.Client, not UserProfile.
    """

    if not created or not instance.is_in_preferred_location:
        return

    cache_key = f"recommendations_{instance.buyer_id}"

    cache.delete(cache_key)


# ---------------------------------------------------------------------------
# Listing Events
# ---------------------------------------------------------------------------

@receiver(post_save, sender=Listing)
def handle_listing_save(sender, instance, created, **kwargs):
    """
    Broadcast listing creation/update events.

    GraphQL subscription infrastructure is imported lazily to avoid
    unnecessary import-time coupling and circular-import problems.
    """

    from graphq.realestate.subscriptions import RealestateSubscriptions

    event = "listing_created" if created else "listing_updated"

    RealestateSubscriptions.broadcast_sync(
        group=event,
        payload={
            "event": event,
            "data": instance,
        },
    )


@receiver(post_delete, sender=Listing)
def handle_listing_delete(sender, instance, **kwargs):
    """
    Broadcast listing deletion events.
    """

    from graphq.realestate.subscriptions import RealestateSubscriptions

    RealestateSubscriptions.broadcast_sync(
        group="listing_deleted",
        payload={
            "event": "listing_deleted",
            "data": instance,
        },
    )

