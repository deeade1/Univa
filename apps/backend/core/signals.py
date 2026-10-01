# ------------------------------------------------------------------------------
# apps/backend/core/signals.py
# ------------------------------------------------------------------------------

"""
Reusable Location Signals.

Purpose
-------
Provides automatic location processing for every model that inherits
LocationModel.

Features
--------
✓ Creates PointField automatically
✓ Schedules reverse geocoding (configurable)
✓ Schedules address verification (configurable)
✓ Broadcasts GraphQL location updates
✓ Detects coordinate changes
✓ Prevents unnecessary Celery jobs
✓ Executes background work only after database commit

Supported Applications
----------------------
• Accounts
• Banking
• Transport
• Logistics
• Marketplace
• Real Estate
• Warehouse
• Social
"""

import logging

from django.contrib.gis.geos import Point
from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from graphq.core.subscriptions.location_subscriptions import (
    LocationUpdatedSubscription,
)
from core.models.location import LocationModel
from core.tasks.reverse_geocode import reverse_geocode_location
from core.tasks.verify_address import verify_address_task

logger = logging.getLogger(__name__)


# ==============================================================================
# Helpers
# ==============================================================================


def _coordinates_changed(instance):
    """
    Returns True if latitude or longitude changed.
    """

    if instance.pk is None:
        return True

    try:
        previous = (
            instance.__class__.objects.only(
                "latitude",
                "longitude",
            ).get(pk=instance.pk)
        )

        return (
            previous.latitude != instance.latitude
            or previous.longitude != instance.longitude
        )

    except instance.__class__.DoesNotExist:
        return True


def _supports_address_verification(instance):
    """
    Returns whether this model requires address verification.

    Example:

        class Property(LocationModel):
            VERIFY_ADDRESS = True

        class Warehouse(LocationModel):
            VERIFY_ADDRESS = True

        class Vehicle(LocationModel):
            VERIFY_ADDRESS = False
    """

    return getattr(instance, "VERIFY_ADDRESS", False)


def _supports_reverse_geocoding(instance):
    """
    Returns whether reverse geocoding should be performed.

    Default = True
    """

    return getattr(instance, "REVERSE_GEOCODE", True)


def _supports_location_broadcast(instance):
    """
    Returns whether live GraphQL updates should be broadcast.

    Default = True
    """

    return getattr(instance, "BROADCAST_LOCATION", True)


def _should_process_location(instance, created):
    """
    Determines whether location processing should occur.
    """

    if instance.latitude is None or instance.longitude is None:
        return False

    if not created and not _coordinates_changed(instance):
        return False

    return True


# ==============================================================================
# PRE SAVE
# ==============================================================================


@receiver(
    pre_save,
    dispatch_uid="core_location_pre_save",
)
def location_pre_save(sender, instance, **kwargs):
    """
    Automatically build PointField before saving.
    """

    if not isinstance(instance, LocationModel):
        return

    if instance.latitude is None or instance.longitude is None:
        return

    try:
        instance.location_point = Point(
            float(instance.longitude),
            float(instance.latitude),
            srid=4326,
        )

    except Exception:
        logger.exception(
            "Unable to build PointField for %s",
            instance._meta.label,
        )


# ==============================================================================
# POST SAVE
# ==============================================================================


@receiver(
    post_save,
    dispatch_uid="core_location_post_save",
)
def location_post_save(sender, instance, created, **kwargs):
    """
    Schedule background location processing.

    Coordinates are already persisted.

    Background Tasks
    ----------------
    • Reverse Geocoding
    • Address Verification

    Real-Time
    ---------
    • GraphQL Location Broadcast

    All background work is executed only after the database transaction
    successfully commits.
    """

    if not isinstance(instance, LocationModel):
        return

    if not _should_process_location(instance, created):
        return

    logger.info(
        "Processing location update for %s (%s)",
        instance._meta.label,
        instance.pk,
    )

    app_label = instance._meta.app_label
    model_name = instance._meta.model_name
    object_id = instance.pk
    latitude = float(instance.latitude)
    longitude = float(instance.longitude)

    # ----------------------------------------------------------------------
    # Execute after successful database commit
    # ----------------------------------------------------------------------

    def process_location():
        # --------------------------------------------------------------
        # Reverse Geocoding
        # --------------------------------------------------------------

        if _supports_reverse_geocoding(instance):
            logger.debug(
                "Scheduling reverse geocoding for %s (%s)",
                instance._meta.label,
                object_id,
            )

            reverse_geocode_location.delay(
                app_label=app_label,
                model_name=model_name,
                object_id=object_id,
                latitude=latitude,
                longitude=longitude,
            )

        # --------------------------------------------------------------
        # Address Verification
        # --------------------------------------------------------------

        if _supports_address_verification(instance):
            logger.debug(
                "Scheduling address verification for %s (%s)",
                instance._meta.label,
                object_id,
            )

            verify_address_task.delay(
                app_label=app_label,
                model_name=model_name,
                object_id=object_id,
            )

        # --------------------------------------------------------------
        # GraphQL Subscription
        # --------------------------------------------------------------

        if _supports_location_broadcast(instance):
            try:
                LocationUpdatedSubscription.trigger(instance)

                logger.debug(
                    "Broadcasted location update for %s (%s)",
                    instance._meta.label,
                    object_id,
                )

            except Exception:
                logger.exception(
                    "Failed broadcasting location update for %s (%s)",
                    instance._meta.label,
                    object_id,
                )

    transaction.on_commit(process_location)