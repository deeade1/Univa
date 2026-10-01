"""
GraphQL queries for the centralized UserProfile model.

Graphene:
    3.2.3

Relay:
    Global Relay Node IDs

Architecture
------------

This module is the query/composition layer for UserProfile.

Responsibilities:
    - Expose UserProfile through Relay.
    - Connect UserProfileFilter to the Relay connection.
    - Delegate queryset construction to resolvers.
    - Resolve the authenticated user's own profile.

This module must NOT:
    - mutate profiles,
    - handle PIN/security credentials,
    - handle KYC/biometric verification,
    - implement feature-specific business logic,
    - expose sensitive profile fields directly.

Flow:

    GraphQL
        │
        ▼
    ProfileQuery
        │
        ├── UserProfileNode
        │
        ├── UserProfileFilter
        │
        └── Profile resolver
                │
                ▼
          UserProfile queryset
"""

from __future__ import annotations

import graphene
from graphene import relay
from graphene_django.filter import DjangoFilterConnectionField

from graphq.accounts.filters.profile import UserProfileFilter
from graphq.accounts.resolvers.profile import (
    optimize_profile_queryset,
    resolve_current_profile,
    resolve_profile,
    resolve_profiles,
)
from graphq.accounts.types.profile import UserProfileNode


class ProfileQuery(graphene.ObjectType):
    """
    Relay queries for the centralized UserProfile model.
    """

    # ==================================================================
    # Single profile
    # ==================================================================

    profile = graphene.Field(
        UserProfileNode,
        id=graphene.ID(
            required=True,
            description="Global Relay ID of the user profile.",
        ),
    )

    # ==================================================================
    # Profile connection
    # ==================================================================

    profiles = DjangoFilterConnectionField(
        UserProfileNode,
        filterset_class=UserProfileFilter,
        description="Relay connection of user profiles.",
    )

    # ==================================================================
    # Current authenticated user's profile
    # ==================================================================

    my_profile = graphene.Field(
        UserProfileNode,
        description=(
            "The profile belonging to the currently authenticated user."
        ),
    )

    # ==================================================================
    # Resolvers
    # ==================================================================

    @staticmethod
    def resolve_profile(root, info, id):
        """
        Resolve one UserProfile from a Relay global ID.

        Graphene decodes the Relay global ID. The resulting database
        primary key is then delegated to the profile resolver.
        """

        user_profile = relay.Node.get_node_from_global_id(
            info,
            id,
            only_type=UserProfileNode,
        )

        if user_profile is None:
            return None

        return resolve_profile(
            info,
            user_profile.pk,
        )

    @staticmethod
    def resolve_profiles(root, info, **kwargs):
        """
        Resolve the base UserProfile queryset.

        UserProfileFilter handles filtering and
        DjangoFilterConnectionField handles Relay pagination.

        The resolver is responsible only for constructing the
        optimized queryset.
        """

        queryset = resolve_profiles(info)

        return optimize_profile_queryset(queryset)

    @staticmethod
    def resolve_my_profile(root, info):
        """
        Resolve the currently authenticated user's profile.

        Returns None when:

            - the request is unauthenticated, or
            - the authenticated user has no profile.
        """

        return resolve_current_profile(info)


__all__ = [
    "ProfileQuery",
]