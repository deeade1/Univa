"""
GraphQL resolvers for account-owned addresses.

Graphene:
    3.2.3

Relay:
    Global Relay Node IDs

Architecture
------------

    GraphQL Query
         │
         ▼
    AddressQuery
         │
         ├── AddressNode
         ├── AddressFilter
         └── Address resolvers
                 │
                 ▼
             Address queryset

Responsibilities:
    - construct Address querysets
    - enforce authentication
    - enforce address ownership / visibility
    - optimize related-object loading
    - resolve individual addresses
    - resolve the authenticated user's default addresses

This module does NOT:
    - define GraphQL types
    - define GraphQL filters
    - create or update addresses
    - perform mutations
    - handle authentication
    - contain feature-specific business logic

Compatible with:
    - Graphene 3.2.3
    - Graphene-Django
    - Relay
    - Django ORM
"""

from __future__ import annotations

from django.db.models import Q
from django.utils import timezone

from accounts.models.address import Address
from accounts.models.role import UserRole


# ============================================================================
# Base Queryset
# ============================================================================


def get_address_queryset():
    """
    Return the optimized base Address queryset.

    No request-specific authorization is applied here.

    This function is intentionally reusable by the other resolver
    functions in this module.
    """

    return (
        Address.objects
        .select_related(
            "user",
        )
        .prefetch_related(
            "role_visibility",
        )
    )


# ============================================================================
# Authentication
# ============================================================================


def _is_authenticated(user):
    """
    Return whether the supplied user is authenticated.
    """

    return bool(
        user
        and getattr(user, "is_authenticated", False)
    )


# ============================================================================
# User-owned Addresses
# ============================================================================


def get_user_address_queryset(user):
    """
    Return addresses owned by the authenticated user.

    Ownership is enforced at the database-query level.

    Unauthenticated users receive an empty queryset.
    """

    if not _is_authenticated(user):
        return Address.objects.none()

    return (
        get_address_queryset()
        .filter(
            user=user,
        )
    )


# ============================================================================
# Active Requester Roles
# ============================================================================


def get_active_role_ids(user):
    """
    Return the IDs of the user's currently effective roles.

    A role is considered effective only when:

        - the assignment is active
        - it has not been revoked
        - it has not expired
    """

    if not _is_authenticated(user):
        return UserRole.objects.none().values("role_id")

    now = timezone.now()

    return (
        UserRole.objects
        .filter(
            user=user,
            is_active=True,
            revoked_at__isnull=True,
        )
        .filter(
            Q(expires_at__isnull=True)
            | Q(expires_at__gt=now)
        )
        .values("role_id")
    )


# ============================================================================
# Visible Addresses
# ============================================================================


def get_visible_address_queryset(user):
    """
    Return addresses the authenticated user is allowed to view.

    Visibility rules:

        1. The owner can always view their own addresses.

        2. Another authenticated user can view an address only when
           one of their currently active roles has been explicitly
           granted visibility through Address.role_visibility.

    Authorization is performed in SQL rather than by evaluating
    Address.is_visible_to() for every object individually.
    """

    if not _is_authenticated(user):
        return Address.objects.none()

    active_role_ids = get_active_role_ids(user)

    return (
        get_address_queryset()
        .filter(
            Q(user=user)
            | Q(role_visibility__in=active_role_ids)
        )
        .distinct()
    )


# ============================================================================
# Address Connection
# ============================================================================


def resolve_addresses(user):
    """
    Resolve the Address Relay connection queryset.

    The queryset remains lazy so Graphene-Django can apply:

        - AddressFilter
        - Relay cursor pagination
        - connection slicing

    before the query is evaluated.
    """

    return get_visible_address_queryset(user)


# ============================================================================
# Single Address
# ============================================================================


def resolve_address(user, address_id):
    """
    Resolve a single Address while enforcing visibility.

    Parameters:
        user:
            Current authenticated GraphQL user.

        address_id:
            Database primary key of the Address.

    Relay global-ID decoding belongs to the GraphQL query/type layer.
    This resolver works with the decoded database primary key.
    """

    if not _is_authenticated(user):
        return None

    return (
        get_visible_address_queryset(user)
        .filter(
            pk=address_id,
        )
        .first()
    )


# ============================================================================
# Default Addresses
# ============================================================================


def resolve_default_addresses(
    user,
    address_type=None,
):
    """
    Resolve the authenticated user's default addresses.

    Defaults are account-owned data, therefore this function intentionally
    uses the ownership queryset rather than the broader visibility queryset.
    """

    if not _is_authenticated(user):
        return Address.objects.none()

    queryset = (
        get_user_address_queryset(user)
        .filter(
            is_default=True,
        )
    )

    if address_type:
        queryset = queryset.filter(
            address_type=address_type,
        )

    return queryset


# ============================================================================
# Single Default Address
# ============================================================================


def resolve_default_address(
    user,
    address_type,
):
    """
    Resolve one default address for the authenticated user.

    Returns None when no matching default address exists.
    """

    if not _is_authenticated(user):
        return None

    return (
        get_user_address_queryset(user)
        .filter(
            address_type=address_type,
            is_default=True,
        )
        .first()
    )


# ============================================================================
# Address Visibility
# ============================================================================


def can_view_address(
    user,
    address,
):
    """
    Determine whether a user may view an Address.

    The Address model remains the authoritative domain-level
    visibility check.

    Collection queries should normally use
    get_visible_address_queryset() instead, because it performs
    authorization in SQL.
    """

    if not address:
        return False

    return address.is_visible_to(user)


# ============================================================================
# Queryset Optimization
# ============================================================================


def optimize_address_queryset(queryset):
    """
    Apply GraphQL-oriented queryset optimization.

    The base resolver already performs the primary select/prefetch
    optimization. This function provides a stable optimization hook
    for the GraphQL query layer and keeps optimization concerns out
    of the GraphQL type.

    Keeping this as a separate function also makes it easy to extend
    later if AddressNode gains additional relationships.
    """

    return (
        queryset
        .select_related(
            "user",
        )
        .prefetch_related(
            "role_visibility",
        )
    )


__all__ = [
    "get_address_queryset",
    "get_user_address_queryset",
    "get_active_role_ids",
    "get_visible_address_queryset",
    "resolve_addresses",
    "resolve_address",
    "resolve_default_addresses",
    "resolve_default_address",
    "can_view_address",
    "optimize_address_queryset",
]