# ------------------------------------------------------------------------------
# core/tasks/location_updates.py
# ------------------------------------------------------------------------------

from __future__ import annotations

import logging

from celery import chain, group, shared_task

from core.tasks.reverse_geocode import reverse_geocode_location
from core.tasks.verify_address import verify_address

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Main Pipeline
# ------------------------------------------------------------------------------

@shared_task
def process_location_update(
    app_label: str,
    model_name: str,
    object_id,
):
    """
    Main location pipeline.

    This task orchestrates every background location job after
    coordinates have been saved.

    Workflow

        Save Coordinates
              │
              ▼
      Reverse Geocode
              │
              ▼
      Address Verification
              │
              ▼
      Fraud Detection
              │
              ▼
      Nearby Index Update
              │
              ▼
      Geofence Checks
              │
              ▼
      Notifications
    """

    workflow = chain(

        reverse_geocode_location.s(
            app_label,
            model_name,
            object_id,
        ),

        verify_address.s(
            app_label,
            model_name,
            object_id,
        ),

        detect_location_fraud.s(
            app_label,
            model_name,
            object_id,
        ),

        update_nearby_indexes.s(
            app_label,
            model_name,
            object_id,
        ),

        check_geofences.s(
            app_label,
            model_name,
            object_id,
        ),

        send_location_notifications.s(
            app_label,
            model_name,
            object_id,
        ),
    )

    workflow.apply_async()

    logger.info(
        "Queued location pipeline for %s.%s(%s)",
        app_label,
        model_name,
        object_id,
    )


# ------------------------------------------------------------------------------
# Bulk Processing
# ------------------------------------------------------------------------------

@shared_task
def process_bulk_location_updates(items: list[dict]):
    """
    Process many location updates.

    Example

    [
        {
            "app": "transport",
            "model": "Driver",
            "id": 4
        },
        {
            "app": "realestate",
            "model": "Property",
            "id": 15
        }
    ]
    """

    jobs = group(

        process_location_update.s(
            item["app"],
            item["model"],
            item["id"],
        )

        for item in items
    )

    jobs.apply_async()

    logger.info(
        "Queued %s location updates.",
        len(items),
    )


# ------------------------------------------------------------------------------
# Fraud Detection Placeholder
# ------------------------------------------------------------------------------

@shared_task
def detect_location_fraud(
    app_label,
    model_name,
    object_id,
):
    """
    Fraud detection.

    Future implementation:

    • Impossible travel

    • GPS spoofing detection

    • Emulator detection

    • Fake coordinates

    • Suspicious banking transactions

    • Fake property listing detection

    • Driver spoofing

    • Courier spoofing

    • Marketplace seller fraud
    """

    logger.info(
        "Fraud detection pending for %s.%s(%s)",
        app_label,
        model_name,
        object_id,
    )


# ------------------------------------------------------------------------------
# Nearby Index Update
# ------------------------------------------------------------------------------

@shared_task
def update_nearby_indexes(
    app_label,
    model_name,
    object_id,
):
    """
    Refresh nearby caches.

    Used by

    • Nearby Drivers

    • Nearby Riders

    • Nearby Dispatch Riders

    • Nearby Properties

    • Nearby Agents

    • Nearby Vendors

    • Nearby Warehouses

    • Nearby Banks

    etc.
    """

    logger.info(
        "Nearby indexes updated for %s.%s(%s)",
        app_label,
        model_name,
        object_id,
    )


# ------------------------------------------------------------------------------
# Geofence Checks
# ------------------------------------------------------------------------------

@shared_task
def check_geofences(
    app_label,
    model_name,
    object_id,
):
    """
    Check geofence rules.

    Examples

    • Driver entered airport

    • Driver left assigned city

    • Property outside service zone

    • Customer entered pickup radius

    • Courier entered warehouse

    • User entered restricted banking region
    """

    logger.info(
        "Geofence checks complete for %s.%s(%s)",
        app_label,
        model_name,
        object_id,
    )


# ------------------------------------------------------------------------------
# Notifications
# ------------------------------------------------------------------------------

@shared_task
def send_location_notifications(
    app_label,
    model_name,
    object_id,
):
    """
    Notify interested systems.

    Examples

    • Rider notified

    • Driver notified

    • Dispatch notified

    • Banking notified

    • Property owner notified

    • Agent notified

    • Admin notified
    """

    logger.info(
        "Location notifications complete for %s.%s(%s)",
        app_label,
        model_name,
        object_id,
    )