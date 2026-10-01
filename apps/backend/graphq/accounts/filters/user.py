"""
User GraphQL filters.

Architecture
------------
This module defines the filtering boundary for the Accounts User
GraphQL node.

Responsibilities:
    - expose safe User filtering
    - translate GraphQL filter arguments into Django ORM filters
    - provide reusable filtering methods

This module does NOT:
    - perform authorization
    - resolve users
    - create/update users
    - assign roles
    - contain authentication logic
    - depend on feature applications

Compatible with:
    - Django
    - django-filter
    - Graphene-Django
    - Graphene 3.2.3
    - Relay
"""

from django.db.models import Q
from django_filters import rest_framework as filters

from accounts.models.user import User


class UserFilter(filters.FilterSet):
    """
    FilterSet for the Accounts User GraphQL Relay node.

    Filters are deliberately limited to fields that belong to the
    centralized account identity model.

    Authorization and visibility are handled by the resolver layer.
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

    # ------------------------------------------------------------------
    # Personal identity
    # ------------------------------------------------------------------

    first_name = filters.CharFilter(
        field_name="first_name",
        lookup_expr="icontains",
    )

    last_name = filters.CharFilter(
        field_name="last_name",
        lookup_expr="icontains",
    )

    # ------------------------------------------------------------------
    # Account state
    # ------------------------------------------------------------------

    is_active = filters.BooleanFilter(
        field_name="is_active",
        lookup_expr="exact",
    )

    is_staff = filters.BooleanFilter(
        field_name="is_staff",
        lookup_expr="exact",
    )

    is_superuser = filters.BooleanFilter(
        field_name="is_superuser",
        lookup_expr="exact",
    )

    # ------------------------------------------------------------------
    # Email verification
    # ------------------------------------------------------------------

    email_verified = filters.BooleanFilter(
        field_name="email_verified",
        lookup_expr="exact",
    )

    # ------------------------------------------------------------------
    # Dates
    # ------------------------------------------------------------------

    date_joined = filters.DateTimeFilter(
        field_name="date_joined",
        lookup_expr="exact",
    )

    date_joined_gte = filters.DateTimeFilter(
        field_name="date_joined",
        lookup_expr="gte",
    )

    date_joined_lte = filters.DateTimeFilter(
        field_name="date_joined",
        lookup_expr="lte",
    )

    last_login = filters.DateTimeFilter(
        field_name="last_login",
        lookup_expr="exact",
    )

    last_login_gte = filters.DateTimeFilter(
        field_name="last_login",
        lookup_expr="gte",
    )

    last_login_lte = filters.DateTimeFilter(
        field_name="last_login",
        lookup_expr="lte",
    )

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    search = filters.CharFilter(
        method="filter_search",
    )

    # ------------------------------------------------------------------
    # Role filtering
    # ------------------------------------------------------------------

    role_name = filters.CharFilter(
        field_name="user_roles__role__name",
        lookup_expr="exact",
    )

    role_name_contains = filters.CharFilter(
        field_name="user_roles__role__name",
        lookup_expr="icontains",
    )

    app_name = filters.CharFilter(
        field_name="user_roles__role__app_name",
        lookup_expr="exact",
    )

    # ------------------------------------------------------------------
    # Role state
    # ------------------------------------------------------------------

    has_active_role = filters.BooleanFilter(
        method="filter_has_active_role",
    )

    # ------------------------------------------------------------------
    # Profile filters
    # ------------------------------------------------------------------

    verification_status = filters.CharFilter(
        field_name="profile__verification_status",
        lookup_expr="exact",
    )

    verification_status_in = filters.BaseInFilter(
        field_name="profile__verification_status",
        lookup_expr="in",
    )

    is_business = filters.BooleanFilter(
        field_name="profile__is_business",
        lookup_expr="exact",
    )

    gender = filters.CharFilter(
        field_name="profile__gender",
        lookup_expr="exact",
    )

    language_code = filters.CharFilter(
        field_name="profile__language_code",
        lookup_expr="exact",
    )

    preferred_notification_method = filters.CharFilter(
        field_name="profile__preferred_notification_method",
        lookup_expr="exact",
    )

    is_online = filters.BooleanFilter(
        field_name="profile__is_online",
        lookup_expr="exact",
    )

    # ------------------------------------------------------------------
    # Profile location
    # ------------------------------------------------------------------

    location_source = filters.CharFilter(
        field_name="profile__location_source",
        lookup_expr="exact",
    )

    # ------------------------------------------------------------------
    # Meta
    # ------------------------------------------------------------------

    class Meta:
        model = User

        fields = [
            # Identity
            "email",
            "email_contains",
            "phone_number",

            # Personal
            "first_name",
            "last_name",

            # Account state
            "is_active",
            "is_staff",
            "is_superuser",

            # Verification
            "email_verified",

            # Dates
            "date_joined",
            "date_joined_gte",
            "date_joined_lte",
            "last_login",
            "last_login_gte",
            "last_login_lte",

            # Search
            "search",

            # Roles
            "role_name",
            "role_name_contains",
            "app_name",
            "has_active_role",

            # Profile
            "verification_status",
            "verification_status_in",
            "is_business",
            "gender",
            "language_code",
            "preferred_notification_method",
            "is_online",

            # Location
            "location_source",
        ]

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def filter_search(self, queryset, name, value):
        """
        Perform a broad account search.

        Searches identity and basic profile fields only.

        Feature-specific searchable fields should be implemented
        by the owning application.
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
            | Q(profile__univa_id__icontains=value)
            | Q(profile__company_name__icontains=value)
        ).distinct()

    # ------------------------------------------------------------------
    # Active role filtering
    # ------------------------------------------------------------------

    def filter_has_active_role(
        self,
        queryset,
        name,
        value,
    ):
        """
        Filter users according to whether they currently have
        at least one effective role.

        Effective role:

            is_active=True
            revoked_at IS NULL
            expires_at IS NULL OR expires_at > now
        """

        if value is None:
            return queryset

        from django.utils import timezone

        now = timezone.now()

        active_role_query = (
            Q(user_roles__is_active=True)
            & Q(user_roles__revoked_at__isnull=True)
            & (
                Q(user_roles__expires_at__isnull=True)
                | Q(user_roles__expires_at__gt=now)
            )
        )

        if value:
            return queryset.filter(
                active_role_query
            ).distinct()

        return queryset.exclude(
            active_role_query
        ).distinct()