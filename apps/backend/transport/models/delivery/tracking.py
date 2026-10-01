"""
Unified tracking models with LocationModel integration.

Tracking and TrackingEvent inherit LocationModel directly.
LocationModel is the canonical location model for Univa.
"""

import secrets
import string

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models.location import LocationModel


class Tracking(LocationModel):
    """
    Unified tracking model that supports both Package and Delivery
    tracking.

    Location capabilities are inherited directly from LocationModel.
    """

    class Status(models.TextChoices):
        # Package statuses
        LABEL_CREATED = "label_created", _("Label Created")
        PACKAGING = "packaging", _("Packaging")
        READY_FOR_PICKUP = "ready_for_pickup", _("Ready for Pickup")
        PICKED_UP = "picked_up", _("Picked Up")

        # In transit statuses
        IN_TRANSIT = "in_transit", _("In Transit")
        PROCESSING = "processing", _("Processing")
        SORTED = "sorted", _("Sorted")
        DEPARTED = "departed", _("Departed")
        ARRIVED = "arrived", _("Arrived")
        CUSTOMS = "customs", _("Customs Clearance")

        # Delivery statuses
        OUT_FOR_DELIVERY = "out_for_delivery", _("Out for Delivery")
        DELIVERY_ATTEMPTED = "delivery_attempted", _("Delivery Attempted")
        DELIVERED = "delivered", _("Delivered")
        DELIVERY_CONFIRMED = "delivery_confirmed", _("Delivery Confirmed")

        # Exception statuses
        EXCEPTION = "exception", _("Exception")
        DAMAGED = "damaged", _("Damaged")
        LOST = "lost", _("Lost")
        RETURNED = "returned", _("Returned")
        RETURN_TO_SENDER = "return_to_sender", _("Return to Sender")

        # Final statuses
        COMPLETED = "completed", _("Completed")
        CANCELLED = "cancelled", _("Cancelled")

    class Priority(models.TextChoices):
        STANDARD = "standard", _("Standard")
        EXPRESS = "express", _("Express")
        PRIORITY = "priority", _("Priority")
        SAME_DAY = "same_day", _("Same Day")

    # ============================================================
    # Relationships
    # ============================================================

    package = models.OneToOneField(
        "transport.Package",
        on_delete=models.CASCADE,
        related_name="tracking",
        null=True,
        blank=True,
        db_index=True,
        help_text=_("The package being tracked"),
    )

    delivery = models.ForeignKey(
        "transport.Delivery",
        on_delete=models.CASCADE,
        related_name="tracking_records",
        null=True,
        blank=True,
        db_index=True,
        help_text=_("The delivery this tracking belongs to"),
    )

    # Backward-compatible ServiceRequest reference.
    service_request = models.ForeignKey(
        "transport.ServiceRequest",
        on_delete=models.CASCADE,
        related_name="tracking_old",
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Legacy service request reference"),
    )

    # ============================================================
    # Tracking Identification
    # ============================================================

    tracking_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text=_("Unique tracking number"),
    )

    carrier_tracking_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        db_index=True,
        help_text=_("Carrier's tracking number (if different)"),
    )

    carrier_name = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Name of the carrier"),
    )

    # ============================================================
    # Status
    # ============================================================

    current_status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.LABEL_CREATED,
        db_index=True,
        help_text=_("Current tracking status"),
    )

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.STANDARD,
        db_index=True,
        help_text=_("Delivery priority"),
    )

    # ============================================================
    # Timestamps
    # ============================================================

    estimated_delivery = models.DateTimeField(
        db_index=True,
        help_text=_("Estimated delivery date/time"),
    )

    actual_delivery = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Actual delivery date/time"),
    )

    last_updated = models.DateTimeField(
        auto_now=True,
        db_index=True,
    )

    # ============================================================
    # Delivery Confirmation
    # ============================================================

    signature_required = models.BooleanField(
        default=False,
        help_text=_("Whether signature is required"),
    )

    signature_name = models.CharField(
        max_length=200,
        blank=True,
        help_text=_("Name of person who signed"),
    )

    signature_image = models.ImageField(
        upload_to="signatures/",
        blank=True,
        null=True,
        help_text=_("Signature image"),
    )

    delivery_photo = models.ImageField(
        upload_to="delivery_photos/",
        blank=True,
        null=True,
        help_text=_("Photo of delivered package"),
    )

    # ============================================================
    # Delivery Attempt Tracking
    # ============================================================

    delivery_attempts = models.PositiveIntegerField(
        default=0,
        help_text=_("Number of delivery attempts"),
    )

    last_attempt_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Date of last delivery attempt"),
    )

    # ============================================================
    # Metadata
    # ============================================================

    notes = models.TextField(
        blank=True,
        help_text=_("Additional tracking notes"),
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Additional metadata"),
    )

    # ============================================================
    # Timestamps
    # ============================================================

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["tracking_number", "current_status"]
            ),
            models.Index(fields=["package"]),
            models.Index(fields=["delivery"]),
            models.Index(fields=["estimated_delivery"]),
            models.Index(fields=["actual_delivery"]),
            models.Index(fields=["carrier_name"]),
            models.Index(fields=["priority", "current_status"]),
        ]
        verbose_name = _("Tracking")
        verbose_name_plural = _("Tracking Records")
        ordering = ["-last_updated"]

    def __str__(self):
        return (
            f"Tracking #{self.tracking_number} - "
            f"{self.get_current_status_display()}"
        )

    def clean(self):
        """Validate tracking data."""
        if not self.package and not self.delivery:
            raise ValidationError(
                _(
                    "Tracking must be associated with either "
                    "a Package or a Delivery."
                )
            )

    def save(self, *args, **kwargs):
        if not self.tracking_number:
            self.tracking_number = self.generate_tracking_number()

        self.full_clean()
        super().save(*args, **kwargs)

    def generate_tracking_number(self):
        """Generate a unique tracking number."""
        prefix = "PKG" if self.package else "DLV"

        rand_part = "".join(
            secrets.choice(
                string.ascii_uppercase + string.digits
            )
            for _ in range(8)
        )

        return f"{prefix}-{rand_part}"

    # ============================================================
    # Location Methods
    # ============================================================

    def update_location(
        self,
        latitude,
        longitude,
        address=None,
        accuracy=None,
        source="gps",
    ):
        """
        Update this tracking record's canonical location.

        Location fields are inherited from LocationModel.
        """

        if address is not None:
            self.location = address

        LocationModel.update_location(
            self,
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy,
            source=source,
            save=True,
        )

        return self

    def get_location_coordinates(self):
        """Get current location coordinates as (lat, lng)."""
        return self.coordinates

    def get_location_info(self):
        """Get current location information."""
        return self.get_location_info()

    @property
    def current_lat(self):
        """Get current latitude."""
        return (
            float(self.latitude)
            if self.latitude is not None
            else None
        )

    @property
    def current_lng(self):
        """Get current longitude."""
        return (
            float(self.longitude)
            if self.longitude is not None
            else None
        )

    @property
    def has_location(self):
        """Check whether the tracking record has a location."""
        return super().has_location

    @property
    def location_string(self):
        """Get the human-readable location string."""
        return super().location_string or "Location not set"

    # ============================================================
    # Status Update Methods
    # ============================================================

    def update_status(
        self,
        new_status,
        location=None,
        description=None,
        lat=None,
        lng=None,
        address=None,
    ):
        """
        Update tracking status and create a tracking event.
        """

        if new_status not in dict(self.Status.choices):
            raise ValueError(_("Invalid status"))

        old_status = self.current_status
        self.current_status = new_status
        self.last_updated = timezone.now()

        if lat is not None and lng is not None:
            self.update_location(
                latitude=lat,
                longitude=lng,
                address=address or location,
                source="tracking_update",
            )
        elif address:
            self.location = address

        self.save(
            update_fields=[
                "current_status",
                "last_updated",
                "location",
            ]
        )

        event = TrackingEvent.objects.create(
            tracking=self,
            status=new_status,
            location=location or self.location_string,
            latitude=lat,
            longitude=lng,
            description=(
                description
                or f"Status updated to "
                f"{self.get_current_status_display()}"
            ),
            address=address,
        )

        self._update_related_status(new_status)

        return event

    def _update_related_status(self, status):
        """Update related Package or Delivery status."""

        if self.package:
            package_status_map = {
                self.Status.LABEL_CREATED: "pending",
                self.Status.PICKED_UP: "in_transit",
                self.Status.IN_TRANSIT: "in_transit",
                self.Status.OUT_FOR_DELIVERY: "out_for_delivery",
                self.Status.DELIVERED: "delivered",
                self.Status.DELIVERY_CONFIRMED: "delivered",
                self.Status.RETURNED: "returned",
                self.Status.LOST: "lost",
            }

            if status in package_status_map:
                self.package.status = package_status_map[status]
                self.package.save(update_fields=["status"])

        if self.delivery:
            if status in [
                self.Status.DELIVERED,
                self.Status.DELIVERY_CONFIRMED,
            ]:
                all_packages = self.delivery.packages.filter(
                    tracking__isnull=False
                )

                delivered_count = all_packages.filter(
                    tracking__current_status__in=[
                        self.Status.DELIVERED,
                        self.Status.DELIVERY_CONFIRMED,
                        self.Status.COMPLETED,
                    ]
                ).count()

                if (
                    delivered_count == all_packages.count()
                    and all_packages.count() > 0
                ):
                    self.delivery.status = "completed"
                    self.delivery.completed_at = timezone.now()
                    self.delivery.save(
                        update_fields=[
                            "status",
                            "completed_at",
                        ]
                    )

    def add_delivery_attempt(
        self,
        location=None,
        lat=None,
        lng=None,
        address=None,
        notes="",
    ):
        """Record a delivery attempt."""

        self.delivery_attempts += 1
        self.last_attempt_date = timezone.now()

        if lat is not None and lng is not None:
            self.update_location(
                latitude=lat,
                longitude=lng,
                address=address or location,
                source="delivery_attempt",
            )
        elif address:
            self.location = address

        self.save(
            update_fields=[
                "delivery_attempts",
                "last_attempt_date",
                "location",
            ]
        )

        return TrackingEvent.objects.create(
            tracking=self,
            status=self.Status.DELIVERY_ATTEMPTED,
            location=location or self.location_string,
            latitude=lat,
            longitude=lng,
            description=(
                f"Delivery attempt #{self.delivery_attempts}: "
                f"{notes}"
            ),
            address=address,
        )

    def confirm_delivery(
        self,
        signature_name=None,
        signature_image=None,
        delivery_photo=None,
        lat=None,
        lng=None,
        address=None,
    ):
        """Confirm package delivery."""

        if signature_name:
            self.signature_name = signature_name

        if signature_image:
            self.signature_image = signature_image

        if delivery_photo:
            self.delivery_photo = delivery_photo

        self.actual_delivery = timezone.now()

        if lat is not None and lng is not None:
            self.update_location(
                latitude=lat,
                longitude=lng,
                address=address or "Delivery location",
                source="delivery_confirmation",
            )
        elif address:
            self.location = address

        self.save(
            update_fields=[
                "signature_name",
                "signature_image",
                "delivery_photo",
                "actual_delivery",
                "location",
            ]
        )

        return self.update_status(
            new_status=self.Status.DELIVERY_CONFIRMED,
            location=address or "Delivery confirmed",
            description=(
                "Delivery confirmed. Signed by: "
                f"{signature_name or 'Unknown'}"
            ),
            lat=lat,
            lng=lng,
            address=address,
        )

    # ============================================================
    # Properties
    # ============================================================

    @property
    def is_delivered(self):
        return self.current_status in [
            self.Status.DELIVERED,
            self.Status.DELIVERY_CONFIRMED,
            self.Status.COMPLETED,
        ]

    @property
    def is_delayed(self):
        if self.is_delivered:
            return False

        if (
            self.estimated_delivery
            and timezone.now() > self.estimated_delivery
        ):
            return True

        return False

    @property
    def is_exception(self):
        return self.current_status in [
            self.Status.EXCEPTION,
            self.Status.DAMAGED,
            self.Status.LOST,
            self.Status.RETURNED,
            self.Status.RETURN_TO_SENDER,
        ]

    @property
    def days_in_transit(self):
        if not self.created_at:
            return None

        end_date = self.actual_delivery or timezone.now()
        return (end_date - self.created_at).days

    @property
    def is_pending(self):
        return self.current_status in [
            self.Status.LABEL_CREATED,
            self.Status.PACKAGING,
            self.Status.READY_FOR_PICKUP,
        ]

    @property
    def is_in_transit(self):
        return self.current_status in [
            self.Status.IN_TRANSIT,
            self.Status.PROCESSING,
            self.Status.SORTED,
            self.Status.DEPARTED,
            self.Status.ARRIVED,
            self.Status.CUSTOMS,
            self.Status.OUT_FOR_DELIVERY,
        ]

    @property
    def is_completed(self):
        return self.current_status in [
            self.Status.COMPLETED,
            self.Status.DELIVERED,
            self.Status.DELIVERY_CONFIRMED,
            self.Status.CANCELLED,
            self.Status.RETURNED,
            self.Status.RETURN_TO_SENDER,
        ]


