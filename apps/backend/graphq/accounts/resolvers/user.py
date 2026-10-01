"""
User GraphQL resolvers.

Architecture
------------
This module is the queryset/resolution boundary for the Accounts
GraphQL User node.

Responsibilities:
    - build optimized User querysets
    - resolve authenticated/current users
    - resolve users visible to the requester
    - optimize profile and role relationships
    - resolve individual users by database primary key

This module does NOT:
    - define GraphQL types
    - define mutations
    - define filters
    - create users
    - assign roles
    - contain authentication business logic
    - contain feature-specific application logic

Compatible with:
    - Django
    - Graphene 3.2.3
    - Graphene-Django
    - Relay
"""

from django.contrib.auth import get_user_model
from django.db.models import Prefetch, Q
from django.utils import timezone

from accounts.models.role import UserRole


User = get_user_model()


# ============================================================================
# Queryset Optimization
# ============================================================================

def optimize_user_queryset(queryset):
    """
    Apply standard optimizations to a User queryset.

    Idempotent: safe to call on an already-optimized queryset.

    This includes:
        - select_related for profile
        - prefetch_related for active roles
    """

    # Guard against double-prefetching the same relation, which
    # Django rejects with:
    #   "'graphql_active_roles' lookup was already seen with a
    #    different queryset."
    if getattr(queryset, "_graphql_user_optimized", False):
        return queryset

    active_role_queryset = (
        UserRole.objects
        .filter(
            is_active=True,
            revoked_at__isnull=True,
        )
        .filter(
            Q(expires_at__isnull=True)
            | Q(expires_at__gt=timezone.now())
        )
        .select_related("role")
    )

    optimized = (
        queryset
        .select_related("profile")
        .prefetch_related(
            Prefetch(
                "user_roles",
                queryset=active_role_queryset,
                to_attr="graphql_active_roles",
            )
        )
    )

    optimized._graphql_user_optimized = True
    return optimized

def get_user_queryset():
    """
    Return the optimized base User queryset.

    This function deliberately contains no request-specific
    authorization rules.

    Related objects:
        profile
        active user roles
        roles attached to those assignments
    """

    return optimize_user_queryset(User.objects.all())


# ============================================================================
# Active Users
# ============================================================================


def get_active_user_queryset():
    """
    Return active users.

    Inactive/deactivated accounts are excluded.
    """

    return (
        get_user_queryset()
        .filter(
            is_active=True,
        )
    )


# ============================================================================
# Current User
# ============================================================================


def resolve_current_user(user):
    """
    Resolve the authenticated user's User object.

    Returns:
        User | None

    Unauthenticated requests return None.
    """

    if not user or not user.is_authenticated:
        return None

    return (
        get_user_queryset()
        .filter(
            pk=user.pk,
            is_active=True,
        )
        .first()
    )


# ============================================================================
# Visible Users
# ============================================================================


def get_visible_user_queryset(user):
    """
    Return users that may be exposed through the Accounts GraphQL API.

    Current policy:

        - unauthenticated users receive no users
        - authenticated users may see active users
        - the current user is included

    Feature-specific visibility rules should be implemented by the
    owning application rather than added here.

    For example:
        social visibility -> social application
        vendor visibility -> ecommerce application
        driver visibility -> transport application
    """

    if not user or not user.is_authenticated:
        return User.objects.none()

    return get_active_user_queryset()


# ============================================================================
# User Collection
# ============================================================================


def resolve_user(user, target_pk):
    """
    Resolve one User by primary key, scoped to what the requester
    may see.

    Returns:
        User | None
    """

    if not user or not user.is_authenticated:
        return None

    return (
        get_visible_user_queryset(user)
        .filter(pk=target_pk)
        .first()
    )


def resolve_users(user):
    """
    Resolve the base User queryset visible to the requester.

    The GraphQL boundary extracts the authenticated Django user
    from info.context before delegating to the resolver layer.
    """

    return get_visible_user_queryset(user)


# ============================================================================
# User By Email
# ============================================================================


