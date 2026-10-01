"""
Canonical refresh-token rotation service for Univa.

This module owns refresh-token rotation.

Responsibilities
----------------

    - Validate refresh JWTs through univa_jwt.tokens.
    - Enforce refresh-token type.
    - Detect revoked refresh tokens.
    - Enforce single-use refresh-token rotation.
    - Atomically claim a refresh-token JTI before rotation.
    - Revoke the consumed refresh token.
    - Issue a new access token.
    - Issue a new refresh token.
    - Detect replay attempts.
    - Fail closed when the rotation store is unavailable.

Architecture
------------

    GraphQL / HTTP
            │
            ▼
        refresh.py
            │
            ├── validate_refresh_token()
            │
            ├── atomic rotation claim
            │
            ├── revoke_refresh_token()
            │
            ├── create_access_token()
            │
            └── create_refresh_token()
                    │
                    ▼
                tokens.py
                    │
                    ▼
                  PyJWT


Security model
--------------

Refresh tokens are single-use.

For a refresh token with JTI:

    RT-A

the first successful rotation:

    RT-A
      │
      ├── validated
      ├── atomically claimed
      ├── revoked
      └── replaced by RT-B

A second request using RT-A is a replay:

    RT-A
      │
      └── rotation claim already exists
              │
              ▼
        RefreshTokenReplayError


IMPORTANT

The rotation marker is claimed BEFORE replacement credentials are
issued.

Once the marker has been successfully claimed, the old refresh token
is considered consumed.

If a later operation fails, the marker is intentionally NOT removed.

This is fail-closed behavior.

Removing the marker after an ambiguous failure could allow the old
refresh token to be reused and could permit multiple credential pairs
to be issued from the same refresh token.

JWT cryptography is NOT implemented here.

All JWT validation is delegated to:

    univa_jwt.tokens

This module operates only on validated TokenClaims after the raw JWT
has crossed the canonical validation boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from django.core.cache import cache

from .constants import REFRESH_TOKEN
from .exceptions import (
    TokenDecodeError,
    TokenExpiredError,
    TokenInvalidError,
    TokenTypeError,
)
from .revocation import (
    RevocationConfigurationError,
    RevocationStorageError,
    revoke_refresh_token,
)
from .tokens import (
    create_access_token,
    create_refresh_token,
    validate_refresh_token,
)


# =============================================================================
# Configuration
# =============================================================================

ROTATION_CACHE_PREFIX = "univa:jwt:refresh:rotated"

MIN_ROTATION_TTL = 1

MAX_ROTATION_TTL = 60 * 60 * 24 * 365 * 10  # 10 years


# =============================================================================
# Exceptions
# =============================================================================


class RefreshTokenError(Exception):
    """
    Base exception for refresh-token failures.
    """


class RefreshTokenInvalidError(RefreshTokenError):
    """
    Raised when a refresh token cannot be authenticated or does not
    satisfy the canonical refresh-token requirements.
    """


class RefreshTokenReplayError(RefreshTokenError):
    """
    Raised when a previously consumed refresh token is presented again.
    """


class RefreshTokenRotationError(RefreshTokenError):
    """
    Raised when rotation cannot be completed safely.
    """


class RefreshTokenStorageError(RefreshTokenRotationError):
    """
    Raised when the rotation/revocation storage layer is unavailable.

    Rotation must fail closed in this situation.
    """


# =============================================================================
# Result object
# =============================================================================


@dataclass(frozen=True, slots=True)
class RefreshTokenRotation:
    """
    Result of a successful refresh-token rotation.
    """

    access_token: str
    refresh_token: str
    access_claims: Any
    refresh_claims: Any
    previous_refresh_jti: str


# =============================================================================
# Internal helpers
# =============================================================================


def _utc_now() -> datetime:
    """
    Return the current timezone-aware UTC time.
    """

    return datetime.now(timezone.utc)


def _rotation_cache_key(jti: Any) -> str:
    """
    Build the canonical cache key for a refresh-token rotation marker.
    """

    if jti is None:
        raise RefreshTokenInvalidError(
            "Refresh token does not contain a JTI."
        )

    normalized = str(jti).strip()

    if not normalized:
        raise RefreshTokenInvalidError(
            "Refresh token contains an empty JTI."
        )

    return f"{ROTATION_CACHE_PREFIX}:{normalized}"

def _get_user_id(claims: Any) -> str:
    """
    Extract the canonical user ID from validated TokenClaims.

    TokenClaims exposes the JWT `sub` claim through the `user_id`
    attribute. Refresh-token services must consume that canonical
    contract rather than accessing raw JWT claim names.
    """

    user_id = getattr(
        claims,
        "user_id",
        None,
    )

    if user_id is None:
        raise RefreshTokenInvalidError(
            "Refresh token does not contain a user ID."
        )

    user_id = str(user_id).strip()

    if not user_id:
        raise RefreshTokenInvalidError(
            "Refresh token contains an empty user ID."
        )

    return user_id
def _get_jti(claims: Any) -> str:
    """
    Extract the canonical JTI from validated TokenClaims.
    """

    jti = getattr(
        claims,
        "jti",
        None,
    )

    if jti is None:
        raise RefreshTokenInvalidError(
            "Refresh token does not contain a JTI."
        )

    if not isinstance(jti, str):
        raise RefreshTokenInvalidError(
            "Refresh token JTI must be a string."
        )

    normalized = jti.strip()

    if not normalized:
        raise RefreshTokenInvalidError(
            "Refresh token contains an empty JTI."
        )

    return normalized


def _get_expiration(claims: Any) -> datetime:
    """
    Extract and normalize the expiration timestamp from validated
    TokenClaims.

    Canonical TokenClaims exposes ``expires_at`` as a Unix timestamp.

    This helper intentionally accepts only the canonical numeric form.
    """

    expires_at = getattr(
        claims,
        "expires_at",
        None,
    )

    if expires_at is None:
        raise RefreshTokenInvalidError(
            "Refresh token does not contain an expiration time."
        )

    if isinstance(expires_at, bool):
        raise RefreshTokenInvalidError(
            "Refresh token expiration is invalid."
        )

    if isinstance(expires_at, datetime):
        # Defensive compatibility for older TokenClaims implementations.
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(
                tzinfo=timezone.utc,
            )

        return expires_at.astimezone(
            timezone.utc,
        )

    try:
        timestamp = int(expires_at)
    except (TypeError, ValueError) as exc:
        raise RefreshTokenInvalidError(
            "Refresh token expiration is invalid."
        ) from exc

    if timestamp <= 0:
        raise RefreshTokenInvalidError(
            "Refresh token expiration is invalid."
        )

    try:
        return datetime.fromtimestamp(
            timestamp,
            tz=timezone.utc,
        )
    except (OverflowError, OSError, ValueError) as exc:
        raise RefreshTokenInvalidError(
            "Refresh token expiration is invalid."
        ) from exc


def _remaining_lifetime(claims: Any) -> int:
    """
    Calculate remaining lifetime for the rotation marker.

    The token has already passed canonical expiration validation, but
    the TTL is calculated again because the rotation marker has its
    own cache lifetime.
    """

    expires_at = _get_expiration(
        claims,
    )

    remaining = (
        expires_at - _utc_now()
    ).total_seconds()

    if remaining <= 0:
        return 0

    ttl = int(remaining)

    return min(
        max(
            ttl,
            MIN_ROTATION_TTL,
        ),
        MAX_ROTATION_TTL,
    )


# =============================================================================
# Atomic rotation claim
# =============================================================================


def _claim_refresh_token(
    claims: Any,
) -> str:
    """
    Atomically consume a refresh token.

    cache.add() is deliberately used instead of:

        cache.get()
        cache.set()

    because get-then-set is vulnerable to concurrent replay.

    Two simultaneous requests can both observe a missing key when
    get/set is used.

    cache.add() provides create-if-absent semantics.

    Returns
    -------

    str
        The rotation marker cache key.

    Raises
    ------

    RefreshTokenReplayError
        The refresh token has already been consumed.

    RefreshTokenStorageError
        The cache backend cannot establish rotation state.
    """

    jti = _get_jti(
        claims,
    )

    ttl = _remaining_lifetime(
        claims,
    )

    if ttl <= 0:
        raise RefreshTokenInvalidError(
            "Refresh token has expired."
        )

    key = _rotation_cache_key(
        jti,
    )

    try:
        claimed = cache.add(
            key,
            "rotated",
            timeout=ttl,
        )

    except Exception as exc:
        raise RefreshTokenStorageError(
            "Unable to establish refresh-token rotation state."
        ) from exc

    if not claimed:
        raise RefreshTokenReplayError(
            "Refresh token has already been used."
        )

    return key


# =============================================================================
# Revocation
# =============================================================================


def _revoke_consumed_refresh_token(
    claims: Any,
) -> None:
    """
    Revoke the refresh token after it has been atomically consumed.

    The rotation marker and revocation record have different purposes:

        rotation marker
            prevents repeated/concurrent rotation

        revocation record
            prevents the consumed JWT from being accepted elsewhere
    """

    try:
        revoke_refresh_token(
            claims,
        )

    except RevocationStorageError as exc:
        raise RefreshTokenStorageError(
            "Unable to revoke the consumed refresh token."
        ) from exc

    except RevocationConfigurationError as exc:
        raise RefreshTokenInvalidError(
            "Refresh token claims cannot be revoked safely."
        ) from exc


# =============================================================================
# Replacement token issuance
# =============================================================================


def _issue_replacement_tokens(
    *,
    user_id: str,
) -> tuple[
    str,
    Any,
    str,
    Any,
]:
    """
    Issue a new access token and a new refresh token.

    The token factory is the only component responsible for JWT
    creation.
    """

    try:
        access_token, access_claims = create_access_token(
            user_id=user_id,
        )

        refresh_token, refresh_claims = create_refresh_token(
            user_id=user_id,
        )

    except (
        TokenDecodeError,
        TokenExpiredError,
        TokenInvalidError,
        TokenTypeError,
    ) as exc:
        raise RefreshTokenRotationError(
            "Unable to issue replacement authentication tokens."
        ) from exc

    except Exception as exc:
        raise RefreshTokenRotationError(
            "Unable to issue replacement authentication tokens."
        ) from exc

    return (
        access_token,
        access_claims,
        refresh_token,
        refresh_claims,
    )

# =============================================================================
# Replacement invariant validation
# =============================================================================


def _validate_replacement_claims(
    *,
    access_claims: Any,
    refresh_claims: Any,
    previous_refresh_jti: str,
    expected_user_id: str,
) -> None:
    """
    Verify invariants of newly created credentials.

    These claims were already normalized by tokens.py.

    This function does not decode raw JWTs.

    It verifies the contract between refresh.py and tokens.py.
    """

    # -------------------------------------------------------------------------
    # Access token
    # -------------------------------------------------------------------------

    access_type = getattr(
        access_claims,
        "token_type",
        None,
    )

    if access_type != "access":
        raise RefreshTokenRotationError(
            "Token service generated an invalid access token."
        )

    access_jti = getattr(
        access_claims,
        "jti",
        None,
    )

    if not isinstance(access_jti, str) or not access_jti.strip():
        raise RefreshTokenRotationError(
            "Replacement access token does not contain a valid JTI."
        )

    access_user_id = getattr(
        access_claims,
        "user_id",
        None,
    )

    if str(access_user_id).strip() != expected_user_id:
        raise RefreshTokenRotationError(
            "Replacement access token belongs to a different user."
        )

    # -------------------------------------------------------------------------
    # Replacement refresh token
    # -------------------------------------------------------------------------

    refresh_type = getattr(
        refresh_claims,
        "token_type",
        None,
    )

    if refresh_type != REFRESH_TOKEN:
        raise RefreshTokenRotationError(
            "Token service generated an invalid refresh token."
        )

    refresh_jti = getattr(
        refresh_claims,
        "jti",
        None,
    )

    if not isinstance(refresh_jti, str) or not refresh_jti.strip():
        raise RefreshTokenRotationError(
            "Replacement refresh token does not contain a valid JTI."
        )

    # The replacement refresh token must never reuse the consumed JTI.
    if refresh_jti == previous_refresh_jti:
        raise RefreshTokenRotationError(
            "Replacement refresh token reused the consumed JTI."
        )

    refresh_user_id = getattr(
        refresh_claims,
        "user_id",
        None,
    )

    if str(refresh_user_id).strip() != expected_user_id:
        raise RefreshTokenRotationError(
            "Replacement refresh token belongs to a different user."
        )


# =============================================================================
# Canonical refresh-token rotation
# =============================================================================


def rotate_refresh_token(
    refresh_token: str,
) -> RefreshTokenRotation:
    """
    Validate and rotate a refresh token.

    Canonical pipeline:

        raw refresh JWT
                │
                ▼
        validate_refresh_token()
                │
                ├── signature
                ├── algorithm
                ├── exp
                ├── iat
                ├── iss
                ├── aud
                ├── canonical claims
                ├── token_type
                └── revocation
                        │
                        ▼
                validated TokenClaims
                        │
                        ▼
                atomic JTI claim
                        │
                        ├── replay
                        │
                        ▼
                revoke old refresh token
                        │
                        ▼
                create access token
                        │
                        ▼
                create refresh token
                        │
                        ▼
                validate replacement invariants
                        │
                        ▼
                return rotation result

    Security properties
    -------------------

    1. Raw JWTs never reach revocation.py.

    2. Raw JWTs never reach application-level user resolution.

    3. Only validated TokenClaims are used after validation.

    4. A refresh token can win the atomic rotation claim only once.

    5. Revoked refresh tokens cannot pass validation.

    6. Replay attempts are explicitly distinguishable.

    7. Rotation-store failures fail closed.

    8. Once a refresh token is claimed, its rotation marker is never
       removed automatically.
    """

    if not isinstance(
        refresh_token,
        str,
    ) or not refresh_token.strip():
        raise RefreshTokenInvalidError(
            "Refresh token is required."
        )

    # -------------------------------------------------------------------------
    # Canonical validation boundary.
    # -------------------------------------------------------------------------

    try:
        claims = validate_refresh_token(
            refresh_token,
        )

    except (
        TokenExpiredError,
        TokenInvalidError,
        TokenDecodeError,
        TokenTypeError,
    ) as exc:
        raise RefreshTokenInvalidError(
            str(exc) or "Refresh token is invalid."
        ) from exc

    # -------------------------------------------------------------------------
    # Defensive token-type invariant.
    # -------------------------------------------------------------------------

    token_type = getattr(
        claims,
        "token_type",
        None,
    )

    if token_type != REFRESH_TOKEN:
        raise RefreshTokenInvalidError(
            "JWT is not a refresh token."
        )

    # -------------------------------------------------------------------------
    # Canonical identity fields.
    #
    # TokenClaims uses:
    #
    #     user_id
    #     jti
    #     expires_at
    #
    # NOT:
    #
    #     subject
    # -------------------------------------------------------------------------

    user_id = _get_user_id(
        claims,
    )

    previous_jti = _get_jti(
        claims,
    )

    # -------------------------------------------------------------------------
    # ATOMIC CONSUMPTION.
    #
    # This must happen before replacement credentials are created.
    #
    # We intentionally do not roll this marker back on downstream
    # failure. Once the marker exists, the old refresh token remains
    # consumed.
    # -------------------------------------------------------------------------

    _claim_refresh_token(
        claims,
    )

    # -------------------------------------------------------------------------
    # Revoke consumed refresh token.
    #
    # If this fails, RefreshTokenStorageError propagates.
    #
    # The rotation marker remains in place.
    # -------------------------------------------------------------------------

    _revoke_consumed_refresh_token(
        claims,
    )

    # -------------------------------------------------------------------------
    # Issue replacement credentials.
    # -------------------------------------------------------------------------

    (
        access_token,
        access_claims,
        new_refresh_token,
        new_refresh_claims,
    ) = _issue_replacement_tokens(
        user_id=user_id,
    )

    # -------------------------------------------------------------------------
    # Verify the contract returned by tokens.py.
    # -------------------------------------------------------------------------

    _validate_replacement_claims(
        access_claims=access_claims,
        refresh_claims=new_refresh_claims,
        previous_refresh_jti=previous_jti,
        expected_user_id=claims.user_id,
    )

    # -------------------------------------------------------------------------
    # Return immutable rotation result.
    # -------------------------------------------------------------------------

    return RefreshTokenRotation(
        access_token=access_token,
        refresh_token=new_refresh_token,
        access_claims=access_claims,
        refresh_claims=new_refresh_claims,
        previous_refresh_jti=previous_jti,
    )


# =============================================================================
# Semantic aliases
# =============================================================================


def refresh_tokens(
    refresh_token: str,
) -> RefreshTokenRotation:
    """
    Service-facing alias for rotate_refresh_token().
    """

    return rotate_refresh_token(
        refresh_token,
    )


def rotate(
    refresh_token: str,
) -> RefreshTokenRotation:
    """
    Short semantic alias for rotate_refresh_token().
    """

    return rotate_refresh_token(
        refresh_token,
    )


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "RefreshTokenError",
    "RefreshTokenInvalidError",
    "RefreshTokenReplayError",
    "RefreshTokenRotationError",
    "RefreshTokenStorageError",
    "RefreshTokenRotation",
    "rotate_refresh_token",
    "refresh_tokens",
    "rotate",
]