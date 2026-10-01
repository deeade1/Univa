"""
Tests for GraphQL role and user-role mutations.

Target:
    apps/backend/graphq/accounts/mutations/role.py

Testing strategy
----------------

These tests intentionally cover the highest-risk boundaries first:

    1. Authentication
    2. Superuser authorization
    3. Admin/staff authorization
    4. Relay global-ID validation
    5. Role lifecycle
    6. UserRole lifecycle
    7. Verification-required roles
    8. Expiration
    9. Revocation
    10. Atomic replacement/bulk operations
    11. Cross-user query authorization
    12. Application-role selection

The tests call the mutation classes directly with a GraphQL-like
context. This keeps the suite focused on the mutation module itself
rather than coupling every test to the entire GraphQL schema.

Run:

    python manage.py test graphq.accounts.mutations.tests.test_role

or, if pytest is configured:

    pytest graphq/accounts/mutations/tests/test_role.py -q
"""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from graphql import GraphQLError
from graphql_relay import to_global_id

from accounts.models.role import Role, UserRole

from graphq.accounts.mutations.role import (
    AssignUserRoleMutation,
    BulkAssignUserRolesMutation,
    BulkDeleteUserRolesMutation,
    CreateRoleMutation,
    DeleteRoleMutation,
    GetActiveAppRoleMutation,
    RoleMutationMixin,
    RoleQueries,
    RevokeUserRoleMutation,
    SwitchAppRoleMutation,
    UnassignUserRoleMutation,
    UpdateRoleMutation,
    UpdateUserRoleMutation,
    UpdateUserRolesMutation,
    VerifyUserRoleMutation,
)

from graphq.accounts.types import (
    RoleNode,
    UserNode,
    UserRoleNode,
)


User = get_user_model()


# =============================================================================
# TEST FIXTURES
# =============================================================================


class RoleMutationTestCase(TestCase):
    """
    Shared fixtures for role mutation tests.
    """

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            email="role-superuser@example.com",
            password="test-password",
        )

        self.staff_user = User.objects.create_user(
            email="role-staff@example.com",
            password="test-password",
        )
        self.staff_user.is_staff = True
        self.staff_user.save(
            update_fields=["is_staff"]
        )

        self.normal_user = User.objects.create_user(
            email="role-normal@example.com",
            password="test-password",
        )

        self.target_user = User.objects.create_user(
            email="role-target@example.com",
            password="test-password",
        )

        self.transport_driver_role = Role.objects.create(
            name="driver",
            app_name="transport",
            description="Transport driver",
            requires_verification=False,
            is_default=False,
            auto_assign=False,
        )

        self.transport_verified_role = Role.objects.create(
            name="verified_driver",
            app_name="transport",
            description="Verification-required driver",
            requires_verification=True,
            is_default=False,
            auto_assign=False,
        )

        self.realestate_agent_role = Role.objects.create(
            name="agent",
            app_name="realestate",
            description="Real estate agent",
            requires_verification=True,
            is_default=False,
            auto_assign=False,
        )

    # -------------------------------------------------------------------------
    # GRAPHQL CONTEXT
    # -------------------------------------------------------------------------

    @staticmethod
    def info_for(user):
        """
        Build the minimal request-like GraphQL context expected by the
        mutation authorization helpers and login_required decorator.
        """
        return SimpleNamespace(
            context=SimpleNamespace(
                user=user,
            )
        )

    # -------------------------------------------------------------------------
    # RELAY IDS
    # -------------------------------------------------------------------------

    @staticmethod
    def role_id(role):
        return to_global_id(
            RoleNode._meta.name,
            role.pk,
        )

    @staticmethod
    def user_id(user):
        return to_global_id(
            UserNode._meta.name,
            user.pk,
        )

    @staticmethod
    def user_role_id(user_role):
        return to_global_id(
            UserRoleNode._meta.name,
            user_role.pk,
        )

    # -------------------------------------------------------------------------
    # ROLE INPUT
    # -------------------------------------------------------------------------

    @staticmethod
    def role_input(
        *,
        app_name,
        role_name,
        is_active=False,
        expires_at=None,
        notes="",
    ):
        return SimpleNamespace(
            app_name=app_name,
            role_name=role_name,
            is_active=is_active,
            expires_at=expires_at,
            notes=notes,
        )


# =============================================================================
# ROLE MUTATION MIXIN
# =============================================================================


class RoleMutationMixinTests(RoleMutationTestCase):
    """
    Test the security-sensitive helper layer independently.
    """

    def test_authenticated_user_is_returned(self):
        info = self.info_for(self.normal_user)

        result = RoleMutationMixin.require_authenticated_user(
            info
        )

        self.assertEqual(
            result,
            self.normal_user,
        )

    def test_anonymous_user_is_rejected(self):
        anonymous_user = User.objects.create_user(
            email="anonymous-test@example.com",
            password="test-password",
        )

        anonymous_user.is_active = False
        anonymous_user.save(
            update_fields=["is_active"]
        )

        info = self.info_for(anonymous_user)

        with self.assertRaises(GraphQLError):
            RoleMutationMixin.require_authenticated_user(
                info
            )

    def test_normal_user_cannot_pass_admin_boundary(self):
        info = self.info_for(self.normal_user)

        with self.assertRaises(GraphQLError) as exc:
            RoleMutationMixin.require_admin(
                info
            )

        self.assertIn(
            "Admin access required",
            str(exc.exception),
        )

    def test_staff_user_passes_admin_boundary(self):
        info = self.info_for(self.staff_user)

        result = RoleMutationMixin.require_admin(
            info
        )

        self.assertEqual(
            result,
            self.staff_user,
        )

    def test_staff_user_cannot_pass_superuser_boundary(self):
        info = self.info_for(self.staff_user)

        with self.assertRaises(GraphQLError) as exc:
            RoleMutationMixin.require_superuser(
                info
            )

        self.assertIn(
            "Superuser access required",
            str(exc.exception),
        )

    def test_superuser_passes_superuser_boundary(self):
        info = self.info_for(self.superuser)

        result = RoleMutationMixin.require_superuser(
            info
        )

        self.assertEqual(
            result,
            self.superuser,
        )


