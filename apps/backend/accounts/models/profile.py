from django.conf import settings
from django.contrib.postgres.indexes import GinIndex, GistIndex
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.hashers import check_password, make_password

from django_resized import ResizedImageField

from core.models.location import LocationModel
import uuid


def generate_univa_id():
    """
    Generate a unique public Univa identifier.
    """
    return f"UVA-{uuid.uuid4().hex[:12].upper()}"

try:
    from pgvector.django import VectorField
except ImportError:
    VectorField = None
    
    
class UserProfile(LocationModel):
    """
    Centralized user profile.

    Architectural boundary
    ----------------------
    UserProfile owns core user/profile data only.

    This model must NOT depend on feature applications such as:
        - ecommerce
        - transport
        - real_estate
        - social
        - banking
        - loyalty
        - notifications

    Feature-specific business logic belongs in the corresponding
    application services.

    Some fields such as `rating`, `loyalty_points`, social counters,
    and `interest_vector` are currently retained for compatibility.
    Their authoritative domain ownership can be extracted later
    without introducing cross-application imports here.
    """

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    VERIFICATION_STATUS_CHOICES = [
        ("unverified", _("Unverified")),
        ("basic", _("Basic Verification")),
        ("id_verified", _("ID Verified")),
        ("address_verified", _("Address Verified")),
        ("payment_verified", _("Payment Verified")),
        ("premium_verified", _("Premium Verified")),
    ]

    VERIFICATION_LEVELS = {
        "unverified": 0,
        "basic": 1,
        "id_verified": 2,
        "address_verified": 3,
        "payment_verified": 4,
        "premium_verified": 5,
    }

    # ------------------------------------------------------------------
    # Ownership
    # ------------------------------------------------------------------

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    # ------------------------------------------------------------------
    # Personal Information
    # ------------------------------------------------------------------

    profile_picture = ResizedImageField(
        size=[1200, 1200],
        upload_to="profile_pics/",
        quality=90,
        blank=True,
        null=True,
    )

    date_of_birth = models.DateField(
        null=True,
        blank=True,
        db_index=True,
    )

    gender = models.CharField(
        max_length=20,
        choices=[
            ("male", _("Male")),
            ("female", _("Female")),
            ("other", _("Other")),
            ("prefer_not_to_say", _("Prefer not to say")),
        ],
        blank=True,
        db_index=True,
    )

   

    # ------------------------------------------------------------------
    # Verification State
    # ------------------------------------------------------------------

    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS_CHOICES,
        default="unverified",
        db_index=True,
    )

    verification_date = models.DateTimeField(
        null=True,
        blank=True,
    )

    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_profiles",
    )

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------

    id_type = models.CharField(
        max_length=50,
        blank=True,
    )

    id_number = models.CharField(
        max_length=50,
        blank=True,
        db_index=True,
    )

    id_image = ResizedImageField(
        size=[1200, 1200],
        upload_to="user_ids/",
        quality=90,
        blank=True,
        null=True,
    )

    # ------------------------------------------------------------------
    # Generic Profile / Social Compatibility
    #
    # These counters are retained for compatibility. Their authoritative
    # ownership can later move to the social application.
    # ------------------------------------------------------------------

    bio = models.TextField(
        blank=True,
    )

    website = models.URLField(
        blank=True,
    )

    follower_count = models.PositiveIntegerField(
        default=0,
    )

    following_count = models.PositiveIntegerField(
        default=0,
    )

    likes_count = models.PositiveIntegerField(
        default=0,
    )

    video_count = models.PositiveIntegerField(
        default=0,
    )

    # Cached aggregate rating.
    #
    # IMPORTANT:
    # UserProfile does NOT calculate this.
    # Rating/analytics services are responsible for updating it.
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=5.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(5),
        ],
    )

    # ------------------------------------------------------------------
    # Generic Business Identity
    # ------------------------------------------------------------------

    is_business = models.BooleanField(
        default=False,
    )

    company_name = models.CharField(
        max_length=120,
        blank=True,
    )

    univa_id = models.CharField(
        max_length=50,
        unique=True,
        default=generate_univa_id,
        editable=False,
        db_index=True,
        help_text=_("Unique public Univa identifier."),
    )
   

    # ------------------------------------------------------------------
    # Preferences
    # ------------------------------------------------------------------

    
    language_code = models.CharField(
        max_length=35,
        choices=settings.LANGUAGES,
        default="en",
    )

    preferred_notification_method = models.CharField(
        max_length=20,
        choices=[
            ("email", _("Email")),
            ("sms", _("SMS")),
            ("push", _("Push Notification")),
            ("whatsapp", _("WhatsApp")),
        ],
        default="email",
        db_index=True,
    )

    # ------------------------------------------------------------------
    # Loyalty / Recommendation Compatibility
    #
    # These are intentionally retained during the restructuring phase.
    # Loyalty will eventually own the authoritative points balance.
    # Recommendation/analytics can eventually own the interest vector.
    # ------------------------------------------------------------------

    loyalty_points = models.PositiveIntegerField(
        default=0,
    )

    interest_vector = (
        VectorField(
            null=True,
            blank=True,
        )
        if VectorField
        else models.JSONField(
            null=True,
            blank=True,
        )
    )

    # ------------------------------------------------------------------
    # Activity / Presence
    # ------------------------------------------------------------------

    last_active = models.DateTimeField(
        auto_now=True,
        db_index=True,
    )

    is_online = models.BooleanField(
        default=False,
        db_index=True,
    )

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    # ------------------------------------------------------------------
    # Additional
    # ------------------------------------------------------------------

    note = models.TextField(
        blank=True,
    )

    search_document = models.TextField(
        blank=True,
        default="",
    )

    # ------------------------------------------------------------------
    # Model Meta
    # ------------------------------------------------------------------

    class Meta:
        ordering = ["-last_active"]

        constraints = [
            models.UniqueConstraint(
                fields=["id_type", "id_number"],
                condition=(
                    models.Q(id_type__gt="")
                    & models.Q(id_number__gt="")
                ),
                name="unique_profile_identity_document",
            ),
        ]

        indexes = [
            GinIndex(
                fields=["search_document"],
                name="profile_search_gin",
                opclasses=["gin_trgm_ops"],
            ),
            GistIndex(
                fields=["location_point"],
                name="user_location_gist_idx",
            ),
            models.Index(
                fields=["is_online", "last_active"],
                name="profile_online_active_idx",
            ),
            models.Index(
                fields=["verification_status"],
                name="profile_verification_idx",
            ),
            models.Index(
                fields=["date_of_birth"],
                name="profile_dob_idx",
            ),
        ]

        verbose_name = _("User Profile")
        verbose_name_plural = _("User Profiles")


    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __str__(self):
        return f"Profile for {self.user}"

    

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    @property
    def is_verified(self):
        """
        Backward-compatible verification status property.
        """
        return self.verification_status != "unverified"

    @property
    def verification_level(self):
        """
        Numeric verification level.

        0 = Unverified
        1 = Basic
        2 = ID verified
        3 = Address verified
        4 = Payment verified
        5 = Premium verified
        """
        return self.VERIFICATION_LEVELS.get(
            self.verification_status,
            0,
        )

    def get_verification_badge(self):
        """
        Return the human-readable verification status.

        Kept as a method for backward compatibility with existing
        GraphQL/API/frontend consumers.
        """
        return dict(
            self.VERIFICATION_STATUS_CHOICES
        ).get(
            self.verification_status,
            _("Unknown"),
        )

    def verify(self, status, verified_by=None):
        """
        Update the user's verification status.
        """
        valid_statuses = dict(
            self.VERIFICATION_STATUS_CHOICES
        )

        if status not in valid_statuses:
            raise ValidationError(
                _("Invalid verification status: %(status)s"),
                params={
                    "status": status,
                },
            )

        self.verification_status = status
        self.verification_date = timezone.now()
        self.verified_by = verified_by

        self.save(
            update_fields=[
                "verification_status",
                "verification_date",
                "verified_by",
                "updated_at",
            ]
        )

    # ------------------------------------------------------------------
    # Location
    # ------------------------------------------------------------------

    def update_location(
        self,
        latitude,
        longitude,
        address=None,
    ):
        """
        Update the profile's geographic location.

        LocationModel owns geographic coordinates.
        UserProfile optionally stores the human-readable address.
        """
        super().update_location(
            latitude,
            longitude,
        )

        if address is not None:
            self.location = address

            self.save(
                update_fields=[
                    "location",
                    "updated_at",
                ]
            )

    # ------------------------------------------------------------------
    # Derived Identity Helpers
    # ------------------------------------------------------------------

    @property
    def age(self):
        """
        Calculate the user's current age from date of birth.
        """
        if not self.date_of_birth:
            return None

        today = timezone.now().date()

        return (
            today.year
            - self.date_of_birth.year
            - (
                (today.month, today.day)
                < (
                    self.date_of_birth.month,
                    self.date_of_birth.day,
                )
            )
        )

    @property
    def display_name(self):
        """
        Return the best available human-readable display name.
        """
        first_name = (self.user.first_name or "").strip()
        last_name = (self.user.last_name or "").strip()

        if first_name and last_name:
            return f"{first_name} {last_name}"

        if first_name:
            return first_name

        if last_name:
            return last_name

        if self.univa_id:
            return f"@{self.univa_id}"

        return (
            self.user.email
            or str(self.user.phone_number or "")
            or _("User")
        )