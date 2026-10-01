# apps/backend/accounts/tests/test_user_role.py

"""
Tests for the UserRole model.

UserRole owns the lifecycle of a user's application role assignment.

Important distinction:

    Role.requires_verification
        means the ROLE requires verification.

It does NOT mean:

    the user requires face verification at registration.

FaceEncoding and FaceVerification belong to application-specific
verification workflows and are deliberately outside UserRole.
"""

from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from accounts.models.role import Role, UserRole


User = get_user_model()


class UserRoleModelTests(TestCase):
    """Tests for UserRole lifecycle behavior."""

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
    ):
        return Role.objects.create(
            name=name,
            app_name=app_name,
            requires_verification=requires_verification,
        )

    # =========================================================================
    # BASIC ASSIGNMENT
    # =========================================================================

    def test_create_user_role(self):
        """A user can be assigned a role."""

        user = self.create_user(
            "user@example.com",
        )

        role = self.create_role()

        user_role = UserRole.objects.create(
            user=user,
            role=role,
        )

        self.assertEqual(
            user_role.user,
            user,
        )

        self.assertEqual(
            user_role.role,
            role,
        )

        self.assertTrue(
            user_role.is_active,
        )

    def test_user_role_defaults_to_active(self):
        """Normal non-verification roles are active by default."""

        user = self.create_user(
            "active@example.com",
        )

        role = self.create_role()

        user_role = UserRole.objects.create(
            user=user,
            role=role,
        )

        self.assertTrue(
            user_role.is_active,
        )

    def test_user_role_string_representation(self):
        user = self.create_user(
            "string@example.com",
        )

        role = self.create_role(
            name="customer",
            app_name="ecommerce",
        )

        user_role = UserRole.objects.create(
            user=user,
            role=role,
        )

        self.assertIn(
            "string@example.com",
            str(user_role),
        )

        self.assertIn(
            "customer",
            str(user_role),
        )

    # =========================================================================
    # UNIQUENESS
    # =========================================================================

    def test_same_user_cannot_have_duplicate_role_assignment(self):
        """A user may have a given Role only once."""

        user = self.create_user(
            "duplicate@example.com",
        )

        role = self.create_role()

        UserRole.objects.create(
            user=user,
            role=role,
        )

        with self.assertRaises(
            IntegrityError,
        ):
            UserRole.objects.create(
                user=user,
                role=role,
            )

    def test_different_users_can_have_same_role(self):
        """A role can be assigned to many users."""

        user_one = self.create_user(
            "one@example.com",
        )

        user_two = self.create_user(
            "two@example.com",
        )

        role = self.create_role()

        first = UserRole.objects.create(
            user=user_one,
            role=role,
        )

        second = UserRole.objects.create(
            user=user_two,
            role=role,
        )

        self.assertNotEqual(
            first.pk,
            second.pk,
        )

    # =========================================================================
    # VERIFICATION-REQUIRED ROLES
    # =========================================================================

    def test_verification_required_role_cannot_be_active_without_verification(
        self,
    ):
        """
        A verification-required role cannot be activated without
        verification information.
        """

        user = self.create_user(
            "pending@example.com",
        )

        role = self.create_role(
            name="agent",
            app_name="realestate",
            requires_verification=True,
        )

        user_role = UserRole(
            user=user,
            role=role,
            is_active=True,
        )

        with self.assertRaises(
            ValidationError,
        ):
            user_role.full_clean()

    def test_verification_required_role_can_exist_inactive(self):
        """
        A verification-required role may exist in a pending/inactive
        state.
        """

        user = self.create_user(
            "pending2@example.com",
        )

        role = self.create_role(
            name="agent",
            app_name="realestate",
            requires_verification=True,
        )

        user_role = UserRole.objects.create(
            user=user,
            role=role,
            is_active=False,
        )

        self.assertFalse(
            user_role.is_active,
        )

    def test_verification_required_role_can_be_activated_by_verified_user(
        self,
    ):
        """
        activate() requires verified_by for verification-required roles.
        """

        user = self.create_user(
            "agent@example.com",
        )

        verifier = self.create_user(
            "admin@example.com",
        )

        role = self.create_role(
            name="agent",
            app_name="realestate",
            requires_verification=True,
        )

        user_role = UserRole.objects.create(
            user=user,
            role=role,
            is_active=False,
        )

        user_role.activate(
            verified_by=verifier,
        )

        user_role.refresh_from_db()

        self.assertTrue(
            user_role.is_active,
        )

        self.assertEqual(
            user_role.verified_by,
            verifier,
        )

        self.assertIsNotNone(
            user_role.verified_at,
        )

        self.assertFalse(
            user_role.is_revoked,
        )

    def test_verification_required_role_activation_without_verifier_fails(
        self,
    ):
        """activate() must reject unverified activation."""

        user = self.create_user(
            "agent2@example.com",
        )

        role = self.create_role(
            name="agent",
            app_name="realestate",
            requires_verification=True,
        )

        user_role = UserRole.objects.create(
            user=user,
            role=role,
            is_active=False,
        )

        with self.assertRaises(
            ValidationError,
        ):
            user_role.activate()

    # =========================================================================
    # ORDINARY ROLE ACTIVATION
    # =========================================================================

    def test_non_verification_role_can_be_activated(self):
        """Ordinary roles do not require a verifier."""

        user = self.create_user(
            "ordinary@example.com",
        )

        role = self.create_role(
            requires_verification=False,
        )

        user_role = UserRole.objects.create(
            user=user,
            role=role,
            is_active=False,
        )

        user_role.activate()

        user_role.refresh_from_db()

        self.assertTrue(
            user_role.is_active,
        )

    # =========================================================================
    # DEACTIVATION
    # =========================================================================

    def test_deactivate_role(self):
        """deactivate() disables the assignment."""

        user = self.create_user(
            "deactivate@example.com",
        )

        role = self.create_role()

        user_role = UserRole.objects.create(
            user=user,
            role=role,
            is_active=True,
        )

        user_role.deactivate()

        user_role.refresh_from_db()

        self.assertFalse(
            user_role.is_active,
        )

    # =========================================================================
    # REVOCATION
    # =========================================================================

    def test_revoke_role(self):
        """revoke() permanently records revocation."""

        user = self.create_user(
            "revoke@example.com",
        )

        admin = self.create_user(
            "admin2@example.com",
        )

        role = self.create_role()

        user_role = UserRole.objects.create(
            user=user,
            role=role,
            is_active=True,
        )

        user_role.revoke(
            by_user=admin,
        )

        user_role.refresh_from_db()

        self.assertFalse(
            user_role.is_active,
        )

        self.assertTrue(
            user_role.is_revoked,
        )

        self.assertIsNotNone(
            user_role.revoked_at,
        )

        self.assertEqual(
            user_role.revoked_by,
            admin,
        )

    # =========================================================================
    # VERIFICATION STATE
    # =========================================================================

    def test_is_verified_false_for_unverified_assignment(self):
        user = self.create_user(
            "notverified@example.com",
        )

        role = self.create_role()

        user_role = UserRole.objects.create(
            user=user,
            role=role,
        )

        self.assertFalse(
            user_role.is_verified,
        )

    def test_is_verified_true_when_verification_fields_exist(self):
        user = self.create_user(
            "verified@example.com",
        )

        verifier = self.create_user(
            "verifier@example.com",
        )

        role = self.create_role(
            name="verified-role",
            app_name="realestate",
        )

        now = timezone.now()

        user_role = UserRole.objects.create(
            user=user,
            role=role,
            is_active=True,
            verified_by=verifier,
            verified_at=now,
        )

        self.assertTrue(
            user_role.is_verified,
        )

    # =========================================================================
    # EXPIRATION
    # =========================================================================

    def test_role_is_not_expired_without_expiration_date(self):
        user = self.create_user(
            "neverexpires@example.com",
        )

        role = self.create_role()

        user_role = UserRole.objects.create(
            user=user,
            role=role,
        )

        self.assertFalse(
            user_role.is_expired,
        )

    def test_role_is_not_expired_before_expiration(self):
        user = self.create_user(
            "future@example.com",
        )

        role = self.create_role()

        user_role = UserRole.objects.create(
            user=user,
            role=role,
            expires_at=timezone.now() + timedelta(days=1),
        )

        self.assertFalse(
            user_role.is_expired,
        )

    def test_role_is_expired_after_expiration(self):
        user = self.create_user(
            "expired@example.com",
        )

        role = self.create_role()

        user_role = UserRole.objects.create(
            user=user,
            role=role,
            expires_at=timezone.now() - timedelta(seconds=1),
        )

        self.assertTrue(
            user_role.is_expired,
        )

    # =========================================================================
    # EFFECTIVE ACTIVE STATE
    # =========================================================================

    def test_effective_active_for_normal_active_role(self):
        user = self.create_user(
            "effective@example.com",
        )

        role = self.create_role()

        user_role = UserRole.objects.create(
            user=user,
            role=role,
            is_active=True,
        )

        self.assertTrue(
            user_role.effective_active,
        )

    def test_effective_active_false_for_expired_role(self):
        user = self.create_user(
            "effective-expired@example.com",
        )

        role = self.create_role()

        user_role = UserRole.objects.create(
            user=user,
            role=role,
            is_active=True,
            expires_at=timezone.now() - timedelta(seconds=1),
        )

        self.assertFalse(
            user_role.effective_active,
        )

    def test_effective_active_false_for_revoked_role(self):
        user = self.create_user(
            "effective-revoked@example.com",
        )

        role = self.create_role()

        user_role = UserRole.objects.create(
            user=user,
            role=role,
            is_active=True,
        )

        user_role.revoke()

        user_role.refresh_from_db()

        self.assertFalse(
            user_role.effective_active,
        )

    # =========================================================================
    # CLEAR VERIFICATION
    # =========================================================================

    def test_clear_verification_removes_verification_state(self):
        user = self.create_user(
            "clear@example.com",
        )

        verifier = self.create_user(
            "clear-verifier@example.com",
        )

        role = self.create_role(
            name="verified",
            app_name="realestate",
            requires_verification=True,
        )

        user_role = UserRole.objects.create(
            user=user,
            role=role,
            is_active=True,
            verified_by=verifier,
            verified_at=timezone.now(),
        )

        user_role.clear_verification()

        user_role.refresh_from_db()

        self.assertIsNone(
            user_role.verified_by,
        )

        self.assertIsNone(
            user_role.verified_at,
        )

        self.assertFalse(
            user_role.is_active,
        )

    # =========================================================================
    # QUERY HELPERS
    # =========================================================================

    def test_get_user_roles_returns_active_roles(self):
        user = self.create_user(
            "query@example.com",
        )

        active_role = self.create_role(
            name="customer",
            app_name="ecommerce",
        )

        inactive_role = self.create_role(
            name="vendor",
            app_name="ecommerce",
        )

        UserRole.objects.create(
            user=user,
            role=active_role,
            is_active=True,
        )

        UserRole.objects.create(
            user=user,
            role=inactive_role,
            is_active=False,
        )

        roles = UserRole.get_user_roles(
            user,
        )

        self.assertEqual(
            roles.count(),
            1,
        )

        self.assertEqual(
            roles.first().role,
            active_role,
        )

    def test_get_user_roles_can_filter_by_app(self):
        user = self.create_user(
            "appfilter@example.com",
        )

        ecommerce_role = self.create_role(
            name="customer",
            app_name="ecommerce",
        )

        realestate_role = self.create_role(
            name="buyer",
            app_name="realestate",
        )

        UserRole.objects.create(
            user=user,
            role=ecommerce_role,
        )

        UserRole.objects.create(
            user=user,
            role=realestate_role,
        )

        roles = UserRole.get_user_roles(
            user,
            app_name="realestate",
        )

        self.assertEqual(
            roles.count(),
            1,
        )

        self.assertEqual(
            roles.first().role,
            realestate_role,
        )

    def test_get_pending_verification_roles(self):
        user = self.create_user(
            "pending-query@example.com",
        )

        role = self.create_role(
            name="agent",
            app_name="realestate",
            requires_verification=True,
        )

        assignment = UserRole.objects.create(
            user=user,
            role=role,
            is_active=False,
        )

        pending = UserRole.get_pending_verification_roles(
            user=user,
        )

        self.assertIn(
            assignment,
            pending,
        )

    # =========================================================================
    # VERIFICATION IS ROLE-SPECIFIC
    # =========================================================================

    def test_role_verification_does_not_require_face_encoding(self):
        """
        Role verification is intentionally independent from face data.

        This test documents the architecture:

            Role
                ↓
            UserRole
                ↓
            role verification

        FaceEncoding is NOT required by UserRole.
        """

        user = self.create_user(
            "no-face-required@example.com",
        )

        verifier = self.create_user(
            "role-verifier@example.com",
        )

        role = self.create_role(
            name="agent",
            app_name="realestate",
            requires_verification=True,
        )

        user_role = UserRole.objects.create(
            user=user,
            role=role,
            is_active=False,
        )

        user_role.activate(
            verified_by=verifier,
        )

        user_role.refresh_from_db()

        self.assertTrue(
            user_role.is_active,
        )

        self.assertTrue(
            user_role.is_verified,
        )