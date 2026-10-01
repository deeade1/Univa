"""
Integration tests for the canonical Univa JWT subsystem.

These tests verify that the JWT package works as one security boundary:

    tokens
        │
        ├── claims
        │
        ├── revocation
        │
        └── refresh rotation
                │
                ▼
            middleware

The tests intentionally exercise public APIs rather than private PyJWT
implementation details.

Coverage
--------

- Access-token creation and validation
- Refresh-token creation and validation
- Token-type enforcement
- JWT tampering
- Expiration
- Revocation
- Revocation fail-closed behavior
- Authorization-header parsing
- HTTP authentication
- Anonymous requests
- Invalid credentials
- Inactive/nonexistent users
- Refresh-token rotation
- Refresh-token single-use semantics
- Refresh-token replay detection
- Rotation-storage failure
- Replacement-token issuance failure
- WebSocket authentication
- GraphQL middleware authentication path

Database strategy
-----------------

Normal synchronous integration tests use Django TestCase.

WebSocket middleware tests use TransactionTestCase because Channels'
database_sync_to_async executes synchronous ORM work in a different thread.
Django TestCase's per-test transaction wrapping can leave the connection
unusable from that worker thread.

We therefore deliberately use TransactionTestCase for the actual ASGI
middleware integration tests.

We do NOT force SQLite here. The project uses PostgreSQL/PostGIS and the
Django test database should remain consistent with the application's real
database backend.
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import (
    RequestFactory,
    TestCase,
    TransactionTestCase,
    override_settings,
)

from univa_jwt.constants import ACCESS_TOKEN, REFRESH_TOKEN

from univa_jwt.exceptions import (
    TokenDecodeError,
    TokenExpiredError,
    TokenInvalidError,
    TokenTypeError,
)

from univa_jwt.middleware import (
    JWTAuthenticationError,
    authenticate_request,
    authenticate_token,
    extract_http_token,
    extract_websocket_token,
    is_authenticated,
    parse_authorization_header,
    require_authenticated_user,
)

from univa_jwt.refresh import (
    RefreshTokenInvalidError,
    RefreshTokenReplayError,
    RefreshTokenRotationError,
    RefreshTokenStorageError,
    rotate_refresh_token,
)

from univa_jwt.revocation import (
    RevocationStorageError,
    check_revocation_backend,
    is_jti_revoked,
    is_token_revoked,
    revoke_access_token,
    revoke_claims,
    revoke_refresh_token,
    unrevoke_jti,
)

from univa_jwt.schema.websocket import JWTWebSocketMiddleware

from univa_jwt.tokens import (
    create_access_token,
    create_refresh_token,
    create_token,
    decode_access_token,
    decode_refresh_token,
    decode_token,
    is_token_expired,
    token_remaining_lifetime,
    validate_access_token,
    validate_refresh_token,
    verify_token,
)


User = get_user_model()


# =============================================================================
# Test configuration
# =============================================================================

TEST_CACHE = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "univa-jwt-integration-tests",
    },
}


# =============================================================================
# Base test cases
# =============================================================================


@override_settings(CACHES=TEST_CACHE)
class JWTIntegrationTestCase(TestCase):
    """
    Base test case for synchronous JWT integration tests.

    Django TestCase provides fast isolated database tests using transactions.

    The LocMemCache gives the JWT tests an isolated cache backend while
    preserving Django's cache.add() atomic create-if-absent semantics required
    by refresh-token rotation.
    """

    def setUp(self):
        super().setUp()

        cache.clear()

        self.user = User.objects.create_user(
            email="jwt-test@example.com",
            password="StrongTestPassword123!",
        )

    def tearDown(self):
        cache.clear()
        super().tearDown()


@override_settings(CACHES=TEST_CACHE)
class JWTAsyncIntegrationTestCase(TransactionTestCase):
    """
    Database-safe base class for asynchronous JWT integration tests.

    Channels' database_sync_to_async may execute ORM operations from a worker
    thread. TransactionTestCase is used instead of TestCase so those database
    operations receive a normal usable database connection.

    This class intentionally does not force SQLite. The test suite should use
    the same database backend family as the application, including PostgreSQL
    / PostGIS-specific behavior.
    """

    reset_sequences = False

    def setUp(self):
        super().setUp()

        cache.clear()

        self.user = User.objects.create_user(
            email="jwt-websocket-test@example.com",
            password="StrongTestPassword123!",
        )

    def tearDown(self):
        cache.clear()
        super().tearDown()


# =============================================================================
# Token creation
# =============================================================================


class TokenCreationTests(JWTIntegrationTestCase):
    """Verify canonical JWT creation."""

    def test_create_access_token_returns_token_and_claims(self):
        token, claims = create_access_token(
            user_id=self.user.pk,
        )

        self.assertIsInstance(token, str)
        self.assertTrue(token)

        self.assertEqual(
            str(claims.user_id),
            str(self.user.pk),
        )

        self.assertEqual(
            str(claims.subject),
            str(self.user.pk),
        )

        self.assertEqual(
            claims.token_type,
            ACCESS_TOKEN,
        )

        self.assertTrue(claims.jti)
        self.assertIsNotNone(claims.issued_at)
        self.assertIsNotNone(claims.expires_at)

    def test_create_refresh_token_returns_token_and_claims(self):
        token, claims = create_refresh_token(
            user_id=self.user.pk,
        )

        self.assertIsInstance(token, str)
        self.assertTrue(token)

        self.assertEqual(
            str(claims.user_id),
            str(self.user.pk),
        )

        self.assertEqual(
            claims.token_type,
            REFRESH_TOKEN,
        )

        self.assertTrue(claims.jti)

    def test_access_and_refresh_tokens_have_different_jtis(self):
        access_token, access_claims = create_access_token(
            user_id=self.user.pk,
        )

        refresh_token, refresh_claims = create_refresh_token(
            user_id=self.user.pk,
        )

        self.assertNotEqual(
            access_token,
            refresh_token,
        )

        self.assertNotEqual(
            access_claims.jti,
            refresh_claims.jti,
        )

    def test_create_token_rejects_unknown_token_type(self):
        with self.assertRaises(TokenTypeError):
            create_token(
                user_id=self.user.pk,
                token_type="invalid",
                lifetime=timedelta(minutes=5),
            )


# =============================================================================
# Token validation
# =============================================================================


class TokenValidationTests(JWTIntegrationTestCase):
    """Verify canonical token validation."""

    def test_access_token_round_trips(self):
        token, original_claims = create_access_token(
            user_id=self.user.pk,
        )

        claims = validate_access_token(
            token,
        )

        self.assertEqual(
            claims.user_id,
            original_claims.user_id,
        )

        self.assertEqual(
            claims.jti,
            original_claims.jti,
        )

        self.assertEqual(
            claims.token_type,
            ACCESS_TOKEN,
        )

    def test_refresh_token_round_trips(self):
        token, original_claims = create_refresh_token(
            user_id=self.user.pk,
        )

        claims = validate_refresh_token(
            token,
        )

        self.assertEqual(
            claims.user_id,
            original_claims.user_id,
        )

        self.assertEqual(
            claims.jti,
            original_claims.jti,
        )

        self.assertEqual(
            claims.token_type,
            REFRESH_TOKEN,
        )

    def test_decode_access_token_uses_canonical_validation(self):
        token, _ = create_access_token(
            user_id=self.user.pk,
        )

        claims = decode_access_token(
            token,
        )

        self.assertEqual(
            claims.token_type,
            ACCESS_TOKEN,
        )

    def test_decode_refresh_token_uses_canonical_validation(self):
        token, _ = create_refresh_token(
            user_id=self.user.pk,
        )

        claims = decode_refresh_token(
            token,
        )

        self.assertEqual(
            claims.token_type,
            REFRESH_TOKEN,
        )

    def test_generic_decode_requires_expected_token_type_when_requested(self):
        token, _ = create_access_token(
            user_id=self.user.pk,
        )

        with self.assertRaises(TokenTypeError):
            decode_token(
                token,
                expected_token_type=REFRESH_TOKEN,
            )

    def test_refresh_token_cannot_be_validated_as_access_token(self):
        token, _ = create_refresh_token(
            user_id=self.user.pk,
        )

        with self.assertRaises(TokenTypeError):
            validate_access_token(
                token,
            )

    def test_access_token_cannot_be_validated_as_refresh_token(self):
        token, _ = create_access_token(
            user_id=self.user.pk,
        )

        with self.assertRaises(TokenTypeError):
            validate_refresh_token(
                token,
            )

    def test_tampered_token_is_rejected(self):
        token, _ = create_access_token(
            user_id=self.user.pk,
        )

        parts = token.split(".")

        self.assertEqual(
            len(parts),
            3,
        )

        signature = parts[2]

        replacement = (
            "A"
            if signature[-1] != "A"
            else "B"
        )

        tampered_signature = (
            signature[:-1] + replacement
        )

        tampered_token = ".".join(
            [
                parts[0],
                parts[1],
                tampered_signature,
            ]
        )

        with self.assertRaises(
            (TokenDecodeError, TokenInvalidError)
        ):
            validate_access_token(
                tampered_token,
            )

    def test_empty_token_is_rejected(self):
        with self.assertRaises(TokenInvalidError):
            validate_access_token("")

    def test_non_string_token_is_rejected(self):
        with self.assertRaises(TokenInvalidError):
            validate_access_token(None)  # type: ignore

    def test_verify_token_returns_true_for_valid_access_token(self):
        token, _ = create_access_token(
            user_id=self.user.pk,
        )

        self.assertTrue(
            verify_token(
                token,
                expected_token_type=ACCESS_TOKEN,
            )
        )

    def test_verify_token_returns_false_for_wrong_token_type(self):
        token, _ = create_refresh_token(
            user_id=self.user.pk,
        )

        self.assertFalse(
            verify_token(
                token,
                expected_token_type=ACCESS_TOKEN,
            )
        )


# =============================================================================
# Token lifetime
# =============================================================================


class TokenLifetimeTests(JWTIntegrationTestCase):
    """Verify token expiration helpers."""

    def test_new_token_has_positive_remaining_lifetime(self):
        _, claims = create_access_token(
            user_id=self.user.pk,
        )

        remaining = token_remaining_lifetime(
            claims,
        )

        self.assertGreater(
            remaining,
            0,
        )

    def test_new_token_is_not_expired(self):
        _, claims = create_access_token(
            user_id=self.user.pk,
        )

        self.assertFalse(
            is_token_expired(
                claims,
            )
        )


# =============================================================================
# Revocation
# =============================================================================


class TokenRevocationTests(JWTIntegrationTestCase):
    """Verify server-side JWT revocation."""

    def test_access_token_is_not_revoked_initially(self):
        _, claims = create_access_token(
            user_id=self.user.pk,
        )

        self.assertFalse(
            is_token_revoked(
                claims,
            )
        )

    def test_revoke_access_token_marks_token_revoked(self):
        token, claims = create_access_token(
            user_id=self.user.pk,
        )

        self.assertFalse(
            is_token_revoked(
                claims,
            )
        )

        result = revoke_access_token(
            claims,
        )

        self.assertTrue(result)

        self.assertTrue(
            is_token_revoked(
                claims,
            )
        )

        self.assertTrue(
            is_jti_revoked(
                claims.jti,
            )
        )

        with self.assertRaises(TokenInvalidError):
            validate_access_token(
                token,
            )

    def test_revoke_claims_works_for_access_token(self):
        _, claims = create_access_token(
            user_id=self.user.pk,
        )

        self.assertTrue(
            revoke_claims(
                claims,
            )
        )

        self.assertTrue(
            is_token_revoked(
                claims,
            )
        )

    def test_revoke_refresh_token_marks_refresh_token_revoked(self):
        token, claims = create_refresh_token(
            user_id=self.user.pk,
        )

        self.assertTrue(
            revoke_refresh_token(
                claims,
            )
        )

        self.assertTrue(
            is_token_revoked(
                claims,
            )
        )

        with self.assertRaises(TokenInvalidError):
            validate_refresh_token(
                token,
            )

    def test_revocation_backend_health_check(self):
        self.assertTrue(
            check_revocation_backend()
        )

    @patch(
        "univa_jwt.revocation.cache.get",
        side_effect=Exception("Redis unavailable"),
    )
    def test_revocation_read_failure_raises_storage_error(
        self,
        mocked_get,
    ):
        _, claims = create_access_token(
            user_id=self.user.pk,
        )

        with self.assertRaises(
            RevocationStorageError
        ):
            is_token_revoked(
                claims,
            )

    @patch(
        "univa_jwt.revocation.cache.set",
        side_effect=Exception("Redis unavailable"),
    )
    def test_revocation_write_failure_raises_storage_error(
        self,
        mocked_set,
    ):
        _, claims = create_access_token(
            user_id=self.user.pk,
        )

        with self.assertRaises(
            RevocationStorageError
        ):
            revoke_access_token(
                claims,
            )

    @patch(
        "univa_jwt.tokens._check_revocation",
        side_effect=TokenInvalidError(
            "Unable to verify JWT revocation state."
        ),
    )
    def test_token_validation_fails_closed_when_revocation_is_unavailable(
        self,
        mocked_revocation,
    ):
        token, _ = create_access_token(
            user_id=self.user.pk,
        )

        with self.assertRaises(TokenInvalidError):
            validate_access_token(
                token,
            )


# =============================================================================
# Authorization header parsing
# =============================================================================


class AuthorizationHeaderTests(JWTIntegrationTestCase):
    """Verify strict Bearer-header parsing."""

    def test_missing_header_is_anonymous(self):
        token, supplied = parse_authorization_header(
            None,
        )

        self.assertIsNone(token)
        self.assertFalse(supplied)

    def test_empty_header_is_anonymous(self):
        token, supplied = parse_authorization_header(
            "",
        )

        self.assertIsNone(token)
        self.assertFalse(supplied)

    def test_valid_bearer_header(self):
        token, supplied = parse_authorization_header(
            "Bearer abc123",
        )

        self.assertEqual(
            token,
            "abc123",
        )

        self.assertTrue(
            supplied,
        )

    def test_bearer_scheme_is_case_insensitive(self):
        token, supplied = parse_authorization_header(
            "bEaReR abc123",
        )

        self.assertEqual(
            token,
            "abc123",
        )

        self.assertTrue(
            supplied,
        )

    def test_header_without_two_parts_is_rejected(self):
        with self.assertRaises(
            JWTAuthenticationError
        ):
            parse_authorization_header(
                "Bearer",
            )

    def test_header_with_too_many_parts_is_rejected(self):
        with self.assertRaises(
            JWTAuthenticationError
        ):
            parse_authorization_header(
                "Bearer abc def",
            )

    def test_unsupported_scheme_is_rejected(self):
        with self.assertRaises(
            JWTAuthenticationError
        ):
            parse_authorization_header(
                "Basic abc123",
            )

    def test_missing_bearer_token_is_rejected(self):
        with self.assertRaises(
            JWTAuthenticationError
        ):
            parse_authorization_header(
                "Bearer ",
            )

    def test_bytes_header_is_supported(self):
        token, supplied = parse_authorization_header(
            b"Bearer abc123",
        )

        self.assertEqual(
            token,
            "abc123",
        )

        self.assertTrue(
            supplied,
        )


# =============================================================================
# HTTP authentication
# =============================================================================


class HTTPAuthenticationTests(JWTIntegrationTestCase):
    """Verify Django HTTP authentication."""

    def setUp(self):
        super().setUp()

        self.factory = RequestFactory()

    def _request_with_token(
        self,
        token: str,
    ):
        return self.factory.get(
            "/graphql",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

    def test_request_without_credentials_is_anonymous(self):
        request = self.factory.get(
            "/graphql",
        )

        user = authenticate_request(
            request,
        )

        self.assertFalse(
            is_authenticated(user)
        )

        self.assertTrue(
            hasattr(request, "jwt_claims")
        )

        self.assertIsNone(
            request.jwt_claims
        )

    def test_valid_access_token_authenticates_user(self):
        token, claims = create_access_token(
            user_id=self.user.pk,
        )

        request = self._request_with_token(
            token,
        )

        user = authenticate_request(
            request,
        )

        self.assertEqual(
            user.pk,
            self.user.pk,
        )

        self.assertTrue(
            is_authenticated(user)
        )

        self.assertEqual(
            request.jwt_claims.jti,
            claims.jti,
        )

    def test_invalid_token_is_not_converted_to_anonymous(self):
        request = self._request_with_token(
            "invalid.jwt.token",
        )

        with self.assertRaises(
            JWTAuthenticationError
        ):
            authenticate_request(
                request,
            )

    def test_nonexistent_user_is_rejected(self):
        token, _ = create_access_token(
            user_id=999999999,
        )

        request = self._request_with_token(
            token,
        )

        with self.assertRaises(
            JWTAuthenticationError
        ):
            authenticate_request(
                request,
            )

    def test_inactive_user_is_rejected(self):
        self.user.is_active = False

        self.user.save(
            update_fields=["is_active"]
        )

        token, _ = create_access_token(
            user_id=self.user.pk,
        )

        request = self._request_with_token(
            token,
        )

        with self.assertRaises(
            JWTAuthenticationError
        ):
            authenticate_request(
                request,
            )

    def test_require_authenticated_user_rejects_anonymous_request(
        self,
    ):
        request = self.factory.get(
            "/graphql",
        )

        with self.assertRaises(
            JWTAuthenticationError
        ):
            require_authenticated_user(
                request,
            )

    def test_require_authenticated_user_accepts_valid_user(
        self,
    ):
        token, _ = create_access_token(
            user_id=self.user.pk,
        )

        request = self._request_with_token(
            token,
        )

        user = require_authenticated_user(
            request,
        )

        self.assertEqual(
            user.pk,
            self.user.pk,
        )

    def test_authentication_state_is_reused(self):
        token, _ = create_access_token(
            user_id=self.user.pk,
        )

        request = self._request_with_token(
            token,
        )

        first_user = authenticate_request(
            request,
        )

        with patch(
            "univa_jwt.middleware.extract_http_token"
        ) as mocked_extract:
            second_user = authenticate_request(
                request,
            )

        mocked_extract.assert_not_called()

        self.assertEqual(
            first_user.pk,
            second_user.pk,
        )

    def test_authenticated_request_contains_canonical_claims(
        self,
    ):
        token, claims = create_access_token(
            user_id=self.user.pk,
        )

        request = self._request_with_token(
            token,
        )

        authenticate_request(
            request,
        )

        self.assertEqual(
            request.jwt_claims.jti,
            claims.jti,
        )


# =============================================================================
# Direct authentication
# =============================================================================


class DirectAuthenticationTests(JWTIntegrationTestCase):
    """Verify the canonical authenticate_token() boundary."""

    def test_authenticate_token_returns_user_and_claims(self):
        token, claims = create_access_token(
            user_id=self.user.pk,
        )

        user, resolved_claims = authenticate_token(
            token,
        )

        self.assertEqual(
            user.pk,
            self.user.pk,
        )

        self.assertEqual(
            resolved_claims.jti,
            claims.jti,
        )

    def test_authenticate_token_rejects_refresh_token(self):
        token, _ = create_refresh_token(
            user_id=self.user.pk,
        )

        with self.assertRaises(
            JWTAuthenticationError
        ):
            authenticate_token(
                token,
            )


# =============================================================================
# Refresh-token rotation
# =============================================================================


class RefreshRotationTests(JWTIntegrationTestCase):
    """Verify canonical refresh-token rotation."""

    def test_refresh_token_rotates_successfully(self):
        original_token, original_claims = (
            create_refresh_token(
                user_id=self.user.pk,
            )
        )

        result = rotate_refresh_token(
            original_token,
        )

        self.assertIsNotNone(result)

        self.assertEqual(
            result.previous_refresh_jti,
            original_claims.jti,
        )

        self.assertTrue(
            result.access_token,
        )

        self.assertTrue(
            result.refresh_token,
        )

        self.assertEqual(
            result.access_claims.token_type,
            ACCESS_TOKEN,
        )

        self.assertEqual(
            result.refresh_claims.token_type,
            REFRESH_TOKEN,
        )

    def test_rotation_creates_new_refresh_jti(self):
        original_token, original_claims = (
            create_refresh_token(
                user_id=self.user.pk,
            )
        )

        result = rotate_refresh_token(
            original_token,
        )

        self.assertNotEqual(
            result.refresh_claims.jti,
            original_claims.jti,
        )

    def test_old_refresh_token_is_revoked_after_rotation(self):
        original_token, original_claims = (
            create_refresh_token(
                user_id=self.user.pk,
            )
        )

        rotate_refresh_token(
            original_token,
        )

        self.assertTrue(
            is_jti_revoked(
                original_claims.jti,
            )
        )

        with self.assertRaises(
            TokenInvalidError
        ):
            validate_refresh_token(
                original_token,
            )

    def test_rotated_refresh_token_cannot_be_used_again(
        self,
    ):
        original_token, _ = create_refresh_token(
            user_id=self.user.pk,
        )

        rotate_refresh_token(
            original_token,
        )

        with self.assertRaises(
            RefreshTokenInvalidError
        ):
            rotate_refresh_token(
                original_token,
            )

    def test_rotation_replay_is_detected_when_claim_exists_before_validation_revocation(
        self,
    ):
        """
        Verify that the single-use marker itself prevents reuse.

        The normal second-use path is expected to fail at JWT revocation
        first because the consumed token was revoked. This test explicitly
        removes that revocation marker and verifies that the independent
        rotation marker still detects replay.
        """

        original_token, original_claims = (
            create_refresh_token(
                user_id=self.user.pk,
            )
        )

        first_rotation = rotate_refresh_token(
            original_token,
        )

        self.assertTrue(
            first_rotation.refresh_token
        )

        unrevoke_jti(
            original_claims.jti,
        )

        with self.assertRaises(
            RefreshTokenReplayError
        ):
            rotate_refresh_token(
                original_token,
            )

    def test_rotation_of_already_revoked_refresh_token_fails(
        self,
    ):
        original_token, original_claims = (
            create_refresh_token(
                user_id=self.user.pk,
            )
        )

        revoke_refresh_token(
            original_claims,
        )

        with self.assertRaises(
            RefreshTokenInvalidError
        ):
            rotate_refresh_token(
                original_token,
            )

    @patch(
        "univa_jwt.refresh.cache.add",
        side_effect=Exception("Redis unavailable"),
    )
    def test_rotation_store_failure_fails_closed(
        self,
        mocked_add,
    ):
        token, _ = create_refresh_token(
            user_id=self.user.pk,
        )

        with self.assertRaises(
            RefreshTokenStorageError
        ):
            rotate_refresh_token(
                token,
            )

    @patch(
        "univa_jwt.refresh._revoke_consumed_refresh_token",
        side_effect=RefreshTokenStorageError(
            "Unable to revoke the consumed refresh token."
        ),
    )
    def test_revocation_failure_prevents_token_issuance(
        self,
        mocked_revoke,
    ):
        token, _ = create_refresh_token(
            user_id=self.user.pk,
        )

        with self.assertRaises(
            RefreshTokenStorageError
        ):
            rotate_refresh_token(
                token,
            )

    @patch(
        "univa_jwt.refresh._issue_replacement_tokens",
        side_effect=RefreshTokenRotationError(
            "Token issuance failed"
        ),
    )
    def test_replacement_issuance_failure_fails_closed(
        self,
        mocked_issue,
    ):
        token, claims = create_refresh_token(
            user_id=self.user.pk,
        )

        with self.assertRaises(
            RefreshTokenRotationError
        ):
            rotate_refresh_token(
                token,
            )

        self.assertTrue(
            is_jti_revoked(
                claims.jti,
            )
        )

    def test_rotation_replacement_tokens_belong_to_same_user(
        self,
    ):
        token, _ = create_refresh_token(
            user_id=self.user.pk,
        )

        result = rotate_refresh_token(
            token,
        )

        self.assertEqual(
            str(result.access_claims.user_id),
            str(self.user.pk),
        )

        self.assertEqual(
            str(result.refresh_claims.user_id),
            str(self.user.pk),
        )


# =============================================================================
# WebSocket authentication
# =============================================================================


class WebSocketAuthenticationTests(JWTIntegrationTestCase):
    """Verify WebSocket JWT authentication."""

    def test_websocket_token_extraction(self):
        token, _ = create_access_token(
            user_id=self.user.pk,
        )

        scope = {
            "type": "websocket",
            "headers": [
                (
                    b"authorization",
                    f"Bearer {token}".encode(),
                ),
            ],
        }

        extracted, supplied = extract_websocket_token(
            scope,
        )

        self.assertEqual(
            extracted,
            token,
        )

        self.assertTrue(
            supplied,
        )

    def test_websocket_without_credentials_is_anonymous(self):
        scope = {
            "type": "websocket",
            "headers": [],
        }

        token, supplied = extract_websocket_token(
            scope,
        )

        self.assertIsNone(token)
        self.assertFalse(supplied)

    def test_websocket_query_string_token_is_not_supported(self):
        scope = {
            "type": "websocket",
            "query_string": b"token=some-jwt",
            "headers": [],
        }

        token, supplied = extract_websocket_token(
            scope,
        )

        self.assertIsNone(token)
        self.assertFalse(supplied)

    def test_websocket_invalid_authorization_header_is_rejected(
        self,
    ):
        scope = {
            "type": "websocket",
            "headers": [
                (
                    b"authorization",
                    b"Basic abc123",
                ),
            ],
        }

        with self.assertRaises(
            JWTAuthenticationError
        ):
            extract_websocket_token(
                scope,
            )


# =============================================================================
# WebSocket middleware
# =============================================================================


class JWTWebSocketMiddlewareTests(JWTAsyncIntegrationTestCase):
    """
    Verify the actual ASGI middleware integration.

    IMPORTANT:
        This class uses TransactionTestCase rather than TestCase.

    The JWT middleware authenticates the WebSocket in a synchronous worker
    thread through Channels' database_sync_to_async boundary. TransactionTestCase
    provides normal database connections for this execution model.
    """

    async def _application(
        self,
        scope,
        receive,
        send,
    ):
        self.received_scope = scope

    async def _receive(self):
        return {
            "type": "websocket.connect",
        }

    async def _send(self, message):
        return None

    async def test_authenticated_websocket_scope_contains_user_and_claims(
        self,
    ):
        token, claims = create_access_token(
            user_id=self.user.pk,
        )

        scope = {
            "type": "websocket",
            "headers": [
                (
                    b"authorization",
                    f"Bearer {token}".encode(),
                ),
            ],
        }

        middleware = JWTWebSocketMiddleware(
            self._application,
        )

        await middleware(
            scope,
            self._receive,
            self._send,
        )

        self.assertEqual(
            self.received_scope["user"].pk,
            self.user.pk,
        )

        self.assertEqual(
            self.received_scope["univa_jwt"].jti,
            claims.jti,
        )

    async def test_anonymous_websocket_scope_contains_anonymous_user(
        self,
    ):
        from univa_jwt.middleware import JWT_CLAIMS_ATTRIBUTE

        scope = {
            "type": "websocket",
            "headers": [],
        }

        middleware = JWTWebSocketMiddleware(
            self._application,
        )

        await middleware(
            scope,
            self._receive,
            self._send,
        )

        self.assertFalse(
            self.received_scope["user"].is_authenticated
        )

        self.assertIsNone(
            self.received_scope.get(
                JWT_CLAIMS_ATTRIBUTE
            )
        )

    async def test_invalid_websocket_token_is_rejected(
        self,
    ):
        scope = {
            "type": "websocket",
            "headers": [
                (
                    b"authorization",
                    b"Bearer invalid.jwt.token",
                ),
            ],
        }

        middleware = JWTWebSocketMiddleware(
            self._application,
        )

        with self.assertRaises(
            JWTAuthenticationError
        ):
            await middleware(
                scope,
                self._receive,
                self._send,
            )


# =============================================================================
# GraphQL authentication middleware
# =============================================================================


class GraphQLAuthenticationMiddlewareTests(
    JWTIntegrationTestCase,
):
    """
    Verify that the GraphQL middleware delegates authentication to
    authenticate_request() rather than implementing another JWT path.
    """

    def test_graphql_middleware_calls_canonical_authentication(
        self,
    ):
        from univa_jwt.schema.middleware import (
            JWTAuthMiddleware,
        )

        token, claims = create_access_token(
            user_id=self.user.pk,
        )

        request = RequestFactory().get(
            "/graphql",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        class Info:
            context = request

        middleware = JWTAuthMiddleware()

        with patch(
            "univa_jwt.schema.middleware.authenticate_request",
            wraps=authenticate_request,
        ) as mocked_authenticate:
            result = middleware.resolve(
                lambda root, info, **kwargs: info.context.user,
                None,
                Info(),
            )

        mocked_authenticate.assert_called_once_with(
            request,
        )

        self.assertEqual(
            result.pk,
            self.user.pk,
        )

        self.assertEqual(
            request.jwt_claims.jti,
            claims.jti,
        )

    def test_graphql_middleware_allows_anonymous_request(
        self,
    ):
        from univa_jwt.schema.middleware import (
            JWTAuthMiddleware,
        )

        request = RequestFactory().get(
            "/graphql",
        )

        class Info:
            context = request

        middleware = JWTAuthMiddleware()

        result = middleware.resolve(
            lambda root, info, **kwargs: info.context.user,
            None,
            Info(),
        )

        self.assertFalse(
            result.is_authenticated
        )

    def test_graphql_middleware_does_not_swallow_invalid_credentials(
        self,
    ):
        from univa_jwt.schema.middleware import (
            JWTAuthMiddleware,
        )

        request = RequestFactory().get(
            "/graphql",
            HTTP_AUTHORIZATION="Bearer invalid.jwt.token",
        )

        class Info:
            context = request

        middleware = JWTAuthMiddleware()

        with self.assertRaises(
            JWTAuthenticationError
        ):
            middleware.resolve(
                lambda root, info, **kwargs: info.context.user,
                None,
                Info(),
            )


# =============================================================================
# Cross-boundary invariants
# =============================================================================


class JWTBoundaryInvariantTests(JWTIntegrationTestCase):
    """
    Tests that enforce architectural invariants across the package.
    """

    def test_access_token_created_by_tokens_is_accepted_by_middleware(
        self,
    ):
        token, _ = create_access_token(
            user_id=self.user.pk,
        )

        request = RequestFactory().get(
            "/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        user = authenticate_request(
            request,
        )

        self.assertEqual(
            user.pk,
            self.user.pk,
        )

    def test_refresh_token_created_by_tokens_is_accepted_by_refresh_service(
        self,
    ):
        token, _ = create_refresh_token(
            user_id=self.user.pk,
        )

        result = rotate_refresh_token(
            token,
        )

        self.assertEqual(
            result.access_claims.token_type,
            ACCESS_TOKEN,
        )

        self.assertEqual(
            result.refresh_claims.token_type,
            REFRESH_TOKEN,
        )

    def test_revoked_access_token_fails_every_authentication_boundary(
        self,
    ):
        token, claims = create_access_token(
            user_id=self.user.pk,
        )

        revoke_access_token(
            claims,
        )

        with self.assertRaises(
            TokenInvalidError
        ):
            validate_access_token(
                token,
            )

        with self.assertRaises(
            JWTAuthenticationError
        ):
            authenticate_token(
                token,
            )

        request = RequestFactory().get(
            "/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        with self.assertRaises(
            JWTAuthenticationError
        ):
            authenticate_request(
                request,
            )

    def test_refresh_rotation_invalidates_original_token_across_token_boundary(
        self,
    ):
        token, claims = create_refresh_token(
            user_id=self.user.pk,
        )

        result = rotate_refresh_token(
            token,
        )

        self.assertEqual(
            result.previous_refresh_jti,
            claims.jti,
        )

        self.assertTrue(
            is_jti_revoked(
                claims.jti,
            )
        )

        with self.assertRaises(
            TokenInvalidError
        ):
            validate_refresh_token(
                token,
            )

        with self.assertRaises(
            RefreshTokenInvalidError
        ):
            rotate_refresh_token(
                token,
            )

    def test_new_refresh_token_from_rotation_is_valid(self):
        token, _ = create_refresh_token(
            user_id=self.user.pk,
        )

        result = rotate_refresh_token(
            token,
        )

        claims = validate_refresh_token(
            result.refresh_token,
        )

        self.assertEqual(
            claims.jti,
            result.refresh_claims.jti,
        )

        self.assertEqual(
            claims.token_type,
            REFRESH_TOKEN,
        )

    def test_new_access_token_from_rotation_is_valid(self):
        token, _ = create_refresh_token(
            user_id=self.user.pk,
        )

        result = rotate_refresh_token(
            token,
        )

        claims = validate_access_token(
            result.access_token,
        )

        self.assertEqual(
            claims.jti,
            result.access_claims.jti,
        )

        self.assertEqual(
            claims.token_type,
            ACCESS_TOKEN,
        )