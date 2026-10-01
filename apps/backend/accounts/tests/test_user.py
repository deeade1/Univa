# apps/backend/accounts/tests/test_user.py

"""
Tests for the canonical accounts User model.

These tests verify:

    - email registration
    - phone registration
    - USERNAME_FIELD configuration
    - password hashing
    - email verification state
    - User.verify_email()
    - role helper behavior
    - account identity separation

Face verification is intentionally NOT tested here.
FaceEncoding / FaceVerification belong to application-specific
verification workflows rather than basic account creation.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from accounts.models.role import Role, UserRole


User = get_user_model()


class UserModelTests(TestCase):
    """Tests for the canonical User model."""

    PASSWORD = "StrongTestPassword123!"

    def create_user(
        self,
        *,
        email=None,
        phone_number=None,
        password=None,
        **extra,
    ):
        """
        Create a user using the project's canonical UserManager.
        """

        password = password or self.PASSWORD

        return User.objects.create_user(
            email=email,
            phone_number=phone_number,
            password=password,
            **extra,
        )

    # =========================================================================
    # MODEL CONFIGURATION
    # =========================================================================

    def test_user_uses_email_as_username_field(self):
        """Email remains the canonical Django authentication identifier."""

        self.assertEqual(
            User.USERNAME_FIELD,
            "email",
        )

        self.assertEqual(
            User.REQUIRED_FIELDS,
            [],
        )

    def test_username_field_is_not_present(self):
        """The legacy username field should not be part of the model."""

        field_names = {
            field.name
            for field in User._meta.get_fields()
        }

        self.assertNotIn(
            "username",
            field_names,
        )

    # =========================================================================
    # EMAIL USERS
    # =========================================================================

    def test_create_user_with_email(self):
        """A user can be created with an email address."""

        user = self.create_user(
            email="john@example.com",
        )

        self.assertEqual(
            user.email,
            "john@example.com",
        )

        self.assertIsNone(
            user.phone_number,
        )

        self.assertTrue(
            user.check_password(self.PASSWORD),
        )

        self.assertFalse(
            user.email_verified,
        )

        self.assertIsNone(
            user.email_verified_at,
        )

    def test_password_is_hashed(self):
        """Passwords must never be stored in plaintext."""

        user = self.create_user(
            email="hashed@example.com",
        )

        self.assertNotEqual(
            user.password,
            self.PASSWORD,
        )

        self.assertTrue(
            user.check_password(self.PASSWORD),
        )

    # =========================================================================
    # PHONE USERS
    # =========================================================================

    def test_create_user_with_phone(self):
        """A user can be created using a phone number."""

        user = self.create_user(
            phone_number="+2348012345678",
        )

        self.assertIsNone(
            user.email,
        )

        self.assertEqual(
            str(user.phone_number),
            "+2348012345678",
        )

        self.assertTrue(
            user.check_password(self.PASSWORD),
        )

    # =========================================================================
    # EMAIL VERIFICATION
    # =========================================================================

    def test_new_user_email_is_unverified(self):
        """New accounts start with email verification disabled."""

        user = self.create_user(
            email="unverified@example.com",
        )

        self.assertFalse(
            user.email_verified,
        )

        self.assertIsNone(
            user.email_verified_at,
        )

    def test_verify_email_marks_email_verified(self):
        """verify_email() records verification and timestamp."""

        user = self.create_user(
            email="verify@example.com",
        )

        before = timezone.now()

        user.verify_email()

        after = timezone.now()

        user.refresh_from_db()

        self.assertTrue(
            user.email_verified,
        )

        self.assertIsNotNone(
            user.email_verified_at,
        )

        self.assertGreaterEqual(
            user.email_verified_at,
            before,
        )

        self.assertLessEqual(
            user.email_verified_at,
            after,
        )

    def test_is_email_verified_property_matches_field(self):
        """Backward-compatible verification property remains consistent."""

        user = self.create_user(
            email="property@example.com",
        )

        self.assertFalse(
            user.is_email_verified,
        )

        user.verify_email()

        user.refresh_from_db()

        self.assertTrue(
            user.is_email_verified,
        )

    def test_verify_email_is_idempotent(self):
        """Calling verify_email twice should not break the account."""

        user = self.create_user(
            email="idempotent@example.com",
        )

        user.verify_email()

        first_timestamp = user.email_verified_at

        user.verify_email()

        user.refresh_from_db()

        self.assertTrue(
            user.email_verified,
        )

        self.assertEqual(
            user.email_verified_at,
            first_timestamp,
        )

    # =========================================================================
    # ROLE HELPERS
    # =========================================================================

    def test_user_has_no_roles_initially(self):
        """A newly created user has no application roles unless assigned."""

        user = self.create_user(
            email="noroles@example.com",
        )

        self.assertEqual(
            user.user_roles.count(),
            0,
        )

    def test_user_active_roles_returns_active_roles(self):
        """active_roles contains active application assignments."""

        user = self.create_user(
            email="roles@example.com",
        )

        role = Role.objects.create(
            name="customer",
            app_name="ecommerce",
            requires_verification=False,
        )

        UserRole.objects.create(
            user=user,
            role=role,
            is_active=True,
        )

        user.refresh_from_db()

        self.assertIn(
            (
                "ecommerce",
                "customer",
            ),
            user.active_roles,
        )

    def test_user_active_roles_excludes_inactive_roles(self):
        """Inactive assignments are not exposed as active roles."""

        user = self.create_user(
            email="inactive-role@example.com",
        )

        role = Role.objects.create(
            name="customer",
            app_name="ecommerce",
        )

        UserRole.objects.create(
            user=user,
            role=role,
            is_active=False,
        )

        user.refresh_from_db()

        self.assertNotIn(
            (
                "ecommerce",
                "customer",
            ),
            user.active_roles,
        )

    def test_user_has_role(self):
        """has_role() correctly identifies an active assignment."""

        user = self.create_user(
            email="has-role@example.com",
        )

        role = Role.objects.create(
            name="customer",
            app_name="ecommerce",
        )

        UserRole.objects.create(
            user=user,
            role=role,
            is_active=True,
        )

        user.refresh_from_db()

        self.assertTrue(
            user.has_role(
                "ecommerce",
                "customer",
            ),
        )

    def test_user_does_not_have_role_when_inactive(self):
        """has_role() returns False for inactive assignments."""

        user = self.create_user(
            email="no-role@example.com",
        )

        role = Role.objects.create(
            name="customer",
            app_name="ecommerce",
        )

        UserRole.objects.create(
            user=user,
            role=role,
            is_active=False,
        )

        user.refresh_from_db()

        self.assertFalse(
            user.has_role(
                "ecommerce",
                "customer",
            ),
        )

    # =========================================================================
    # STRING REPRESENTATION
    # =========================================================================

    def test_user_string_representation_uses_email(self):
        """Email users should stringify using their email."""

        user = self.create_user(
            email="string@example.com",
        )

        self.assertEqual(
            str(user),
            "string@example.com",
        )

    def test_user_string_representation_uses_phone_when_no_email(self):
        """Phone-only users should stringify using their phone."""

        user = self.create_user(
            phone_number="+2348011111111",
        )

        self.assertEqual(
            str(user),
            "+2348011111111",
        )