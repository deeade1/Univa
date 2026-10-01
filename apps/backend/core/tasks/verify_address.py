# ------------------------------------------------------------------------------
# core/tasks/verify_address.py
# ------------------------------------------------------------------------------

from __future__ import annotations

import logging

from celery import shared_task
from django.apps import apps
from django.db import transaction

from core.services.address_verification import full_verification

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 5},
)
def verify_address_task(
    self,
    app_label: str,
    model_name: str,
    object_id,
):
    """
    Verify the address of any LocationModel subclass.

    Example
    -------

    verify_address.delay(
        "realestate",
        "Property",
        property.id,
    )

    verify_address.delay(
        "banking",
        "CustomerProfile",
        profile.id,
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
            "%s.%s(%s) no longer exists",
            app_label,
            model_name,
            object_id,
        )
        return

    if not obj.latitude or not obj.longitude:
        logger.warning(
            "%s.%s(%s) has no coordinates",
            app_label,
            model_name,
            object_id,
        )
        return

    if not obj.location:
        logger.warning(
            "%s.%s(%s) has no address",
            app_label,
            model_name,
            object_id,
        )
        return

    report = full_verification(
        latitude=obj.latitude,
        longitude=obj.longitude,
        address=obj.location,
    )

    with transaction.atomic():

        if hasattr(obj, "address_verified"):
            obj.address_verified = report["verified"]

        if hasattr(obj, "verification_confidence"):
            obj.verification_confidence = report["confidence"]

        if hasattr(obj, "fraud_risk"):
            obj.fraud_risk = report["risk"]

        if hasattr(obj, "address_distance_km"):
            obj.address_distance_km = report["distance_km"]

        if hasattr(obj, "normalized_address"):
            obj.normalized_address = report["normalized_address"]

        update_fields = [
            field
            for field in [
                "address_verified",
                "verification_confidence",
                "fraud_risk",
                "address_distance_km",
                "normalized_address",
            ]
            if hasattr(obj, field)
        ]

        if update_fields:
            obj.save(update_fields=update_fields)

    logger.info(
        "Verified address for %s.%s(%s)",
        app_label,
        model_name,
        object_id,
    )