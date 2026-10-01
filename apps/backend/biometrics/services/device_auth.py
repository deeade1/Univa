# apps/backend/biometrics/services/device_auth.py

"""
Biometric device authentication service.

This service owns cryptographic verification of device signatures.

Architecture
------------

GraphQL
    │
    ▼
biometrics.services.device_auth
    │
    ├── cryptographic verification
    ├── public key management
    ├── challenge validation
    └── device authentication

This module deliberately does NOT:

    - issue JWTs
    - authenticate Django users
    - access GraphQL
    - raise GraphQLError
    - perform database queries for authentication
    - contain GraphQL mutation logic
    - fabricate successful verification results
"""

from __future__ import annotations

import base64
import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa, padding
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


# ============================================================================
# CONSTANTS
# ============================================================================

CHALLENGE_TIMEOUT_SECONDS = 300  # 5 minutes
MAX_VERIFICATION_ATTEMPTS = 3
LOCKOUT_DURATION_MINUTES = 15


# ============================================================================
# EXCEPTIONS
# ============================================================================


class DeviceAuthError(Exception):
    """Base exception for device authentication failures."""


class InvalidPublicKey(DeviceAuthError):
    """Raised when the public key is invalid or malformed."""


class InvalidSignatureError(DeviceAuthError):
    """Raised when the signature verification fails."""


class ChallengeExpiredError(DeviceAuthError):
    """Raised when the challenge has expired."""


class ChallengeNotFoundError(DeviceAuthError):
    """Raised when the challenge is not found in cache."""


class DeviceLockedError(DeviceAuthError):
    """Raised when the device is locked due to too many failed attempts."""


# ============================================================================
# RESULT TYPES
# ============================================================================


@dataclass(frozen=True)
class DeviceAuthResult:
    """
    Result of a device authentication operation.

    Attributes:
        verified: Whether the authentication was successful.
        user_id: The authenticated user's ID if successful.
        device_id: The authenticated device ID.
        message: Optional message describing the result.
        requires_retry: Whether the user should retry.
        lockout_until: When the device lockout expires, if applicable.
    """

    verified: bool
    user_id: Optional[int] = None
    device_id: Optional[str] = None
    message: str = ""
    requires_retry: bool = False
    lockout_until: Optional[datetime] = None


# ============================================================================
# PUBLIC KEY VALIDATION
# ============================================================================


def validate_public_key(public_key_pem: str) -> bool:
    """
    Validate that a public key is properly formatted and usable.

    Args:
        public_key_pem: PEM-encoded public key string.

    Returns:
        True if the public key is valid, False otherwise.

    Raises:
        InvalidPublicKey: If the public key is invalid.
    """
    if not public_key_pem:
        raise InvalidPublicKey("Public key is required.")

    if not public_key_pem.strip().startswith("-----BEGIN"):
        raise InvalidPublicKey("Public key must be in PEM format.")

    try:
        load_pem_public_key(public_key_pem.encode("utf-8"))
        return True
    except ValueError as exc:
        raise InvalidPublicKey(f"Invalid public key format: {exc}") from exc


def get_key_type(public_key_pem: str) -> str:
    """
    Get the type of public key (RSA, EC, etc.)

    Args:
        public_key_pem: PEM-encoded public key string.

    Returns:
        String indicating the key type.

    Raises:
        InvalidPublicKey: If the public key is invalid.
    """
    try:
        key = load_pem_public_key(public_key_pem.encode("utf-8"))

        if isinstance(key, rsa.RSAPublicKey):
            return "RSA"
        elif isinstance(key, ec.EllipticCurvePublicKey):
            return "EC"
        else:
            return "Unknown"
    except ValueError as exc:
        raise InvalidPublicKey(f"Invalid public key: {exc}") from exc


# ============================================================================
# CHALLENGE MANAGEMENT
# ============================================================================


