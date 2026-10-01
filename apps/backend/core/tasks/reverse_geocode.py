# ------------------------------------------------------------------------------
# core/tasks/reverse_geocode.py
# ------------------------------------------------------------------------------

from __future__ import annotations

import logging

from celery import shared_task
from django.apps import apps
from django.db import transaction

from core.services.geocoding import reverse_geocode

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Reverse Geocode Task
# ------------------------------------------------------------------------------

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 5},
)
def reverse_geocode_location(
    self,
    app_label: str,
    model_name: str,
    object_id,
):
    """
    Reverse geocode any LocationModel subclass.

    Example:

        reverse_geocode_location.delay(
            "transport",
            "Trip",
            trip.id,
        )

        reverse_geocode_location.delay(
            "realestate",
            "Property",
            property.id,
        )

        reverse_geocode_location.delay(
            "accounts",
            "Address",
            address.id,
        )
    """

    try:
        model = apps.get_model(app_label, model_name)

    except LookupError:
        logger.error(
            "Model %s.%s not found",
            app_label,
            model_name,
        )
        return

    try:
        obj = model.objects.get(pk=object_id)

    except model.DoesNotExist:
        logger.warning(
            "%s.%s(%s) no longer exists.",
            app_label,
            model_name,
            object_id,
        )
        return

    if not obj.latitude or not obj.longitude:
        logger.warning(
            "%s.%s(%s) has no coordinates.",
            app_label,
            model_name,
            object_id,
        )
        return

    result = reverse_geocode(
        obj.latitude,
        obj.longitude,
    )

    if result is None:
        logger.warning(
            "Reverse geocoding failed for %s.%s(%s)",
            app_label,
            model_name,
            object_id,
        )
        return

    with transaction.atomic():

        # Human-readable address
        if hasattr(obj, "location"):
            obj.location = result["address"]

        # Optional structured fields
        if hasattr(obj, "city"):
            obj.city = result.get("city")

        if hasattr(obj, "state"):
            obj.state = result.get("state")

        if hasattr(obj, "country"):
            obj.country = result.get("country")

        if hasattr(obj, "postal_code"):
            obj.postal_code = result.get("postal_code")

        obj.save(
            update_fields=[
                field
                for field in [
                    "location",
                    "city",
                    "state",
                    "country",
                    "postal_code",
                ]
                if hasattr(obj, field)
            ]
        )

    logger.info(
        "Reverse geocoded %s.%s(%s)",
        app_label,
        model_name,
        object_id,
    )