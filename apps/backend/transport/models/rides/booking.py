from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings


class Booking(models.Model):
    """
    Optimized booking model.
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        CONFIRMED = "confirmed", _("Confirmed")
        CANCELLED = "cancelled", _("Cancelled")
        COMPLETED = "completed", _("Completed")

    service_request = models.ForeignKey(
        "ServiceRequest",
        on_delete=models.CASCADE,
        related_name="bookings",
        db_index=True,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings",
        db_index=True,
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    booked_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )

    class Meta:
        verbose_name = _("Booking")
        verbose_name_plural = _("Bookings")
        ordering = ["-booked_at"]

        indexes = [
            models.Index(fields=["service_request", "status"]),
            models.Index(fields=["user", "status"]),
            models.Index(fields=["booked_at"]),
            models.Index(fields=["confirmed_at"]),
            models.Index(fields=["cancelled_at"]),
            models.Index(fields=["completed_at"]),
        ]

    def __str__(self):
        email = (
            self.user.user.email
            if self.user and self.user.user
            else "Unknown"
        )

        return (
            f"Booking #{self.pk} "
            f"for {self.service_request.get_service_type_display()} "
            f"by {email}"
        )

    def clean(self):
        if not self.service_request:
            raise ValidationError(
                _("Service request must be provided")
            )

        if (
            self.status == self.Status.CONFIRMED
            and not self.service_request.provider
        ):
            raise ValidationError(
                _("Cannot confirm booking without an assigned provider")
            )

    def save(self, *args, **kwargs):
        """
        Automatically populate lifecycle timestamps
        based on the current booking status.
        """
        if (
            self.status == self.Status.CONFIRMED
            and self.confirmed_at is None
        ):
            self.confirmed_at = timezone.now()

        elif (
            self.status == self.Status.CANCELLED
            and self.cancelled_at is None
        ):
            self.cancelled_at = timezone.now()

        elif (
            self.status == self.Status.COMPLETED
            and self.completed_at is None
        ):
            self.completed_at = timezone.now()

        super().save(*args, **kwargs)

    def confirm(self):
        """
        Confirm the booking.
        """
        if self.status != self.Status.CONFIRMED:
            self.status = self.Status.CONFIRMED
            self.confirmed_at = timezone.now()
            self.save(
                update_fields=[
                    "status",
                    "confirmed_at",
                ]
            )

    def cancel(self):
        """
        Cancel the booking.
        """
        if self.status != self.Status.CANCELLED:
            self.status = self.Status.CANCELLED
            self.cancelled_at = timezone.now()
            self.save(
                update_fields=[
                    "status",
                    "cancelled_at",
                ]
            )

    def complete(self):
        """
        Mark the booking as completed.
        """
        if self.status != self.Status.COMPLETED:
            self.status = self.Status.COMPLETED
            self.completed_at = timezone.now()
            self.save(
                update_fields=[
                    "status",
                    "completed_at",
                ]
            )