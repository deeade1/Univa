"""
GraphQL queries for the centralized Accounts User model.

Graphene:
    3.2.3

Relay:
    Global Relay Node IDs

Architecture
------------
This module is the query/composition layer.

Responsibilities:
    - Expose Relay UserNode queries.
    - Connect UserFilter to the Relay connection.
    - Delegate queryset construction to resolvers.
    - Resolve individual Users through Relay global IDs.

This module must NOT:
    - mutate users,
    - assign roles,
    - handle authentication,
    - implement verification logic,
    - contain feature-specific business logic.
"""

import graphene
from graphene import relay
from graphene_django.filter import DjangoFilterConnectionField

from graphq.accounts.filters.user import UserFilter
from graphq.accounts.resolvers.user import (
    resolve_current_user,
    resolve_user,
    resolve_users,
)
from graphq.accounts.types.user import UserNode


class UserQuery(graphene.ObjectType):
    """
    Relay queries for the centralized User model.
    """

    # ==================================================================
    # Single user
    # ==================================================================

    user = graphene.Field(
        UserNode,
        id=graphene.ID(
            required=True,
            description="Global Relay ID of the user.",
        ),
    )

    # ==================================================================
    # User connection
    # ==================================================================

    users = DjangoFilterConnectionField(
        UserNode,
        filterset_class=UserFilter,
        description="Relay connection of users.",
    )

    # ==================================================================
    # Current authenticated user
    # ==================================================================

    me = graphene.Field(
        UserNode,
        description="The currently authenticated user.",
    )

    # ==================================================================
    # Resolvers
    # ==================================================================

    @staticmethod
    def resolve_user(root, info, id):
        """
        Resolve one User from a Relay global ID.
        """

        target_user = relay.Node.get_node_from_global_id(
            info,
            id,
            only_type=UserNode,
        )

        if target_user is None:
            return None

        return resolve_user(
            info.context.user,
            target_user.pk,
        )

    @staticmethod
    def resolve_users(root, info, **kwargs):
        """
        Resolve the base User queryset.

        Filtering and Relay pagination are handled by
        DjangoFilterConnectionField.

        The resolver layer already returns an optimized queryset,
        so no additional optimization is applied here.
        """

        return resolve_users(info.context.user)

    @staticmethod
    def resolve_me(root, info):
        """
        Resolve the currently authenticated User.
        """

        return resolve_current_user(info.context.user)


__all__ = [
    "UserQuery",
]