def generate_challenge(device_id: str) -> str:
    """
    Generate a cryptographic challenge for device authentication.

    Args:
        device_id: The device ID to generate a challenge for.

    Returns:
        A unique challenge string.

    The challenge is stored in cache with a timeout to prevent replay attacks.
    """
    # Generate a random challenge
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(
            f"{device_id}{timezone.now().isoformat()}".encode()
        ).digest()
    ).decode()

    # Store the challenge in cache with timeout
    cache_key = f"biometric_challenge:{device_id}"
    cache.set(cache_key, challenge, timeout=CHALLENGE_TIMEOUT_SECONDS)

    logger.info("Generated challenge for device: %s", device_id)

    return challenge


def validate_challenge(device_id: str, challenge: str) -> bool:
    """
    Validate that a challenge exists and hasn't expired.

    Args:
        device_id: The device ID.
        challenge: The challenge to validate.

    Returns:
        True if the challenge is valid, False otherwise.

    Raises:
        ChallengeNotFoundError: If the challenge is not found in cache.
        ChallengeExpiredError: If the challenge has expired.
    """
    cache_key = f"biometric_challenge:{device_id}"
    stored_challenge = cache.get(cache_key)

    if stored_challenge is None:
        raise ChallengeNotFoundError(
            "Challenge not found or already used."
        )

    if stored_challenge != challenge:
        return False

    # Challenge is valid, delete it to prevent replay
    cache.delete(cache_key)

    return True


# ============================================================================
# SIGNATURE VERIFICATION
# ============================================================================


