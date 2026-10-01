# apps/backend/graphq/accounts/filters/role.py

"""
GraphQL filters for Accounts roles.

Graphene:
    3.2.3

Relay:
    Global Relay Node IDs

Architecture
------------

This module contains filtering concerns only.

It is responsible for:
    - filtering Role records
    - filtering UserRole assignments
    - validating filter input
    - exposing predictable django-filter FilterSets

It does NOT:
    - authorize users
    - assign roles
    - revoke roles
    - activate/deactivate roles
    - perform mutations
    - contain GraphQL types
    - contain resolver logic

Models:
    accounts.models.role.Role
    accounts.models.role.UserRole
"""

from __future__ import annotations

import django_filters
from django.db.models import Q

from accounts.models.role import Role, UserRole


# ============================================================================
# Role Filter
# ============================================================================


class RoleFilter(django_filters.FilterSet):
    """
    FilterSet for the application Role model.

    Supported filters:

        name
        name_contains
        app_name
        is_default
        requires_verification
        auto_assign
    """

    # ------------------------------------------------------------------
    # Name
    # ------------------------------------------------------------------

    name = django_filters.CharFilter(
        field_name="name",
        lookup_expr="exact",
    )

    name_contains = django_filters.CharFilter(
        field_name="name",
        lookup_expr="icontains",
    )

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------

    app_name = django_filters.CharFilter(
        field_name="app_name",
        lookup_expr="exact",
    )

    # ------------------------------------------------------------------
    # Role configuration
    # ------------------------------------------------------------------

    is_default = django_filters.BooleanFilter(
        field_name="is_default",
    )

    requires_verification = django_filters.BooleanFilter(
        field_name="requires_verification",
    )

    auto_assign = django_filters.BooleanFilter(
        field_name="auto_assign",
    )

    class Meta:
        model = Role

        fields = {
            "name": ["exact", "icontains"],
            "app_name": ["exact"],
            "is_default": ["exact"],
            "requires_verification": ["exact"],
            "auto_assign": ["exact"],
        }


# ============================================================================
# User Role Filter
# ============================================================================


class UserRoleFilter(django_filters.FilterSet):
    """
    FilterSet for persistent UserRole assignments.

    This filters assignments, not the effective authorization state.

    Effective-role authorization remains the responsibility of the
    Accounts domain/resolver layer.

    Supported filters:

        user
        role
        role_name
        role_app_name
        is_active
        expires_at
        expires_after
        expires_before
        revoked_at
        is_revoked
        created_at
        created_after
        created_before
        verified_at
        is_verified
    """

    # ------------------------------------------------------------------
    # Ownership
    # ------------------------------------------------------------------

    user = django_filters.NumberFilter(
        field_name="user_id",
        lookup_expr="exact",
    )

    # ------------------------------------------------------------------
    # Role
    # ------------------------------------------------------------------

    role = django_filters.NumberFilter(
        field_name="role_id",
        lookup_expr="exact",
    )

    role_name = django_filters.CharFilter(
        field_name="role__name",
        lookup_expr="exact",
    )

    role_name_contains = django_filters.CharFilter(
        field_name="role__name",
        lookup_expr="icontains",
    )

    role_app_name = django_filters.CharFilter(
        field_name="role__app_name",
        lookup_expr="exact",
    )

    # ------------------------------------------------------------------
    # Assignment state
    # ------------------------------------------------------------------

    is_active = django_filters.BooleanFilter(
        field_name="is_active",
    )

    # ------------------------------------------------------------------
    # Expiration
    # ------------------------------------------------------------------

    expires_at = django_filters.IsoDateTimeFilter(
        field_name="expires_at",
        lookup_expr="exact",
    )

    expires_after = django_filters.IsoDateTimeFilter(
        field_name="expires_at",
        lookup_expr="gte",
    )

    expires_before = django_filters.IsoDateTimeFilter(
        field_name="expires_at",
        lookup_expr="lte",
    )

    # ------------------------------------------------------------------
    # Revocation
    # ------------------------------------------------------------------

    revoked_at = django_filters.IsoDateTimeFilter(
        field_name="revoked_at",
        lookup_expr="exact",
    )

    is_revoked = django_filters.BooleanFilter(
        method="filter_is_revoked",
    )

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    created_at = django_filters.IsoDateTimeFilter(
        field_name="created_at",
        lookup_expr="exact",
    )

    created_after = django_filters.IsoDateTimeFilter(
        field_name="created_at",
        lookup_expr="gte",
    )

    created_before = django_filters.IsoDateTimeFilter(
        field_name="created_at",
        lookup_expr="lte",
    )

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    verified_at = django_filters.IsoDateTimeFilter(
        field_name="verified_at",
        lookup_expr="exact",
    )

    is_verified = django_filters.BooleanFilter(
        method="filter_is_verified",
    )

    # ------------------------------------------------------------------
    # Custom filters
    # ------------------------------------------------------------------

    @staticmethod
    def filter_is_revoked(queryset, name, value):
        """
        Filter assignments according to revocation state.

        is_revoked=True:
            revoked_at IS NOT NULL

        is_revoked=False:
            revoked_at IS NULL
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

    @staticmethod
    def filter_is_verified(queryset, name, value):
        """
        Filter assignments according to whether they have been verified.

        A UserRole is considered verified when verified_at is populated.
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

    class Meta:
        model = UserRole

        fields = {
            "user": ["exact"],
            "role": ["exact"],
            "is_active": ["exact"],
            "created_at": ["exact", "gte", "lte"],
            "expires_at": ["exact", "gte", "lte"],
            "revoked_at": ["exact", "isnull"],
            "verified_at": ["exact", "isnull"],
        }


# ============================================================================
# Effective User Role Filter
# ============================================================================


class ActiveUserRoleFilter(UserRoleFilter):
    """
    FilterSet specifically intended for active role assignments.

    The base UserRoleFilter exposes lifecycle fields.

    This filter additionally provides a convenient `effective` filter
    for consumers that need to distinguish currently effective
    assignments from merely active database records.

    Effective means:

        is_active=True
        revoked_at IS NULL
        expires_at IS NULL OR expires_at > now

    The actual authorization decision should still remain in the
    Accounts domain layer.
    """

    effective = django_filters.BooleanFilter(
        method="filter_effective",
    )

    def filter_effective(self, queryset, name, value):
        """
        Filter currently effective role assignments.
        """

        if value is None:
            return queryset

        from django.utils import timezone

        now = timezone.now()

        effective_query = Q(
            is_active=True,
            revoked_at__isnull=True,
        ) & (
            Q(expires_at__isnull=True)
            | Q(expires_at__gt=now)
        )

        if value:
            return queryset.filter(effective_query)

        return queryset.exclude(effective_query)


# ============================================================================
# Public API
# ============================================================================


__all__ = [
    "RoleFilter",
    "UserRoleFilter",
    "ActiveUserRoleFilter",
]