def resolve_user_by_email(user, email):
    """
    Resolve an active user by email address.

    Email lookup is case-insensitive.
    """

    if not user or not user.is_authenticated:
        return None

    if not email:
        return None

    return (
        get_visible_user_queryset(user)
        .filter(
            email__iexact=email.strip(),
        )
        .first()
    )


# ============================================================================
# User By Phone
# ============================================================================


def resolve_user_by_phone(user, phone_number):
    """
    Resolve an active user by phone number.

    The phone number is treated as an identity credential and is
    therefore matched exactly.
    """

    if not user or not user.is_authenticated:
        return None

    if not phone_number:
        return None

    return (
        get_visible_user_queryset(user)
        .filter(
            phone_number=phone_number,
        )
        .first()
    )


# ============================================================================
# User Profile
# ============================================================================


def resolve_user_profile(user):
    """
    Resolve the authenticated user's profile.

    Returns None if the user is unauthenticated or has no profile.
    """

    current_user = resolve_current_user(user)

    if not current_user:
        return None

    return getattr(
        current_user,
        "profile",
        None,
    )


# ============================================================================
# User Roles
# ============================================================================


def resolve_user_roles(user, target_user):
    """
    Resolve active role assignments for a target user.

    The target user's role assignments are already optimized when the
    target was obtained through get_user_queryset().

    Falls back to a database query if the user object was created
    outside this resolver layer.
    """

    if not target_user:
        return UserRole.objects.none()

    # --------------------------------------------------------------
    # Optimized queryset populated by get_user_queryset()
    # --------------------------------------------------------------

    cached_roles = getattr(
        target_user,
        "graphql_active_roles",
        None,
    )

    if cached_roles is not None:
        return cached_roles

    # --------------------------------------------------------------
    # Safe fallback
    # --------------------------------------------------------------

    return (
        UserRole.objects
        .filter(
            user=target_user,
            is_active=True,
            revoked_at__isnull=True,
        )
        .filter(
            Q(expires_at__isnull=True)
            | Q(expires_at__gt=timezone.now())
        )
        .select_related("role")
    )


# ============================================================================
# User Application Roles
# ============================================================================


def resolve_user_app_roles(user, target_user, app_name):
    """
    Resolve active roles belonging to one application.

    Example:

        resolve_user_app_roles(
            info.context.user,
            target_user,
            "transport",
        )
    """

    if not target_user or not app_name:
        return UserRole.objects.none()

    return (
        resolve_user_roles(
            user,
            target_user,
        )
        .filter(
            role__app_name=app_name,
        )
    )


# ============================================================================
# Role Check
# ============================================================================


def user_has_role(
    target_user,
    app_name,
    role_name,
):
    """
    Check whether a user currently holds an active role.

    This mirrors User.has_role() while remaining useful to GraphQL
    resolvers that already have an optimized User object.
    """

    if not target_user:
        return False

    cached_roles = getattr(
        target_user,
        "graphql_active_roles",
        None,
    )

    if cached_roles is not None:
        return any(
            assignment.role
            and assignment.role.app_name == app_name
            and assignment.role.name == role_name
            for assignment in cached_roles
        )

    return (
        UserRole.objects
        .filter(
            user=target_user,
            is_active=True,
            revoked_at__isnull=True,
            role__app_name=app_name,
            role__name=role_name,
        )
        .filter(
            Q(expires_at__isnull=True)
            | Q(expires_at__gt=timezone.now())
        )
        .exists()
    )


# ============================================================================
# Application Access
# ============================================================================


def user_can_access_app(
    target_user,
    app_name,
):
    """
    Determine whether a user has an active role for an application.
    """

    if not target_user or not app_name:
        return False

    cached_roles = getattr(
        target_user,
        "graphql_active_roles",
        None,
    )

    if cached_roles is not None:
        return any(
            assignment.role
            and assignment.role.app_name == app_name
            for assignment in cached_roles
        )

    return (
        UserRole.objects
        .filter(
            user=target_user,
            is_active=True,
            revoked_at__isnull=True,
            role__app_name=app_name,
        )
        .filter(
            Q(expires_at__isnull=True)
            | Q(expires_at__gt=timezone.now())
        )
        .exists()
    )