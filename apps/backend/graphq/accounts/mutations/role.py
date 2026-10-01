"""
GraphQL mutations for application Roles and UserRole assignments.

All mutations use relay.ClientIDMutation.

Responsibilities
----------------
Role mutations manage application-level Role definitions.

UserRole mutations manage:
    - assigning roles to users
    - activating/deactivating assignments
    - verification
    - revocation
    - switching active application roles

Role verification here means verification of the ROLE ASSIGNMENT.
It does not perform face verification, KYC, or identity verification.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

import graphene
from graphene import relay
from graphql import GraphQLError
from graphql_relay import from_global_id
from accounts.models import Role, UserRole
from accounts.models.user import User

from graphq.accounts.types.role import RoleNode, UserRoleNode
from graphq.accounts.types.user import UserNode


# =============================================================================
# HELPERS
# =============================================================================


class RoleMutationMixin:
    """Shared authentication, authorization and ID helpers."""

    @staticmethod
    def require_authenticated_user(info):
        user = getattr(info.context, "user", None)

        if not user or not user.is_authenticated:
            raise GraphQLError("Authentication required.")

        if not user.is_active:
            raise GraphQLError("User account is inactive.")

        return user

    @staticmethod
    def require_superuser(info):
        user = RoleMutationMixin.require_authenticated_user(info)

        if not user.is_superuser:
            raise GraphQLError(
                "Superuser permission required."
            )

        return user

    @staticmethod
    def require_admin(info):
        user = RoleMutationMixin.require_authenticated_user(info)

        if not (
            user.is_superuser
            or getattr(user, "is_staff", False)
            or user.has_role("admin", "admin")
        ):
            raise GraphQLError(
                "Administrator permission required."
            )

        return user

    @staticmethod
    def decode_id(global_id, expected_type=None):
        """Decode a Relay global ID and optionally validate its type."""

        if not global_id:
            raise GraphQLError("A valid ID is required.")

        try:
            type_name, database_id = from_global_id(global_id)
        except Exception as exc:
            raise GraphQLError(
                "Invalid Relay global ID."
            ) from exc

        if not database_id:
            raise GraphQLError("Invalid Relay global ID.")

        if expected_type and type_name != expected_type:
            raise GraphQLError(
                f"Expected {expected_type} ID, received {type_name}."
            )

        return database_id

    @staticmethod
    def get_role(role_id):
        database_id = RoleMutationMixin.decode_id(
            role_id,
            expected_type="RoleNode",
        )

        try:
            return Role.objects.get(pk=database_id)
        except Role.DoesNotExist as exc:
            raise GraphQLError(
                "Role not found."
            ) from exc

    @staticmethod
    def get_user(user_id):
        database_id = RoleMutationMixin.decode_id(
            user_id,
            expected_type="UserNode",
        )

        try:
            return User.objects.get(pk=database_id)
        except User.DoesNotExist as exc:
            raise GraphQLError(
                "User not found."
            ) from exc

    @staticmethod
    def get_user_role(user_role_id):
        database_id = RoleMutationMixin.decode_id(
            user_role_id,
            expected_type="UserRoleNode",
        )

        try:
            return UserRole.objects.select_related(
                "user",
                "role",
                "created_by",
                "verified_by",
                "revoked_by",
            ).get(pk=database_id)
        except UserRole.DoesNotExist as exc:
            raise GraphQLError(
                "User role assignment not found."
            ) from exc

    @staticmethod
    def get_or_create_role(app_name, role_name):
        try:
            return Role.objects.get(
                app_name=app_name,
                name=role_name,
            )
        except Role.DoesNotExist as exc:
            raise GraphQLError(
                f"Role '{role_name}' does not exist "
                f"for application '{app_name}'."
            ) from exc

    @staticmethod
    def build_user_role_defaults(
        role,
        *,
        is_active=True,
        created_by=None,
        expires_at=None,
        notes="",
    ):
        """
        Build UserRole state while respecting role verification policy.

        Roles requiring verification cannot become active until verified.
        """

        if role.requires_verification:
            is_active = False

        return {
            "is_active": is_active,
            "created_by": created_by,
            "expires_at": expires_at,
            "notes": notes or "",
        }


# =============================================================================
# CREATE ROLE
# =============================================================================


class CreateRole(relay.ClientIDMutation, RoleMutationMixin):
    class Input:
        name = graphene.String(required=True)
        app_name = graphene.String(required=True)
        description = graphene.String()
        is_default = graphene.Boolean()
        requires_verification = graphene.Boolean()
        auto_assign = graphene.Boolean()

    success = graphene.Boolean()
    message = graphene.String()
    role = graphene.Field(RoleNode)

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        cls.require_superuser(info)

        name = input["name"].strip()
        app_name = input["app_name"].strip().lower()

        if not name:
            raise GraphQLError(
                "Role name cannot be empty."
            )

        valid_apps = dict(Role.APP_CHOICES)

        if app_name not in valid_apps:
            raise GraphQLError(
                f"Invalid application: {app_name}."
            )

        if Role.objects.filter(
            name=name,
            app_name=app_name,
        ).exists():
            raise GraphQLError(
                "A role with this name already exists "
                "for this application."
            )

        role = Role.objects.create(
            name=name,
            app_name=app_name,
            description=input.get("description", "") or "",
            is_default=input.get("is_default", False),
            requires_verification=input.get(
                "requires_verification",
                False,
            ),
            auto_assign=input.get("auto_assign", False),
        )

        return cls(
            success=True,
            message="Role created successfully.",
            role=role,
        )


# =============================================================================
# UPDATE ROLE
# =============================================================================


class UpdateRole(relay.ClientIDMutation, RoleMutationMixin):
    class Input:
        role_id = graphene.ID(required=True)
        name = graphene.String()
        app_name = graphene.String()
        description = graphene.String()
        is_default = graphene.Boolean()
        requires_verification = graphene.Boolean()
        auto_assign = graphene.Boolean()

    success = graphene.Boolean()
    message = graphene.String()
    role = graphene.Field(RoleNode)

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        cls.require_superuser(info)

        role = cls.get_role(input["role_id"])

        if "name" in input and input["name"] is not None:
            name = input["name"].strip()

            if not name:
                raise GraphQLError(
                    "Role name cannot be empty."
                )

            role.name = name

        if "app_name" in input and input["app_name"] is not None:
            app_name = input["app_name"].strip().lower()

            if app_name not in dict(Role.APP_CHOICES):
                raise GraphQLError(
                    f"Invalid application: {app_name}."
                )

            role.app_name = app_name

        if "description" in input:
            role.description = input["description"] or ""

        if "is_default" in input:
            role.is_default = input["is_default"]

        if "requires_verification" in input:
            role.requires_verification = input[
                "requires_verification"
            ]

        if "auto_assign" in input:
            role.auto_assign = input["auto_assign"]

        role.full_clean()
        role.save()

        return cls(
            success=True,
            message="Role updated successfully.",
            role=role,
        )


# =============================================================================
# DELETE ROLE
# =============================================================================


class DeleteRole(relay.ClientIDMutation, RoleMutationMixin):
    class Input:
        role_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    deleted_id = graphene.ID()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        cls.require_superuser(info)

        role = cls.get_role(input["role_id"])

        deleted_id = input["role_id"]
        role.delete()

        return cls(
            success=True,
            message="Role deleted successfully.",
            deleted_id=deleted_id,
        )


# =============================================================================
# ASSIGN USER ROLE
# =============================================================================


class AssignUserRole(relay.ClientIDMutation, RoleMutationMixin):
    class Input:
        user_id = graphene.ID(required=True)
        role_id = graphene.ID(required=True)
        is_active = graphene.Boolean()
        expires_at = graphene.DateTime()
        notes = graphene.String()

    success = graphene.Boolean()
    message = graphene.String()
    user = graphene.Field(UserNode)
    user_role = graphene.Field(UserRoleNode)

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        actor = cls.require_authenticated_user(info)

        user = cls.get_user(input["user_id"])
        role = cls.get_role(input["role_id"])

        if UserRole.objects.filter(
            user=user,
            role=role,
        ).exists():
            raise GraphQLError(
                "This user already has an assignment for this role."
            )

        # Capability roles requiring verification must remain pending.
        if role.requires_verification:
            is_active = False
        else:
            is_active = input.get("is_active", True)

        user_role = UserRole.objects.create(
            user=user,
            role=role,
            is_active=is_active,
            created_by=actor,
            expires_at=input.get("expires_at"),
            notes=input.get("notes", "") or "",
        )

        user_role.full_clean()

        return cls(
            success=True,
            message=(
                "Role assigned and activated successfully."
                if user_role.is_active
                else "Role assigned and awaiting verification."
            ),
            user=user,
            user_role=user_role,
        )


# =============================================================================
# BULK ASSIGN USER ROLES
# =============================================================================


class BulkAssignUserRoles(relay.ClientIDMutation, RoleMutationMixin):
    class Input:
        user_id = graphene.ID(required=True)
        role_ids = graphene.List(
            graphene.NonNull(graphene.ID),
            required=True,
        )
        notes = graphene.String()

    success = graphene.Boolean()
    message = graphene.String()
    user_roles = graphene.List(UserRoleNode)

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        actor = cls.require_authenticated_user(info)

        user = cls.get_user(input["user_id"])

        created = []

        for role_id in input["role_ids"]:
            role = cls.get_role(role_id)

            if UserRole.objects.filter(
                user=user,
                role=role,
            ).exists():
                continue

            user_role = UserRole.objects.create(
                user=user,
                role=role,
                is_active=not role.requires_verification,
                created_by=actor,
                notes=input.get("notes", "") or "",
            )

            user_role.full_clean()
            created.append(user_role)

        return cls(
            success=True,
            message=f"{len(created)} role(s) assigned.",
            user_roles=created,
        )


# =============================================================================
# UNASSIGN USER ROLE
# =============================================================================


class UnassignUserRole(relay.ClientIDMutation, RoleMutationMixin):
    class Input:
        user_role_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    user_role = graphene.Field(UserRoleNode)

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        actor = cls.require_authenticated_user(info)

        user_role = cls.get_user_role(input["user_role_id"])

        # Keep lifecycle history instead of deleting the assignment.
        user_role.deactivate()

        if user_role.revoked_at is None:
            user_role.revoked_by = actor
            user_role.revoked_at = timezone.now()
            user_role.save(
                update_fields=[
                    "is_active",
                    "revoked_at",
                    "revoked_by",
                ]
            )

        return cls(
            success=True,
            message="Role assignment revoked.",
            user_role=user_role,
        )


# =============================================================================
# UPDATE USER ROLE
# =============================================================================


class UpdateUserRole(relay.ClientIDMutation, RoleMutationMixin):
    class Input:
        user_role_id = graphene.ID(required=True)
        expires_at = graphene.DateTime()
        notes = graphene.String()
        is_active = graphene.Boolean()

    success = graphene.Boolean()
    message = graphene.String()
    user_role = graphene.Field(UserRoleNode)

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        cls.require_authenticated_user(info)

        user_role = cls.get_user_role(input["user_role_id"])

        if "expires_at" in input:
            user_role.expires_at = input["expires_at"]

        if "notes" in input:
            user_role.notes = input["notes"] or ""

        if "is_active" in input:
            requested_active = input["is_active"]

            if (
                requested_active
                and user_role.role.requires_verification
                and not user_role.is_verified
            ):
                raise GraphQLError(
                    "This role requires verification before activation."
                )

            user_role.is_active = requested_active

        user_role.full_clean()
        user_role.save()

        return cls(
            success=True,
            message="User role updated successfully.",
            user_role=user_role,
        )


# =============================================================================
# BULK DELETE USER ROLES
# =============================================================================


class BulkDeleteUserRoles(relay.ClientIDMutation, RoleMutationMixin):
    class Input:
        user_role_ids = graphene.List(
            graphene.NonNull(graphene.ID),
            required=True,
        )

    success = graphene.Boolean()
    message = graphene.String()
    deleted_ids = graphene.List(graphene.ID)

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        cls.require_admin(info)

        deleted_ids = []

        for user_role_id in input["user_role_ids"]:
            user_role = cls.get_user_role(user_role_id)
            deleted_ids.append(user_role_id)
            user_role.delete()

        return cls(
            success=True,
            message=f"{len(deleted_ids)} role assignment(s) deleted.",
            deleted_ids=deleted_ids,
        )


# =============================================================================
# VERIFY USER ROLE
# =============================================================================


class VerifyUserRole(relay.ClientIDMutation, RoleMutationMixin):
    class Input:
        user_role_id = graphene.ID(required=True)
        notes = graphene.String()

    success = graphene.Boolean()
    message = graphene.String()
    user_role = graphene.Field(UserRoleNode)

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        verifier = cls.require_admin(info)

        user_role = cls.get_user_role(input["user_role_id"])

        if user_role.revoked_at:
            raise GraphQLError(
                "A revoked role assignment cannot be verified."
            )

        if not user_role.role.requires_verification:
            raise GraphQLError(
                "This role does not require verification."
            )

        if input.get("notes") is not None:
            user_role.notes = input["notes"]

        user_role.activate(verified_by=verifier)

        return cls(
            success=True,
            message="Role assignment verified and activated.",
            user_role=user_role,
        )


# =============================================================================
# REVOKE USER ROLE
# =============================================================================


class RevokeUserRole(relay.ClientIDMutation, RoleMutationMixin):
    class Input:
        user_role_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    user_role = graphene.Field(UserRoleNode)

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        actor = cls.require_authenticated_user(info)

        user_role = cls.get_user_role(input["user_role_id"])

        user_role.revoke(by_user=actor)

        return cls(
            success=True,
            message="Role assignment revoked successfully.",
            user_role=user_role,
        )


# =============================================================================
# SWITCH ACTIVE APP ROLE
# =============================================================================


class SwitchAppRole(relay.ClientIDMutation, RoleMutationMixin):
    class Input:
        user_role_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    active_role = graphene.Field(UserRoleNode)

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = cls.require_authenticated_user(info)

        target = cls.get_user_role(input["user_role_id"])

        if target.user_id != user.pk:
            raise GraphQLError(
                "You can only switch your own active role."
            )

        if not target.effective_active:
            raise GraphQLError(
                "This role assignment is not currently active."
            )

        # Deactivate other effective roles in the same application.
        UserRole.objects.filter(
            user=user,
            role__app_name=target.role.app_name,
            is_active=True,
            revoked_at__isnull=True,
        ).exclude(
            pk=target.pk,
        ).update(
            is_active=False,
        )

        target.is_active = True
        target.save(update_fields=["is_active"])

        return cls(
            success=True,
            message="Active application role switched.",
            active_role=target,
        )


# =============================================================================
# GET ACTIVE APP ROLE
# =============================================================================


class GetActiveAppRole(relay.ClientIDMutation, RoleMutationMixin):
    class Input:
        user_id = graphene.ID(required=True)
        app_name = graphene.String(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    active_role = graphene.Field(UserRoleNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        actor = cls.require_authenticated_user(info)

        user = cls.get_user(input["user_id"])
        app_name = input["app_name"].strip().lower()

        # Users may inspect themselves. Admins may inspect another user.
        if user.pk != actor.pk:
            cls.require_admin(info)

        active_role = (
            UserRole.objects
            .get_user_roles(
                user=user,
                app_name=app_name,
            )
            .select_related(
                "role",
                "user",
                "created_by",
                "verified_by",
                "revoked_by",
            )
            .first()
        )

        if not active_role:
            return cls(
                success=False,
                message="No active role found for this application.",
                active_role=None,
            )

        return cls(
            success=True,
            message="Active role retrieved successfully.",
            active_role=active_role,
        )


# =============================================================================
# GRAPHENE MUTATION REGISTRY
# =============================================================================


class RoleMutations(graphene.ObjectType):
    create_role = CreateRole.Field()
    update_role = UpdateRole.Field()
    delete_role = DeleteRole.Field()

    assign_user_role = AssignUserRole.Field()
    bulk_assign_user_roles = BulkAssignUserRoles.Field()
    unassign_user_role = UnassignUserRole.Field()

    update_user_role = UpdateUserRole.Field()
    bulk_delete_user_roles = BulkDeleteUserRoles.Field()

    verify_user_role = VerifyUserRole.Field()
    revoke_user_role = RevokeUserRole.Field()

    switch_app_role = SwitchAppRole.Field()
    get_active_app_role = GetActiveAppRole.Field()
