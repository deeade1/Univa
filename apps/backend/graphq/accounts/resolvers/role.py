# apps/backend/graphq/accounts/resolvers/role.py

"""
GraphQL resolvers for Accounts roles.

Graphene:
    3.2.3

Relay:
    Global Relay Node IDs

Architecture
------------

This module is the resolver/queryset layer for:

    accounts.models.role.Role
    accounts.models.role.UserRole

Responsibilities:
    - construct optimized Role querysets
    - construct optimized UserRole querysets
    - resolve individual Role records
    - resolve individual UserRole records
    - resolve a user's role assignments
    - resolve effective role assignments

This module does NOT:
    - define GraphQL types
    - define filters
    - perform mutations
    - assign roles
    - revoke roles
    - activate/deactivate roles
    - handle authentication
    - contain feature-specific business logic

Relay global-ID decoding belongs in the GraphQL query layer.

The resolver functions here work with database primary keys.
"""

from __future__ import annotations

from django.db.models import Prefetch, Q
from django.utils import timezone

from accounts.models.role import Role, UserRole


# ============================================================================
# Role Queryset
# ============================================================================


def get_role_queryset():
    """
    Return the optimized base Role queryset.

    Role permissions are prefetched because Role exposes its
    permissions relationship.

    User assignments are also prefetched when required by consumers.

    No request-specific authorization is applied here.
    """

    return (
        Role.objects
        .prefetch_related(
            "permissions",
        )
    )


# ============================================================================
# UserRole Queryset
# ============================================================================


def get_user_role_queryset():
    """
    Return the optimized base UserRole queryset.

    The related User and Role are loaded with select_related().

    Role permissions are prefetched through the related Role.
    """

    return (
        UserRole.objects
        .select_related(
            "user",
            "role",
            "created_by",
            "verified_by",
            "revoked_by",
        )
        .prefetch_related(
            "role__permissions",
        )
    )


# ============================================================================
# Role by ID
# ============================================================================


def resolve_role(role_id):
    """
    Resolve a single Role by database primary key.

    `role_id` is expected to be the database primary key.

    Relay global-ID decoding must happen before calling this function.
    """

    if not role_id:
        return None

    return (
        get_role_queryset()
        .filter(pk=role_id)
        .first()
    )


# ============================================================================
# UserRole by ID
# ============================================================================


def resolve_user_role(user_role_id):
    """
    Resolve a single UserRole assignment by database primary key.

    Relay global-ID decoding must happen in the GraphQL query layer.
    """

    if not user_role_id:
        return None

    return (
        get_user_role_queryset()
        .filter(pk=user_role_id)
        .first()
    )


# ============================================================================
# Role Connection
# ============================================================================


def resolve_roles():
    """
    Return the base Role queryset for the Relay connection.

    Filtering and pagination are handled by:

        RoleFilter
        DjangoFilterConnectionField
    """

    return get_role_queryset()


# ============================================================================
# UserRole Connection
# ============================================================================


def resolve_user_roles():
    """
    Return the base UserRole queryset for the Relay connection.

    Filtering and Relay pagination are handled by the GraphQL layer.
    """

    return get_user_role_queryset()


# ============================================================================
# User's Role Assignments
# ============================================================================


def resolve_user_role_assignments(user):
    """
    Return role assignments belonging to a specific user.

    This includes the complete assignment lifecycle state.

    It does not automatically restrict the result to effective roles.
    """

    if not user or not user.is_authenticated:
        return UserRole.objects.none()

    return (
        get_user_role_queryset()
        .filter(
            user=user,
        )
        .order_by(
            "-created_at",
        )
    )


# ============================================================================
# User's Active Role Assignments
# ============================================================================


def resolve_active_user_roles(user):
    """
    Return currently active role assignments for a user.

    Active means:

        is_active=True
        revoked_at IS NULL

    Expired assignments are excluded as well.
    """

    if not user or not user.is_authenticated:
        return UserRole.objects.none()

    now = timezone.now()

    return (
        get_user_role_queryset()
        .filter(
            user=user,
            is_active=True,
            revoked_at__isnull=True,
        )
        .filter(
            Q(expires_at__isnull=True)
            | Q(expires_at__gt=now)
        )
        .order_by(
            "role__app_name",
            "role__name",
            "-created_at",
        )
    )