# =============================================================================
# RELAY ID VALIDATION
# =============================================================================


class RoleRelayIDTests(RoleMutationTestCase):
    """
    Relay global IDs are part of the mutation security boundary.
    """

    def test_role_global_id_resolves_role(self):
        global_id = self.role_id(
            self.transport_driver_role
        )

        role = RoleMutationMixin.get_role_from_global_id(
            global_id
        )

        self.assertEqual(
            role,
            self.transport_driver_role,
        )

    def test_user_global_id_resolves_user(self):
        global_id = self.user_id(
            self.target_user
        )

        user = RoleMutationMixin.get_user_from_global_id(
            global_id
        )

        self.assertEqual(
            user,
            self.target_user,
        )

    def test_user_role_global_id_resolves_assignment(self):
        assignment = UserRole.objects.create(
            user=self.target_user,
            role=self.transport_driver_role,
            created_by=self.superuser,
            is_active=True,
        )

        global_id = self.user_role_id(
            assignment
        )

        result = (
            RoleMutationMixin
            .get_user_role_from_global_id(
                global_id
            )
        )

        self.assertEqual(
            result.pk,
            assignment.pk,
        )

    def test_invalid_global_id_is_rejected(self):
        with self.assertRaises(GraphQLError):
            RoleMutationMixin.decode_global_id(
                "not-a-relay-id"
            )

    def test_wrong_role_global_id_type_is_rejected(self):
        user_global_id = self.user_id(
            self.target_user
        )

        with self.assertRaises(GraphQLError):
            RoleMutationMixin.decode_global_id(
                user_global_id,
                expected_type=RoleNode._meta.name,
            )

    def test_missing_global_id_is_rejected(self):
        with self.assertRaises(GraphQLError):
            RoleMutationMixin.decode_global_id(
                None
            )


# =============================================================================
# ROLE VALIDATION
# =============================================================================


class RoleValidationTests(RoleMutationTestCase):
    """
    Validate application and role resolution.
    """

    def test_valid_app_name_is_accepted(self):
        result = RoleMutationMixin.validate_app_name(
            "transport"
        )

        self.assertEqual(
            result,
            "transport",
        )

    def test_app_name_is_trimmed(self):
        result = RoleMutationMixin.validate_app_name(
            "  transport  "
        )

        self.assertEqual(
            result,
            "transport",
        )

    def test_invalid_app_name_is_rejected(self):
        with self.assertRaises(GraphQLError):
            RoleMutationMixin.validate_app_name(
                "not-a-real-app"
            )

    def test_missing_app_name_is_rejected(self):
        with self.assertRaises(GraphQLError):
            RoleMutationMixin.validate_app_name(
                ""
            )

    def test_role_name_is_trimmed(self):
        role = RoleMutationMixin.get_role(
            app_name="transport",
            role_name="  driver  ",
        )

        self.assertEqual(
            role,
            self.transport_driver_role,
        )

    def test_missing_role_name_is_rejected(self):
        with self.assertRaises(GraphQLError):
            RoleMutationMixin.get_role(
                app_name="transport",
                role_name="",
            )

    def test_unknown_role_is_rejected(self):
        with self.assertRaises(GraphQLError):
            RoleMutationMixin.get_role(
                app_name="transport",
                role_name="does-not-exist",
            )


# =============================================================================
# CREATE ROLE
# =============================================================================


class CreateRoleMutationTests(RoleMutationTestCase):
    """
    Role creation is a superuser-only operation.
    """

    def test_normal_user_cannot_create_role(self):
        info = self.info_for(
            self.normal_user
        )

        with self.assertRaises(GraphQLError):
            CreateRoleMutation.mutate_and_get_payload(
                None,
                info,
                name="dispatcher",
                app_name="transport",
            )

        self.assertFalse(
            Role.objects.filter(
                name="dispatcher",
                app_name="transport",
            ).exists()
        )

    def test_staff_user_cannot_create_role(self):
        info = self.info_for(
            self.staff_user
        )

        with self.assertRaises(GraphQLError):
            CreateRoleMutation.mutate_and_get_payload(
                None,
                info,
                name="dispatcher",
                app_name="transport",
            )

    def test_superuser_can_create_role(self):
        info = self.info_for(
            self.superuser
        )

        result = (
            CreateRoleMutation
            .mutate_and_get_payload(
                None,
                info,
                name="dispatcher",
                app_name="transport",
                description="Dispatch operator",
                is_default=False,
                requires_verification=False,
                auto_assign=False,
            )
        )

        self.assertTrue(
            result.success
        )

        role = Role.objects.get(
            name="dispatcher",
            app_name="transport",
        )

        self.assertEqual(
            role.description,
            "Dispatch operator",
        )

    def test_duplicate_role_is_rejected_without_creating_second_role(self):
        info = self.info_for(
            self.superuser
        )

        before = Role.objects.filter(
            name="driver",
            app_name="transport",
        ).count()

        result = (
            CreateRoleMutation
            .mutate_and_get_payload(
                None,
                info,
                name="driver",
                app_name="transport",
            )
        )

        after = Role.objects.filter(
            name="driver",
            app_name="transport",
        ).count()

        self.assertFalse(
            result.success
        )
        self.assertEqual(
            before,
            after,
        )

    def test_invalid_application_is_rejected(self):
        info = self.info_for(
            self.superuser
        )

        with self.assertRaises(GraphQLError):
            CreateRoleMutation.mutate_and_get_payload(
                None,
                info,
                name="dispatcher",
                app_name="invalid",
            )


# =============================================================================
# UPDATE ROLE
# =============================================================================


