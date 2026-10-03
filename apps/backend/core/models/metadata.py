# core/models/metadata.py

from typing import Any

from django.contrib.postgres.indexes import GinIndex
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models import JSONField
from measurement.measures import Weight

from core.pricing.money import Money
from core.models.job_status import JobStatus


MONEY_TYPE = "Money"


class CustomJsonEncoder(DjangoJSONEncoder):
    """
    JSON encoder that knows how to serialize Money and Weight.

    Used by the metadata JSONFields on ModelWithMetadata so that
    metadata payloads can safely contain monetary and measurement
    values.
    """

    def default(self, obj):
        if isinstance(obj, Money):
            return {
                "_type": MONEY_TYPE,
                "amount": str(obj.amount),
                "currency": obj.currency,
            }
        if isinstance(obj, Weight):
            # Mirror django_measurement.MeasurementField's
            # value_to_string behaviour.
            return f"{obj.value}:{obj.unit}"
        return super().default(obj)


class ModelWithMetadata(models.Model):
    private_metadata = JSONField(
        blank=True,
        null=True,
        default=dict,
        encoder=CustomJsonEncoder,
    )
    metadata = JSONField(
        blank=True,
        null=True,
        default=dict,
        encoder=CustomJsonEncoder,
    )

    class Meta:
        indexes = [
            GinIndex(fields=["private_metadata"], name="%(class)s_p_meta_idx"),
            GinIndex(fields=["metadata"], name="%(class)s_meta_idx"),
        ]
        abstract = True

    # ------------------------------------------------------------------
    # Private metadata
    # ------------------------------------------------------------------

    def get_value_from_private_metadata(self, key: str, default: Any = None) -> Any:
        return self.private_metadata.get(key, default)

    def store_value_in_private_metadata(self, items: dict):
        if not self.private_metadata:
            self.private_metadata = {}
        self.private_metadata.update(items)

    def clear_private_metadata(self):
        self.private_metadata = {}

    def delete_value_from_private_metadata(self, key: str):
        if key in self.private_metadata:
            del self.private_metadata[key]

    # ------------------------------------------------------------------
    # Public metadata
    # ------------------------------------------------------------------

    def get_value_from_metadata(self, key: str, default: Any = None) -> Any:
        return self.metadata.get(key, default)

    def store_value_in_metadata(self, items: dict):
        if not self.metadata:
            self.metadata = {}
        self.metadata.update(items)

    def clear_metadata(self):
        self.metadata = {}

    def delete_value_from_metadata(self, key: str):
        if key in self.metadata:
            del self.metadata[key]


class ModelWithExternalReference(models.Model):
    external_reference = models.CharField(
        max_length=250,
        unique=True,
        blank=True,
        null=True,
        db_index=True,
    )

    class Meta:
        abstract = True


class Job(models.Model):
    status = models.CharField(
        max_length=50,
        choices=JobStatus.CHOICES,
        default=JobStatus.PENDING,
    )
    message = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True