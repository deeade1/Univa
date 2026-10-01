"""
Tests for GraphQL authentication mutations.

The GraphQL layer is tested as an adapter.

JWT cryptography, token signing, token decoding, refresh rotation,
and revocation internals are mocked at the GraphQL boundary.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone as dt_timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.test import RequestFactory, TestCase
from graphql import GraphQLError

from accounts.models import User

from graphq.accounts.mutations.auth import (
    LogoutMutation,
    ObtainJSONWebTokenMutation,
    RefreshTokenMutation,
    ResendMagicLinkMutation,
    RevokeAllTokensMutation,
    RevokeTokenMutation,
    SendMagicLinkMutation,
    SendPasswordResetMutation,
    VerifyMagicLinkMutation,
    VerifyTokenMutation,
)

from univa_jwt.constants import REFRESH_TOKEN


# ============================================================================
# TEST CONTEXT
# ============================================================================


def make_context(user=None):
    """
    Build a Graphene-compatible test context.

    Production Graphene passes:

        info.context -> Django request

    The custom ``login_required`` decorator also expects a real
    ResolveInfo-like object containing ``context``.

    Therefore the tests intentionally use:

        context.context -> request
        context.context.user -> authenticated user

    This keeps direct mutation testing compatible with the production
    GraphQL authentication boundary.
    """

    request = RequestFactory().post(
        "/graphql/",
        data={},
        content_type="application/json",
    )

    request.user = user or AnonymousUser()

    request.refresh_token = None

    return SimpleNamespace(
        context=request,
    )


# ============================================================================
# BASE TEST CASE
# ============================================================================


class AuthenticationMutationTestCase(TestCase):
    """
    Shared setup for authentication mutation tests.
    """

    def setUp(self):
        cache.clear()

        self.user = User.objects.create_user(
            email="auth-test@example.com",
            password="TestPassword123!",
            is_active=True,
        )

        self.context = make_context(
            self.user,
        )


# ============================================================================
# SIGN IN
# ============================================================================


class SignInMutationTests(
    AuthenticationMutationTestCase,
):
    """
    Tests for ObtainJSONWebTokenMutation.
    """

    @patch(
        "graphq.accounts.mutations.auth.ObtainJSONWebTokenMutation.check_global_rate_limit"
    )
    @patch(
        "graphq.accounts.mutations.auth.ObtainJSONWebTokenMutation.check_rate_limit"
    )
    @patch(
        "graphq.accounts.mutations.auth.issue_token_pair"
    )
    @patch(
        "graphq.accounts.mutations.auth.authenticate_credentials"
    )
    def test_sign_in_delegates_authentication_and_token_issuance(
        self,
        mock_authenticate,
        mock_issue_tokens,
        mock_rate_limit,
        mock_global_rate_limit,
    ):
        mock_authenticate.return_value = self.user

        mock_issue_tokens.return_value = (
            "access-token",
            "refresh-token",
        )

        result = (
            ObtainJSONWebTokenMutation
            .mutate_and_get_payload(
                None,
                self.context,
                contact=self.user.email,
                password="TestPassword123!",
            )
        )

        mock_authenticate.assert_called_once()

        mock_issue_tokens.assert_called_once_with(
            self.user,
        )

        self.assertEqual(
            result.token,
            "access-token",
        )

        self.assertEqual(
            result.refresh_token,
            "refresh-token",
        )

        self.assertEqual(
            result.user,
            self.user,
        )

    def test_rejects_empty_contact(self):
        with self.assertRaises(GraphQLError) as exc:
            ObtainJSONWebTokenMutation.mutate_and_get_payload(
                None,
                self.context,
                contact="",
                password="password",
            )

        self.assertEqual(
            str(exc.exception),
            "Contact is required.",
        )

    def test_rejects_empty_password(self):
        with self.assertRaises(GraphQLError) as exc:
            ObtainJSONWebTokenMutation.mutate_and_get_payload(
                None,
                self.context,
                contact=self.user.email,
                password="",
            )

        self.assertEqual(
            str(exc.exception),
            "Password is required.",
        )

    @patch(
        "graphq.accounts.mutations.auth.ObtainJSONWebTokenMutation.check_global_rate_limit"
    )
    @patch(
        "graphq.accounts.mutations.auth.ObtainJSONWebTokenMutation.check_rate_limit"
    )
    @patch(
        "graphq.accounts.mutations.auth.authenticate_credentials"
    )
    def test_invalid_credentials_are_rejected(
        self,
        mock_authenticate,
        mock_rate_limit,
        mock_global_rate_limit,
    ):
        mock_authenticate.return_value = None

        with self.assertRaises(GraphQLError) as exc:
            ObtainJSONWebTokenMutation.mutate_and_get_payload(
                None,
                self.context,
                contact=self.user.email,
                password="wrong-password",
            )

        self.assertEqual(
            str(exc.exception),
            "Invalid credentials.",
        )


# ============================================================================
# REFRESH TOKEN
# ============================================================================


class RefreshTokenMutationTests(
    AuthenticationMutationTestCase,
):
    """
    Tests for refresh-token rotation.

    The GraphQL adapter delegates refresh-token handling to
    ``univa_jwt.authentication.refresh_access_token``.
    """

    @patch(
        "graphq.accounts.mutations.auth.refresh_access_token"
    )
    def test_refresh_rotates_tokens(
        self,
        mock_refresh,
    ):
        mock_refresh.return_value = (
            "new-access",
            "new-refresh",
        )

        result = RefreshTokenMutation.mutate_and_get_payload(
            None,
            self.context,
            refresh_token="old-refresh",
        )

        mock_refresh.assert_called_once_with(
            "old-refresh",
        )

        self.assertEqual(
            result.token,
            "new-access",
        )

        self.assertEqual(
            result.refresh_token,
            "new-refresh",
        )

    def test_requires_refresh_token(self):
        with self.assertRaises(GraphQLError) as exc:
            RefreshTokenMutation.mutate_and_get_payload(
                None,
                self.context,
                refresh_token="",
            )

        self.assertEqual(
            str(exc.exception),
            "Refresh token is required.",
        )


# ============================================================================
# REVOKE ONE REFRESH TOKEN
# ============================================================================


class RevokeTokenMutationTests(
    AuthenticationMutationTestCase,
):
    """
    Tests for single refresh-token revocation.
    """

    @patch(
        "graphq.accounts.mutations.auth.revoke_refresh_token_service"
    )
    def test_revokes_refresh_token(
        self,
        mock_revoke,
    ):
        mock_revoke.return_value = True

        result = RevokeTokenMutation.mutate_and_get_payload(
            None,
            self.context,
            refresh_token="refresh-token",
        )

        mock_revoke.assert_called_once_with(
            "refresh-token",
        )

        self.assertTrue(
            result.success,
        )

    @patch(
        "graphq.accounts.mutations.auth.revoke_refresh_token_service"
    )
    def test_revoke_failure_is_rejected(
        self,
        mock_revoke,
    ):
        mock_revoke.return_value = False

        with self.assertRaises(GraphQLError) as exc:
            RevokeTokenMutation.mutate_and_get_payload(
                None,
                self.context,
                refresh_token="refresh-token",
            )

        self.assertEqual(
            str(exc.exception),
            "Unable to revoke refresh token.",
        )


# ============================================================================
# VERIFY ACCESS TOKEN
# ============================================================================


class VerifyTokenMutationTests(
    AuthenticationMutationTestCase,
):
    """
    Tests for access-token verification.
    """

    @patch(
        "graphq.accounts.mutations.auth.authenticate_access_token_with_claims"
    )
    def test_valid_token_returns_claims(
        self,
        mock_authenticate,
    ):
        now = datetime.now(
            dt_timezone.utc,
        )

        claims = SimpleNamespace(
            user_id=str(
                self.user.pk,
            ),
            jti="test-jti",
            token_type="access",
            issued_at=now,
            expires_at=(
                now
                + timedelta(
                    minutes=15,
                )
            ),
            issuer="univa",
            audience="univa-api",
        )

        mock_authenticate.return_value = (
            self.user,
            claims,
        )

        result = VerifyTokenMutation.mutate_and_get_payload(
            None,
            self.context,
            token="valid-token",
        )

        mock_authenticate.assert_called_once_with(
            "valid-token",
        )

        self.assertTrue(
            result.valid,
        )

        self.assertEqual(
            result.user,
            self.user,
        )

        self.assertEqual(
            result.payload["sub"],
            str(
                self.user.pk,
            ),
        )

        self.assertEqual(
            result.payload["jti"],
            "test-jti",
        )

        self.assertEqual(
            result.payload["token_type"],
            "access",
        )

        self.assertEqual(
            result.payload["iat"],
            int(
                claims.issued_at.timestamp(),
            ),
        )

        self.assertEqual(
            result.payload["exp"],
            int(
                claims.expires_at.timestamp(),
            ),
        )

        self.assertEqual(
            result.payload["iss"],
            "univa",
        )

        self.assertEqual(
            result.payload["aud"],
            "univa-api",
        )

    @patch(
        "graphq.accounts.mutations.auth.authenticate_access_token_with_claims"
    )
    def test_invalid_token_is_returned_as_invalid(
        self,
        mock_authenticate,
    ):
        mock_authenticate.side_effect = ValueError(
            "Token expired.",
        )

        result = VerifyTokenMutation.mutate_and_get_payload(
            None,
            self.context,
            token="expired-token",
        )

        mock_authenticate.assert_called_once_with(
            "expired-token",
        )

        self.assertFalse(
            result.valid,
        )

        self.assertIsNone(
            result.user,
        )

        self.assertIsNone(
            result.expires_at,
        )

        self.assertEqual(
            result.payload,
            {
                "error": "Invalid or expired token.",
            },
        )


# ============================================================================
# LOGOUT
# ============================================================================


class LogoutMutationTests(
    AuthenticationMutationTestCase,
):
    """
    Tests for logout.

    Logout is protected by the production ``login_required`` decorator.

    The refresh-token service is mocked at the GraphQL boundary.
    """

    @patch(
    "graphq.accounts.mutations.auth.user_logged_out.send"
    )
    @patch(
        "graphq.accounts.mutations.auth.revoke_refresh_token"
    )
    @patch(
        "graphq.accounts.mutations.auth.authenticate_refresh_token"
    )
    def test_logout_revokes_refresh_token(
        self,
        mock_authenticate,
        mock_revoke,
        mock_signal,
    ):
        mock_authenticate.return_value = (
            self.user,
            MagicMock(),
        )

        mock_revoke.return_value = True

        result = LogoutMutation.mutate_and_get_payload(
            None,
            self.context,
            refresh_token="refresh-token",
        )

        mock_authenticate.assert_called_once_with(
            "refresh-token",
        )

        mock_revoke.assert_called_once_with(
            "refresh-token",
        )

        mock_signal.assert_called_once()

        self.assertTrue(
            result.success,
        )
# ============================================================================
# REVOKE ALL TOKENS
# ============================================================================


class RevokeAllTokensMutationTests(
    AuthenticationMutationTestCase,
):
    """
    Tests for revoking every active refresh token belonging to
    the authenticated user.
    """

    @patch(
        "graphq.accounts.mutations.auth.revoke_all_for_user"
    )
    def test_revokes_all_tokens(
        self,
        mock_revoke_all,
    ):
        mock_revoke_all.return_value = 3

        result = (
            RevokeAllTokensMutation
            .mutate_and_get_payload(
                None,
                self.context,
            )
        )

        mock_revoke_all.assert_called_once_with(
            user_id=str(
                self.user.pk,
            ),
            token_type=REFRESH_TOKEN,
        )

        self.assertEqual(
            result.revoked_count,
            3,
        )


# ============================================================================
# PASSWORD RESET
# ============================================================================


class PasswordResetMutationTests(
    AuthenticationMutationTestCase,
):
    """
    Tests for Django's password-reset token flow.
    """

    @patch(
        "graphq.accounts.mutations.auth.SendPasswordResetMutation.check_rate_limit"
    )
    def test_unknown_email_returns_success(
        self,
        mock_rate_limit,
    ):
        result = (
            SendPasswordResetMutation
            .mutate_and_get_payload(
                None,
                self.context,
                email="unknown@example.com",
            )
        )

        self.assertTrue(
            result.success,
        )

    @patch(
        "graphq.accounts.mutations.auth.send_mail"
    )
    @patch(
        "graphq.accounts.mutations.auth.SendPasswordResetMutation.check_rate_limit"
    )
    def test_password_reset_sends_email(
        self,
        mock_rate_limit,
        mock_send_mail,
    ):
        result = (
            SendPasswordResetMutation
            .mutate_and_get_payload(
                None,
                self.context,
                email=self.user.email,
            )
        )

        self.assertTrue(
            result.success,
        )

        mock_send_mail.assert_called_once()

        kwargs = mock_send_mail.call_args.kwargs

        self.assertEqual(
            kwargs["recipient_list"],
            [
                self.user.email,
            ],
        )


# ============================================================================
# SEND MAGIC LINK
# ============================================================================


class MagicLinkMutationTests(
    AuthenticationMutationTestCase,
):
    """
    Tests for sending magic links.
    """

    def test_rejects_invalid_channel(self):
        with self.assertRaises(GraphQLError) as exc:
            SendMagicLinkMutation.mutate_and_get_payload(
                None,
                self.context,
                contact=self.user.email,
                channel="carrier_pigeon",
            )

        self.assertEqual(
            str(exc.exception),
            "Invalid magic-link channel.",
        )

    def test_unknown_account_returns_success(self):
        result = SendMagicLinkMutation.mutate_and_get_payload(
            None,
            self.context,
            contact="unknown@example.com",
            channel="email",
        )

        self.assertTrue(
            result.success,
        )

        self.assertIn(
            "If the account exists",
            result.message,
        )

    @patch(
        "graphq.accounts.mutations.auth.send_magic_link_email"
    )
    @patch(
        "graphq.accounts.mutations.auth.MagicLoginToken.create_for_user"
    )
    def test_sends_email_magic_link(
        self,
        mock_create_token,
        mock_send_email,
    ):
        token = MagicMock()

        mock_create_token.return_value = token

        result = SendMagicLinkMutation.mutate_and_get_payload(
            None,
            self.context,
            contact=self.user.email,
            channel="email",
        )

        mock_create_token.assert_called_once()

        mock_send_email.assert_called_once_with(
            self.user,
            token,
        )

        self.assertTrue(
            result.success,
        )

        self.assertEqual(
            result.message,
            "Magic link sent to your email.",
        )


# ============================================================================
# VERIFY MAGIC LINK
# ============================================================================


class VerifyMagicLinkMutationTests(
    AuthenticationMutationTestCase,
):
    """
    Tests for MagicLoginToken validation.
    """

    def test_empty_token_is_invalid(self):
        result = (
            VerifyMagicLinkMutation
            .mutate_and_get_payload(
                None,
                self.context,
                token="",
            )
        )

        self.assertFalse(
            result.valid,
        )

        self.assertEqual(
            result.message,
            "Token is required.",
        )

    @patch(
        "graphq.accounts.mutations.auth.MagicLoginToken.validate_token"
    )
    def test_invalid_magic_link_returns_invalid(
        self,
        mock_validate,
    ):
        mock_validate.side_effect = ValueError(
            "Token expired.",
        )

        result = (
            VerifyMagicLinkMutation
            .mutate_and_get_payload(
                None,
                self.context,
                token="expired-token",
            )
        )

        self.assertFalse(
            result.valid,
        )

        self.assertEqual(
            result.message,
            "Token expired.",
        )


# ============================================================================
# RESEND MAGIC LINK
# ============================================================================


class ResendMagicLinkMutationTests(
    AuthenticationMutationTestCase,
):
    """
    Tests for magic-link resend behavior.
    """

    def test_rejects_invalid_channel(self):
        with self.assertRaises(GraphQLError) as exc:
            ResendMagicLinkMutation.mutate_and_get_payload(
                None,
                self.context,
                contact=self.user.email,
                channel="carrier_pigeon",
            )

        self.assertEqual(
            str(exc.exception),
            "Invalid magic-link channel.",
        )

    def test_unknown_account_returns_success(self):
        result = (
            ResendMagicLinkMutation
            .mutate_and_get_payload(
                None,
                self.context,
                contact="unknown@example.com",
                channel="email",
            )
        )

        self.assertTrue(
            result.success,
        )

        self.assertIn(
            "If the account exists",
            result.message,
        )