# ============================================================================
# User's Roles
# ============================================================================


def resolve_user_roles_for_app(
    user,
    app_name=None,
):
    """
    Return effective role assignments for a user.

    Optionally restrict the result to a particular application.

    Example:

        resolve_user_roles_for_app(
            user,
            "transport",
        )
    """

    queryset = resolve_active_user_roles(user)

    if app_name:
        queryset = queryset.filter(
            role__app_name=app_name,
        )

    return queryset


# ============================================================================
# Role Assignments for a Role
# ============================================================================


def resolve_role_assignments(role):
    """
    Return UserRole assignments belonging to a specific Role.
    """

    if not role:
        return UserRole.objects.none()

    return (
        get_user_role_queryset()
        .filter(
            role=role,
        )
        .order_by(
            "-created_at",
        )
    )


# ============================================================================
# Active Assignments for a Role
# ============================================================================


def resolve_active_role_assignments(role):
    """
    Return currently effective assignments for a Role.
    """

    if not role:
        return UserRole.objects.none()

    now = timezone.now()

    return (
        get_user_role_queryset()
        .filter(
            role=role,
            is_active=True,
            revoked_at__isnull=True,
        )
        .filter(
            Q(expires_at__isnull=True)
            | Q(expires_at__gt=now)
        )
        .order_by(
            "-created_at",
        )
    )


# ============================================================================
# Effective Role Check
# ============================================================================


def has_effective_role(
    user,
    app_name,
    role_name,
):
    """
    Determine whether a user currently has an effective role.

    This mirrors User.has_role() at the queryset level.

    The method is intentionally small so callers that already have
    a User instance may use the model's domain method directly.
    """

    if not user or not user.is_authenticated:
        return False

    now = timezone.now()

    return (
        UserRole.objects
        .filter(
            user=user,
            role__app_name=app_name,
            role__name=role_name,
            is_active=True,
            revoked_at__isnull=True,
        )
        .filter(
            Q(expires_at__isnull=True)
            | Q(expires_at__gt=now)
        )
        .exists()
    )


# ============================================================================
# Effective Roles
# ============================================================================


def resolve_effective_roles(user):
    """
    Return the Role objects currently effective for a user.

    This returns Role records rather than UserRole assignment records.
    """

    if not user or not user.is_authenticated:
        return Role.objects.none()

    now = timezone.now()

    role_ids = (
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

    return (
        get_role_queryset()
        .filter(
            pk__in=role_ids,
        )
        .order_by(
            "app_name",
            "name",
        )
    )


# ============================================================================
# Role Lookup Helpers
# ============================================================================


def resolve_role_by_name(
    app_name,
    role_name,
):
    """
    Resolve a Role using its application and role name.

    Role.name is only unique together with app_name, according to
    the Role model's unique_together constraint.
    """

    if not app_name or not role_name:
        return None

    return (
        get_role_queryset()
        .filter(
            app_name=app_name,
            name=role_name,
        )
        .first()
    )


# ============================================================================
# Default Roles
# ============================================================================


def resolve_default_roles():
    """
    Return roles configured as automatically/default available roles.

    This delegates to the Role model's existing domain-level
    get_default_roles() method.
    """

    return (
        Role.get_default_roles()
        .prefetch_related(
            "permissions",
        )
    )


# ============================================================================
# Application Roles
# ============================================================================


def resolve_app_roles(app_name):
    """
    Return all roles belonging to a specific application.
    """

    if not app_name:
        return Role.objects.none()

    return (
        Role.get_app_roles(app_name)
        .prefetch_related(
            "permissions",
        )
        .order_by(
            "name",
        )
    )


# ============================================================================
# Public API
# ============================================================================


__all__ = [
    "get_role_queryset",
    "get_user_role_queryset",
    "resolve_role",
    "resolve_user_role",
    "resolve_roles",
    "resolve_user_roles",
    "resolve_user_role_assignments",
    "resolve_active_user_roles",
    "resolve_user_roles_for_app",
    "resolve_role_assignments",
    "resolve_active_role_assignments",
    "has_effective_role",
    "resolve_effective_roles",
    "resolve_role_by_name",
    "resolve_default_roles",
    "resolve_app_roles",
]