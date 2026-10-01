# transport/models/core/vehicle_inspection.py

"""
Vehicle inspection models for tracking vehicle safety and compliance.
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class VehicleInspection(models.Model):
    """
    Vehicle inspection records for tracking vehicle safety and compliance.
    Combines both simple and comprehensive inspection tracking.
    """
    
    # ============================================================
    # Inspection Types
    # ============================================================
    
    class InspectionType(models.TextChoices):
        PRE_TRIP = 'pre_trip', _('Pre-Trip Inspection')
        POST_TRIP = 'post_trip', _('Post-Trip Inspection')
        ROUTINE = 'routine', _('Routine Inspection')
        SAFETY = 'safety', _('Safety Inspection')
        ANNUAL = 'annual', _('Annual Inspection')
        BIANNUAL = 'biannual', _('Bi-annual Inspection')
        QUARTERLY = 'quarterly', _('Quarterly Inspection')
        SPOT = 'spot', _('Spot Inspection')
        RANDOM = 'random', _('Random Inspection')
    
    # ============================================================
    # Inspection Results
    # ============================================================
    
    class InspectionResult(models.TextChoices):
        PASSED = 'passed', _('Passed')
        FAILED = 'failed', _('Failed')
        CONDITIONAL = 'conditional', _('Passed with Conditions')
        PENDING = 'pending', _('Pending')
        DEFERRED = 'deferred', _('Deferred')
    
    # ============================================================
    # Fields
    # ============================================================
    
    vehicle = models.ForeignKey(
        'transport.Vehicle',
        on_delete=models.CASCADE,
        related_name='inspections',
        db_index=True,
        help_text=_("Vehicle being inspected")
    )
    
    inspection_type = models.CharField(
        max_length=20,
        choices=InspectionType.choices,
        db_index=True,
        help_text=_("Type of inspection")
    )
    
    result = models.CharField(
        max_length=20,
        choices=InspectionResult.choices,
        default=InspectionResult.PENDING,
        db_index=True,
        help_text=_("Inspection result")
    )
    
    inspected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vehicle_inspections',
        help_text=_("Inspector")
    )
    
    inspection_date = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text=_("Date and time of inspection")
    )
    
    next_inspection_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Suggested date for next inspection")
    )
    
    # ============================================================
    # Inspection Details
    # ============================================================
    
    checklist = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Inspection checklist with results")
    )
    
    findings = models.TextField(
        blank=True,
        help_text=_("Detailed findings from inspection")
    )
    
    recommendations = models.TextField(
        blank=True,
        help_text=_("Recommendations for repairs or improvements")
    )
    
    notes = models.TextField(
        blank=True,
        help_text=_("Additional notes")
    )
    
    # ============================================================
    # Follow-up
    # ============================================================
    
    follow_up_required = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Whether follow-up is required")
    )
    
    follow_up_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Follow-up inspection date")
    )
    
    follow_up_result = models.CharField(
        max_length=20,
        choices=InspectionResult.choices,
        null=True,
        blank=True,
        help_text=_("Follow-up inspection result")
    )
    
    # ============================================================
    # Signatures and Photos
    # ============================================================
    
    inspector_signature = models.TextField(
        blank=True,
        help_text=_("Base64 encoded signature of inspector")
    )
    
    photos = models.JSONField(
        default=list,
        blank=True,
        help_text=_("List of photo URLs from inspection")
    )
    
    inspection_report = models.FileField(
        upload_to='inspection_reports/%Y/%m/%d/',
        blank=True,
        null=True,
        help_text=_("Inspection report PDF")
    )
    
    # ============================================================
    # Metadata
    # ============================================================
    
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Additional inspection metadata")
    )
    
    # ============================================================
    # Timestamps
    # ============================================================
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # ============================================================
    # Meta
    # ============================================================
    
    class Meta:
        verbose_name = _("Vehicle Inspection")
        verbose_name_plural = _("Vehicle Inspections")
        ordering = ['-inspection_date']
        indexes = [
            models.Index(fields=['vehicle', 'inspection_date']),
            models.Index(fields=['inspection_type', 'result']),
            models.Index(fields=['inspected_by', 'inspection_date']),
            models.Index(fields=['result']),
            models.Index(fields=['follow_up_required']),
            models.Index(fields=['next_inspection_date']),
        ]
    
    # ============================================================
    # String Representation
    # ============================================================
    
    def __str__(self):
        return f"{self.get_inspection_type_display()} for {self.vehicle} on {self.inspection_date.strftime('%Y-%m-%d %H:%M')}"
    
    # ============================================================
    # Properties
    # ============================================================
    
    @property
    def is_pass(self):
        """Check if inspection passed."""
        return self.result == self.InspectionResult.PASSED
    
    @property
    def is_fail(self):
        """Check if inspection failed."""
        return self.result == self.InspectionResult.FAILED
    
    @property
    def is_pending(self):
        """Check if inspection is pending."""
        return self.result == self.InspectionResult.PENDING
    
    @property
    def is_conditional(self):
        """Check if inspection passed with conditions."""
        return self.result == self.InspectionResult.CONDITIONAL
    
    @property
    def is_completed(self):
        """Check if inspection is completed."""
        return self.result not in [self.InspectionResult.PENDING, self.InspectionResult.DEFERRED]
    
    @property
    def passed_items(self):
        """Get count of passed checklist items."""
        if not self.checklist:
            return 0
        return sum(1 for item in self.checklist.values() if item.get('passed', False))
    
    @property
    def failed_items(self):
        """Get count of failed checklist items."""
        if not self.checklist:
            return 0
        return sum(1 for item in self.checklist.values() if not item.get('passed', False))
    
    @property
    def total_items(self):
        """Get total checklist items."""
        if not self.checklist:
            return 0
        return len(self.checklist)
    
    @property
    def pass_rate(self):
        """Calculate pass rate as percentage."""
        if self.total_items == 0:
            return 0
        return (self.passed_items / self.total_items) * 100
    
    @property
    def days_since_inspection(self):
        """Calculate days since inspection."""
        if not self.inspection_date:
            return None
        delta = timezone.now() - self.inspection_date
        return delta.days
    
    @property
    def is_overdue_for_next_inspection(self):
        """Check if next inspection is overdue."""
        if not self.next_inspection_date:
            return False
        return timezone.now() > self.next_inspection_date
    
    # ============================================================
    # Methods
    # ============================================================
    
    def pass_inspection(self, notes=None):
        """
        Mark inspection as passed.
        
        Args:
            notes: Optional notes about the pass
        """
        self.result = self.InspectionResult.PASSED
        if notes:
            self.notes = notes
        self.save(update_fields=['result', 'notes', 'updated_at'])
        self._update_vehicle_inspection_date()
    
    def fail_inspection(self, notes=None):
        """
        Mark inspection as failed.
        
        Args:
            notes: Optional notes about the failure
        """
        self.result = self.InspectionResult.FAILED
        if notes:
            self.notes = notes
        self.save(update_fields=['result', 'notes', 'updated_at'])
    
    def mark_conditional(self, notes=None):
        """
        Mark inspection as conditional pass.
        
        Args:
            notes: Conditions that need to be met
        """
        self.result = self.InspectionResult.CONDITIONAL
        if notes:
            self.notes = notes
        self.save(update_fields=['result', 'notes', 'updated_at'])
    
    def schedule_follow_up(self, follow_up_date):
        """
        Schedule a follow-up inspection.
        
        Args:
            follow_up_date: Date for follow-up inspection
        """
        self.follow_up_required = True
        self.follow_up_date = follow_up_date
        self.save(update_fields=['follow_up_required', 'follow_up_date', 'updated_at'])
    
    def complete_follow_up(self, result, notes=None):
        """
        Complete the follow-up inspection.
        
        Args:
            result: Follow-up result
            notes: Optional notes
        """
        self.follow_up_result = result
        if notes:
            self.notes = notes
        self.save(update_fields=['follow_up_result', 'notes', 'updated_at'])
    
    def add_checklist_item(self, item_name, passed, notes=None):
        """
        Add or update a checklist item.
        
        Args:
            item_name: Name of the checklist item
            passed: Whether the item passed
            notes: Optional notes about the item
        """
        if not self.checklist:
            self.checklist = {}
        
        self.checklist[item_name] = {
            'passed': passed,
            'notes': notes or '',
            'checked_at': timezone.now().isoformat()
        }
        self.save(update_fields=['checklist', 'updated_at'])
    
    def add_photo(self, photo_url):
        """
        Add a photo to the inspection.
        
        Args:
            photo_url: URL of the photo
        """
        if not self.photos:
            self.photos = []
        self.photos.append({
            'url': photo_url,
            'uploaded_at': timezone.now().isoformat()
        })
        self.save(update_fields=['photos', 'updated_at'])
    
    def add_signature(self, signature_data):
        """
        Add inspector signature.
        
        Args:
            signature_data: Base64 encoded signature
        """
        self.inspector_signature = signature_data
        self.save(update_fields=['inspector_signature', 'updated_at'])
    
    def _update_vehicle_inspection_date(self):
        """
        Update vehicle's last inspection date.
        """
        if hasattr(self.vehicle, 'last_inspection_date'):
            self.vehicle.last_inspection_date = self.inspection_date
            if self.next_inspection_date:
                self.vehicle.next_inspection_date = self.next_inspection_date
            self.vehicle.save(update_fields=['last_inspection_date', 'next_inspection_date'])
    
    def get_summary(self):
        """
        Get a summary of the inspection.
        
        Returns:
            dict: Inspection summary
        """
        return {
            'id': self.id,
            'vehicle': str(self.vehicle),
            'inspection_type': self.get_inspection_type_display(),
            'result': self.get_result_display(),
            'inspection_date': self.inspection_date,
            'inspector': str(self.inspected_by) if self.inspected_by else None,
            'total_items': self.total_items,
            'passed_items': self.passed_items,
            'failed_items': self.failed_items,
            'pass_rate': self.pass_rate,
            'follow_up_required': self.follow_up_required,
            'is_completed': self.is_completed,
        }
    
    def to_dict(self):
        """
        Convert inspection to dictionary for API responses.
        
        Returns:
            dict: Complete inspection data
        """
        return {
            'id': self.id,
            'vehicle_id': self.vehicle.id,
            'vehicle_plate': self.vehicle.license_plate,
            'inspection_type': self.inspection_type,
            'inspection_type_display': self.get_inspection_type_display(),
            'result': self.result,
            'result_display': self.get_result_display(),
            'inspected_by': {
                'id': self.inspected_by.id,
                'name': self.inspected_by.get_full_name() if self.inspected_by else None
            } if self.inspected_by else None,
            'inspection_date': self.inspection_date.isoformat(),
            'next_inspection_date': self.next_inspection_date.isoformat() if self.next_inspection_date else None,
            'checklist': self.checklist,
            'findings': self.findings,
            'recommendations': self.recommendations,
            'notes': self.notes,
            'follow_up_required': self.follow_up_required,
            'follow_up_date': self.follow_up_date.isoformat() if self.follow_up_date else None,
            'follow_up_result': self.follow_up_result,
            'photos': self.photos,
            'inspection_report': self.inspection_report.url if self.inspection_report else None,
            'pass_rate': self.pass_rate,
            'summary': self.get_summary(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
    
    # ============================================================
    # Class Methods
    # ============================================================
    
    @classmethod
    def get_recent_for_vehicle(cls, vehicle, limit=5):
        """
        Get recent inspections for a vehicle.
        
        Args:
            vehicle: Vehicle instance
            limit: Number of inspections to return
        
        Returns:
            QuerySet: Recent inspections
        """
        return cls.objects.filter(
            vehicle=vehicle
        ).order_by('-inspection_date')[:limit]
    
    @classmethod
    def get_failed_for_vehicle(cls, vehicle):
        """
        Get failed inspections for a vehicle.
        
        Args:
            vehicle: Vehicle instance
        
        Returns:
            QuerySet: Failed inspections
        """
        return cls.objects.filter(
            vehicle=vehicle,
            result=cls.InspectionResult.FAILED
        ).order_by('-inspection_date')
    
    @classmethod
    def get_pending_for_vehicle(cls, vehicle):
        """
        Get pending inspections for a vehicle.
        
        Args:
            vehicle: Vehicle instance
        
        Returns:
            QuerySet: Pending inspections
        """
        return cls.objects.filter(
            vehicle=vehicle,
            result=cls.InspectionResult.PENDING
        ).order_by('-inspection_date')
    
    @classmethod
    def get_overdue_follow_ups(cls):
        """
        Get inspections with overdue follow-ups.
        
        Returns:
            QuerySet: Inspections with overdue follow-ups
        """
        return cls.objects.filter(
            follow_up_required=True,
            follow_up_date__lt=timezone.now(),
            follow_up_result__isnull=True
        )