class UpdateRoleMutationTests(RoleMutationTestCase):
    """
    Updating a role remains superuser-only.
    """

    def test_normal_user_cannot_update_role(self):
        info = self.info_for(
            self.normal_user
        )

        with self.assertRaises(GraphQLError):
            UpdateRoleMutation.mutate_and_get_payload(
                None,
                info,
                role_id=self.role_id(
                    self.transport_driver_role
                ),
                name="changed",
            )

    def test_staff_user_cannot_update_role(self):
        info = self.info_for(
            self.staff_user
        )

        with self.assertRaises(GraphQLError):
            UpdateRoleMutation.mutate_and_get_payload(
                None,
                info,
                role_id=self.role_id(
                    self.transport_driver_role
                ),
                name="changed",
            )

    def test_superuser_can_update_role(self):
        info = self.info_for(
            self.superuser
        )

        result = (
            UpdateRoleMutation
            .mutate_and_get_payload(
                None,
                info,
                role_id=self.role_id(
                    self.transport_driver_role
                ),
                name="senior_driver",
                description="Senior transport driver",
                is_default=True,
                requires_verification=False,
                auto_assign=True,
            )
        )

        self.assertTrue(
            result.success
        )

        self.transport_driver_role.refresh_from_db()

        self.assertEqual(
            self.transport_driver_role.name,
            "senior_driver",
        )
        self.assertEqual(
            self.transport_driver_role.description,
            "Senior transport driver",
        )
        self.assertTrue(
            self.transport_driver_role.is_default
        )
        self.assertTrue(
            self.transport_driver_role.auto_assign
        )

    def test_role_name_cannot_be_changed_to_duplicate_name(self):
        duplicate_role = Role.objects.create(
            name="other",
            app_name="transport",
        )

        info = self.info_for(
            self.superuser
        )

        with self.assertRaises(GraphQLError):
            UpdateRoleMutation.mutate_and_get_payload(
                None,
                info,
                role_id=self.role_id(
                    self.transport_driver_role
                ),
                name=duplicate_role.name,
            )

        self.transport_driver_role.refresh_from_db()

        self.assertEqual(
            self.transport_driver_role.name,
            "driver",
        )


# =============================================================================
# DELETE ROLE
# =============================================================================


class DeleteRoleMutationTests(RoleMutationTestCase):
    """
    Role deletion must protect existing assignments unless force=True.
    """

    def test_role_with_assignments_cannot_be_deleted_without_force(self):
        UserRole.objects.create(
            user=self.target_user,
            role=self.transport_driver_role,
            created_by=self.superuser,
            is_active=True,
        )

        info = self.info_for(
            self.superuser
        )

        with self.assertRaises(GraphQLError):
            DeleteRoleMutation.mutate_and_get_payload(
                None,
                info,
                role_id=self.role_id(
                    self.transport_driver_role
                ),
                force=False,
            )

        self.assertTrue(
            Role.objects.filter(
                pk=self.transport_driver_role.pk
            ).exists()
        )

        self.assertEqual(
            UserRole.objects.filter(
                role=self.transport_driver_role
            ).count(),
            1,
        )

    def test_force_delete_removes_role_and_assignments(self):
        UserRole.objects.create(
            user=self.target_user,
            role=self.transport_driver_role,
            created_by=self.superuser,
            is_active=True,
        )

        role_pk = self.transport_driver_role.pk

        info = self.info_for(
            self.superuser
        )

        result = (
            DeleteRoleMutation
            .mutate_and_get_payload(
                None,
                info,
                role_id=self.role_id(
                    self.transport_driver_role
                ),
                force=True,
            )
        )

        self.assertTrue(
            result.success
        )

        self.assertFalse(
            Role.objects.filter(
                pk=role_pk
            ).exists()
        )

        self.assertEqual(
            UserRole.objects.filter(
                role_id=role_pk
            ).count(),
            0,
        )

    def test_normal_user_cannot_delete_role(self):
        info = self.info_for(
            self.normal_user
        )

        with self.assertRaises(GraphQLError):
            DeleteRoleMutation.mutate_and_get_payload(
                None,
                info,
                role_id=self.role_id(
                    self.transport_driver_role
                ),
                force=True,
            )


# =============================================================================
# ASSIGN USER ROLE
# =============================================================================


