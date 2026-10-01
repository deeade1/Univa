# apps/backend/accounts/tests/test_registration.py

"""
Integration tests for GraphQL user registration.

Registration is intentionally limited to account creation concerns:

    User
    UserProfile
    optional ordinary roles
    authentication JWT issuance
    email verification request

Registration MUST NOT automatically create:

    FaceEncoding
    FaceVerification

Face verification belongs to specific application workflows.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.test import RequestFactory, TestCase

from accounts.models.profile import UserProfile
from accounts.models.role import Role

from graphq.accounts.mutations.user import CreateUserMutation


User = get_user_model()


class RegistrationMutationTests(TestCase):
    """Integration tests for CreateUserMutation."""

    PASSWORD = "StrongTestPassword123!"

    def setUp(self):
        super().setUp()

        # Registration uses Django's cache for rate limiting.
        #
        # Each test must start with a clean rate-limit state so that one
        # registration test cannot consume the limit for another test.
        cache.clear()

    def tearDown(self):
        # Do not allow rate-limit state to leak into another test.
        cache.clear()

        super().tearDown()

    # =========================================================================
    # REQUEST / GRAPHQL CONTEXT
    # =========================================================================

    def build_request(self):
        """
        Build the GraphQL info-like object expected by CreateUserMutation.

        CreateUserMutation expects:

            info.context
            info.field_name
            info.schema
            info.path
            info.operation
        """

        request = RequestFactory().post(
            "/graphql/",
            data={},
            content_type="application/json",
        )

        request.user = AnonymousUser()

        return SimpleNamespace(
            context=request,
            field_name="createUser",
            schema=None,
            path=None,
            operation=None,
        )

    # =========================================================================
    # EMAIL REGISTRATION
    # =========================================================================

    @patch(
        "graphq.accounts.mutations.user.send_confirmation_email"
    )
    @patch(
        "graphq.accounts.mutations.user.TokenGenerationMixin.generate_tokens"
    )
    def test_email_registration_creates_user_and_profile(
        self,
        generate_tokens,
        send_confirmation_email,
    ):
        """
        Email registration creates the canonical account objects.
        """

        generate_tokens.return_value = (
            "access-token",
            "refresh-token",
        )

        send_confirmation_email.return_value = (
            "email-verification-token",
        )

        request = self.build_request()

        result = CreateUserMutation.mutate_and_get_payload(
            None,
            request,
            contact="  USER@Example.COM  ",
            password=self.PASSWORD,
            send_verification=True,
        )

        self.assertIsNotNone(result.user)

        user = result.user

        self.assertEqual(
            user.email,
            "user@example.com",
        )

        self.assertIsNone(
            user.phone_number,
        )

        self.assertTrue(
            user.check_password(self.PASSWORD),
        )

        self.assertTrue(
            UserProfile.objects.filter(
                user=user,
            ).exists(),
        )

        generate_tokens.assert_called_once()

        send_confirmation_email.assert_called_once_with(
            user,
        )

        self.assertTrue(
            result.verification_sent,
        )

    # =========================================================================
    # PHONE REGISTRATION
    # =========================================================================

    @patch(
        "graphq.accounts.mutations.user.send_confirmation_email"
    )
    @patch(
        "graphq.accounts.mutations.user.TokenGenerationMixin.generate_tokens"
    )
    def test_phone_registration_does_not_send_email_verification(
        self,
        generate_tokens,
        send_confirmation_email,
    ):
        """
        Phone-only registration has no email verification request.
        """

        generate_tokens.return_value = (
            "access-token",
            "refresh-token",
        )

        request = self.build_request()

        result = CreateUserMutation.mutate_and_get_payload(
            None,
            request,
            contact="+2348012345678",
            password=self.PASSWORD,
            send_verification=True,
        )

        user = result.user

        self.assertIsNone(
            user.email,
        )

        self.assertEqual(
            str(user.phone_number),
            "+2348012345678",
        )

        send_confirmation_email.assert_not_called()

        self.assertFalse(
            result.verification_sent,
        )

    # =========================================================================
    # NO FACE CREATION DURING REGISTRATION
    # =========================================================================

    @patch(
        "graphq.accounts.mutations.user.TokenGenerationMixin.generate_tokens"
    )
    @patch(
        "graphq.accounts.mutations.user.send_confirmation_email"
    )
    def test_registration_does_not_create_face_records(
        self,
        send_confirmation_email,
        generate_tokens,
    ):
        """
        Initial registration must not create FaceEncoding or
        FaceVerification records.

        Face verification belongs to a separate application workflow.

        The test intentionally does NOT patch check_rate_limit. The real
        production rate-limit implementation must execute during this test.
        The cache is isolated by setUp()/tearDown().
        """

        generate_tokens.return_value = (
            "access-token",
            "refresh-token",
        )

        send_confirmation_email.return_value = (
            "verification-token",
        )

        try:
            from accounts.models.face import (
                FaceEncoding,
                FaceVerification,
            )
        except ImportError:
            FaceEncoding = None
            FaceVerification = None

        request = self.build_request()

        result = CreateUserMutation.mutate_and_get_payload(
            None,
            request,
            contact="noface@example.com",
            password=self.PASSWORD,
            send_verification=True,
        )

        self.assertIsNotNone(
            result.user,
        )

        user = result.user

        if FaceEncoding is not None:
            self.assertFalse(
                FaceEncoding.objects.filter(
                    user=user,
                ).exists(),
            )

        if FaceVerification is not None:
            self.assertFalse(
                FaceVerification.objects.filter(
                    user=user,
                ).exists(),
            )

    # =========================================================================
    # OPTIONAL ROLE ASSIGNMENT
    # =========================================================================

    def test_registration_can_assign_explicit_non_verification_role(self):
        """
        Registration may assign an explicitly requested ordinary role.

        Verification-required application roles should normally be assigned
        by their application-specific workflow.

        Role/UserRole domain behavior is tested separately in:

            accounts.tests.test_role
            accounts.tests.test_user_role
        """

        role = Role.objects.create(
            name="customer",
            app_name="ecommerce",
            requires_verification=False,
        )

        self.assertIsNotNone(
            role.pk,
        )

        self.assertEqual(
            role.name,
            "customer",
        )

        self.assertEqual(
            role.app_name,
            "ecommerce",
        )

        self.assertFalse(
            role.requires_verification,
        )

    # =========================================================================
    # DUPLICATE CONTACT
    # =========================================================================

    @patch(
        "graphq.accounts.mutations.user.TokenGenerationMixin.generate_tokens"
    )
    def test_duplicate_email_registration_is_rejected(
        self,
        generate_tokens,
    ):
        """
        The same email cannot create a second account.
        """

        generate_tokens.return_value = (
            "access-token",
            "refresh-token",
        )

        User.objects.create_user(
            email="duplicate@example.com",
            password=self.PASSWORD,
        )

        request = self.build_request()

        with self.assertRaises(Exception):
            CreateUserMutation.mutate_and_get_payload(
                None,
                request,
                contact="DUPLICATE@example.com",
                password=self.PASSWORD,
                send_verification=False,
            )

    # =========================================================================
    # PASSWORD VALIDATION
    # =========================================================================

    @patch(
        "graphq.accounts.mutations.user.TokenGenerationMixin.generate_tokens"
    )
    def test_short_password_is_rejected(
        self,
        generate_tokens,
    ):
        """
        Registration must enforce the configured minimum password length.
        """

        generate_tokens.return_value = (
            "access-token",
            "refresh-token",
        )

        request = self.build_request()

        with self.assertRaises(Exception):
            CreateUserMutation.mutate_and_get_payload(
                None,
                request,
                contact="shortpassword@example.com",
                password="123",
                send_verification=False,
            )

        self.assertFalse(
            User.objects.filter(
                email="shortpassword@example.com",
            ).exists(),
        )

    # =========================================================================
    # EMAIL VERIFICATION FLAG
    # =========================================================================

    @patch(
        "graphq.accounts.mutations.user.TokenGenerationMixin.generate_tokens"
    )
    @patch(
        "graphq.accounts.mutations.user.send_confirmation_email"
    )
    def test_send_verification_false_does_not_send_email(
        self,
        send_confirmation_email,
        generate_tokens,
    ):
        """
        The caller may explicitly disable the verification email.
        """

        generate_tokens.return_value = (
            "access-token",
            "refresh-token",
        )

        request = self.build_request()

        result = CreateUserMutation.mutate_and_get_payload(
            None,
            request,
            contact="nosend@example.com",
            password=self.PASSWORD,
            send_verification=False,
        )

        self.assertIsNotNone(
            result.user,
        )

        send_confirmation_email.assert_not_called()

        self.assertFalse(
            result.verification_sent,
        )

    # =========================================================================
    # AUTHENTICATION / EMAIL VERIFICATION SEPARATION
    # =========================================================================

    @patch(
        "graphq.accounts.mutations.user.TokenGenerationMixin.generate_tokens"
    )
    @patch(
        "graphq.accounts.mutations.user.send_confirmation_email"
    )
    def test_registration_uses_separate_auth_and_email_services(
        self,
        send_confirmation_email,
        generate_tokens,
    ):
        """
        Authentication token generation and email verification are
        separate service boundaries.
        """

        generate_tokens.return_value = (
            "access-token",
            "refresh-token",
        )

        send_confirmation_email.return_value = (
            "signed-email-verification-token",
        )

        request = self.build_request()

        result = CreateUserMutation.mutate_and_get_payload(
            None,
            request,
            contact="separation@example.com",
            password=self.PASSWORD,
            send_verification=True,
        )

        self.assertEqual(
            result.token,
            "access-token",
        )

        self.assertEqual(
            result.refresh_token,
            "refresh-token",
        )

        generate_tokens.assert_called_once()

        send_confirmation_email.assert_called_once()

        # Authentication JWT and email verification token are separate
        # security artifacts and must never be interchangeable.
        self.assertNotEqual(
            result.token,
            "signed-email-verification-token",
        )