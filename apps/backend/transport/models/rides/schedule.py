import uuid

from django.db import models
from django.utils import timezone


class TripScheduleTemplate(models.Model):
    """Schedule Template for recurring trips"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    route_name = models.CharField(max_length=255)
    departure_state = models.CharField(max_length=100)
    departure_city = models.CharField(max_length=100)
    destination_state = models.CharField(max_length=100)
    destination_city = models.CharField(max_length=100)
    departure_time = models.TimeField(help_text="Local departure time (HH:MM)")
    days_of_week = models.JSONField(default=list, help_text="List of weekdays e.g. [0,1,2] Monday=0")
    vehicle_type = models.CharField(max_length=50, blank=True, null=True)
    base_fare = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["departure_state", "destination_state"]),
            models.Index(fields=["active"]),
        ]

    def __str__(self):
        return f"{self.route_name} ({self.departure_city}→{self.destination_city})"

    def instantiate_for_date(self, date):
        """Create Trip instance for a specific date"""
        from django.contrib.gis.geos import Point

        from .trip import Trip
        
        dt = timezone.datetime.combine(date, self.departure_time)
        trip = Trip.objects.create(
            customer=None,
            service_type=Trip.ServiceType.INTERSTATE,
            departure_state=self.departure_state,
            departure_city=self.departure_city,
            destination_state=self.destination_state,
            destination_city=self.destination_city,
            departure_time=timezone.make_aware(dt),
            base_fare=self.base_fare,
            total_fare=self.base_fare,
            is_recurring_daily=False,
            shared=True,
            available_seats=12,
        )
        return trip