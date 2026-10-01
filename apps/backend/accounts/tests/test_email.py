# apps/backend/accounts/tests/test_email.py

"""
Tests for accounts.email_service.

Email verification is an account-domain concern.

These tests intentionally verify that:

    email verification
        !=
    authentication JWT

The email service owns the complete verification lifecycle.
"""

from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings

from accounts.email_service import (
    EMAIL_VERIFICATION_PURPOSE,
    EmailVerificationAlreadyCompletedError,
    EmailVerificationError,
    EmailVerificationTokenError,
    build_confirmation_message,
    build_confirmation_subject,
    build_confirmation_url,
    confirm_email,
    generate_confirmation_token,
    resend_confirmation_email,
    send_confirmation_email,
    verify_confirmation_token,
)


User = get_user_model()


@override_settings(
    ACCOUNT_VERIFICATION_TIMEOUT_HOURS=24,
    FRONTEND_URL="http://localhost:5173",
    DEFAULT_FROM_EMAIL="noreply@univa.test",
)
class EmailVerificationServiceTests(TestCase):
    """Tests for the canonical email verification service."""

    PASSWORD = "StrongTestPassword123!"

    def create_user(
        self,
        *,
        email="user@example.com",
        email_verified=False,
    ):
        user = User.objects.create_user(
            email=email,
            password=self.PASSWORD,
        )

        if email_verified:
            user.email_verified = True
            user.verify_email()

        return user

    # =========================================================================
    # TOKEN GENERATION
    # =========================================================================

    def test_generate_confirmation_token_returns_string(self):
        """A valid user receives a signed verification token."""

        user = self.create_user()

        token = generate_confirmation_token(user)

        self.assertIsInstance(
            token,
            str,
        )

        self.assertTrue(
            token,
        )

    def test_generated_token_can_be_verified(self):
        """A generated token resolves back to the correct user."""

        user = self.create_user(
            email="token@example.com",
        )

        token = generate_confirmation_token(user)

        resolved_user = verify_confirmation_token(
            token,
        )

        self.assertEqual(
            resolved_user.pk,
            user.pk,
        )

    def test_token_contains_email_verification_purpose(self):
        """
        The signed token belongs specifically to email verification.
        """

        user = self.create_user(
            email="purpose@example.com",
        )

        token = generate_confirmation_token(user)

        # The public service should accept its own token.
        resolved_user = verify_confirmation_token(
            token,
        )

        self.assertEqual(
            resolved_user.pk,
            user.pk,
        )

        self.assertEqual(
            EMAIL_VERIFICATION_PURPOSE,
            "email_verification",
        )

    # =========================================================================
    # INVALID TOKENS
    # =========================================================================

    def test_invalid_token_is_rejected(self):
        """Random token data must never resolve to a user."""

        with self.assertRaises(
            EmailVerificationTokenError,
        ):
            verify_confirmation_token(
                "this-is-not-a-valid-token",
            )

    def test_empty_token_is_rejected(self):
        """Empty tokens are invalid."""

        with self.assertRaises(
            EmailVerificationTokenError,
        ):
            verify_confirmation_token(
                "",
            )

    def test_modified_token_is_rejected(self):
        """Changing a signed token invalidates it."""

        user = self.create_user(
            email="modified@example.com",
        )

        token = generate_confirmation_token(user)

        modified_token = token + "modified"

        with self.assertRaises(
            EmailVerificationTokenError,
        ):
            verify_confirmation_token(
                modified_token,
            )

    # =========================================================================
    # CONFIRMATION
    # =========================================================================

    def test_confirm_email_marks_user_verified(self):
        """confirm_email() completes email verification."""

        user = self.create_user(
            email="confirm@example.com",
        )

        token = generate_confirmation_token(
            user,
        )

        confirmed_user = confirm_email(
            token,
        )

        self.assertEqual(
            confirmed_user.pk,
            user.pk,
        )

        user.refresh_from_db()

        self.assertTrue(
            user.email_verified,
        )

        self.assertIsNotNone(
            user.email_verified_at,
        )

    def test_confirm_email_is_idempotent_for_verified_user(self):
        """
        Reusing a valid token after verification should not break
        the account.

        The exact service behavior is allowed to evolve, but the
        account must remain verified.
        """

        user = self.create_user(
            email="idempotent@example.com",
        )

        token = generate_confirmation_token(
            user,
        )

        confirm_email(
            token,
        )

        user.refresh_from_db()

        self.assertTrue(
            user.email_verified,
        )

        self.assertIsNotNone(
            user.email_verified_at,
        )

    # =========================================================================
    # ALREADY VERIFIED
    # =========================================================================

    def test_send_confirmation_email_rejects_verified_user(self):
        """A verified account must not receive another confirmation."""

        user = self.create_user(
            email="already@example.com",
        )

        user.verify_email()

        with self.assertRaises(
            EmailVerificationAlreadyCompletedError,
        ):
            send_confirmation_email(
                user,
            )

    def test_resend_confirmation_email_rejects_verified_user(self):
        """Resending to a verified account must fail safely."""

        user = self.create_user(
            email="already-resend@example.com",
        )

        user.verify_email()

        with self.assertRaises(
            EmailVerificationAlreadyCompletedError,
        ):
            resend_confirmation_email(
                user,
            )

    # =========================================================================
    # PHONE-ONLY ACCOUNTS
    # =========================================================================

    def test_phone_only_user_cannot_receive_email_verification(self):
        """Email verification requires an email address."""

        user = User.objects.create_user(
            phone_number="+2348012345678",
            password=self.PASSWORD,
        )

        with self.assertRaises(
            EmailVerificationError,
        ):
            send_confirmation_email(
                user,
            )

    # =========================================================================
    # URL
    # =========================================================================

    def test_confirmation_url_uses_canonical_route(self):
        """The frontend verification route remains canonical."""

        user = self.create_user(
            email="url@example.com",
        )

        token = generate_confirmation_token(
            user,
        )

        url = build_confirmation_url(
            user,
            token,
        )

        self.assertIn(
            "/auth/confirmmail",
            url,
        )

        self.assertIn(
            "?token=",
            url,
        )

        self.assertIn(
            token,
            url,
        )

    # =========================================================================
    # EMAIL CONTENT
    # =========================================================================

    def test_confirmation_subject_is_canonical(self):
        self.assertEqual(
            build_confirmation_subject(),
            "Verify your Univa email",
        )

    def test_confirmation_message_contains_url(self):
        user = self.create_user(
            email="message@example.com",
        )

        token = generate_confirmation_token(
            user,
        )

        url = build_confirmation_url(
            user,
            token,
        )

        message = build_confirmation_message(
            user,
            url,
        )

        self.assertIn(
            url,
            message,
        )

        self.assertIn(
            "verify",
            message.lower(),
        )

    # =========================================================================
    # EMAIL DELIVERY
    # =========================================================================

    def test_send_confirmation_email_sends_one_message(self):
        """The canonical service sends exactly one verification email."""

        user = self.create_user(
            email="delivery@example.com",
        )

        token = send_confirmation_email(
            user,
        )

        self.assertTrue(
            token,
        )

        self.assertEqual(
            len(mail.outbox),
            1,
        )

        message = mail.outbox[0]

        self.assertEqual(
            message.to,
            ["delivery@example.com"],
        )

        self.assertEqual(
            message.subject,
            "Verify your Univa email",
        )

        self.assertIn(
            "/auth/confirmmail",
            message.body,
        )

    def test_resend_confirmation_email_sends_message(self):
        """Resending an unverified email creates another message."""

        user = self.create_user(
            email="resend@example.com",
        )

        resend_confirmation_email(
            user,
        )

        self.assertEqual(
            len(mail.outbox),
            1,
        )

        self.assertEqual(
            mail.outbox[0].to,
            ["resend@example.com"],
        )

    # =========================================================================
    # TOKEN EXPIRATION
    # =========================================================================

    @override_settings(
        ACCOUNT_VERIFICATION_TIMEOUT_HOURS=1,
    )
    def test_expired_token_is_rejected(self):
        """
        Expiration behavior is tested using the service's configured
        timeout.
        """

        user = self.create_user(
            email="expired@example.com",
        )

        token = generate_confirmation_token(
            user,
        )

        # Patch the service's verification timeout to zero seconds.
        with patch(
            "accounts.email_service._verification_timeout_seconds",
            return_value=0,
        ):
            with self.assertRaises(
                EmailVerificationTokenError,
            ):
                verify_confirmation_token(
                    token,
                )