class AssignUserRoleMutationTests(RoleMutationTestCase):
    """
    Assignment lifecycle and verification policy.
    """

    def test_normal_user_cannot_assign_role(self):
        info = self.info_for(
            self.normal_user
        )

        with self.assertRaises(GraphQLError):
            AssignUserRoleMutation.mutate_and_get_payload(
                None,
                info,
                user_id=self.user_id(
                    self.target_user
                ),
                app_name="transport",
                role_name="driver",
            )

        self.assertFalse(
            UserRole.objects.filter(
                user=self.target_user,
                role=self.transport_driver_role,
            ).exists()
        )

    def test_staff_user_can_assign_non_verification_role(self):
        info = self.info_for(
            self.staff_user
        )

        result = (
            AssignUserRoleMutation
            .mutate_and_get_payload(
                None,
                info,
                user_id=self.user_id(
                    self.target_user
                ),
                app_name="transport",
                role_name="driver",
                is_active=True,
            )
        )

        self.assertTrue(
            result.success
        )

        assignment = UserRole.objects.get(
            user=self.target_user,
            role=self.transport_driver_role,
        )

        self.assertTrue(
            assignment.is_active
        )
        self.assertEqual(
            assignment.created_by,
            self.staff_user,
        )

    def test_staff_user_cannot_activate_verification_role(self):
        info = self.info_for(
            self.staff_user
        )

        with self.assertRaises(GraphQLError) as exc:
            AssignUserRoleMutation.mutate_and_get_payload(
                None,
                info,
                user_id=self.user_id(
                    self.target_user
                ),
                app_name="transport",
                role_name="verified_driver",
                is_active=True,
            )

        self.assertIn(
            "superuser approval",
            str(exc.exception),
        )

        assignment = UserRole.objects.get(
            user=self.target_user,
            role=self.transport_verified_role,
        ) if UserRole.objects.filter(
            user=self.target_user,
            role=self.transport_verified_role,
        ).exists() else None

        self.assertIsNone(
            assignment
        )

    def test_staff_user_can_assign_verification_role_inactive(self):
        info = self.info_for(
            self.staff_user
        )

        result = (
            AssignUserRoleMutation
            .mutate_and_get_payload(
                None,
                info,
                user_id=self.user_id(
                    self.target_user
                ),
                app_name="transport",
                role_name="verified_driver",
                is_active=False,
            )
        )

        self.assertTrue(
            result.success
        )

        assignment = UserRole.objects.get(
            user=self.target_user,
            role=self.transport_verified_role,
        )

        self.assertFalse(
            assignment.is_active
        )
        self.assertIsNone(
            assignment.verified_at
        )
        self.assertIsNone(
            assignment.verified_by
        )

    def test_superuser_can_assign_and_activate_verification_role(self):
        info = self.info_for(
            self.superuser
        )

        result = (
            AssignUserRoleMutation
            .mutate_and_get_payload(
                None,
                info,
                user_id=self.user_id(
                    self.target_user
                ),
                app_name="transport",
                role_name="verified_driver",
                is_active=True,
                notes="Approved by administrator",
            )
        )

        self.assertTrue(
            result.success
        )

        assignment = UserRole.objects.get(
            user=self.target_user,
            role=self.transport_verified_role,
        )

        self.assertTrue(
            assignment.is_active
        )
        self.assertEqual(
            assignment.verified_by,
            self.superuser,
        )
        self.assertIsNotNone(
            assignment.verified_at
        )
        self.assertEqual(
            assignment.notes,
            "Approved by administrator",
        )

    def test_assignment_is_idempotently_updated(self):
        info = self.info_for(
            self.staff_user
        )

        first = (
            AssignUserRoleMutation
            .mutate_and_get_payload(
                None,
                info,
                user_id=self.user_id(
                    self.target_user
                ),
                app_name="transport",
                role_name="driver",
                is_active=True,
                notes="First assignment",
            )
        )

        assignment_id = first.user_role.pk

        second = (
            AssignUserRoleMutation
            .mutate_and_get_payload(
                None,
                info,
                user_id=self.user_id(
                    self.target_user
                ),
                app_name="transport",
                role_name="driver",
                is_active=False,
                notes="Updated assignment",
            )
        )

        self.assertTrue(
            second.success
        )

        self.assertEqual(
            second.user_role.pk,
            assignment_id,
        )

        self.assertEqual(
            UserRole.objects.filter(
                user=self.target_user,
                role=self.transport_driver_role,
            ).count(),
            1,
        )

        assignment = UserRole.objects.get(
            pk=assignment_id
        )

        self.assertFalse(
            assignment.is_active
        )
        self.assertEqual(
            assignment.notes,
            "Updated assignment",
        )


# =============================================================================
# BULK ASSIGN
# =============================================================================


class BulkAssignUserRolesMutationTests(RoleMutationTestCase):
    """
    Bulk assignment must validate everything before applying changes.
    """

    def test_bulk_assign_requires_superuser(self):
        info = self.info_for(
            self.staff_user
        )

        roles = [
            self.role_input(
                app_name="transport",
                role_name="driver",
                is_active=True,
            )
        ]

        with self.assertRaises(GraphQLError):
            BulkAssignUserRolesMutation.mutate_and_get_payload(
                None,
                info,
                user_ids=[
                    self.user_id(
                        self.target_user
                    )
                ],
                roles=roles,
            )

    def test_bulk_assign_creates_cartesian_assignments(self):
        second_user = User.objects.create_user(
            email="role-bulk-target@example.com",
            password="test-password",
        )

        info = self.info_for(
            self.superuser
        )

        roles = [
            self.role_input(
                app_name="transport",
                role_name="driver",
                is_active=True,
            ),
            self.role_input(
                app_name="realestate",
                role_name="agent",
                is_active=False,
            ),
        ]

        result = (
            BulkAssignUserRolesMutation
            .mutate_and_get_payload(
                None,
                info,
                user_ids=[
                    self.user_id(self.target_user),
                    self.user_id(second_user),
                ],
                roles=roles,
            )
        )

        self.assertTrue(
            result.success
        )

        self.assertEqual(
            result.assigned_count,
            4,
        )

        self.assertEqual(
            UserRole.objects.filter(
                user=self.target_user
            ).count(),
            2,
        )

        self.assertEqual(
            UserRole.objects.filter(
                user=second_user
            ).count(),
            2,
        )

    def test_bulk_assign_invalid_role_causes_no_partial_changes(self):
        info = self.info_for(
            self.superuser
        )

        valid_role = self.role_input(
            app_name="transport",
            role_name="driver",
            is_active=True,
        )

        invalid_role = self.role_input(
            app_name="transport",
            role_name="does_not_exist",
            is_active=True,
        )

        with self.assertRaises(GraphQLError):
            BulkAssignUserRolesMutation.mutate_and_get_payload(
                None,
                info,
                user_ids=[
                    self.user_id(
                        self.target_user
                    )
                ],
                roles=[
                    valid_role,
                    invalid_role,
                ],
            )

        self.assertEqual(
            UserRole.objects.filter(
                user=self.target_user
            ).count(),
            0,
        )


# =============================================================================
# UNASSIGN
# =============================================================================


class UnassignUserRoleMutationTests(RoleMutationTestCase):
    """
    Unassignment is a destructive delete operation.
    """

    def test_staff_can_unassign_role(self):
        UserRole.objects.create(
            user=self.target_user,
            role=self.transport_driver_role,
            created_by=self.superuser,
            is_active=True,
        )

        info = self.info_for(
            self.staff_user
        )

        result = (
            UnassignUserRoleMutation
            .mutate_and_get_payload(
                None,
                info,
                user_id=self.user_id(
                    self.target_user
                ),
                app_name="transport",
                role_name="driver",
            )
        )

        self.assertTrue(
            result.success
        )

        self.assertFalse(
            UserRole.objects.filter(
                user=self.target_user,
                role=self.transport_driver_role,
            ).exists()
        )

    def test_unassign_missing_role_returns_failure(self):
        info = self.info_for(
            self.staff_user
        )

        result = (
            UnassignUserRoleMutation
            .mutate_and_get_payload(
                None,
                info,
                user_id=self.user_id(
                    self.target_user
                ),
                app_name="transport",
                role_name="driver",
            )
        )

        self.assertFalse(
            result.success
        )

        self.assertIn(
            "not found",
            result.message.lower(),
        )


