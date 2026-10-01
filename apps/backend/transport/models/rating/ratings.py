# transport/models/rating/ratings.py

"""
Rating models for providers, customers, and shared trips.
Updated with proper constraints and relationships.
"""

import logging
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class Rating(models.Model):
    """
    User ratings for shared trips.
    Kept for backward compatibility.
    """
    
    RATING_CHOICES = [
        (1, '1 - Poor'),
        (2, '2 - Fair'),
        (3, '3 - Good'),
        (4, '4 - Very Good'),
        (5, '5 - Excellent'),
    ]
    
    rater = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='given_ratings',
        db_index=True,
        help_text=_("User giving the rating")
    )
    
    rated_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_ratings',
        db_index=True,
        help_text=_("User being rated")
    )
    
    trip = models.ForeignKey(
        'transport.ServiceRequest',
        on_delete=models.CASCADE,
        related_name='ratings',
        db_index=True,
        help_text=_("Trip being rated")
    )
    
    score = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text=_("Rating score (1-5)")
    )
    
    comment = models.TextField(
        blank=True,
        help_text=_("Optional comment")
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text=_("When rating was created")
    )
    
    class Meta:
        verbose_name = _("Rating")
        verbose_name_plural = _("Ratings")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['rater', 'rated_user']),
            models.Index(fields=['trip']),
            models.Index(fields=['score']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['rater', 'rated_user', 'trip'],
                name='rating_unique_rater_rated_user_trip'
            )
        ]
    
    def __str__(self):
        return f"{self.rater.email} rated {self.rated_user.email}: {self.score}/5"
    
    @property
    def rating_display(self):
        """Get human-readable rating display."""
        return dict(self.RATING_CHOICES).get(self.score, str(self.score))


