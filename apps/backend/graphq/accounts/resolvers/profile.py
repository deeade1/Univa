"""
Profile resolvers for the Accounts GraphQL domain.

Architecture
------------
The resolver layer is intentionally thin.

Responsibilities:
    - Resolve profile querysets.
    - Apply authentication / ownership visibility.
    - Optimize ORM access.
    - Delegate business logic to account/domain services.

The resolver must NOT:
    - mutate UserProfile directly,
    - implement verification business rules,
    - handle PIN/security credentials,
    - contain feature-specific logic,
    - perform ecommerce/transport/real-estate queries.

Graphene:
    3.2.3

Relay:
    Global Relay Node IDs
"""

from django.db.models import Q

from accounts.models.profile import UserProfile


# ============================================================================
# Queryset helpers
# ============================================================================

def _profile_queryset():
    """
    Base optimized UserProfile queryset.

    UserProfile has a OneToOne relationship with User, so select_related()
    is appropriate here.

    Location fields are stored directly on UserProfile through
    LocationModel and require no additional relation.
    """
    return (
        UserProfile.objects
        .select_related(
            "user",
        )
    )


# ============================================================================
# Profile access
# ============================================================================

def can_view_profile(requesting_user, profile):
    """
    Determine whether requesting_user may view a profile.

    Public profile information is generally readable.

    Anonymous users may therefore access the public profile surface.

    Private/sensitive fields are controlled by the GraphQL type itself
    and are never exposed merely because the requester owns the profile.
    """

    if not profile:
        return False

    return True


# ============================================================================
# Profile queryset
# ============================================================================

def resolve_profiles(info):
    """
    Resolve the UserProfile collection.

    This is the primary resolver used by the accounts GraphQL query layer.

    Filtering is deliberately not performed here. Filtering belongs to
    ``graphq.accounts.filters.profile``.
    """

    queryset = _profile_queryset()

    return queryset


# ============================================================================
# Single profile resolution
# ============================================================================

def resolve_profile(info, profile_id):
    """
    Resolve a single profile by database primary key.

    This helper is intended for internal resolver composition.

    Relay global-ID decoding should happen before calling this function.
    """

    if profile_id is None:
        return None

    return (
        _profile_queryset()
        .filter(pk=profile_id)
        .first()
    )


# ============================================================================
# Profile by user
# ============================================================================

def resolve_profile_for_user(info, user):
    """
    Resolve the profile belonging to a specific User instance.

    Returns None if the user does not currently have a profile.
    """

    if user is None:
        return None

    return (
        _profile_queryset()
        .filter(user=user)
        .first()
    )


# ============================================================================
# Current authenticated user's profile
# ============================================================================

def resolve_my_profile(info):
    """
    Resolve the currently authenticated user's profile.

    Returns None for anonymous users or users without a profile.
    """

    user = getattr(info.context, "user", None)

    if not user or not user.is_authenticated:
        return None

    return (
        _profile_queryset()
        .filter(user=user)
        .first()
    )


# ============================================================================
# Profile visibility queryset
# ============================================================================

def resolve_visible_profiles(info):
    """
    Return profiles visible to the current GraphQL requester.

    At the current account architecture level, public profile information
    is readable without requiring authentication.

    More restrictive visibility rules can be introduced later through
    dedicated account/privacy services without changing the GraphQL type.
    """

    return _profile_queryset()


# ============================================================================
# Profile optimization
# ============================================================================

def optimize_profile_queryset(queryset):
    """
    Apply additional ORM optimization to an existing profile queryset.

    This function is intentionally reusable by queries, Relay connections,
    and nested resolvers.

    UserProfile currently has one direct relational dependency:

        UserProfile -> User

    Therefore select_related("user") is sufficient here.
    """

    return queryset.select_related("user")


# ============================================================================
# Nested user -> profile resolver
# ============================================================================

def resolve_user_profile(user):
    """
    Resolve a User's profile.

    Designed for the UserNode resolver layer.

    Avoids raising RelatedObjectDoesNotExist when a profile has not yet
    been provisioned.
    """

    if user is None:
        return None

    return (
        UserProfile.objects
        .select_related("user")
        .filter(user=user)
        .first()
    )
    


# ============================================================================
# Current User Profile
# ============================================================================


def resolve_current_profile(info):
    """
    Resolve the authenticated user's profile.
    
    Returns None if:
        - the user is unauthenticated
        - the user has no profile
    """
    user = info.context.user
    
    if not user or not user.is_authenticated:
        return None
    
    # Get the user with the profile optimized
    from .user import get_user_queryset
    
    user_with_profile = (
        get_user_queryset()
        .filter(pk=user.pk)
        .first()
    )
    
    if not user_with_profile:
        return None
    
    return getattr(user_with_profile, "profile", None)