# =============================================================================
# REPLACE ALL USER ROLES
# =============================================================================


class UpdateUserRolesMutationTests(RoleMutationTestCase):
    """
    Replacement must be atomic.

    An invalid role must not leave the user with a partially replaced
    role set.
    """

    def test_replace_all_roles(self):
        old_role = Role.objects.create(
            name="old_role",
            app_name="transport",
        )

        UserRole.objects.create(
            user=self.target_user,
            role=old_role,
            created_by=self.superuser,
            is_active=True,
        )

        info = self.info_for(
            self.superuser
        )

        result = (
            UpdateUserRolesMutation
            .mutate_and_get_payload(
                None,
                info,
                user_id=self.user_id(
                    self.target_user
                ),
                roles=[
                    self.role_input(
                        app_name="transport",
                        role_name="driver",
                        is_active=True,
                    ),
                ],
            )
        )

        self.assertTrue(
            result.success
        )

        self.assertFalse(
            UserRole.objects.filter(
                user=self.target_user,
                role=old_role,
            ).exists()
        )

        self.assertTrue(
            UserRole.objects.filter(
                user=self.target_user,
                role=self.transport_driver_role,
            ).exists()
        )

    def test_invalid_role_does_not_destroy_existing_assignments(self):
        UserRole.objects.create(
            user=self.target_user,
            role=self.transport_driver_role,
            created_by=self.superuser,
            is_active=True,
        )

        info = self.info_for(
            self.superuser
        )

        invalid_role = self.role_input(
            app_name="transport",
            role_name="does_not_exist",
            is_active=True,
        )

        with self.assertRaises(GraphQLError):
            UpdateUserRolesMutation.mutate_and_get_payload(
                None,
                info,
                user_id=self.user_id(
                    self.target_user
                ),
                roles=[invalid_role],
            )

        self.assertTrue(
            UserRole.objects.filter(
                user=self.target_user,
                role=self.transport_driver_role,
            ).exists()
        )

    def test_replace_all_roles_requires_superuser(self):
        info = self.info_for(
            self.staff_user
        )

        with self.assertRaises(GraphQLError):
            UpdateUserRolesMutation.mutate_and_get_payload(
                None,
                info,
                user_id=self.user_id(
                    self.target_user
                ),
                roles=[],
            )


# =============================================================================
# UPDATE SPECIFIC USER ROLE
# =============================================================================


class UpdateUserRoleMutationTests(RoleMutationTestCase):
    """
    Test activation, deactivation, expiration, and notes.
    """

    def create_assignment(
        self,
        *,
        role=None,
        is_active=False,
        expires_at=None,
    ):
        return UserRole.objects.create(
            user=self.target_user,
            role=role or self.transport_driver_role,
            created_by=self.superuser,
            is_active=is_active,
            expires_at=expires_at,
        )

    def test_staff_can_activate_normal_role(self):
        assignment = self.create_assignment(
            is_active=False
        )

        info = self.info_for(
            self.staff_user
        )

        result = (
            UpdateUserRoleMutation
            .mutate_and_get_payload(
                None,
                info,
                user_role_id=self.user_role_id(
                    assignment
                ),
                is_active=True,
            )
        )

        self.assertTrue(
            result.success
        )

        assignment.refresh_from_db()

        self.assertTrue(
            assignment.is_active
        )

    def test_staff_cannot_activate_verification_role(self):
        assignment = self.create_assignment(
            role=self.transport_verified_role,
            is_active=False,
        )

        info = self.info_for(
            self.staff_user
        )

        with self.assertRaises(GraphQLError) as exc:
            UpdateUserRoleMutation.mutate_and_get_payload(
                None,
                info,
                user_role_id=self.user_role_id(
                    assignment
                ),
                is_active=True,
            )

        self.assertIn(
            "superuser approval",
            str(exc.exception),
        )

        assignment.refresh_from_db()

        self.assertFalse(
            assignment.is_active
        )

    def test_superuser_can_activate_verification_role(self):
        assignment = self.create_assignment(
            role=self.transport_verified_role,
            is_active=False,
        )

        info = self.info_for(
            self.superuser
        )

        result = (
            UpdateUserRoleMutation
            .mutate_and_get_payload(
                None,
                info,
                user_role_id=self.user_role_id(
                    assignment
                ),
                is_active=True,
            )
        )

        self.assertTrue(
            result.success
        )

        assignment.refresh_from_db()

        self.assertTrue(
            assignment.is_active
        )
        self.assertEqual(
            assignment.verified_by,
            self.superuser,
        )
        self.assertIsNotNone(
            assignment.verified_at
        )

    def test_staff_can_deactivate_role(self):
        assignment = self.create_assignment(
            is_active=True
        )

        info = self.info_for(
            self.staff_user
        )

        result = (
            UpdateUserRoleMutation
            .mutate_and_get_payload(
                None,
                info,
                user_role_id=self.user_role_id(
                    assignment
                ),
                is_active=False,
            )
        )

        self.assertTrue(
            result.success
        )

        assignment.refresh_from_db()

        self.assertFalse(
            assignment.is_active
        )

    def test_expiration_must_be_after_creation(self):
        assignment = self.create_assignment(
            is_active=False
        )

        info = self.info_for(
            self.staff_user
        )

        invalid_expiration = (
            assignment.created_at
            - timedelta(seconds=1)
        )

        with self.assertRaises(GraphQLError):
            UpdateUserRoleMutation.mutate_and_get_payload(
                None,
                info,
                user_role_id=self.user_role_id(
                    assignment
                ),
                expires_at=invalid_expiration,
            )

    def test_notes_can_be_updated(self):
        assignment = self.create_assignment(
            is_active=False
        )

        info = self.info_for(
            self.staff_user
        )

        result = (
            UpdateUserRoleMutation
            .mutate_and_get_payload(
                None,
                info,
                user_role_id=self.user_role_id(
                    assignment
                ),
                notes="Administrative note",
            )
        )

        self.assertTrue(
            result.success
        )

        assignment.refresh_from_db()

        self.assertEqual(
            assignment.notes,
            "Administrative note",
        )


