# apps/backend/graphq/accounts/queries/role.py

"""
GraphQL queries for Accounts roles.

Graphene:
    3.2.3

Relay:
    Global Relay Node IDs

Architecture
------------

This module is the GraphQL query/composition layer for:

    accounts.models.role.Role
    accounts.models.role.UserRole

Responsibilities:
    - expose Role through Relay
    - expose UserRole through Relay
    - connect django-filter FilterSets to Relay connections
    - decode Relay global IDs
    - delegate queryset construction to resolvers

This module does NOT:
    - create roles
    - assign roles
    - activate roles
    - deactivate roles
    - revoke roles
    - handle authentication
    - implement authorization policy
    - contain feature-specific business logic

Filtering:
    RoleFilter
    UserRoleFilter
    ActiveUserRoleFilter

Querysets:
    graphq.accounts.resolvers.role
"""

from __future__ import annotations

import graphene
from graphene import relay
from graphene_django.filter import DjangoFilterConnectionField

from graphq.accounts.filters.role import (
    ActiveUserRoleFilter,
    RoleFilter,
    UserRoleFilter,
)
from graphq.accounts.resolvers.role import (
    resolve_active_user_roles,
    resolve_default_roles,
    resolve_effective_roles,
    resolve_role,
    resolve_roles,
    resolve_user_role,
    resolve_user_roles,
    resolve_user_role_assignments,
)
from graphq.accounts.types.role import (
    RoleNode,
    UserRoleNode,
)


class RoleQuery(graphene.ObjectType):
    """
    Relay query surface for Accounts roles and role assignments.

    All role-related queries are intentionally composed here so the
    Accounts schema has one predictable query object.
    """

    # ==================================================================
    # Single Role
    # ==================================================================

    role = graphene.Field(
        RoleNode,
        id=graphene.ID(
            required=True,
            description="Global Relay ID of the role.",
        ),
    )

    # ==================================================================
    # Role Connection
    # ==================================================================

    roles = DjangoFilterConnectionField(
        RoleNode,
        filterset_class=RoleFilter,
        description="Relay connection of application roles.",
    )

    # ==================================================================
    # Default Roles
    # ==================================================================

    default_roles = DjangoFilterConnectionField(
        RoleNode,
        filterset_class=RoleFilter,
        description="Relay connection of default application roles.",
    )

    # ==================================================================
    # Single UserRole Assignment
    # ==================================================================

    user_role = graphene.Field(
        UserRoleNode,
        id=graphene.ID(
            required=True,
            description="Global Relay ID of the user-role assignment.",
        ),
    )

    # ==================================================================
    # UserRole Connection
    # ==================================================================

    user_roles = DjangoFilterConnectionField(
        UserRoleNode,
        filterset_class=UserRoleFilter,
        description="Relay connection of user-role assignments.",
    )

    # ==================================================================
    # Current User's Role Assignments
    # ==================================================================

    my_user_roles = DjangoFilterConnectionField(
        UserRoleNode,
        filterset_class=UserRoleFilter,
        description=(
            "Relay connection containing role assignments belonging "
            "to the authenticated user."
        ),
    )

    # ==================================================================
    # Current User's Effective Role Assignments
    # ==================================================================

    my_active_user_roles = DjangoFilterConnectionField(
        UserRoleNode,
        filterset_class=ActiveUserRoleFilter,
        description=(
            "Relay connection containing currently effective role "
            "assignments belonging to the authenticated user."
        ),
    )

    # ==================================================================
    # Current User's Effective Role Definitions
    # ==================================================================

    my_roles = DjangoFilterConnectionField(
        RoleNode,
        filterset_class=RoleFilter,
        description=(
            "Relay connection containing application roles currently "
            "effective for the authenticated user."
        ),
    )

    # ==================================================================
    # Active UserRole Connection
    # ==================================================================

    active_user_roles = DjangoFilterConnectionField(
        UserRoleNode,
        filterset_class=ActiveUserRoleFilter,
        description=(
            "Relay connection of currently effective role assignments."
        ),
    )

    # ==================================================================
    # Single Role Resolver
    # ==================================================================

    @staticmethod
    def resolve_role(root, info, id):
        """
        Resolve one Role from a Relay global ID.

        Relay decoding happens at the GraphQL boundary.
        The database primary key is then passed to the resolver layer.
        """

        role = relay.Node.get_node_from_global_id(
            info,
            id,
            only_type=RoleNode,
        )

        if role is None:
            return None

        return resolve_role(role.pk)

    # ==================================================================
    # Role Connection Resolver
    # ==================================================================

    @staticmethod
    def resolve_roles(root, info, **kwargs):
        """
        Resolve the base Role queryset.

        RoleFilter performs filtering.

        DjangoFilterConnectionField performs:
            - filtering integration
            - Relay pagination
            - connection construction
        """

        return resolve_roles()

    # ==================================================================
    # Default Role Resolver
    # ==================================================================

    @staticmethod
    def resolve_default_roles(root, info, **kwargs):
        """
        Resolve roles configured as default/auto-assigned roles.
        """

        return resolve_default_roles()

    # ==================================================================
    # Single UserRole Resolver
    # ==================================================================

    @staticmethod
    def resolve_user_role(root, info, id):
        """
        Resolve one UserRole assignment from a Relay global ID.
        """

        user_role = relay.Node.get_node_from_global_id(
            info,
            id,
            only_type=UserRoleNode,
        )

        if user_role is None:
            return None

        return resolve_user_role(user_role.pk)

    # ==================================================================
    # UserRole Connection Resolver
    # ==================================================================

    @staticmethod
    def resolve_user_roles(root, info, **kwargs):
        """
        Resolve the base UserRole queryset.

        UserRoleFilter handles filtering.
        """

        return resolve_user_roles()

    # ==================================================================
    # Current User's Role Assignments
    # ==================================================================

    @staticmethod
    def resolve_my_user_roles(root, info, **kwargs):
        """
        Resolve role assignments belonging to the authenticated user.

        Ownership is established by the resolver before GraphQL
        filtering and Relay pagination are applied.
        """

        user = getattr(
            info.context,
            "user",
            None,
        )

        return resolve_user_role_assignments(user)

    # ==================================================================
    # Current User's Effective Role Assignments
    # ==================================================================

    @staticmethod
    def resolve_my_active_user_roles(root, info, **kwargs):
        """
        Resolve currently effective role assignments belonging to
        the authenticated user.
        """

        user = getattr(
            info.context,
            "user",
            None,
        )

        return resolve_active_user_roles(user)

    # ==================================================================
    # Current User's Effective Role Definitions
    # ==================================================================

    @staticmethod
    def resolve_my_roles(root, info, **kwargs):
        """
        Resolve Role definitions currently effective for the
        authenticated user.
        """

        user = getattr(
            info.context,
            "user",
            None,
        )

        return resolve_effective_roles(user)

    # ==================================================================
    # Active UserRole Connection
    # ==================================================================

    @staticmethod
    def resolve_active_user_roles(root, info, **kwargs):
        """
        Resolve currently effective UserRole assignments.

        This is intentionally not scoped to the current user.
        Access control for this broader connection should be handled
        by the Accounts authorization layer before this field is
        exposed publicly.
        """

        return resolve_active_user_roles(
            getattr(
                info.context,
                "user",
                None,
            )
        )


__all__ = [
    "RoleQuery",
]