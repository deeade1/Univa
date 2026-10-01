"""
Server-side JWT revocation service for Univa.

ARCHITECTURE
============

This module owns server-side JWT revocation.

Responsibilities
----------------

    - Revoke individual JWTs by JTI.
    - Check whether a JTI has been revoked.
    - Revoke validated TokenClaims.
    - Revoke all refresh tokens issued to a user before a cutoff.
    - Check user-level refresh-token revocation.
    - Preserve revocation state until the affected JWTs naturally expire.
    - Provide a storage-independent API for authentication and
      refresh-token services.

Dependency direction
--------------------

    tokens.py
        |
        v
    revocation.py
        |
        v
    Django cache
        |
        v
    Redis

IMPORTANT
=========

This module does NOT:

    - decode JWTs
    - call PyJWT
    - inspect raw JWT strings
    - validate JWT signatures
    - validate JWT claims
    - query a deprecated RefreshToken model

JWT cryptography and canonical claim validation belong to:

    univa_jwt.tokens

Revocation operates on already validated TokenClaims or on explicitly
supplied canonical identity data.

SECURITY MODEL
==============

There are two complementary revocation mechanisms.

1. JTI REVOCATION
-----------------

A single JWT is revoked when its JTI exists in the revocation store.

The revocation record receives a TTL equal to the remaining lifetime
of that JWT.

2. USER REFRESH-TOKEN CUTOFF
----------------------------

A user's refresh tokens can be revoked without enumerating tokens.

When ``revoke_all_for_user()`` is called, the current UTC timestamp is
stored as the user's refresh-token revocation cutoff.

A refresh token is considered revoked when:

    issued_at <= user_refresh_revocation_cutoff

This allows "log out all devices" / "revoke all sessions" semantics
without maintaining a refresh-token table or scanning Redis.

The cutoff is retained long enough to cover the configured maximum
refresh-token lifetime.

This module intentionally does not revoke access tokens when
``revoke_all_for_user()`` is called. The operation is specifically
for refresh-token sessions.

WHY A CUTOFF?
=============

The Django cache abstraction does not provide a portable "find all
keys belonging to this user" operation.

Therefore this module must not attempt to scan cache keys.

Instead:

    individual token
        -> JTI key

    all refresh tokens for user
        -> user cutoff key

Both mechanisms are O(1) lookups.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from django.core.cache import cache


# =============================================================================
# Configuration
# =============================================================================

REVOCATION_CACHE_PREFIX = "univa:jwt:revoked"

USER_REFRESH_REVOCATION_PREFIX = (
    "univa:jwt:user-refresh-revoked"
)

MIN_REVOCATION_TTL = 1

MAX_REVOCATION_TTL = (
    60 * 60 * 24 * 365 * 10
)


# =============================================================================
# Exceptions
# =============================================================================


class RevocationError(Exception):
    """Base exception for JWT revocation failures."""


class RevocationConfigurationError(
    RevocationError,
):
    """Raised when revocation input/configuration is invalid."""


class RevocationStorageError(
    RevocationError,
):
    """
    Raised when the configured revocation storage cannot be accessed.

    Authentication callers should normally fail closed when this occurs.
    """


# =============================================================================
# Data objects
# =============================================================================


@dataclass(frozen=True, slots=True)
class RevocationRecord:
    """Representation of a revoked JWT."""

    jti: str
    user_id: str | None
    token_type: str | None
    revoked_at: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class UserRefreshRevocationRecord:
    """
    User-level refresh-token revocation boundary.

    Any refresh token issued at or before ``revoked_at`` is revoked.
    """

    user_id: str
    revoked_at: datetime


# =============================================================================
# Internal helpers
# =============================================================================


def _utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""

    return datetime.now(
        timezone.utc,
    )


def _validate_jti(
    jti: Any,
) -> str:
    """
    Validate and normalize a JWT ID.

    A JTI is an identifier, not a token payload.
    """

    if jti is None:
        raise RevocationConfigurationError(
            "Cannot revoke a JWT without a JTI."
        )

    normalized = str(jti).strip()

    if not normalized:
        raise RevocationConfigurationError(
            "Cannot revoke a JWT with an empty JTI."
        )

    return normalized


def _validate_user_id(
    user_id: Any,
) -> str:
    """
    Validate and normalize a canonical user ID.
    """

    if user_id is None:
        raise RevocationConfigurationError(
            "Cannot revoke tokens without a user ID."
        )

    normalized = str(user_id).strip()

    if not normalized:
        raise RevocationConfigurationError(
            "Cannot revoke tokens for an empty user ID."
        )

    return normalized


def _build_cache_key(
    jti: str,
) -> str:
    """
    Build the canonical cache key for a JTI.
    """

    normalized_jti = _validate_jti(
        jti,
    )

    return (
        f"{REVOCATION_CACHE_PREFIX}:"
        f"{normalized_jti}"
    )


def _build_user_refresh_cache_key(
    user_id: str | int,
) -> str:
    """
    Build the canonical user-level refresh-token
    revocation cache key.
    """

    normalized_user_id = _validate_user_id(
        user_id,
    )

    return (
        f"{USER_REFRESH_REVOCATION_PREFIX}:"
        f"{normalized_user_id}"
    )


def _normalize_datetime(
    value: Any,
) -> datetime:
    """
    Normalize an expiration or timestamp value into
    timezone-aware UTC.
    """

    if isinstance(
        value,
        datetime,
    ):
        result = value

    elif isinstance(
        value,
        (int, float),
    ):
        try:
            result = datetime.fromtimestamp(
                value,
                tz=timezone.utc,
            )
        except (
            OverflowError,
            OSError,
            ValueError,
        ) as exc:
            raise RevocationConfigurationError(
                "Token timestamp is invalid."
            ) from exc

    else:
        raise RevocationConfigurationError(
            "Token timestamp must be a datetime "
            "or Unix timestamp."
        )

    if result.tzinfo is None:
        result = result.replace(
            tzinfo=timezone.utc,
        )

    return result.astimezone(
        timezone.utc,
    )


def _calculate_ttl(
    expires_at: datetime,
) -> int:
    """
    Calculate remaining revocation TTL.

    Returns zero when the token has already expired.
    """

    normalized_expires_at = _normalize_datetime(
        expires_at,
    )

    remaining = (
        normalized_expires_at
        - _utc_now()
    ).total_seconds()

    if remaining <= 0:
        return 0

    ttl = int(remaining)

    return min(
        max(
            ttl,
            MIN_REVOCATION_TTL,
        ),
        MAX_REVOCATION_TTL,
    )


def _calculate_cutoff_ttl() -> int:
    """
    Determine how long a user-level refresh-token cutoff
    should remain in cache.

    The cutoff must survive for at least the maximum configured
    refresh-token lifetime.

    We intentionally use a conservative upper bound here so the
    revocation boundary cannot disappear while valid refresh tokens
    may still exist.
    """

    try:
        from django.conf import settings

        configured = getattr(
            settings,
            "UNIVA_JWT_REFRESH_TOKEN_LIFETIME",
            None,
        )

        if configured is None:
            configured = getattr(
                settings,
                "UNIVA_JWT_REFRESH_EXPIRATION_DELTA",
                None,
            )

        if configured is not None:
            if hasattr(
                configured,
                "total_seconds",
            ):
                seconds = int(
                    configured.total_seconds()
                )

            elif isinstance(
                configured,
                (int, float),
            ):
                seconds = int(
                    configured
                )

            else:
                seconds = 0

            if seconds > 0:
                return min(
                    max(
                        seconds,
                        MIN_REVOCATION_TTL,
                    ),
                    MAX_REVOCATION_TTL,
                )

    except Exception:
        # Configuration lookup must never cause the revocation
        # mechanism to silently disappear.
        pass

    return MAX_REVOCATION_TTL


# =============================================================================
# Individual-token storage
# =============================================================================


def _store_revocation(
    record: RevocationRecord,
    *,
    ttl: int,
) -> None:
    """
    Store individual-token revocation state through
    Django's cache abstraction.
    """

    if ttl <= 0:
        return

    key = _build_cache_key(
        record.jti,
    )

    value = {
        "jti": record.jti,
        "user_id": record.user_id,
        "token_type": record.token_type,
        "revoked_at": (
            record.revoked_at.isoformat()
        ),
        "expires_at": (
            record.expires_at.isoformat()
        ),
    }

    try:
        cache.set(
            key,
            value,
            timeout=ttl,
        )
    except Exception as exc:
        raise RevocationStorageError(
            "Unable to store JWT revocation state."
        ) from exc


def _read_revocation(
    jti: str,
) -> dict[str, Any] | None:
    """
    Read individual-token revocation state.
    """

    key = _build_cache_key(
        jti,
    )

    try:
        value = cache.get(
            key,
        )
    except Exception as exc:
        raise RevocationStorageError(
            "Unable to read JWT revocation state."
        ) from exc

    if value is None:
        return None

    if not isinstance(
        value,
        dict,
    ):
        raise RevocationStorageError(
            "JWT revocation backend returned "
            "invalid revocation data."
        )

    return value


def _delete_revocation(
    jti: str,
) -> None:
    """
    Remove an individual-token revocation record.
    """

    key = _build_cache_key(
        jti,
    )

    try:
        cache.delete(
            key,
        )
    except Exception as exc:
        raise RevocationStorageError(
            "Unable to remove JWT revocation state."
        ) from exc


# =============================================================================
# User-level refresh-token revocation storage
# =============================================================================


def _store_user_refresh_revocation(
    record: UserRefreshRevocationRecord,
    *,
    ttl: int,
) -> None:
    """
    Store the user's refresh-token revocation cutoff.
    """

    if ttl <= 0:
        raise RevocationConfigurationError(
            "User refresh-token revocation TTL must be positive."
        )

    key = _build_user_refresh_cache_key(
        record.user_id,
    )

    value = {
        "user_id": record.user_id,
        "revoked_at": (
            record.revoked_at.isoformat()
        ),
    }

    try:
        cache.set(
            key,
            value,
            timeout=ttl,
        )
    except Exception as exc:
        raise RevocationStorageError(
            "Unable to store user refresh-token "
            "revocation state."
        ) from exc


def _read_user_refresh_revocation(
    user_id: str | int,
) -> UserRefreshRevocationRecord | None:
    """
    Read the user's refresh-token revocation cutoff.
    """

    normalized_user_id = _validate_user_id(
        user_id,
    )

    key = _build_user_refresh_cache_key(
        normalized_user_id,
    )

    try:
        value = cache.get(
            key,
        )
    except Exception as exc:
        raise RevocationStorageError(
            "Unable to read user refresh-token "
            "revocation state."
        ) from exc

    if value is None:
        return None

    if not isinstance(
        value,
        dict,
    ):
        raise RevocationStorageError(
            "User refresh-token revocation backend "
            "returned invalid data."
        )

    revoked_at = value.get(
        "revoked_at",
    )

    if revoked_at is None:
        raise RevocationStorageError(
            "User refresh-token revocation state "
            "does not contain revoked_at."
        )

    try:
        normalized_revoked_at = (
            _normalize_datetime(
                revoked_at,
            )
        )
    except RevocationConfigurationError:
        raise RevocationStorageError(
            "User refresh-token revocation state "
            "contains an invalid timestamp."
        )

    return UserRefreshRevocationRecord(
        user_id=normalized_user_id,
        revoked_at=normalized_revoked_at,
    )


def _delete_user_refresh_revocation(
    user_id: str | int,
) -> None:
    """
    Remove a user-level refresh-token revocation cutoff.

    Administrative/testing use only.
    """

    key = _build_user_refresh_cache_key(
        user_id,
    )

    try:
        cache.delete(
            key,
        )
    except Exception as exc:
        raise RevocationStorageError(
            "Unable to remove user refresh-token "
            "revocation state."
        ) from exc


# =============================================================================
# Public individual-token revocation API
# =============================================================================


def revoke_token(
    *,
    jti: str,
    expires_at: datetime | int | float,
    user_id: str | int | None = None,
    token_type: str | None = None,
) -> bool:
    """
    Revoke a JWT by its canonical JTI.

    Returns False when the token has already expired.
    """

    normalized_jti = _validate_jti(
        jti,
    )

    normalized_expires_at = _normalize_datetime(
        expires_at,
    )

    ttl = _calculate_ttl(
        normalized_expires_at,
    )

    if ttl <= 0:
        return False

    record = RevocationRecord(
        jti=normalized_jti,
        user_id=(
            str(user_id)
            if user_id is not None
            else None
        ),
        token_type=(
            str(token_type)
            if token_type is not None
            else None
        ),
        revoked_at=_utc_now(),
        expires_at=normalized_expires_at,
    )

    _store_revocation(
        record,
        ttl=ttl,
    )

    return True


def revoke_claims(
    claims: Any,
) -> bool:
    """
    Revoke a validated TokenClaims object.

    This is the preferred API for normal authentication flows.
    """

    jti = getattr(
        claims,
        "jti",
        None,
    )

    expires_at = getattr(
        claims,
        "expires_at",
        None,
    )

    user_id = getattr(
        claims,
        "user_id",
        None,
    )

    token_type = getattr(
        claims,
        "token_type",
        None,
    )

    if expires_at is None:
        raise RevocationConfigurationError(
            "Validated token claims do not contain expires_at."
        )

    return revoke_token(
        jti=jti,
        expires_at=expires_at,
        user_id=user_id,
        token_type=token_type,
    )


def is_jti_revoked(
    jti: str,
) -> bool:
    """
    Determine whether a canonical JTI is revoked.

    This is the only JTI-only lookup needed by compatibility
    code, refresh-token rotation, and administrative tooling.
    """

    normalized_jti = _validate_jti(
        jti,
    )

    return (
        _read_revocation(
            normalized_jti,
        )
        is not None
    )


def is_token_revoked(
    claims: Any,
) -> bool:
    """
    Determine whether validated TokenClaims have been revoked.

    Normal authentication should use this function.

    This checks both:

        1. individual JTI revocation
        2. user-level refresh-token revocation
    """

    jti = getattr(
        claims,
        "jti",
        None,
    )

    normalized_jti = _validate_jti(
        jti,
    )

    if is_jti_revoked(
        normalized_jti,
    ):
        return True

    token_type = getattr(
        claims,
        "token_type",
        None,
    )

    if token_type != "refresh":
        return False

    user_id = getattr(
        claims,
        "user_id",
        None,
    )

    issued_at = getattr(
        claims,
        "issued_at",
        None,
    )

    if user_id is None:
        raise RevocationConfigurationError(
            "Refresh-token claims do not contain user_id."
        )

    if issued_at is None:
        raise RevocationConfigurationError(
            "Refresh-token claims do not contain issued_at."
        )

    return is_refresh_token_revoked_for_user(
        user_id=user_id,
        issued_at=issued_at,
    )


# =============================================================================
# User-level refresh-token revocation API
# =============================================================================


def revoke_all_for_user(
    *,
    user_id: str | int,
    token_type: str,
) -> int:
    """
    Revoke all currently valid refresh tokens for a user.

    Parameters
    ----------
    user_id:
        Canonical Django user ID.

    token_type:
        Must be ``"refresh"``.

    Returns
    -------
    int
        ``1`` when the user-level revocation boundary was stored.

    Notes
    -----

    This function deliberately does NOT enumerate cache keys.

    Instead it stores a timestamp cutoff. Every refresh token issued
    before or at that timestamp becomes invalid.

    This gives us O(1) revocation and O(1) validation without a
    server-side refresh-token database.
    """

    if token_type != "refresh":
        raise RevocationConfigurationError(
            "revoke_all_for_user() requires "
            "token_type='refresh'."
        )

    normalized_user_id = _validate_user_id(
        user_id,
    )

    revoked_at = _utc_now()

    record = UserRefreshRevocationRecord(
        user_id=normalized_user_id,
        revoked_at=revoked_at,
    )

    ttl = _calculate_cutoff_ttl()

    _store_user_refresh_revocation(
        record,
        ttl=ttl,
    )

    return 1


def get_user_refresh_revocation_cutoff(
    user_id: str | int,
) -> datetime | None:
    """
    Return the current refresh-token revocation cutoff
    for a user.

    Returns None when no user-level cutoff exists.
    """

    record = _read_user_refresh_revocation(
        user_id,
    )

    if record is None:
        return None

    return record.revoked_at


def is_refresh_token_revoked_for_user(
    *,
    user_id: str | int,
    issued_at: datetime | int | float,
) -> bool:
    """
    Determine whether a refresh token is invalidated by the
    user's refresh-token revocation cutoff.

    A token issued at or before the cutoff is revoked.

    A token issued after the cutoff remains valid unless its own
    JTI has separately been revoked.
    """

    normalized_user_id = _validate_user_id(
        user_id,
    )

    normalized_issued_at = _normalize_datetime(
        issued_at,
    )

    cutoff = (
        get_user_refresh_revocation_cutoff(
            normalized_user_id,
        )
    )

    if cutoff is None:
        return False

    return (
        normalized_issued_at
        <= cutoff
    )


def clear_user_refresh_revocation(
    user_id: str | int,
) -> None:
    """
    Clear a user-level refresh-token revocation cutoff.

    Administrative/testing use only.

    Normal authentication flows must never call this function.
    """

    normalized_user_id = _validate_user_id(
        user_id,
    )

    _delete_user_refresh_revocation(
        normalized_user_id,
    )


# =============================================================================
# Token-type-specific APIs
# =============================================================================


def revoke_access_token(
    claims: Any,
) -> bool:
    """
    Revoke an access token.

    The supplied claims must identify an access token.
    """

    token_type = getattr(
        claims,
        "token_type",
        None,
    )

    if token_type != "access":
        raise RevocationConfigurationError(
            "revoke_access_token() requires an access token."
        )

    return revoke_claims(
        claims,
    )


def revoke_refresh_token(
    claims: Any,
) -> bool:
    """
    Revoke a refresh token.

    The supplied claims must identify a refresh token.
    """

    token_type = getattr(
        claims,
        "token_type",
        None,
    )

    if token_type != "refresh":
        raise RevocationConfigurationError(
            "revoke_refresh_token() requires a refresh token."
        )

    return revoke_claims(
        claims,
    )


def revoke_jti(
    jti: str,
    *,
    expires_at: datetime | int | float,
    user_id: str | int | None = None,
    token_type: str | None = None,
) -> bool:
    """
    Convenience wrapper for explicit JTI-based revocation.
    """

    return revoke_token(
        jti=jti,
        expires_at=expires_at,
        user_id=user_id,
        token_type=token_type,
    )


def unrevoke_jti(
    jti: str,
) -> None:
    """
    Remove an individual-token revocation entry.

    Administrative/testing use only.

    Normal logout and refresh-token rotation must never
    unrevoke a token.
    """

    normalized_jti = _validate_jti(
        jti,
    )

    _delete_revocation(
        normalized_jti,
    )


# =============================================================================
# Health / diagnostics
# =============================================================================


def check_revocation_backend() -> bool:
    """
    Verify that the configured cache backend is reachable.
    """

    health_key = (
        f"{REVOCATION_CACHE_PREFIX}:healthcheck"
    )

    try:
        cache.set(
            health_key,
            "ok",
            timeout=10,
        )

        value = cache.get(
            health_key,
        )

        cache.delete(
            health_key,
        )

    except Exception as exc:
        raise RevocationStorageError(
            "JWT revocation backend is unavailable."
        ) from exc

    return value == "ok"


# =============================================================================
# Public API
# =============================================================================


__all__ = [
    "RevocationError",
    "RevocationConfigurationError",
    "RevocationStorageError",
    "RevocationRecord",
    "UserRefreshRevocationRecord",
    "revoke_token",
    "revoke_claims",
    "revoke_access_token",
    "revoke_refresh_token",
    "revoke_jti",
    "revoke_all_for_user",
    "get_user_refresh_revocation_cutoff",
    "is_refresh_token_revoked_for_user",
    "is_token_revoked",
    "is_jti_revoked",
    "clear_user_refresh_revocation",
    "unrevoke_jti",
    "check_revocation_backend",
]