# =============================================================================
# VERIFY USER ROLE
# =============================================================================


class VerifyUserRoleMutationTests(RoleMutationTestCase):
    """
    Verification is a superuser-only lifecycle transition.

    These tests intentionally test revoked and expired state before
    activation.
    """

    def create_pending_verification_role(self):
        return UserRole.objects.create(
            user=self.target_user,
            role=self.transport_verified_role,
            created_by=self.staff_user,
            is_active=False,
        )

    def test_normal_user_cannot_verify_role(self):
        self.create_pending_verification_role()

        info = self.info_for(
            self.normal_user
        )

        with self.assertRaises(GraphQLError):
            VerifyUserRoleMutation.mutate_and_get_payload(
                None,
                info,
                user_id=self.user_id(
                    self.target_user
                ),
                app_name="transport",
                role_name="verified_driver",
            )

    def test_staff_user_cannot_verify_role(self):
        self.create_pending_verification_role()

        info = self.info_for(
            self.staff_user
        )

        with self.assertRaises(GraphQLError):
            VerifyUserRoleMutation.mutate_and_get_payload(
                None,
                info,
                user_id=self.user_id(
                    self.target_user
                ),
                app_name="transport",
                role_name="verified_driver",
            )

    def test_missing_assignment_cannot_be_verified(self):
        info = self.info_for(
            self.superuser
        )

        with self.assertRaises(GraphQLError) as exc:
            VerifyUserRoleMutation.mutate_and_get_payload(
                None,
                info,
                user_id=self.user_id(
                    self.target_user
                ),
                app_name="transport",
                role_name="verified_driver",
            )

        self.assertIn(
            "does not have this role assigned",
            str(exc.exception),
        )

    def test_pending_role_can_be_verified_and_activated(self):
        assignment = (
            self.create_pending_verification_role()
        )

        info = self.info_for(
            self.superuser
        )

        result = (
            VerifyUserRoleMutation
            .mutate_and_get_payload(
                None,
                info,
                user_id=self.user_id(
                    self.target_user
                ),
                app_name="transport",
                role_name="verified_driver",
            )
        )

        self.assertTrue(
            result.success
        )

        assignment.refresh_from_db()

        self.assertTrue(
            assignment.is_active
        )
        self.assertEqual(
            assignment.verified_by,
            self.superuser,
        )
        self.assertIsNotNone(
            assignment.verified_at
        )

    def test_revoked_role_cannot_be_verified(self):
        assignment = (
            self.create_pending_verification_role()
        )

        assignment.revoked_at = timezone.now()
        assignment.revoked_by = self.staff_user
        assignment.is_active = False
        assignment.save(
            update_fields=[
                "revoked_at",
                "revoked_by",
                "is_active",
            ]
        )

        info = self.info_for(
            self.superuser
        )

        with self.assertRaises(GraphQLError):
            VerifyUserRoleMutation.mutate_and_get_payload(
                None,
                info,
                user_id=self.user_id(
                    self.target_user
                ),
                app_name="transport",
                role_name="verified_driver",
            )

        assignment.refresh_from_db()

        self.assertFalse(
            assignment.is_active
        )

    def test_expired_role_cannot_be_verified(self):
        assignment = (
            self.create_pending_verification_role()
        )

        assignment.expires_at = (
            timezone.now()
            - timedelta(minutes=1)
        )
        assignment.save(
            update_fields=[
                "expires_at",
            ]
        )

        info = self.info_for(
            self.superuser
        )

        with self.assertRaises(GraphQLError):
            VerifyUserRoleMutation.mutate_and_get_payload(
                None,
                info,
                user_id=self.user_id(
                    self.target_user
                ),
                app_name="transport",
                role_name="verified_driver",
            )

        assignment.refresh_from_db()

        self.assertFalse(
            assignment.is_active
        )


# =============================================================================
# REVOKE
# =============================================================================


class RevokeUserRoleMutationTests(RoleMutationTestCase):
    """
    Revocation must preserve the historical UserRole record.
    """

    def create_assignment(self):
        return UserRole.objects.create(
            user=self.target_user,
            role=self.transport_driver_role,
            created_by=self.superuser,
            is_active=True,
        )

    def test_normal_user_cannot_revoke_role(self):
        assignment = self.create_assignment()

        info = self.info_for(
            self.normal_user
        )

        with self.assertRaises(GraphQLError):
            RevokeUserRoleMutation.mutate_and_get_payload(
                None,
                info,
                user_id=self.user_id(
                    self.target_user
                ),
                app_name="transport",
                role_name="driver",
            )

        assignment.refresh_from_db()

        self.assertTrue(
            assignment.is_active
        )
        self.assertIsNone(
            assignment.revoked_at
        )

    def test_staff_can_revoke_role(self):
        assignment = self.create_assignment()

        info = self.info_for(
            self.staff_user
        )

        result = (
            RevokeUserRoleMutation
            .mutate_and_get_payload(
                None,
                info,
                user_id=self.user_id(
                    self.target_user
                ),
                app_name="transport",
                role_name="driver",
                reason="Policy violation",
            )
        )

        self.assertTrue(
            result.success
        )

        assignment.refresh_from_db()

        self.assertFalse(
            assignment.is_active
        )
        self.assertEqual(
            assignment.revoked_by,
            self.staff_user,
        )
        self.assertIsNotNone(
            assignment.revoked_at
        )
        self.assertIn(
            "Policy violation",
            assignment.notes,
        )

    def test_revocation_preserves_assignment(self):
        assignment = self.create_assignment()

        assignment_pk = assignment.pk

        info = self.info_for(
            self.staff_user
        )

        RevokeUserRoleMutation.mutate_and_get_payload(
            None,
            info,
            user_id=self.user_id(
                self.target_user
            ),
            app_name="transport",
            role_name="driver",
            reason="Administrative action",
        )

        self.assertTrue(
            UserRole.objects.filter(
                pk=assignment_pk
            ).exists()
        )


