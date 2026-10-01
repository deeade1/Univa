from django.db import models
from django_resized import ResizedImageField
from django.conf import settings


class DriverProfile(models.Model):
    """
    Transport-specific profile extension.

    Accounts owns the core UserProfile.
    Transport owns everything specific to being a driver.
    """

    profile = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="driver_profile",
    )

    license_number = models.CharField(
        max_length=30,
        blank=True,
    )

    license_image = ResizedImageField(
        size=[1200, 1200],
        upload_to="driver_licenses/",
        quality=90,
        blank=True,
        null=True,
    )

    vehicle_type = models.CharField(
        max_length=50,
        blank=True,
    )

    vehicle_plate = models.CharField(
        max_length=30,
        blank=True,
    )

    vehicle_make = models.CharField(
        max_length=50,
        blank=True,
    )

    vehicle_model = models.CharField(
        max_length=50,
        blank=True,
    )

    vehicle_year = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    insurance_provider = models.CharField(
        max_length=100,
        blank=True,
    )

    insurance_expiry = models.DateField(
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Driver Profile"
        verbose_name_plural = "Driver Profiles"

    def __str__(self):
        return f"Driver Profile for {self.user}"