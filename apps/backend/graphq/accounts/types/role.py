"""
GraphQL Relay types for Accounts roles.

Graphene:
    3.2.3

Relay:
    Global Relay Node IDs

Models:
    accounts.models.role.Role
    accounts.models.role.UserRole

Architecture
------------

    Role
      │
      └── user_assignments
              │
              ▼
          UserRole
              │
              ├── user
              └── role

This module is responsible only for representing the Accounts role
models through GraphQL.

It does NOT:
    - assign roles
    - revoke roles
    - activate/deactivate roles
    - perform authorization decisions
    - implement role-management business logic
    - expose Django Permission internals directly
"""

from __future__ import annotations

import graphene
from graphene import Node
from graphene_django_optimizer import OptimizedDjangoObjectType

from accounts.models.role import Role, UserRole


# ============================================================================
# UserRole Relay Node
# ============================================================================


class UserRoleNode(OptimizedDjangoObjectType):
    """
    Relay node representing a persistent role assignment.

    A UserRole represents the relationship between:

        User
          │
          ▼
        Role

    The lifecycle state of the assignment is exposed, while role
    management operations remain outside this type.
    """

    # ------------------------------------------------------------------
    # Computed / display fields
    # ------------------------------------------------------------------

    role_name = graphene.String(
        description="Name of the assigned role.",
    )

    role_app_name = graphene.String(
        description="Application that owns the assigned role.",
    )

    role_display_name = graphene.String(
        description="Human-readable role label.",
    )

    is_expired = graphene.Boolean(
        description="Whether this role assignment has expired.",
    )

    is_revoked = graphene.Boolean(
        description="Whether this role assignment has been revoked.",
    )

    # ------------------------------------------------------------------
    # Meta
    # ------------------------------------------------------------------

    class Meta:
        model = UserRole

        interfaces = (
            Node,
        )

        fields = (
            "id",
            "user",
            "role",
            "is_active",
            "created_at",
            "created_by",
            "verified_at",
            "verified_by",
            "notes",
            "expires_at",
            "revoked_at",
            "revoked_by",
        )

    # ------------------------------------------------------------------
    # Resolvers
    # ------------------------------------------------------------------

    @staticmethod
    def resolve_role_name(
        root,
        info,
    ):
        role = getattr(
            root,
            "role",
            None,
        )

        return role.name if role else None

    @staticmethod
    def resolve_role_app_name(
        root,
        info,
    ):
        role = getattr(
            root,
            "role",
            None,
        )

        return role.app_name if role else None

    @staticmethod
    def resolve_role_display_name(
        root,
        info,
    ):
        role = getattr(
            root,
            "role",
            None,
        )

        if not role:
            return None

        return role.name

    @staticmethod
    def resolve_is_expired(
        root,
        info,
    ):
        return root.is_expired

    @staticmethod
    def resolve_is_revoked(
        root,
        info,
    ):
        return root.is_revoked


# ============================================================================
# Role Relay Node
# ============================================================================


class RoleNode(OptimizedDjangoObjectType):
    """
    Relay node representing an application role.

    A Role defines an application-level capability grouping.

    Examples:

        transport / driver
        realestate / agent
        ecommerce / vendor
        banking / banker

    Actual authorization decisions remain outside this GraphQL type.
    """

    role_name = graphene.String(
        description="Role name.",
    )

    app_name = graphene.String(
        description="Application that owns this role.",
    )

    app_display_name = graphene.String(
        description="Human-readable application name.",
    )

    role_display_name = graphene.String(
        description="Human-readable role label.",
    )

    user_assignments = graphene.List(
        UserRoleNode,
        description="Role assignments associated with this role.",
    )

    # ------------------------------------------------------------------
    # Meta
    # ------------------------------------------------------------------

    class Meta:
        model = Role

        interfaces = (Node,)

       
        fields = (
            "id",
            "name",
            "app_name",
            "permissions",
            "description",
            "is_default",
            "requires_verification",
            "auto_assign",
        )

    # ------------------------------------------------------------------
    # Resolvers
    # ------------------------------------------------------------------

    @staticmethod
    def resolve_role_name(
        root,
        info,
    ):
        return root.name

    @staticmethod
    def resolve_app_name(
        root,
        info,
    ):
        return root.app_name

    @staticmethod
    def resolve_app_display_name(
        root,
        info,
    ):
        return root.get_app_name_display()

    @staticmethod
    def resolve_role_display_name(
        root,
        info,
    ):
        return str(root)

    @staticmethod
    def resolve_user_assignments(
        root,
        info,
    ):
        """
        Resolve assignments belonging to this role.

        The relationship is already defined by the model as:

            Role.user_assignments

        Query optimization should normally be handled by the resolver
        or queryset supplied by the parent query.
        """

        return (
            root.user_assignments
            .select_related(
                "user",
                "role",
                "created_by",
                "verified_by",
                "revoked_by",
            )
            .all()
        )


__all__ = [
    "RoleNode",
    "UserRoleNode",
]