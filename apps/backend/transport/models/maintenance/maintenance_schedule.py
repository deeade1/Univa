import logging
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.conf import settings



logger = logging.getLogger(__name__)

class MaintenanceSchedule(models.Model):
    """Vehicle maintenance scheduling and tracking"""
    class MaintenanceType(models.TextChoices):
        OIL_CHANGE = 'oil_change', _('Oil Change')
        TIRE_ROTATION = 'tire_rotation', _('Tire Rotation')
        BRAKE_SERVICE = 'brake_service', _('Brake Service')
        BATTERY_CHECK = 'battery_check', _('Battery Check')
        ENGINE_SERVICE = 'engine_service', _('Engine Service')
        INSPECTION = 'inspection', _('General Inspection')
        ROUTINE = 'routine', _('Routine Maintenance')
        REPAIR = 'repair', _('Repair')
    
    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', _('Scheduled')
        IN_PROGRESS = 'in_progress', _('In Progress')
        COMPLETED = 'completed', _('Completed')
        CANCELLED = 'cancelled', _('Cancelled')
        OVERDUE = 'overdue', _('Overdue')

    vehicle = models.ForeignKey(
        'Vehicle',
        on_delete=models.CASCADE,
        related_name='maintenance_schedules'
    )
    maintenance_type = models.CharField(
        max_length=50,
        choices=MaintenanceType.choices,
        db_index=True
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED,
        db_index=True
    )
    
    scheduled_date = models.DateTimeField(db_index=True)
    completed_date = models.DateTimeField(null=True, blank=True)
    estimated_duration = models.DurationField(
        help_text=_("Estimated time to complete"),
        null=True,
        blank=True
    )
    
    last_service_date = models.DateField(null=True, blank=True)
    last_service_odometer = models.PositiveIntegerField(null=True, blank=True)
    next_service_date = models.DateField(null=True, blank=True)
    next_service_odometer = models.PositiveIntegerField(null=True, blank=True)
    
    time_interval_days = models.PositiveIntegerField(
        help_text=_("Days between services"),
        null=True,
        blank=True
    )
    distance_interval_km = models.PositiveIntegerField(
        help_text=_("Kilometers between services"),
        null=True,
        blank=True
    )
    
    description = models.TextField()
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    parts_used = models.JSONField(
        default=list,
        blank=True,
        help_text=_("List of parts used in JSON format")
    )
    mileage_at_service = models.PositiveIntegerField(null=True, blank=True)
    
    service_center = models.CharField(max_length=200, blank=True)
    technician_notes = models.TextField(blank=True)
    
    is_overdue = models.BooleanField(default=False)
    is_urgent = models.BooleanField(default=False)
    
    is_recurring = models.BooleanField(default=False)
    recurrence_interval = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Interval in days for recurring maintenance")
    )
    
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='maintenance'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['vehicle', 'scheduled_date']),
            models.Index(fields=['status', 'scheduled_date']),
            models.Index(fields=['maintenance_type', 'scheduled_date']),
            models.Index(fields=['is_recurring', 'scheduled_date']),
            models.Index(fields=['is_overdue', 'is_urgent']),
        ]
        ordering = ['scheduled_date']
        verbose_name = _("Maintenance Schedule")
        verbose_name_plural = _("Maintenance Schedules")
    
    def __str__(self):
        return f"{self.get_maintenance_type_display()} for {self.vehicle} on {self.scheduled_date}"

class MaintenanceLog(models.Model):
    """Detailed maintenance history log"""
    class LogType(models.TextChoices):
        SERVICE = 'service', _('Service')
        REPAIR = 'repair', _('Repair')
        INSPECTION = 'inspection', _('Inspection')
        INCIDENT = 'incident', _('Incident')
        NOTE = 'note', _('General Note')

    vehicle = models.ForeignKey(
        'Vehicle',
        on_delete=models.CASCADE,
        related_name='maintenance_logs'
    )
    maintenance_schedule = models.ForeignKey(
        MaintenanceSchedule,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='logs'
    )
    
    log_date = models.DateTimeField(default=timezone.now, db_index=True)
    service_date = models.DateField(null=True, blank=True)
    log_type = models.CharField(
        max_length=20,
        choices=LogType.choices,
        db_index=True
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    mileage = models.PositiveIntegerField()
    odometer_reading = models.PositiveIntegerField(null=True, blank=True)
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    parts_changed = models.JSONField(default=list, blank=True)
    technician = models.CharField(max_length=100, blank=True)
    service_provider = models.CharField(max_length=100, blank=True)
    
    receipts = models.FileField(
        upload_to='maintenance_receipts/',
        null=True,
        blank=True
    )
    photos = models.JSONField(
        default=list,
        blank=True,
        help_text=_("List of photo URLs")
    )
    
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_logs'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['vehicle', 'log_date']),
            models.Index(fields=['log_type', 'log_date']),
            models.Index(fields=['service_date']),
        ]
        ordering = ['-log_date']
        verbose_name = _("Maintenance Log")
        verbose_name_plural = _("Maintenance Logs")
    
    def __str__(self):
        return f"{self.log_type.title()} for {self.vehicle} on {self.log_date}"