# =============================================================================
# BULK DELETE
# =============================================================================


class BulkDeleteUserRolesMutationTests(RoleMutationTestCase):
    """
    Bulk deletion is destructive and therefore admin-only.
    """

    def create_assignment(
        self,
        user,
        role,
    ):
        return UserRole.objects.create(
            user=user,
            role=role,
            created_by=self.superuser,
            is_active=True,
        )

    def test_normal_user_cannot_bulk_delete(self):
        assignment = self.create_assignment(
            self.target_user,
            self.transport_driver_role,
        )

        info = self.info_for(
            self.normal_user
        )

        with self.assertRaises(GraphQLError):
            BulkDeleteUserRolesMutation.mutate_and_get_payload(
                None,
                info,
                user_role_ids=[
                    self.user_role_id(
                        assignment
                    )
                ],
            )

        self.assertTrue(
            UserRole.objects.filter(
                pk=assignment.pk
            ).exists()
        )

    def test_staff_can_bulk_delete(self):
        assignment_one = self.create_assignment(
            self.target_user,
            self.transport_driver_role,
        )

        assignment_two = self.create_assignment(
            self.target_user,
            self.realestate_agent_role,
        )

        info = self.info_for(
            self.staff_user
        )

        result = (
            BulkDeleteUserRolesMutation
            .mutate_and_get_payload(
                None,
                info,
                user_role_ids=[
                    self.user_role_id(
                        assignment_one
                    ),
                    self.user_role_id(
                        assignment_two
                    ),
                ],
            )
        )

        self.assertTrue(
            result.success
        )

        self.assertEqual(
            result.deleted_count,
            2,
        )

        self.assertFalse(
            UserRole.objects.filter(
                pk__in=[
                    assignment_one.pk,
                    assignment_two.pk,
                ]
            ).exists()
        )

    def test_invalid_id_aborts_bulk_delete(self):
        assignment = self.create_assignment(
            self.target_user,
            self.transport_driver_role,
        )

        info = self.info_for(
            self.staff_user
        )

        with self.assertRaises(GraphQLError):
            BulkDeleteUserRolesMutation.mutate_and_get_payload(
                None,
                info,
                user_role_ids=[
                    self.user_role_id(
                        assignment
                    ),
                    "invalid-relay-id",
                ],
            )

        self.assertTrue(
            UserRole.objects.filter(
                pk=assignment.pk
            ).exists()
        )


# =============================================================================
# APPLICATION ROLE SELECTION
# =============================================================================


class ApplicationRoleSelectionMutationTests(RoleMutationTestCase):
    """
    Switching roles must only expose active roles belonging to the
    authenticated user.
    """

    def test_switch_selects_active_role(self):
        UserRole.objects.create(
            user=self.target_user,
            role=self.transport_driver_role,
            created_by=self.superuser,
            is_active=True,
        )

        info = self.info_for(
            self.target_user
        )

        result = (
            SwitchAppRoleMutation
            .mutate_and_get_payload(
                None,
                info,
                app_name="transport",
            )
        )

        self.assertTrue(
            result.success
        )

        self.assertEqual(
            result.active_role.role,
            self.transport_driver_role,
        )

    def test_switch_ignores_inactive_roles(self):
        UserRole.objects.create(
            user=self.target_user,
            role=self.transport_driver_role,
            created_by=self.superuser,
            is_active=False,
        )

        info = self.info_for(
            self.target_user
        )

        with self.assertRaises(GraphQLError):
            SwitchAppRoleMutation.mutate_and_get_payload(
                None,
                info,
                app_name="transport",
            )

    def test_switch_does_not_select_another_users_role(self):
        UserRole.objects.create(
            user=self.target_user,
            role=self.transport_driver_role,
            created_by=self.superuser,
            is_active=True,
        )

        info = self.info_for(
            self.normal_user
        )

        with self.assertRaises(GraphQLError):
            SwitchAppRoleMutation.mutate_and_get_payload(
                None,
                info,
                app_name="transport",
            )

    def test_switch_can_select_specific_role(self):
        UserRole.objects.create(
            user=self.target_user,
            role=self.transport_driver_role,
            created_by=self.superuser,
            is_active=True,
        )

        second_role = Role.objects.create(
            name="dispatcher",
            app_name="transport",
        )

        UserRole.objects.create(
            user=self.target_user,
            role=second_role,
            created_by=self.superuser,
            is_active=True,
        )

        info = self.info_for(
            self.target_user
        )

        result = (
            SwitchAppRoleMutation
            .mutate_and_get_payload(
                None,
                info,
                app_name="transport",
                role_name="dispatcher",
            )
        )

        self.assertTrue(
            result.success
        )

        self.assertEqual(
            result.active_role.role,
            second_role,
        )


# =============================================================================
# ACTIVE ROLE RETRIEVAL
# =============================================================================


class GetActiveAppRoleMutationTests(RoleMutationTestCase):
    """
    Compatibility mutation for retrieving an active application role.
    """

    def test_returns_active_role(self):
        UserRole.objects.create(
            user=self.target_user,
            role=self.transport_driver_role,
            created_by=self.superuser,
            is_active=True,
        )

        info = self.info_for(
            self.target_user
        )

        result = (
            GetActiveAppRoleMutation
            .mutate_and_get_payload(
                None,
                info,
                app_name="transport",
            )
        )

        self.assertTrue(
            result.success
        )

        self.assertEqual(
            result.active_role.role,
            self.transport_driver_role,
        )

    def test_returns_failure_when_no_active_role_exists(self):
        info = self.info_for(
            self.target_user
        )

        result = (
            GetActiveAppRoleMutation
            .mutate_and_get_payload(
                None,
                info,
                app_name="transport",
            )
        )

        self.assertFalse(
            result.success
        )
        self.assertIsNone(
            result.active_role
        )


# =============================================================================
# ROLE QUERIES
# =============================================================================


