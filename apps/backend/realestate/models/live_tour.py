 # apps/backend/realestate/models/live_tour.py

"""
Live Tour Schedule model for real estate.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone


class LiveTourSchedule(models.Model):
    property = models.ForeignKey("Listing", on_delete=models.CASCADE, related_name="live_tours")
    agent = models.ForeignKey("Agent", on_delete=models.CASCADE, related_name="as_agent")
    scheduled_time = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=30)
    meeting_link = models.URLField()
    max_attendees = models.PositiveIntegerField(default=10)
    attendees = models.ManyToManyField(settings.AUTH_USER_MODEL, through='LiveTourRegistration')

    class Meta:
        ordering = ["scheduled_time"]
        indexes = [
            models.Index(fields=["property", "scheduled_time"], name="live_tour_property_time_idx"),
            models.Index(fields=["agent", "scheduled_time"], name="live_tour_agent_time_idx"),
        ]

    def __str__(self):
        return f"{self.property.title} - {self.scheduled_time.strftime('%Y-%m-%d %H:%M')}"

    def is_past(self):
        return self.scheduled_time < timezone.now()

    def is_upcoming(self):
        return self.scheduled_time > timezone.now()

    def is_ongoing(self):
        return self.scheduled_time <= timezone.now() <= (self.scheduled_time + timezone.timedelta(minutes=self.duration_minutes))

    def is_fully_booked(self):
        return self.attendees.count() >= self.max_attendees