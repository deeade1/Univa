"""
GraphQL filtering for the Accounts UserProfile model.

Architecture
------------
Filtering belongs to this module.

This module is responsible for:
    - declarative UserProfile filtering
    - safe public profile filters
    - related User filtering
    - location filtering
    - verification filtering
    - activity filtering

This module must NOT:
    - perform mutations
    - contain authentication logic
    - expose PIN/security credentials
    - expose identity-document credentials
    - implement domain business rules
    - import feature applications

Graphene:
    3.2.3

Relay:
    Global Relay Node IDs
"""

import django_filters
from django.contrib.auth import get_user_model
from django.db.models import Q

from accounts.models.profile import UserProfile


User = get_user_model()


# ============================================================================
# Choice constants
# ============================================================================

VERIFICATION_STATUS_CHOICES = tuple(
    UserProfile.VERIFICATION_STATUS_CHOICES
)


# ============================================================================
# UserProfile Filter
# ============================================================================

class UserProfileFilter(django_filters.FilterSet):
    """
    FilterSet for UserProfile.

    The filters intentionally expose only fields that are appropriate
    for GraphQL querying.

    Sensitive profile fields such as:

        pin_hash
        id_number
        id_image

    are never included.
    """

    # ------------------------------------------------------------------
    # Primary / relationship filters
    # ------------------------------------------------------------------

    id = django_filters.NumberFilter(
        field_name="id",
        lookup_expr="exact",
    )

    user_id = django_filters.NumberFilter(
        field_name="user__id",
        lookup_expr="exact",
    )

    user_email = django_filters.CharFilter(
        field_name="user__email",
        lookup_expr="iexact",
    )

    # ------------------------------------------------------------------
    # Name search
    # ------------------------------------------------------------------

    name = django_filters.CharFilter(
        method="filter_name",
    )

    # ------------------------------------------------------------------
    # Public identity
    # ------------------------------------------------------------------

    univa_id = django_filters.CharFilter(
        field_name="univa_id",
        lookup_expr="iexact",
    )

    univa_id_contains = django_filters.CharFilter(
        field_name="univa_id",
        lookup_expr="icontains",
    )

    company_name = django_filters.CharFilter(
        field_name="company_name",
        lookup_expr="icontains",
    )

    is_business = django_filters.BooleanFilter(
        field_name="is_business",
    )

    # ------------------------------------------------------------------
    # Personal profile
    # ------------------------------------------------------------------

    gender = django_filters.CharFilter(
        field_name="gender",
        lookup_expr="exact",
    )

    date_of_birth = django_filters.DateFilter(
        field_name="date_of_birth",
        lookup_expr="exact",
    )

    date_of_birth_after = django_filters.DateFilter(
        field_name="date_of_birth",
        lookup_expr="gte",
    )

    date_of_birth_before = django_filters.DateFilter(
        field_name="date_of_birth",
        lookup_expr="lte",
    )

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    verification_status = django_filters.ChoiceFilter(
        field_name="verification_status",
        choices=VERIFICATION_STATUS_CHOICES,
    )

    verification_status_in = django_filters.MultipleChoiceFilter(
        field_name="verification_status",
        choices=VERIFICATION_STATUS_CHOICES,
        lookup_expr="in",
    )

    is_verified = django_filters.BooleanFilter(
        method="filter_is_verified",
    )

    # ------------------------------------------------------------------
    # Business / profile activity
    # ------------------------------------------------------------------

    is_online = django_filters.BooleanFilter(
        field_name="is_online",
    )

    last_active_after = django_filters.IsoDateTimeFilter(
        field_name="last_active",
        lookup_expr="gte",
    )

    last_active_before = django_filters.IsoDateTimeFilter(
        field_name="last_active",
        lookup_expr="lte",
    )

    # ------------------------------------------------------------------
    # Rating
    # ------------------------------------------------------------------

    rating_min = django_filters.NumberFilter(
        field_name="rating",
        lookup_expr="gte",
    )

    rating_max = django_filters.NumberFilter(
        field_name="rating",
        lookup_expr="lte",
    )

    # ------------------------------------------------------------------
    # Social aggregate fields
    # ------------------------------------------------------------------

    follower_count_min = django_filters.NumberFilter(
        field_name="follower_count",
        lookup_expr="gte",
    )

    follower_count_max = django_filters.NumberFilter(
        field_name="follower_count",
        lookup_expr="lte",
    )

    following_count_min = django_filters.NumberFilter(
        field_name="following_count",
        lookup_expr="gte",
    )

    following_count_max = django_filters.NumberFilter(
        field_name="following_count",
        lookup_expr="lte",
    )

    # ------------------------------------------------------------------
    # Location
    # ------------------------------------------------------------------

    country = django_filters.CharFilter(
        field_name="location",
        lookup_expr="icontains",
    )

    location_contains = django_filters.CharFilter(
        field_name="location",
        lookup_expr="icontains",
    )

    latitude_min = django_filters.NumberFilter(
        field_name="latitude",
        lookup_expr="gte",
    )

    latitude_max = django_filters.NumberFilter(
        field_name="latitude",
        lookup_expr="lte",
    )

    longitude_min = django_filters.NumberFilter(
        field_name="longitude",
        lookup_expr="gte",
    )

    longitude_max = django_filters.NumberFilter(
        field_name="longitude",
        lookup_expr="lte",
    )

    has_location = django_filters.BooleanFilter(
        method="filter_has_location",
    )

    # ------------------------------------------------------------------
    # Preferences
    # ------------------------------------------------------------------

    language_code = django_filters.CharFilter(
        field_name="language_code",
        lookup_expr="exact",
    )

    preferred_notification_method = django_filters.CharFilter(
        field_name="preferred_notification_method",
        lookup_expr="exact",
    )

    # ------------------------------------------------------------------
    # Loyalty compatibility
    # ------------------------------------------------------------------

    loyalty_points_min = django_filters.NumberFilter(
        field_name="loyalty_points",
        lookup_expr="gte",
    )

    loyalty_points_max = django_filters.NumberFilter(
        field_name="loyalty_points",
        lookup_expr="lte",
    )

    # ------------------------------------------------------------------
    # Created / updated timestamps
    # ------------------------------------------------------------------

    created_after = django_filters.IsoDateTimeFilter(
        field_name="created_at",
        lookup_expr="gte",
    )

    created_before = django_filters.IsoDateTimeFilter(
        field_name="created_at",
        lookup_expr="lte",
    )

    updated_after = django_filters.IsoDateTimeFilter(
        field_name="updated_at",
        lookup_expr="gte",
    )

    updated_before = django_filters.IsoDateTimeFilter(
        field_name="updated_at",
        lookup_expr="lte",
    )

    # ------------------------------------------------------------------
    # Meta
    # ------------------------------------------------------------------

    class Meta:
        model = UserProfile

        fields = (
            "id",
            "user_id",
            "user_email",
            "name",
            "univa_id",
            "univa_id_contains",
            "company_name",
            "is_business",
            "gender",
            "date_of_birth",
            "date_of_birth_after",
            "date_of_birth_before",
            "verification_status",
            "verification_status_in",
            "is_verified",
            "is_online",
            "last_active_after",
            "last_active_before",
            "rating_min",
            "rating_max",
            "follower_count_min",
            "follower_count_max",
            "following_count_min",
            "following_count_max",
            "location_contains",
            "latitude_min",
            "latitude_max",
            "longitude_min",
            "longitude_max",
            "has_location",
            "language_code",
            "preferred_notification_method",
            "loyalty_points_min",
            "loyalty_points_max",
            "created_after",
            "created_before",
            "updated_after",
            "updated_before",
        )

    # =========================================================================
    # Custom filters
    # =========================================================================

    def filter_name(self, queryset, name, value):
        """
        Search the user's first name, last name, email, and public Univa ID.

        This is intentionally a public/profile-level search and does not
        inspect sensitive identity fields.
        """

        if not value:
            return queryset

        value = value.strip()

        if not value:
            return queryset

        return queryset.filter(
            Q(user__first_name__icontains=value)
            | Q(user__last_name__icontains=value)
            | Q(user__email__icontains=value)
            | Q(univa_id__icontains=value)
            | Q(company_name__icontains=value)
        ).distinct()

    def filter_is_verified(self, queryset, name, value):
        """
        Filter profiles by verification state.

        A profile is considered verified when its verification status
        is anything other than ``unverified``.
        """

        if value is None:
            return queryset

        if value:
            return queryset.exclude(
                verification_status="unverified",
            )

        return queryset.filter(
            verification_status="unverified",
        )

    def filter_has_location(self, queryset, name, value):
        """
        Filter profiles based on whether geographic coordinates exist.
        """

        if value is None:
            return queryset

        if value:
            return queryset.filter(
                latitude__isnull=False,
                longitude__isnull=False,
                location_point__isnull=False,
            )

        return queryset.filter(
            Q(latitude__isnull=True)
            | Q(longitude__isnull=True)
            | Q(location_point__isnull=True)
        )