class TrackingEvent(LocationModel):
    """
    Individual tracking event in the package/delivery journey.

    Location capabilities are inherited directly from LocationModel.
    """

    tracking = models.ForeignKey(
        Tracking,
        on_delete=models.CASCADE,
        related_name="events",
        db_index=True,
        help_text=_("The tracking record this event belongs to"),
    )

    status = models.CharField(
        max_length=30,
        choices=Tracking.Status.choices,
        db_index=True,
        help_text=_("Status at this event"),
    )

    description = models.TextField(
        help_text=_("Detailed description of the event"),
    )

    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text=_("When the event occurred"),
    )

    event_code = models.CharField(
        max_length=20,
        blank=True,
        help_text=_("Event code for external systems"),
    )

    notes = models.TextField(
        blank=True,
        help_text=_("Additional notes for this event"),
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Additional event metadata"),
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["tracking", "status"]),
            models.Index(fields=["timestamp"]),
            models.Index(fields=["event_code"]),
        ]
        ordering = ["-timestamp"]
        verbose_name = _("Tracking Event")
        verbose_name_plural = _("Tracking Events")

    def __str__(self):
        return (
            f"Event for {self.tracking.tracking_number} - "
            f"{self.get_status_display()} at {self.timestamp}"
        )

    @property
    def lat(self):
        """Get latitude from the canonical LocationModel."""
        return (
            float(self.latitude)
            if self.latitude is not None
            else None
        )

    @property
    def lng(self):
        """Get longitude from the canonical LocationModel."""
        return (
            float(self.longitude)
            if self.longitude is not None
            else None
        )

    @property
    def status_display(self):
        """Get human-readable status display."""
        return dict(
            Tracking.Status.choices
        ).get(self.status, self.status)

    @property
    def has_coordinates(self):
        """Check whether the event has coordinates."""
        return self.location_point is not None
