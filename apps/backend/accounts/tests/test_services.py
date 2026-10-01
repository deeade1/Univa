"""
Tests for account role provisioning services.

These services own orchestration around Role and UserRole.

The tests intentionally verify the current contract:

    assign_default_roles()
        - assigns roles marked for automatic assignment
        - is idempotent
        - does not overwrite existing assignments

    assign_role()
        - creates an explicit role assignment
        - respects activation and verification policy
        - records assignment metadata
        - does not modify an existing assignment

    revoke_role()
        - delegates revocation to UserRole
        - records revocation metadata
        - requires an existing assignment
"""

from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from accounts.models import Role, UserRole
from accounts.services.roles import (
    assign_default_roles,
    assign_role,
    revoke_role,
)


User = get_user_model()


class RoleServiceTests(TestCase):
    """Tests for role provisioning and authorization services."""

    PASSWORD = "StrongTestPassword123!"

    def create_user(
        self,
        email,
    ):
        return User.objects.create_user(
            email=email,
            password=self.PASSWORD,
        )

    def create_role(
        self,
        *,
        name="customer",
        app_name="ecommerce",
        requires_verification=False,
        auto_assign=False,
    ):
        return Role.objects.create(
            name=name,
            app_name=app_name,
            requires_verification=requires_verification,
            auto_assign=auto_assign,
        )

    # =========================================================================
    # DEFAULT ROLE ASSIGNMENT
    # =========================================================================

    def test_assign_default_roles_assigns_auto_assign_roles(self):
        """All roles configured for automatic assignment are assigned."""

        user = self.create_user(
            "default@example.com",
        )

        customer_role = self.create_role(
            name="customer",
            app_name="ecommerce",
            auto_assign=True,
        )

        self.create_role(
            name="vendor",
            app_name="ecommerce",
            auto_assign=False,
        )

        assignments = assign_default_roles(
            user,
        )

        self.assertEqual(
            len(assignments),
            1,
        )

        assignment = assignments[0]

        self.assertEqual(
            assignment.user,
            user,
        )

        self.assertEqual(
            assignment.role,
            customer_role,
        )

        self.assertTrue(
            assignment.is_active,
        )

    def test_assign_default_roles_is_idempotent(self):
        """
        Calling assign_default_roles() repeatedly does not create
        duplicate UserRole records.
        """

        user = self.create_user(
            "idempotent@example.com",
        )

        role = self.create_role(
            name="customer",
            app_name="ecommerce",
            auto_assign=True,
        )

        first = assign_default_roles(
            user,
        )

        second = assign_default_roles(
            user,
        )

        self.assertEqual(
            len(first),
            1,
        )

        self.assertEqual(
            len(second),
            1,
        )

        self.assertEqual(
            first[0].pk,
            second[0].pk,
        )

        self.assertEqual(
            UserRole.objects.filter(
                user=user,
                role=role,
            ).count(),
            1,
        )

    def test_assign_default_roles_creates_verification_role_inactive(self):
        """
        An automatically assigned role requiring verification starts
        inactive.
        """

        user = self.create_user(
            "default-pending@example.com",
        )

        role = self.create_role(
            name="agent",
            app_name="realestate",
            requires_verification=True,
            auto_assign=True,
        )

        assignments = assign_default_roles(
            user,
        )

        self.assertEqual(
            len(assignments),
            1,
        )

        assignment = assignments[0]

        self.assertEqual(
            assignment.role,
            role,
        )

        self.assertFalse(
            assignment.is_active,
        )

    def test_assign_default_roles_does_not_overwrite_existing_assignment(self):
        """
        Existing assignments are returned unchanged.

        assign_default_roles() uses get_or_create(), so an existing
        UserRole is not rewritten by a subsequent provisioning call.
        """

        user = self.create_user(
            "default-existing@example.com",
        )

        role = self.create_role(
            name="customer",
            app_name="ecommerce",
            auto_assign=True,
        )

        assignment = UserRole.objects.create(
            user=user,
            role=role,
            is_active=False,
            notes="Existing assignment",
        )

        assignments = assign_default_roles(
            user,
        )

        assignment.refresh_from_db()

        self.assertEqual(
            assignments[0].pk,
            assignment.pk,
        )

        self.assertFalse(
            assignment.is_active,
        )

        self.assertEqual(
            assignment.notes,
            "Existing assignment",
        )

    # =========================================================================
    # EXPLICIT ROLE ASSIGNMENT
    # =========================================================================

    def test_assign_role_creates_active_ordinary_role(self):
        """An ordinary role is active when assigned with activate=True."""

        user = self.create_user(
            "assign@example.com",
        )

        role = self.create_role()

        assignment = assign_role(
            user,
            role,
        )

        self.assertIsNotNone(
            assignment.pk,
        )

        self.assertEqual(
            assignment.user,
            user,
        )

        self.assertEqual(
            assignment.role,
            role,
        )

        self.assertTrue(
            assignment.is_active,
        )

    def test_assign_role_can_create_inactive_role(self):
        """activate=False creates an inactive assignment."""

        user = self.create_user(
            "inactive@example.com",
        )

        role = self.create_role()

        assignment = assign_role(
            user,
            role,
            activate=False,
        )

        self.assertFalse(
            assignment.is_active,
        )

    def test_assign_role_records_assigned_by(self):
        """The assigning user is recorded on the UserRole."""

        user = self.create_user(
            "assigned-user@example.com",
        )

        admin = self.create_user(
            "assigner@example.com",
        )

        role = self.create_role()

        assignment = assign_role(
            user,
            role,
            assigned_by=admin,
        )

        self.assertEqual(
            assignment.created_by,
            admin,
        )

    def test_assign_role_records_notes(self):
        """Assignment notes are persisted."""

        user = self.create_user(
            "notes@example.com",
        )

        role = self.create_role()

        assignment = assign_role(
            user,
            role,
            notes="Provisioned for ecommerce operations.",
        )

        self.assertEqual(
            assignment.notes,
            "Provisioned for ecommerce operations.",
        )

    def test_assign_role_records_expiration(self):
        """Assignment expiration is persisted."""

        user = self.create_user(
            "expiration@example.com",
        )

        role = self.create_role()

        expires_at = timezone.now() + timedelta(
            days=30,
        )

        assignment = assign_role(
            user,
            role,
            expires_at=expires_at,
        )

        self.assertIsNotNone(
            assignment.expires_at,
        )

        self.assertAlmostEqual(
            assignment.expires_at.timestamp(),
            expires_at.timestamp(),
            places=3,
        )

    # =========================================================================
    # VERIFICATION-REQUIRED ROLE ASSIGNMENT
    # =========================================================================

    def test_assign_role_verification_required_role_without_verifier_is_inactive(
        self,
    ):
        """
        A verification-required role cannot be activated without a verifier.
        """

        user = self.create_user(
            "verification-pending@example.com",
        )

        role = self.create_role(
            name="agent",
            app_name="realestate",
            requires_verification=True,
        )

        assignment = assign_role(
            user,
            role,
        )

        self.assertFalse(
            assignment.is_active,
        )

        self.assertIsNone(
            assignment.verified_by,
        )

        self.assertIsNone(
            assignment.verified_at,
        )

    def test_assign_role_verification_required_role_can_be_activated_by_verifier(
        self,
    ):
        """
        A verification-required role can be created active when a verifier
        is supplied.
        """

        user = self.create_user(
            "verified-assignment@example.com",
        )

        verifier = self.create_user(
            "assignment-verifier@example.com",
        )

        role = self.create_role(
            name="agent",
            app_name="realestate",
            requires_verification=True,
        )

        assignment = assign_role(
            user,
            role,
            verified_by=verifier,
        )

        self.assertTrue(
            assignment.is_active,
        )

        self.assertEqual(
            assignment.verified_by,
            verifier,
        )

        self.assertIsNotNone(
            assignment.verified_at,
        )

    def test_assign_role_verification_required_role_can_be_explicitly_inactive(
        self,
    ):
        """
        activate=False keeps a verification-required assignment inactive,
        even when a verifier is supplied.
        """

        user = self.create_user(
            "verified-inactive@example.com",
        )

        verifier = self.create_user(
            "inactive-verifier@example.com",
        )

        role = self.create_role(
            name="agent",
            app_name="realestate",
            requires_verification=True,
        )

        assignment = assign_role(
            user,
            role,
            verified_by=verifier,
            activate=False,
        )

        self.assertFalse(
            assignment.is_active,
        )

        self.assertEqual(
            assignment.verified_by,
            verifier,
        )

        self.assertIsNotNone(
            assignment.verified_at,
        )

    # =========================================================================
    # EXISTING ASSIGNMENTS
    # =========================================================================

    def test_assign_role_does_not_modify_existing_assignment(self):
        """
        assign_role() does not overwrite an existing UserRole.

        This is an intentional contract of the current get_or_create()
        implementation.
        """

        user = self.create_user(
            "existing@example.com",
        )

        original_assigner = self.create_user(
            "original-assigner@example.com",
        )

        new_assigner = self.create_user(
            "new-assigner@example.com",
        )

        role = self.create_role()

        original = assign_role(
            user,
            role,
            assigned_by=original_assigner,
            activate=False,
            notes="Original assignment",
        )

        result = assign_role(
            user,
            role,
            assigned_by=new_assigner,
            activate=True,
            notes="Replacement assignment",
        )

        original.refresh_from_db()

        self.assertEqual(
            result.pk,
            original.pk,
        )

        self.assertFalse(
            original.is_active,
        )

        self.assertEqual(
            original.created_by,
            original_assigner,
        )

        self.assertEqual(
            original.notes,
            "Original assignment",
        )

    def test_assign_role_does_not_unrevoke_existing_assignment(self):
        """
        A revoked assignment remains revoked when assign_role() is called
        again.

        Reassignment/reactivation is therefore an explicit lifecycle
        operation rather than an implicit side effect of provisioning.
        """

        user = self.create_user(
            "revoked-existing@example.com",
        )

        admin = self.create_user(
            "revoking-admin@example.com",
        )

        role = self.create_role()

        assignment = assign_role(
            user,
            role,
        )

        assignment.revoke(
            by_user=admin,
        )

        result = assign_role(
            user,
            role,
        )

        assignment.refresh_from_db()

        self.assertEqual(
            result.pk,
            assignment.pk,
        )

        self.assertTrue(
            assignment.is_revoked,
        )

        self.assertFalse(
            assignment.is_active,
        )

    # =========================================================================
    # REVOCATION
    # =========================================================================

    def test_revoke_role_revokes_existing_assignment(self):
        """revoke_role() revokes the user's role."""

        user = self.create_user(
            "revoke-service@example.com",
        )

        admin = self.create_user(
            "revoke-admin@example.com",
        )

        role = self.create_role()

        assignment = assign_role(
            user,
            role,
        )

        result = revoke_role(
            user,
            role,
            revoked_by=admin,
        )

        assignment.refresh_from_db()

        self.assertEqual(
            result.pk,
            assignment.pk,
        )

        self.assertFalse(
            assignment.is_active,
        )

        self.assertTrue(
            assignment.is_revoked,
        )

        self.assertEqual(
            assignment.revoked_by,
            admin,
        )

        self.assertIsNotNone(
            assignment.revoked_at,
        )

    def test_revoke_role_requires_existing_assignment(self):
        """
        revoke_role() raises DoesNotExist when no assignment exists.
        """

        user = self.create_user(
            "missing-assignment@example.com",
        )

        role = self.create_role()

        with self.assertRaises(
            UserRole.DoesNotExist,
        ):
            revoke_role(
                user,
                role,
            )