def verify_signature(
    public_key_pem: str,
    challenge: str,
    signature: str,
) -> bool:
    """
    Verify a device's cryptographic signature.

    Args:
        public_key_pem: PEM-encoded public key.
        challenge: The challenge that was signed.
        signature: Base64-encoded signature.

    Returns:
        True if signature is valid, False otherwise.

    Raises:
        InvalidSignatureError: If the signature is invalid.
        InvalidPublicKey: If the public key is invalid.
    """
    try:
        # Decode the signature
        signature_bytes = base64.b64decode(signature)

        # Load the public key
        public_key = load_pem_public_key(public_key_pem.encode("utf-8"))

        # Hash the challenge
        challenge_bytes = challenge.encode("utf-8")

        # Verify based on key type
        if isinstance(public_key, rsa.RSAPublicKey):
            # RSA verification with PKCS1v15 padding
            public_key.verify(
                signature_bytes,
                challenge_bytes,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
        elif isinstance(public_key, ec.EllipticCurvePublicKey):
            # EC verification with ECDSA
            public_key.verify(
                signature_bytes,
                challenge_bytes,
                ec.ECDSA(hashes.SHA256()),
            )
        else:
            raise InvalidSignatureError(
                f"Unsupported key type: {type(public_key)}"
            )

        logger.debug("Signature verification successful")
        return True

    except InvalidSignature as exc:
        raise InvalidSignatureError("Invalid cryptographic signature.") from exc

    except (ValueError, TypeError) as exc:
        raise InvalidPublicKey(f"Invalid public key: {exc}") from exc

    except Exception as exc:
        logger.exception("Unexpected error during signature verification")
        raise InvalidSignatureError(f"Signature verification failed: {exc}") from exc


# ============================================================================
# DEVICE AUTHENTICATION
# ============================================================================


def authenticate_device(
    device_id: str,
    public_key_pem: str,
    challenge: str,
    signature: str,
    *,
    max_attempts: int = MAX_VERIFICATION_ATTEMPTS,
    lockout_minutes: int = LOCKOUT_DURATION_MINUTES,
) -> DeviceAuthResult:
    """
    Authenticate a device using cryptographic signature verification.

    Args:
        device_id: The device ID.
        public_key_pem: PEM-encoded public key.
        challenge: The challenge that was signed.
        signature: Base64-encoded signature.
        max_attempts: Maximum failed attempts before lockout.
        lockout_minutes: Lockout duration in minutes.

    Returns:
        DeviceAuthResult indicating success or failure.

    This function performs the complete device authentication flow:
        1. Validates the public key
        2. Checks for device lockout
        3. Validates the challenge
        4. Verifies the signature
        5. Records attempts
    """
    # Validate public key
    try:
        validate_public_key(public_key_pem)
    except InvalidPublicKey as exc:
        return DeviceAuthResult(
            verified=False,
            device_id=device_id,
            message=str(exc),
            requires_retry=False,
        )

    # Check for lockout
    lockout_key = f"biometric_lockout:{device_id}"
    lockout_until = cache.get(lockout_key)

    if lockout_until:
        lockout_time = datetime.fromisoformat(lockout_until)
        if timezone.now() < lockout_time:
            return DeviceAuthResult(
                verified=False,
                device_id=device_id,
                message=f"Device locked until {lockout_time}",
                requires_retry=False,
                lockout_until=lockout_time,
            )
        else:
            # Lockout expired, clear it
            cache.delete(lockout_key)

    # Validate challenge
    try:
        if not validate_challenge(device_id, challenge):
            return DeviceAuthResult(
                verified=False,
                device_id=device_id,
                message="Invalid challenge.",
                requires_retry=True,
            )
    except ChallengeNotFoundError as exc:
        return DeviceAuthResult(
            verified=False,
            device_id=device_id,
            message=str(exc),
            requires_retry=False,
        )

    # Verify signature
    try:
        verify_signature(public_key_pem, challenge, signature)

        # Success - clear any attempt tracking
        attempts_key = f"biometric_attempts:{device_id}"
        cache.delete(attempts_key)

        return DeviceAuthResult(
            verified=True,
            device_id=device_id,
            message="Device authentication successful.",
        )

    except InvalidSignatureError as exc:
        # Record failed attempt
        attempts_key = f"biometric_attempts:{device_id}"
        attempts = cache.get(attempts_key, 0) + 1
        cache.set(attempts_key, attempts, timeout=3600)  # 1 hour expiry

        if attempts >= max_attempts:
            lockout_time = timezone.now() + timedelta(minutes=lockout_minutes)
            cache.set(
                lockout_key,
                lockout_time.isoformat(),
                timeout=lockout_minutes * 60,
            )

            logger.warning(
                "Device locked due to too many failed attempts: %s",
                device_id,
            )

            return DeviceAuthResult(
                verified=False,
                device_id=device_id,
                message=f"Device locked for {lockout_minutes} minutes.",
                requires_retry=False,
                lockout_until=lockout_time,
            )

        return DeviceAuthResult(
            verified=False,
            device_id=device_id,
            message=str(exc),
            requires_retry=True,
        )

    except InvalidPublicKey as exc:
        return DeviceAuthResult(
            verified=False,
            device_id=device_id,
            message=str(exc),
            requires_retry=False,
        )

    except Exception as exc:
        logger.exception("Unexpected device authentication error: %s", exc)
        return DeviceAuthResult(
            verified=False,
            device_id=device_id,
            message="Device authentication failed.",
            requires_retry=False,
        )


# ============================================================================
# DEVICE CHALLENGE HELPERS
# ============================================================================


def get_challenge_for_device(device_id: str) -> dict:
    """
    Get a challenge for a device ID.

    Args:
        device_id: The device ID.

    Returns:
        Dictionary containing the challenge and expiry information.

    This is intended for the GraphQL mutation that generates challenges.
    """
    challenge = generate_challenge(device_id)

    return {
        "challenge": challenge,
        "expires_in_seconds": CHALLENGE_TIMEOUT_SECONDS,
    }


def revoke_device_challenge(device_id: str) -> bool:
    """
    Revoke any pending challenge for a device.

    Args:
        device_id: The device ID.

    Returns:
        True if a challenge was revoked, False otherwise.
    """
    cache_key = f"biometric_challenge:{device_id}"
    if cache.get(cache_key):
        cache.delete(cache_key)
        return True
    return False


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "DeviceAuthError",
    "InvalidPublicKey",
    "InvalidSignatureError",
    "ChallengeExpiredError",
    "ChallengeNotFoundError",
    "DeviceLockedError",
    "DeviceAuthResult",
    "validate_public_key",
    "get_key_type",
    "generate_challenge",
    "validate_challenge",
    "verify_signature",
    "authenticate_device",
    "get_challenge_for_device",
    "revoke_device_challenge",
    "CHALLENGE_TIMEOUT_SECONDS",
    "MAX_VERIFICATION_ATTEMPTS",
    "LOCKOUT_DURATION_MINUTES",
]