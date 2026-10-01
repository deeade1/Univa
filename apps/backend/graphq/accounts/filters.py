"""
GraphQL filters for the Accounts domain.

Architecture
------------

GraphQL
    ↓
django-filter
    ↓
Django QuerySet
    ↓
accounts models

This module contains filtering rules only.

It must NOT contain:
    - mutation logic
    - authentication logic
    - authorization logic
    - business-domain logic
    - ecommerce logic
    - transport logic
    - real estate logic
    - banking logic
    - loyalty logic
    - biometrics logic

Graphene:
    Graphene 3.2.3
    Relay
"""

from django.contrib.auth import get_user_model
from django.db.models import Q
from django_filters import rest_framework as filters

from accounts.models import (
    Address,
    Role,
    UserProfile,
    UserRole,
)


User = get_user_model()


# ============================================================================
# COMMON FILTER HELPERS
# ============================================================================


class CharInFilter(filters.BaseInFilter, filters.CharFilter):
    """
    Filter accepting multiple character values.

    Example:

        ?verification_status__in=basic,id_verified
    """

    pass


class NumberInFilter(filters.BaseInFilter, filters.NumberFilter):
    """
    Filter accepting multiple numeric values.
    """

    pass


# ============================================================================
# USER FILTER
# ============================================================================


class UserFilter(filters.FilterSet):
    """
    Filters for the centralized User model.

    Only identity/account-level fields belong here.

    Feature-specific filtering must live in the corresponding application.
    """

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    email = filters.CharFilter(
        field_name="email",
        lookup_expr="iexact",
    )

    email_contains = filters.CharFilter(
        field_name="email",
        lookup_expr="icontains",
    )

    phone_number = filters.CharFilter(
        field_name="phone_number",
        lookup_expr="exact",
    )

    phone_contains = filters.CharFilter(
        field_name="phone_number",
        lookup_expr="icontains",
    )

    # ------------------------------------------------------------------
    # Names
    # ------------------------------------------------------------------

    first_name = filters.CharFilter(
        field_name="first_name",
        lookup_expr="iexact",
    )

    first_name_contains = filters.CharFilter(
        field_name="first_name",
        lookup_expr="icontains",
    )

    last_name = filters.CharFilter(
        field_name="last_name",
        lookup_expr="iexact",
    )

    last_name_contains = filters.CharFilter(
        field_name="last_name",
        lookup_expr="icontains",
    )

    # ------------------------------------------------------------------
    # Account state
    # ------------------------------------------------------------------

    is_active = filters.BooleanFilter(
        field_name="is_active",
    )

    is_staff = filters.BooleanFilter(
        field_name="is_staff",
    )

    is_superuser = filters.BooleanFilter(
        field_name="is_superuser",
    )

    email_verified = filters.BooleanFilter(
        field_name="email_verified",
    )

    # ------------------------------------------------------------------
    # Dates
    # ------------------------------------------------------------------

    date_joined = filters.DateTimeFilter(
        field_name="date_joined",
        lookup_expr="exact",
    )

    date_joined_after = filters.DateTimeFilter(
        field_name="date_joined",
        lookup_expr="gte",
    )

    date_joined_before = filters.DateTimeFilter(
        field_name="date_joined",
        lookup_expr="lte",
    )

    # ------------------------------------------------------------------
    # Role filtering
    #
    # These use relationships already defined by the account models.
    # ------------------------------------------------------------------

    role = filters.CharFilter(
        method="filter_role",
    )

    app = filters.CharFilter(
        method="filter_app",
    )

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    search = filters.CharFilter(
        method="filter_search",
    )

    class Meta:
        model = User

        fields = [
            "email",
            "phone_number",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "is_superuser",
            "email_verified",
            "date_joined",
        ]

    # ------------------------------------------------------------------
    # Custom role filters
    # ------------------------------------------------------------------

    def filter_role(self, queryset, name, value):
        """
        Filter users by role name.
        """

        if not value:
            return queryset

        return queryset.filter(
            user_roles__role__name__iexact=value,
            user_roles__is_active=True,
            user_roles__revoked_at__isnull=True,
        ).distinct()

    def filter_app(self, queryset, name, value):
        """
        Filter users who have an active role in an application.
        """

        if not value:
            return queryset

        return queryset.filter(
            user_roles__role__app_name=value,
            user_roles__is_active=True,
            user_roles__revoked_at__isnull=True,
        ).distinct()

    def filter_search(self, queryset, name, value):
        """
        General account identity search.

        Searches:
            email
            phone number
            first name
            last name
        """

        if not value:
            return queryset

        value = value.strip()

        if not value:
            return queryset

        return queryset.filter(
            Q(email__icontains=value)
            | Q(phone_number__icontains=value)
            | Q(first_name__icontains=value)
            | Q(last_name__icontains=value)
        ).distinct()


