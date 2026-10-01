"""
Real-time tracking, traffic conditions, and emergency alert models.

These models inherit from LocationModel, which is the canonical
location model for Univa.
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings
from django.contrib.postgres.indexes import GistIndex

from core.models.location import LocationModel


class RealTimeTracking(LocationModel):
    """
    Real-time tracking data for live vehicle tracking.

    Location capabilities are inherited directly from LocationModel.
    """

    class Platform(models.TextChoices):
        IOS = "ios", _("iOS")
        ANDROID = "android", _("Android")
        WEB = "web", _("Web")
        DEVICE = "device", _("GPS Device")

    # ============================================================
    # Relationships
    # ============================================================

    vehicle = models.ForeignKey(
        "transport.Vehicle",
        on_delete=models.CASCADE,
        related_name="realtime_tracking",
        db_index=True,
        help_text=_("Vehicle being tracked"),
    )

    service_request = models.ForeignKey(
        "transport.ServiceRequest",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="realtime_updates",
        db_index=True,
        help_text=_("Service request associated with this tracking"),
    )

    # ============================================================
    # Movement Data
    # ============================================================

    speed = models.FloatField(
        help_text=_("Speed in km/h"),
        validators=[MinValueValidator(0), MaxValueValidator(300)],
        default=0,
    )

    heading = models.FloatField(
        help_text=_("Direction in degrees (0–360)"),
        validators=[MinValueValidator(0), MaxValueValidator(360)],
        default=0,
    )

    is_moving = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Whether vehicle is currently moving"),
    )

    # ============================================================
    # Location Accuracy
    # ============================================================

    accuracy = models.FloatField(
        null=True,
        blank=True,
        help_text=_("GPS accuracy in meters"),
        validators=[MinValueValidator(0)],
    )

    altitude = models.FloatField(
        null=True,
        blank=True,
        help_text=_("Altitude in meters"),
    )

    # ============================================================
    # Device Information
    # ============================================================

    battery_level = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Device battery level percentage"),
    )

    device_id = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Device identifier"),
    )

    app_version = models.CharField(
        max_length=20,
        blank=True,
        help_text=_("App version"),
    )

    platform = models.CharField(
        max_length=10,
        choices=Platform.choices,
        default=Platform.ANDROID,
        db_index=True,
        help_text=_("Platform of the tracking device"),
    )

    # ============================================================
    # Metadata
    # ============================================================

    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Additional tracking metadata"),
    )

    # ============================================================
    # Timestamps
    # ============================================================

    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text=_("When the tracking data was recorded"),
    )

    class Meta:
        indexes = [
            models.Index(fields=["vehicle", "-timestamp"]),
            models.Index(fields=["service_request", "-timestamp"]),
            GistIndex(
                fields=["location_point"],
                name="realtime_location_gist_idx",
            ),
            models.Index(fields=["timestamp"]),
            models.Index(fields=["is_moving"]),
        ]
        ordering = ["-timestamp"]
        verbose_name = _("Real-time Tracking")
        verbose_name_plural = _("Real-time Tracking Data")

    def __str__(self):
        return f"Real-time tracking for {self.vehicle} at {self.timestamp}"

    # ============================================================
    # Location Methods
    # ============================================================

    def update_location(
        self,
        latitude,
        longitude,
        accuracy=None,
        source="gps",
    ):
        """
        Update this tracking record's canonical location.

        Location fields are inherited from LocationModel.
        """

        self.accuracy = accuracy

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


class TrafficConditions(LocationModel):
    """
    Traffic conditions data for route optimization.

    Location capabilities are inherited directly from LocationModel.
    """

    class TrafficLevel(models.TextChoices):
        FREE_FLOW = "free_flow", _("Free Flow")
        LIGHT = "light", _("Light Traffic")
        MODERATE = "moderate", _("Moderate Traffic")
        HEAVY = "heavy", _("Heavy Traffic")
        CONGESTED = "congested", _("Congested")
        BLOCKED = "blocked", _("Blocked")

    class Source(models.TextChoices):
        GPS = "gps", _("GPS Data")
        USER_REPORT = "user_report", _("User Report")
        TRAFFIC_SERVICE = "traffic_service", _("Traffic Service")
        PREDICTION = "prediction", _("Prediction")

    # ============================================================
    # Traffic Data
    # ============================================================

    road_name = models.CharField(
        max_length=200,
        blank=True,
        db_index=True,
        help_text=_("Name of the road"),
    )

    traffic_level = models.CharField(
        max_length=20,
        choices=TrafficLevel.choices,
        db_index=True,
        help_text=_("Traffic level"),
    )

    average_speed = models.FloatField(
        help_text=_("Average speed in km/h"),
        validators=[MinValueValidator(0), MaxValueValidator(150)],
    )

    delay_minutes = models.FloatField(
        help_text=_("Estimated delay in minutes per km"),
        validators=[MinValueValidator(0)],
        default=0,
    )

    # ============================================================
    # Data Source
    # ============================================================

    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.GPS,
        db_index=True,
        help_text=_("Source of traffic data"),
    )

    confidence = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        default=0.8,
        help_text=_("Data confidence level (0–1)"),
    )

    # ============================================================
    # Metadata
    # ============================================================

    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Additional traffic metadata"),
    )

    # ============================================================
    # Timestamps
    # ============================================================

    recorded_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text=_("When the traffic data was recorded"),
    )

    valid_until = models.DateTimeField(
        db_index=True,
        help_text=_("Until when this traffic data is valid"),
    )

    class Meta:
        indexes = [
            GistIndex(
                fields=["location_point"],
                name="traffic_location_gist_idx",
            ),
            models.Index(fields=["traffic_level", "recorded_at"]),
            models.Index(fields=["road_name"]),
        ]
        ordering = ["-recorded_at"]
        verbose_name = _("Traffic Condition")
        verbose_name_plural = _("Traffic Conditions")

    def __str__(self):
        return (
            f"{self.get_traffic_level_display()} "
            f"on {self.road_name or 'Unknown road'}"
        )

    # ============================================================
    # Location Methods
    # ============================================================

    def update_location(
        self,
        latitude,
        longitude,
        address=None,
    ):
        """
        Update this traffic condition's canonical location.
        """

        if address is not None:
            self.location = address

        LocationModel.update_location(
            self,
            latitude=latitude,
            longitude=longitude,
            source="traffic_data",
            save=True,
        )

        return self

    def get_location_coordinates(self):
        """Get location coordinates as (lat, lng)."""
        return self.coordinates

    @property
    def lat(self):
        """Get latitude."""
        return (
            float(self.latitude)
            if self.latitude is not None
            else None
        )

    @property
    def lng(self):
        """Get longitude."""
        return (
            float(self.longitude)
            if self.longitude is not None
            else None
        )

    @property
    def is_valid(self):
        """Check if traffic data is still valid."""
        return timezone.now() <= self.valid_until

    @property
    def traffic_level_display(self):
        """Get human-readable traffic level display."""
        return self.get_traffic_level_display()


class EmergencyAlert(LocationModel):
    """
    Emergency alert system for drivers and passengers.

    Location capabilities are inherited directly from LocationModel.
    """

    class AlertType(models.TextChoices):
        ACCIDENT = "accident", _("Accident")
        BREAKDOWN = "breakdown", _("Vehicle Breakdown")
        MEDICAL = "medical", _("Medical Emergency")
        SAFETY = "safety", _("Safety Concern")
        TRAFFIC = "traffic", _("Traffic Incident")
        WEATHER = "weather", _("Severe Weather")

    class Severity(models.TextChoices):
        LOW = "low", _("Low")
        MEDIUM = "medium", _("Medium")
        HIGH = "high", _("High")
        CRITICAL = "critical", _("Critical")

    class AlertStatus(models.TextChoices):
        ACTIVE = "active", _("Active")
        ACKNOWLEDGED = "acknowledged", _("Acknowledged")
        RESOLVED = "resolved", _("Resolved")
        CANCELLED = "cancelled", _("Cancelled")

    # ============================================================
    # Alert Details
    # ============================================================

    alert_type = models.CharField(
        max_length=20,
        choices=AlertType.choices,
        db_index=True,
        help_text=_("Type of emergency"),
    )

    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.MEDIUM,
        db_index=True,
        help_text=_("Severity level"),
    )

    status = models.CharField(
        max_length=20,
        choices=AlertStatus.choices,
        default=AlertStatus.ACTIVE,
        db_index=True,
        help_text=_("Alert status"),
    )

    title = models.CharField(
        max_length=200,
        help_text=_("Alert title"),
    )

    description = models.TextField(
        help_text=_("Detailed description of the emergency"),
    )

    location_description = models.CharField(
        max_length=500,
        blank=True,
        help_text=_("Human-readable location description"),
    )

    # ============================================================
    # Relationships
    # ============================================================

    service_request = models.ForeignKey(
        "transport.ServiceRequest",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="emergency_alerts",
        db_index=True,
        help_text=_("Associated service request"),
    )

    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reported_emergencies",
        db_index=True,
        help_text=_("User who reported the emergency"),
    )

    acknowledged_by = models.ManyToManyField(
        "transport.ServiceProviderProfile",
        blank=True,
        related_name="acknowledged_alerts",
        help_text=_("Providers who acknowledged this alert"),
    )

    # ============================================================
    # Metadata
    # ============================================================

    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Additional alert metadata"),
    )

    # ============================================================
    # Timestamps
    # ============================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text=_("When the alert was created"),
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        help_text=_("When the alert was last updated"),
    )

    acknowledged_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the alert was acknowledged"),
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text=_("When the alert was resolved"),
    )

    class Meta:
        indexes = [
            GistIndex(
                fields=["location_point"],
                name="emergency_location_gist_idx",
            ),
            models.Index(fields=["alert_type", "status"]),
            models.Index(fields=["severity", "created_at"]),
            models.Index(fields=["status"]),
        ]
        ordering = ["-created_at"]
        verbose_name = _("Emergency Alert")
        verbose_name_plural = _("Emergency Alerts")

    def __str__(self):
        return (
            f"{self.get_alert_type_display()} Alert - {self.title}"
        )

    # ============================================================
    # Location Methods
    # ============================================================

    def update_location(
        self,
        latitude,
        longitude,
        address=None,
    ):
        """
        Update this emergency alert's canonical location.
        """

        if address is not None:
            self.location = address

        LocationModel.update_location(
            self,
            latitude=latitude,
            longitude=longitude,
            source="emergency_alert",
            save=True,
        )

        return self

    def get_location_coordinates(self):
        """Get location coordinates as (lat, lng)."""
        return self.coordinates

    @property
    def lat(self):
        """Get latitude."""
        return (
            float(self.latitude)
            if self.latitude is not None
            else None
        )

    @property
    def lng(self):
        """Get longitude."""
        return (
            float(self.longitude)
            if self.longitude is not None
            else None
        )

    @property
    def severity_display(self):
        """Get human-readable severity display."""
        return self.get_severity_display()

    @property
    def alert_type_display(self):
        """Get human-readable alert type display."""
        return self.get_alert_type_display()

    @property
    def status_display(self):
        """Get human-readable status display."""
        return self.get_status_display()

    # ============================================================
    # Alert Management Methods
    # ============================================================

    def acknowledge(self, provider):
        """
        Acknowledge the alert by a provider.

        Args:
            provider: ServiceProviderProfile instance
        """
        if self.status != self.AlertStatus.ACTIVE:
            raise ValueError(_("Only active alerts can be acknowledged"))

        self.acknowledged_by.add(provider)

        if (
            self.acknowledged_by.count() > 0
            and self.status == self.AlertStatus.ACTIVE
        ):
            self.status = self.AlertStatus.ACKNOWLEDGED
            self.acknowledged_at = timezone.now()
            self.save(
                update_fields=[
                    "status",
                    "acknowledged_at",
                ]
            )

    def resolve(self):
        """Mark the alert as resolved."""
        self.status = self.AlertStatus.RESOLVED
        self.resolved_at = timezone.now()
        self.save(
            update_fields=[
                "status",
                "resolved_at",
            ]
        )

    def cancel(self):
        """Cancel the alert."""
        self.status = self.AlertStatus.CANCELLED
        self.save(update_fields=["status"])

    def is_active(self):
        """Check if alert is active."""
        return self.status == self.AlertStatus.ACTIVE

    def is_acknowledged(self):
        """Check if alert is acknowledged."""
        return self.status == self.AlertStatus.ACKNOWLEDGED

    def is_resolved(self):
        """Check if alert is resolved."""
        return self.status == self.AlertStatus.RESOLVED

