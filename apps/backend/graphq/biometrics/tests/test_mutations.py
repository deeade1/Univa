"""
Tests for GraphQL biometric mutations.

These tests focus on the mutation-layer security contract.

The biometric device authentication mutation is intentionally
fail-closed until a real cryptographic signature verification
service is implemented.

Architecture under test:

    GraphQL mutation
        |
        +-- input validation
        +-- rate limiting
        +-- device lookup
        +-- trust validation
        +-- public-key validation
        |
        +-- cryptographic verification service
                |
                X  NOT IMPLEMENTED YET

Therefore the current expected behavior for a trusted device is:

    GraphQLError(
        "Biometric device signature verification is not configured."
    )
"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from graphql import GraphQLError

from biometrics.models import BiometricDevice
from graphq.biometrics.mutations import (
    BiometricAuthMutation,
)


pytestmark = pytest.mark.django_db


# ============================================================================
# HELPERS
# ============================================================================


def make_user():
    """
    Create a minimal authenticated user for mutation tests.

    Uses the project's configured custom User model and manager.
    """

    User = get_user_model()

    return User.objects.create_user(
        email="biometric-test@example.com",
        password="StrongTestPassword123!",
    )


def make_info(*, user=None):
    """
    Build the minimal GraphQL info/context object required by the
    mutation under test.
    """

    context = SimpleNamespace(
        user=user,
        FILES={},
    )

    return SimpleNamespace(
        context=context,
    )


def call_biometric_auth(
    *,
    info,
    device_id="device-001",
    signature="test-signature",
    challenge="test-challenge",
):
    """
    Call BiometricAuthMutation directly.

    Direct mutation testing is useful here because we are testing
    the mutation's security contract independently from GraphQL
    schema wiring.
    """

    return BiometricAuthMutation.mutate_and_get_payload(
        None,
        info,
        device_id=device_id,
        signature=signature,
        challenge=challenge,
    )


# ============================================================================
# INPUT VALIDATION
# ============================================================================


class TestBiometricAuthInputValidation:
    """
    Input validation tests for BiometricAuthMutation.
    """

    def test_requires_device_id(self):
        """
        device_id must be supplied.
        """

        info = make_info()

        with pytest.raises(GraphQLError) as exc_info:
            call_biometric_auth(
                info=info,
                device_id="",
            )

        assert str(exc_info.value) == (
            "Device ID is required."
        )

    def test_requires_signature(self):
        """
        signature must be supplied.
        """

        info = make_info()

        with pytest.raises(GraphQLError) as exc_info:
            call_biometric_auth(
                info=info,
                signature="",
            )

        assert str(exc_info.value) == (
            "Signature is required."
        )

    def test_requires_challenge(self):
        """
        challenge must be supplied.
        """

        info = make_info()

        with pytest.raises(GraphQLError) as exc_info:
            call_biometric_auth(
                info=info,
                challenge="",
            )

        assert str(exc_info.value) == (
            "Challenge is required."
        )


# ============================================================================
# DEVICE LOOKUP
# ============================================================================


class TestBiometricAuthDeviceValidation:
    """
    Tests for registered/trusted biometric devices.
    """

    def test_rejects_unknown_device(self):
        """
        An unknown device must never reach signature verification.
        """

        info = make_info()

        with patch.object(
            BiometricAuthMutation,
            "check_rate_limit",
        ), patch.object(
            BiometricAuthMutation,
            "check_global_rate_limit",
        ):
            with pytest.raises(GraphQLError) as exc_info:
                call_biometric_auth(
                    info=info,
                    device_id="unknown-device",
                )

        assert str(exc_info.value) == (
            "Device not registered or not trusted."
        )

    def test_rejects_untrusted_device(self):
        """
        A registered but untrusted device must be rejected.
        """

        user = make_user()

        BiometricDevice.objects.create(
            user=user,
            device_id="untrusted-device",
            public_key="public-key",
            trusted=False,
        )

        info = make_info()

        with patch.object(
            BiometricAuthMutation,
            "check_rate_limit",
        ), patch.object(
            BiometricAuthMutation,
            "check_global_rate_limit",
        ):
            with pytest.raises(GraphQLError) as exc_info:
                call_biometric_auth(
                    info=info,
                    device_id="untrusted-device",
                )

        assert str(exc_info.value) == (
            "Device not registered or not trusted."
        )

    def test_rejects_trusted_device_without_public_key(self):
        """
        A trusted device without a public key must be rejected.

        The public key is required before cryptographic verification
        can even be attempted.
        """

        user = make_user()

        BiometricDevice.objects.create(
            user=user,
            device_id="missing-key-device",
            public_key="",
            trusted=True,
        )

        info = make_info()

        with patch.object(
            BiometricAuthMutation,
            "check_rate_limit",
        ), patch.object(
            BiometricAuthMutation,
            "check_global_rate_limit",
        ):
            with pytest.raises(GraphQLError) as exc_info:
                call_biometric_auth(
                    info=info,
                    device_id="missing-key-device",
                )

        assert str(exc_info.value) == (
            "Device has no registered public key."
        )


# ============================================================================
# FAIL-CLOSED SECURITY CONTRACT
# ============================================================================


class TestBiometricAuthFailClosed:
    """
    Security tests proving that BiometricAuthMutation does not
    authenticate a device without real cryptographic verification.
    """

    def test_trusted_device_fails_closed_until_signature_verification_exists(self):
        """
        A valid-looking trusted device must NOT authenticate yet.

        This is the most important test in the current implementation.

        The mutation must fail closed rather than doing something
        insecure such as:

            return True

        or issuing JWTs without verifying the signature.
        """

        user = make_user()

        BiometricDevice.objects.create(
            user=user,
            device_id="trusted-device",
            public_key="-----BEGIN PUBLIC KEY-----\n"
            "TEST-PUBLIC-KEY\n"
            "-----END PUBLIC KEY-----",
            trusted=True,
        )

        info = make_info()

        with patch.object(
            BiometricAuthMutation,
            "check_rate_limit",
        ), patch.object(
            BiometricAuthMutation,
            "check_global_rate_limit",
        ):
            with pytest.raises(GraphQLError) as exc_info:
                call_biometric_auth(
                    info=info,
                    device_id="trusted-device",
                    signature="fake-signature",
                    challenge="fake-challenge",
                )

        assert str(exc_info.value) == (
            "Biometric device signature verification is not configured."
        )

    def test_trusted_device_does_not_issue_tokens(self):
        """
        A trusted device must not receive JWTs while cryptographic
        verification is unavailable.
        """

        user = make_user()

        BiometricDevice.objects.create(
            user=user,
            device_id="trusted-device",
            public_key="test-public-key",
            trusted=True,
        )

        info = make_info()

        with patch.object(
            BiometricAuthMutation,
            "check_rate_limit",
        ), patch.object(
            BiometricAuthMutation,
            "check_global_rate_limit",
        ), patch.object(
            BiometricAuthMutation,
            "generate_tokens",
        ) as generate_tokens:

            with pytest.raises(GraphQLError):
                call_biometric_auth(
                    info=info,
                    device_id="trusted-device",
                    signature="fake-signature",
                    challenge="fake-challenge",
                )

            generate_tokens.assert_not_called()


# ============================================================================
# RATE LIMITING
# ============================================================================


class TestBiometricAuthRateLimiting:
    """
    Verify that biometric authentication invokes both rate-limit
    layers before device authentication.
    """

    def test_rate_limits_are_checked(self):
        """
        Both local/device and global authentication rate limits
        must be invoked.
        """

        user = make_user()

        BiometricDevice.objects.create(
            user=user,
            device_id="rate-limit-device",
            public_key="test-public-key",
            trusted=True,
        )

        info = make_info()

        with patch.object(
            BiometricAuthMutation,
            "check_rate_limit",
        ) as check_rate_limit, patch.object(
            BiometricAuthMutation,
            "check_global_rate_limit",
        ) as check_global_rate_limit:

            with pytest.raises(GraphQLError) as exc_info:
                call_biometric_auth(
                    info=info,
                    device_id="rate-limit-device",
                )

        assert str(exc_info.value) == (
            "Biometric device signature verification is not configured."
        )

        check_rate_limit.assert_called_once_with(
            "biometric_auth:rate-limit-device",
            limit=3,
            window=300,
        )

        check_global_rate_limit.assert_called_once_with(
            info.context,
            "biometric_auth",
            limit=15,
            window=3600,
        )