# ============================================================================
# USER PROFILE FILTER
# ============================================================================


class UserProfileFilter(filters.FilterSet):
    """
    Filters for centralized UserProfile data.

    Feature-specific profile data must not be added here.
    """

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    verification_status = filters.CharFilter(
        field_name="verification_status",
        lookup_expr="exact",
    )

    verification_status_in = CharInFilter(
        field_name="verification_status",
        lookup_expr="in",
    )

    is_verified = filters.BooleanFilter(
        method="filter_is_verified",
    )

    verification_level = filters.NumberFilter(
        method="filter_verification_level",
    )

    # ------------------------------------------------------------------
    # Personal profile
    # ------------------------------------------------------------------

    gender = filters.CharFilter(
        field_name="gender",
        lookup_expr="exact",
    )

    date_of_birth = filters.DateFilter(
        field_name="date_of_birth",
        lookup_expr="exact",
    )

    date_of_birth_after = filters.DateFilter(
        field_name="date_of_birth",
        lookup_expr="gte",
    )

    date_of_birth_before = filters.DateFilter(
        field_name="date_of_birth",
        lookup_expr="lte",
    )

    # ------------------------------------------------------------------
    # Business identity
    # ------------------------------------------------------------------

    is_business = filters.BooleanFilter(
        field_name="is_business",
    )

    company_name = filters.CharFilter(
        field_name="company_name",
        lookup_expr="iexact",
    )

    company_name_contains = filters.CharFilter(
        field_name="company_name",
        lookup_expr="icontains",
    )

    univa_id = filters.CharFilter(
        field_name="univa_id",
        lookup_expr="iexact",
    )

    univa_id_contains = filters.CharFilter(
        field_name="univa_id",
        lookup_expr="icontains",
    )

    # ------------------------------------------------------------------
    # Presence
    # ------------------------------------------------------------------

    is_online = filters.BooleanFilter(
        field_name="is_online",
    )

    last_active_after = filters.DateTimeFilter(
        field_name="last_active",
        lookup_expr="gte",
    )

    last_active_before = filters.DateTimeFilter(
        field_name="last_active",
        lookup_expr="lte",
    )

    # ------------------------------------------------------------------
    # Rating
    # ------------------------------------------------------------------

    rating_min = filters.NumberFilter(
        field_name="rating",
        lookup_expr="gte",
    )

    rating_max = filters.NumberFilter(
        field_name="rating",
        lookup_expr="lte",
    )

    # ------------------------------------------------------------------
    # Notification preference
    # ------------------------------------------------------------------

    preferred_notification_method = filters.CharFilter(
        field_name="preferred_notification_method",
        lookup_expr="exact",
    )

    # ------------------------------------------------------------------
    # Language
    # ------------------------------------------------------------------

    language_code = filters.CharFilter(
        field_name="language_code",
        lookup_expr="exact",
    )

    # ------------------------------------------------------------------
    # Location
    # ------------------------------------------------------------------

    location_source = filters.CharFilter(
        field_name="location_source",
        lookup_expr="exact",
    )

    has_location = filters.BooleanFilter(
        method="filter_has_location",
    )

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    search = filters.CharFilter(
        method="filter_search",
    )

    class Meta:
        model = UserProfile

        fields = [
            "verification_status",
            "gender",
            "date_of_birth",
            "is_business",
            "company_name",
            "univa_id",
            "is_online",
            "preferred_notification_method",
            "language_code",
            "location_source",
        ]

    # ------------------------------------------------------------------
    # Verification filters
    # ------------------------------------------------------------------

    def filter_is_verified(self, queryset, name, value):
        """
        Filter profiles based on whether verification_status is
        unverified or not.
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

    def filter_verification_level(self, queryset, name, value):
        """
        Filter by minimum verification level.

        Mapping:

            0 = unverified
            1 = basic
            2 = id_verified
            3 = address_verified
            4 = payment_verified
            5 = premium_verified
        """

        if value is None:
            return queryset

        status_order = [
            "unverified",
            "basic",
            "id_verified",
            "address_verified",
            "payment_verified",
            "premium_verified",
        ]

        try:
            level = int(value)
        except (TypeError, ValueError):
            return queryset.none()

        if level < 0:
            level = 0

        if level >= len(status_order):
            level = len(status_order) - 1

        allowed_statuses = status_order[level:]

        return queryset.filter(
            verification_status__in=allowed_statuses,
        )

    # ------------------------------------------------------------------
    # Location
    # ------------------------------------------------------------------

    def filter_has_location(self, queryset, name, value):
        """
        Filter profiles that have geographic coordinates.
        """

        if value is None:
            return queryset

        if value:
            return queryset.filter(
                location_point__isnull=False,
            )

        return queryset.filter(
            location_point__isnull=True,
        )

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def filter_search(self, queryset, name, value):
        """
        Search public profile information.

        Searches:
            univa_id
            company_name
            bio
            user's first name
            user's last name
        """

        if not value:
            return queryset

        value = value.strip()

        if not value:
            return queryset

        return queryset.filter(
            Q(univa_id__icontains=value)
            | Q(company_name__icontains=value)
            | Q(bio__icontains=value)
            | Q(user__first_name__icontains=value)
            | Q(user__last_name__icontains=value)
        ).distinct()


# ============================================================================
# ROLE FILTER
# ============================================================================


class RoleFilter(filters.FilterSet):
    """
    Filters for application roles.
    """

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    name = filters.CharFilter(
        field_name="name",
        lookup_expr="iexact",
    )

    name_contains = filters.CharFilter(
        field_name="name",
        lookup_expr="icontains",
    )

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------

    app_name = filters.CharFilter(
        field_name="app_name",
        lookup_expr="exact",
    )

    app_name_in = CharInFilter(
        field_name="app_name",
        lookup_expr="in",
    )

    # ------------------------------------------------------------------
    # Role state
    # ------------------------------------------------------------------

    is_default = filters.BooleanFilter(
        field_name="is_default",
    )

    requires_verification = filters.BooleanFilter(
        field_name="requires_verification",
    )

    auto_assign = filters.BooleanFilter(
        field_name="auto_assign",
    )

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    search = filters.CharFilter(
        method="filter_search",
    )

    class Meta:
        model = Role

        fields = [
            "name",
            "app_name",
            "is_default",
            "requires_verification",
            "auto_assign",
        ]

    def filter_search(self, queryset, name, value):
        """
        Search role name and description.
        """

        if not value:
            return queryset

        value = value.strip()

        if not value:
            return queryset

        return queryset.filter(
            Q(name__icontains=value)
            | Q(description__icontains=value)
        ).distinct()


# ============================================================================
# USER ROLE FILTER
# ============================================================================


class UserRoleFilter(filters.FilterSet):
    """
    Filters for user-role assignments.

    This filters the assignment itself, not the Role definition.
    """

    # ------------------------------------------------------------------
    # Assignment state
    # ------------------------------------------------------------------

    is_active = filters.BooleanFilter(
        field_name="is_active",
    )

    is_expired = filters.BooleanFilter(
        method="filter_is_expired",
    )

    is_revoked = filters.BooleanFilter(
        method="filter_is_revoked",
    )

    # ------------------------------------------------------------------
    # User
    # ------------------------------------------------------------------

    user_id = filters.NumberFilter(
        field_name="user_id",
    )

    # ------------------------------------------------------------------
    # Role
    # ------------------------------------------------------------------

    role_id = filters.NumberFilter(
        field_name="role_id",
    )

    role_name = filters.CharFilter(
        field_name="role__name",
        lookup_expr="iexact",
    )

    role_name_contains = filters.CharFilter(
        field_name="role__name",
        lookup_expr="icontains",
    )

    app_name = filters.CharFilter(
        field_name="role__app_name",
        lookup_expr="exact",
    )

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    verified = filters.BooleanFilter(
        method="filter_verified",
    )

    # ------------------------------------------------------------------
    # Dates
    # ------------------------------------------------------------------

    created_after = filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="gte",
    )

    created_before = filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="lte",
    )

    expires_after = filters.DateTimeFilter(
        field_name="expires_at",
        lookup_expr="gte",
    )

    expires_before = filters.DateTimeFilter(
        field_name="expires_at",
        lookup_expr="lte",
    )

    # ------------------------------------------------------------------
    # Meta
    # ------------------------------------------------------------------

    class Meta:
        model = UserRole

        fields = [
            "is_active",
            "user_id",
            "role_id",
            "role_name",
            "app_name",
        ]

    # ------------------------------------------------------------------
    # Lifecycle filters
    # ------------------------------------------------------------------

    def filter_is_expired(self, queryset, name, value):
        """
        Filter assignments based on expiration state.
        """

        if value is None:
            return queryset

        from django.utils import timezone

        now = timezone.now()

        if value:
            return queryset.filter(
                expires_at__isnull=False,
                expires_at__lte=now,
            )

        return queryset.filter(
            Q(expires_at__isnull=True)
            | Q(expires_at__gt=now)
        )

    def filter_is_revoked(self, queryset, name, value):
        """
        Filter assignments based on revocation state.
        """

        if value is None:
            return queryset

        if value:
            return queryset.filter(
                revoked_at__isnull=False,
            )

        return queryset.filter(
            revoked_at__isnull=True,
        )

    def filter_verified(self, queryset, name, value):
        """
        Filter assignments based on whether verification exists.
        """

        if value is None:
            return queryset

        if value:
            return queryset.filter(
                verified_at__isnull=False,
            )

        return queryset.filter(
            verified_at__isnull=True,
        )


# ============================================================================
# ADDRESS FILTER
# ============================================================================


class AddressFilter(filters.FilterSet):
    """
    Filters for account addresses.

    Address remains part of the account domain and therefore its
    filtering rules live here.
    """

    # ------------------------------------------------------------------
    # Ownership
    # ------------------------------------------------------------------

    user_id = filters.NumberFilter(
        field_name="user_id",
    )

    # ------------------------------------------------------------------
    # Address classification
    # ------------------------------------------------------------------

    address_type = filters.CharFilter(
        field_name="address_type",
        lookup_expr="exact",
    )

    is_default = filters.BooleanFilter(
        field_name="is_default",
    )

    role_visibility = filters.CharFilter(
        field_name="role_visibility",
        lookup_expr="exact",
    )

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    first_name = filters.CharFilter(
        field_name="first_name",
        lookup_expr="icontains",
    )

    last_name = filters.CharFilter(
        field_name="last_name",
        lookup_expr="icontains",
    )

    company_name = filters.CharFilter(
        field_name="company_name",
        lookup_expr="icontains",
    )

    # ------------------------------------------------------------------
    # Geography
    # ------------------------------------------------------------------

    city = filters.CharFilter(
        field_name="city",
        lookup_expr="icontains",
    )

    city_area = filters.CharFilter(
        field_name="city_area",
        lookup_expr="icontains",
    )

    state = filters.CharFilter(
        field_name="state",
        lookup_expr="exact",
    )

    country = filters.CharFilter(
        field_name="country",
        lookup_expr="exact",
    )

    postal_code = filters.CharFilter(
        field_name="postal_code",
        lookup_expr="exact",
    )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    validation_skipped = filters.BooleanFilter(
        field_name="validation_skipped",
    )

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    search = filters.CharFilter(
        method="filter_search",
    )

    # ------------------------------------------------------------------
    # Meta
    # ------------------------------------------------------------------

    class Meta:
        model = Address

        fields = [
            "user_id",
            "address_type",
            "is_default",
            "role_visibility",
            "city",
            "city_area",
            "state",
            "country",
            "postal_code",
            "validation_skipped",
        ]

    def filter_search(self, queryset, name, value):
        """
        Search address identity and location fields.
        """

        if not value:
            return queryset

        value = value.strip()

        if not value:
            return queryset

        return queryset.filter(
            Q(first_name__icontains=value)
            | Q(last_name__icontains=value)
            | Q(company_name__icontains=value)
            | Q(street_address_1__icontains=value)
            | Q(street_address_2__icontains=value)
            | Q(city__icontains=value)
            | Q(city_area__icontains=value)
            | Q(postal_code__icontains=value)
        ).distinct()