class ProviderRating(models.Model):
    """
    Comprehensive rating for service providers with multiple criteria.
    """
    
    # ============================================================
    # Relationships
    # ============================================================
    
    provider = models.ForeignKey(
        'transport.ServiceProviderProfile',
        on_delete=models.CASCADE,
        related_name='provider_ratings',
        db_index=True,
        help_text=_("Provider being rated")
    )
    
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='provider_ratings_given',
        db_index=True,
        help_text=_("Customer giving the rating")
    )
    
    service_request = models.ForeignKey(
        'transport.ServiceRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='provider_ratings',
        db_index=True,
        help_text=_("Service request being rated")
    )
    
    # ============================================================
    # Rating Scores (1-5)
    # ============================================================
    
    overall_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text=_("Overall rating (1-5)")
    )
    
    punctuality = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text=_("Punctuality rating (1-5)")
    )
    
    professionalism = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text=_("Professionalism rating (1-5)")
    )
    
    communication = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text=_("Communication rating (1-5)")
    )
    
    service_quality = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text=_("Service quality rating (1-5)")
    )
    
    value_for_money = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text=_("Value for money rating (1-5)")
    )
    
    vehicle_condition = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text=_("Vehicle condition rating (1-5)")
    )
    
    safety = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text=_("Safety rating (1-5)")
    )
    
    # ============================================================
    # Review and Media
    # ============================================================
    
    review = models.TextField(
        blank=True,
        help_text=_("Written review")
    )
    
    photos = models.JSONField(
        default=list,
        blank=True,
        help_text=_("List of photo URLs")
    )
    
    # ============================================================
    # Provider Response
    # ============================================================
    
    provider_response = models.TextField(
        blank=True,
        help_text=_("Provider's response to rating")
    )
    
    provider_response_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When provider responded")
    )
    
    # ============================================================
    # Status
    # ============================================================
    
    is_verified = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Whether rating is verified (customer had actual service)")
    )
    
    is_public = models.BooleanField(
        default=True,
        db_index=True,
        help_text=_("Whether rating is public")
    )
    
    is_edited = models.BooleanField(
        default=False,
        help_text=_("Whether rating has been edited")
    )
    
    edit_history = models.JSONField(
        default=list,
        blank=True,
        help_text=_("History of edits made to this rating")
    )
    
    # ============================================================
    # Metadata
    # ============================================================
    
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Additional rating metadata")
    )
    
    # ============================================================
    # Timestamps
    # ============================================================
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text=_("When rating was created")
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text=_("When rating was last updated")
    )
    
    # ============================================================
    # Meta
    # ============================================================
    
    class Meta:
        verbose_name = _("Provider Rating")
        verbose_name_plural = _("Provider Ratings")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['provider']),
            models.Index(fields=['customer']),
            models.Index(fields=['service_request']),
            models.Index(fields=['is_verified', 'is_public']),
            models.Index(fields=['overall_rating']),
        ]
        constraints = [
            # Ensure one rating per customer-provider-service_request
            models.UniqueConstraint(
                fields=['provider', 'customer', 'service_request'],
                name='provider_rating_unique'
            ),
            # Ensure rating is within valid range
            models.CheckConstraint(
                condition=models.Q(overall_rating__gte=1, overall_rating__lte=5),
                name='provider_rating_valid_overall'
            ),
        ]
    
    def __str__(self):
        return f"{self.customer.email} rated {self.provider} - {self.overall_rating}/5"
    
    # ============================================================
    # Properties
    # ============================================================
    
    @property
    def average_score(self):
        """
        Calculate average of all rating categories.
        """
        scores = [
            self.overall_rating,
            self.punctuality,
            self.professionalism,
            self.communication,
            self.service_quality,
            self.value_for_money,
            self.vehicle_condition,
            self.safety,
        ]
        valid_scores = [s for s in scores if s is not None]
        if valid_scores:
            return round(sum(valid_scores) / len(valid_scores), 2)
        return float(self.overall_rating)
    
    @property
    def is_high_rating(self):
        """Check if rating is 4 or above."""
        return self.overall_rating >= 4
    
    @property
    def is_low_rating(self):
        """Check if rating is 2 or below."""
        return self.overall_rating <= 2
    
    @property
    def rating_summary(self):
        """Get a summary of the rating."""
        return {
            'overall': self.overall_rating,
            'average': self.average_score,
            'categories': {
                'punctuality': self.punctuality,
                'professionalism': self.professionalism,
                'communication': self.communication,
                'service_quality': self.service_quality,
                'value_for_money': self.value_for_money,
                'vehicle_condition': self.vehicle_condition,
                'safety': self.safety,
            }
        }
    
    # ============================================================
    # Methods
    # ============================================================
    
    def respond(self, response_text):
        """
        Add a provider response to this rating.
        
        Args:
            response_text: Provider's response
        """
        self.provider_response = response_text
        self.provider_response_at = timezone.now()
        self.save(update_fields=['provider_response', 'provider_response_at'])
    
    def edit_rating(self, **updated_fields):
        """
        Edit the rating (customer can edit their rating).
        
        Args:
            **updated_fields: Fields to update
        """
        # Store edit history
        if not self.edit_history:
            self.edit_history = []
        
        self.edit_history.append({
            'timestamp': timezone.now().isoformat(),
            'previous_values': {
                'overall_rating': float(self.overall_rating),
                'review': self.review,
                'punctuality': float(self.punctuality) if self.punctuality else None,
                'professionalism': float(self.professionalism) if self.professionalism else None,
                'communication': float(self.communication) if self.communication else None,
                'service_quality': float(self.service_quality) if self.service_quality else None,
                'value_for_money': float(self.value_for_money) if self.value_for_money else None,
                'vehicle_condition': float(self.vehicle_condition) if self.vehicle_condition else None,
                'safety': float(self.safety) if self.safety else None,
            }
        })
        
        # Update fields
        for key, value in updated_fields.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        self.is_edited = True
        self.save()
    
    def verify(self):
        """Mark this rating as verified."""
        self.is_verified = True
        self.save(update_fields=['is_verified'])
    
    def to_dict(self):
        """
        Convert rating to dictionary for API responses.
        """
        return {
            'id': self.id,
            'provider': {
                'id': self.provider.id,
                'name': self.provider.display_name,
            },
            'customer': {
                'id': self.customer.id,
                'name': self.customer.get_full_name() or self.customer.email,
            },
            'service_request': self.service_request.id if self.service_request else None,
            'overall_rating': self.overall_rating,
            'average_score': self.average_score,
            'categories': {
                'punctuality': self.punctuality,
                'professionalism': self.professionalism,
                'communication': self.communication,
                'service_quality': self.service_quality,
                'value_for_money': self.value_for_money,
                'vehicle_condition': self.vehicle_condition,
                'safety': self.safety,
            },
            'review': self.review,
            'photos': self.photos,
            'provider_response': self.provider_response,
            'provider_response_at': self.provider_response_at,
            'is_verified': self.is_verified,
            'is_public': self.is_public,
            'is_edited': self.is_edited,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

class CustomerRating(models.Model):
    """
    Rating for customers by providers.
    """
    
    # ============================================================
    # Relationships
    # ============================================================
    
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='customer_ratings',
        db_index=True,
        help_text=_("Customer being rated")
    )
    
    provider = models.ForeignKey(
        'transport.ServiceProviderProfile',
        on_delete=models.CASCADE,
        related_name='customer_ratings_given',
        db_index=True,
        help_text=_("Provider giving the rating")
    )
    
    service_request = models.ForeignKey(
        'transport.ServiceRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customer_ratings',
        db_index=True,
        help_text=_("Service request being rated")
    )
    
    # ============================================================
    # Rating Scores
    # ============================================================
    
    overall_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text=_("Overall rating (1-5)")
    )
    
    punctuality = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text=_("Customer punctuality (1-5)")
    )
    
    communication = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text=_("Communication rating (1-5)")
    )
    
    behavior = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text=_("Customer behavior (1-5)")
    )
    
    respect = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text=_("Respectfulness (1-5)")
    )
    
    # ============================================================
    # Review
    # ============================================================
    
    review = models.TextField(
        blank=True,
        help_text=_("Review of the customer")
    )
    
    # ============================================================
    # Status
    # ============================================================
    
    is_public = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Whether rating is public")
    )
    
    is_edited = models.BooleanField(
        default=False,
        help_text=_("Whether rating has been edited")
    )
    
    # ============================================================
    # Timestamps
    # ============================================================
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text=_("When rating was created")
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text=_("When rating was last updated")
    )
    
    # ============================================================
    # Meta
    # ============================================================
    
    class Meta:
        verbose_name = _("Customer Rating")
        verbose_name_plural = _("Customer Ratings")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer']),
            models.Index(fields=['provider']),
            models.Index(fields=['service_request']),
            models.Index(fields=['overall_rating']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['customer', 'provider', 'service_request'],
                name='customer_rating_unique'
            ),
            models.CheckConstraint(
                condition=models.Q(overall_rating__gte=1, overall_rating__lte=5),
                name='customer_rating_valid_overall'
            ),
        ]
    
    def __str__(self):
        return f"Rating for {self.customer.email} - {self.overall_rating}/5"
    
    @property
    def average_score(self):
        """
        Calculate average of all rating categories.
        """
        scores = [
            self.overall_rating,
            self.punctuality,
            self.communication,
            self.behavior,
            self.respect,
        ]
        valid_scores = [s for s in scores if s is not None]
        if valid_scores:
            return round(sum(valid_scores) / len(valid_scores), 2)
        return float(self.overall_rating)
    
    @property
    def is_high_rating(self):
        """Check if rating is 4 or above."""
        return self.overall_rating >= 4
    
    @property
    def is_low_rating(self):
        """Check if rating is 2 or below."""
        return self.overall_rating <= 2
    
    def to_dict(self):
        """
        Convert rating to dictionary for API responses.
        """
        return {
            'id': self.id,
            'customer': {
                'id': self.customer.id,
                'name': self.customer.get_full_name() or self.customer.email,
            },
            'provider': {
                'id': self.provider.id,
                'name': self.provider.display_name,
            },
            'service_request': self.service_request.id if self.service_request else None,
            'overall_rating': self.overall_rating,
            'average_score': self.average_score,
            'categories': {
                'punctuality': self.punctuality,
                'communication': self.communication,
                'behavior': self.behavior,
                'respect': self.respect,
            },
            'review': self.review,
            'is_public': self.is_public,
            'is_edited': self.is_edited,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }


# ============================================================
# Utility Functions
# ============================================================

def update_provider_rating(provider):
    """
    Update a provider's overall rating based on all their ratings.
    
    Args:
        provider: ServiceProviderProfile instance
    
    Returns:
        Decimal: New average rating
    """
    from django.db.models import Avg
    
    avg = ProviderRating.objects.filter(
        provider=provider,
        is_public=True,
        is_verified=True
    ).aggregate(
        avg=Avg('overall_rating')
    )['avg']
    
    if avg is not None:
        avg = round(avg, 2)
        provider.rating = avg
        provider.total_ratings = ProviderRating.objects.filter(
            provider=provider,
            is_public=True,
            is_verified=True
        ).count()
        provider.save(update_fields=['rating', 'total_ratings'])
    
    return avg