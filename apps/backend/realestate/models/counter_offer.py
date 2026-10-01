
# apps/backend/realestate/models/counter_offer.py

"""
Counter Offer model for real estate.
"""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class CounterOffer(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"), ("accepted", "Accepted"), ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"), ("expired", "Expired"),
    ]

    original_offer = models.ForeignKey("Offer", on_delete=models.CASCADE, related_name="counter_offers")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, 
                                   related_name="created_counter_offers")
    counter_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    expiration_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["original_offer", "created_at"], name="counter_offer_original_idx"),
            models.Index(fields=["status"], name="counter_offer_sta_idx"),
            models.Index(fields=["expiration_date"], name="counter_offer_expire_idx"),
        ]

    def __str__(self):
        return f"Counter {self.counter_price} for Offer #{self.original_offer_id}"

    def is_expired(self):
        return self.expiration_date and timezone.now() > self.expiration_date