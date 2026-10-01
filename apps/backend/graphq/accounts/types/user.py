"""
GraphQL User type.

Accounts GraphQL boundary
-------------------------
This module exposes the centralized Univa User model through Graphene.

Architecture:
    Django User model
          │
          ▼
    UserNode
          │
          ├── UserFilter
          ├── User resolver/queryset
          └── Relay connection

Responsibilities:
    - GraphQL representation of User
    - Relay Node implementation
    - computed identity fields
    - lightweight profile/role resolution

Non-responsibilities:
    - authentication
    - authorization
    - user creation
    - role assignment
    - feature-specific business logic

Compatible with:
    - Graphene 3.2.3
    - Graphene-Django
    - Relay
"""

import graphene
from graphene import Node
from graphene_django import DjangoObjectType

from accounts.models.user import User

from graphq.accounts.filters.user import UserFilter


class UserNode(DjangoObjectType):
    """
    Relay GraphQL node for the centralized Univa User model.

    The node intentionally exposes only account-owned identity fields.

    Feature-specific information should be exposed by the owning
    application's GraphQL types.
    """

    # ------------------------------------------------------------------
    # Computed identity fields
    # ------------------------------------------------------------------

    full_name = graphene.String(
        description="User's complete name.",
    )

    display_name = graphene.String(
        description="Best available human-readable display name.",
    )

    is_email_verified = graphene.Boolean(
        description="Whether the user's email address has been verified.",
    )

    # ------------------------------------------------------------------
    # Role helpers
    # ------------------------------------------------------------------

    has_role = graphene.Boolean(
        app_name=graphene.String(required=True),
        role_name=graphene.String(required=True),
        description="Whether the user currently has the specified role.",
    )

    can_access_app = graphene.Boolean(
        app_name=graphene.String(required=True),
        description="Whether the user currently has access to an application.",
    )

    # ------------------------------------------------------------------
    # Meta
    # ------------------------------------------------------------------

    class Meta:
        model = User

        interfaces = (Node,)

        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "email_verified",
            "email_verified_at",
            "is_active",
            "date_joined",
            "last_login",
        )

        filterset_class = UserFilter

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    def resolve_full_name(self, info):
        """
        Return the user's first and last name.
        """

        first_name = (self.first_name or "").strip()
        last_name = (self.last_name or "").strip()

        return " ".join(
            part
            for part in (
                first_name,
                last_name,
            )
            if part
        )

    def resolve_display_name(self, info):
        """
        Resolve the user's best available display name.

        Priority:
            1. Profile display_name
            2. User full name
            3. Profile Univa ID
            4. Email
            5. Phone number
            6. Generic "User"
        """

        profile = getattr(
            self,
            "profile",
            None,
        )

        if profile:
            profile_display_name = getattr(
                profile,
                "display_name",
                None,
            )

            if profile_display_name:
                return profile_display_name

        full_name = self.resolve_full_name(info)

        if full_name:
            return full_name

        if profile:
            univa_id = getattr(
                profile,
                "univa_id",
                None,
            )

            if univa_id:
                return (
                    univa_id
                    if str(univa_id).startswith("@")
                    else f"@{univa_id}"
                )

        if self.email:
            return self.email

        if self.phone_number:
            return str(self.phone_number)

        return "User"

    # ------------------------------------------------------------------
    # Email verification
    # ------------------------------------------------------------------

    def resolve_is_email_verified(self, info):
        """
        Backward-compatible GraphQL alias for User.email_verified.
        """

        return self.email_verified

    # ------------------------------------------------------------------
    # Role checks
    # ------------------------------------------------------------------

    def resolve_has_role(
        self,
        info,
        app_name,
        role_name,
    ):
        """
        Resolve whether this user currently holds a role.

        Prefer the optimized GraphQL role cache populated by the
        User resolver when available.
        """

        if not app_name or not role_name:
            return False

        cached_roles = getattr(
            self,
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

        return self.has_role(
            app_name,
            role_name,
        )

    # ------------------------------------------------------------------
    # Application access
    # ------------------------------------------------------------------

    def resolve_can_access_app(
        self,
        info,
        app_name,
    ):
        """
        Resolve whether this user has access to an application.
        """

        if not app_name:
            return False

        cached_roles = getattr(
            self,
            "graphql_active_roles",
            None,
        )

        if cached_roles is not None:
            return any(
                assignment.role
                and assignment.role.app_name == app_name
                for assignment in cached_roles
            )

        return self.can_access_app(
            app_name,
        )