class RoleQueryAuthorizationTests(RoleMutationTestCase):
    """
    Query authorization must prevent users from inspecting other
    users' role assignments.
    """

    def test_user_can_view_own_roles(self):
        UserRole.objects.create(
            user=self.target_user,
            role=self.transport_driver_role,
            created_by=self.superuser,
            is_active=True,
        )

        info = self.info_for(
            self.target_user
        )

        result = RoleQueries.resolve_user_roles(
            None,
            info,
            user_id=self.user_id(
                self.target_user
            ),
        )

        self.assertEqual(
            result.count(),
            1,
        )

    def test_normal_user_cannot_view_another_users_roles(self):
        UserRole.objects.create(
            user=self.target_user,
            role=self.transport_driver_role,
            created_by=self.superuser,
            is_active=True,
        )

        info = self.info_for(
            self.normal_user
        )

        with self.assertRaises(GraphQLError):
            RoleQueries.resolve_user_roles(
                None,
                info,
                user_id=self.user_id(
                    self.target_user
                ),
            )

    def test_staff_can_view_another_users_roles(self):
        UserRole.objects.create(
            user=self.target_user,
            role=self.transport_driver_role,
            created_by=self.superuser,
            is_active=True,
        )

        info = self.info_for(
            self.staff_user
        )

        result = RoleQueries.resolve_user_roles(
            None,
            info,
            user_id=self.user_id(
                self.target_user
            ),
        )

        self.assertEqual(
            result.count(),
            1,
        )

    def test_superuser_can_view_another_users_roles(self):
        UserRole.objects.create(
            user=self.target_user,
            role=self.transport_driver_role,
            created_by=self.superuser,
            is_active=True,
        )

        info = self.info_for(
            self.superuser
        )

        result = RoleQueries.resolve_user_roles(
            None,
            info,
            user_id=self.user_id(
                self.target_user
            ),
        )

        self.assertEqual(
            result.count(),
            1,
        )

    def test_active_role_query_only_returns_active_roles(self):
        active_role = UserRole.objects.create(
            user=self.target_user,
            role=self.transport_driver_role,
            created_by=self.superuser,
            is_active=True,
        )

        UserRole.objects.create(
            user=self.target_user,
            role=self.realestate_agent_role,
            created_by=self.superuser,
            is_active=False,
        )

        info = self.info_for(
            self.target_user
        )

        result = RoleQueries.resolve_user_active_roles(
            None,
            info,
            user_id=self.user_id(
                self.target_user
            ),
        )

        self.assertEqual(
            result.count(),
            1,
        )
        self.assertEqual(
            result.first().pk,
            active_role.pk,
        )

    def test_invalid_user_id_returns_empty_result(self):
        info = self.info_for(
            self.superuser
        )

        result = RoleQueries.resolve_user_roles(
            None,
            info,
            user_id="invalid-relay-id",
        )

        self.assertEqual(
            list(result),
            [],
        )


# =============================================================================
# TRANSACTIONAL INVARIANT TESTS
# =============================================================================


class RoleMutationAtomicityTests(RoleMutationTestCase):
    """
    Verify that multi-step operations do not leave partially-mutated
    role state.
    """

    def test_update_all_roles_validates_before_deleting_existing_roles(self):
        existing = UserRole.objects.create(
            user=self.target_user,
            role=self.transport_driver_role,
            created_by=self.superuser,
            is_active=True,
        )

        info = self.info_for(
            self.superuser
        )

        invalid_role = self.role_input(
            app_name="transport",
            role_name="missing-role",
            is_active=True,
        )

        with self.assertRaises(GraphQLError):
            UpdateUserRolesMutation.mutate_and_get_payload(
                None,
                info,
                user_id=self.user_id(
                    self.target_user
                ),
                roles=[invalid_role],
            )

        self.assertTrue(
            UserRole.objects.filter(
                pk=existing.pk
            ).exists()
        )

    def test_bulk_assign_invalid_user_causes_no_assignment(self):
        info = self.info_for(
            self.superuser
        )

        valid_role = self.role_input(
            app_name="transport",
            role_name="driver",
            is_active=True,
        )

        with self.assertRaises(GraphQLError):
            BulkAssignUserRolesMutation.mutate_and_get_payload(
                None,
                info,
                user_ids=[
                    self.user_id(
                        self.target_user
                    ),
                    "invalid-user-id",
                ],
                roles=[valid_role],
            )

        self.assertEqual(
            UserRole.objects.filter(
                user=self.target_user
            ).count(),
            0,
        )


# =============================================================================
# VERIFICATION POLICY HELPERS
# =============================================================================


class RoleActivationPolicyTests(RoleMutationTestCase):
    """
    Test the central activation policy independently from GraphQL.
    """

    def test_non_verification_role_can_be_activated_by_staff(self):
        RoleMutationMixin.ensure_role_can_be_activated(
            role=self.transport_driver_role,
            current_user=self.staff_user,
        )

    def test_verification_role_requires_superuser(self):
        with self.assertRaises(GraphQLError):
            RoleMutationMixin.ensure_role_can_be_activated(
                role=self.transport_verified_role,
                current_user=self.staff_user,
            )

    def test_superuser_can_activate_verification_role(self):
        RoleMutationMixin.ensure_role_can_be_activated(
            role=self.transport_verified_role,
            current_user=self.superuser,
        )

    def test_non_active_verification_assignment_has_no_verification_metadata(
        self,
    ):
        defaults = (
            RoleMutationMixin.build_user_role_defaults(
                role=self.transport_verified_role,
                current_user=self.staff_user,
                is_active=False,
            )
        )

        self.assertFalse(
            defaults["is_active"]
        )
        self.assertIsNone(
            defaults["verified_by"]
        )
        self.assertIsNone(
            defaults["verified_at"]
        )

    def test_superuser_activation_populates_verification_metadata(self):
        defaults = (
            RoleMutationMixin.build_user_role_defaults(
                role=self.transport_verified_role,
                current_user=self.superuser,
                is_active=True,
            )
        )

        self.assertTrue(
            defaults["is_active"]
        )
        self.assertEqual(
            defaults["verified_by"],
            self.superuser,
        )
        self.assertIsNotNone(
            defaults["verified_at"]
        )