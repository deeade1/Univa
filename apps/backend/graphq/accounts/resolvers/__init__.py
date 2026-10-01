"""
Accounts GraphQL resolver package.

Graphene:
    3.2.3

Relay:
    Global Relay Node IDs

This package contains resolver modules for the centralized
Accounts GraphQL layer.

Modules:

    user.py
        User queryset and user resolution.

    profile.py
        UserProfile queryset and profile resolution.

    address.py
        Address queryset, visibility, and address resolution.

Architectural boundary
----------------------

Resolvers are responsible for:

    - constructing querysets
    - applying request-level authorization boundaries
    - optimizing related-object loading
    - resolving individual domain objects

Resolvers are NOT responsible for:

    - defining GraphQL types
    - defining GraphQL filters
    - implementing mutations
    - authentication flows
    - domain mutations
    - feature-specific business logic

The individual resolver modules remain the source of truth for
their respective domain.
"""

from .address import (
    can_view_address,
    get_active_role_ids,
    get_address_queryset,
    get_user_address_queryset,
    get_visible_address_queryset,
    optimize_address_queryset,
    resolve_address,
    resolve_addresses,
    resolve_default_address,
    resolve_default_addresses,
)

from .profile import (
    optimize_profile_queryset,
    resolve_profile,
    resolve_profiles,
    resolve_visible_profiles,
    resolve_my_profile,
    resolve_profile_for_user,
    can_view_profile,
    resolve_current_profile,  # ADD THIS
)

from .user import (
    get_user_queryset,
    get_active_user_queryset,  # ADD THIS
    resolve_current_user,
    get_visible_user_queryset,
    resolve_user,
    resolve_users,
    resolve_user_by_email,
    resolve_user_by_phone,
    resolve_user_profile,
    resolve_user_roles,
    resolve_user_app_roles,
    user_has_role,
    user_can_access_app,
    optimize_user_queryset,  # ADD THIS
)


__all__ = [
    # --------------------------------------------------------------
    # User
    # --------------------------------------------------------------
    "get_user_queryset",
    "get_active_user_queryset",  # ADD THIS
    "resolve_current_user",
    "get_visible_user_queryset",
    "resolve_user",
    "resolve_users",
    "resolve_user_by_email",
    "resolve_user_by_phone",
    "resolve_user_profile",
    "resolve_user_roles",
    "resolve_user_app_roles",
    "user_has_role",
    "user_can_access_app",
    "optimize_user_queryset",  # ADD THIS

    # --------------------------------------------------------------
    # Profile
    # --------------------------------------------------------------
    "optimize_profile_queryset",
    "resolve_profile",
    "resolve_profiles",
    "resolve_visible_profiles",
    "resolve_my_profile",
    "resolve_profile_for_user",
    "can_view_profile",
    "resolve_current_profile",  # ADD THIS

    # --------------------------------------------------------------
    # Address
    # --------------------------------------------------------------
    "can_view_address",
    "get_active_role_ids",
    "get_address_queryset",
    "get_user_address_queryset",
    "get_visible_address_queryset",
    "optimize_address_queryset",
    "resolve_address",
    "resolve_addresses",
    "resolve_default_address",
    "resolve_default_addresses",
]