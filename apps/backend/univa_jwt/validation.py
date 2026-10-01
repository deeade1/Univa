# apps/backend/univa_jwt/validation.py

"""
Compatibility facade for canonical Univa JWT validation.

IMPORTANT
=========

This module is NOT a JWT implementation.

The canonical JWT validation boundary is:

    univa_jwt.tokens

This module exists only to preserve a stable compatibility API for
older callers while the application migrates to TokenClaims.

There is intentionally NO second JWT validation engine here.

Do not:

    - import PyJWT here
    - decode JWTs here
    - validate signatures here
    - validate exp/iat/iss/aud here
    - maintain a second ValidatedToken model
    - perform a second revocation implementation

All JWT validation responsibilities belong to univa_jwt.tokens.
"""

from __future__ import annotations

from typing import Any, Mapping

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist

from .claims import TokenClaims
from .constants import ACCESS_TOKEN, REFRESH_TOKEN
from .exceptions import (
    TokenDecodeError,
    TokenExpiredError,
    TokenInvalidError,
    TokenTypeError,
)
from .tokens import (
    decode_access_token,
    decode_refresh_token,
    decode_token,
    validate_access_token as _validate_access_token,
    validate_refresh_token as _validate_refresh_token,
    verify_token,
)


# =============================================================================
# Compatibility exception aliases
# =============================================================================

JWTValidationError = TokenInvalidError
JWTExpiredError = TokenExpiredError
JWTMalformedError = TokenDecodeError
JWTClaimsError = TokenInvalidError
JWTTokenTypeError = TokenTypeError


class JWTConfigurationError(Exception):
    """
    Compatibility exception for legacy configuration handling.

    New code should normally allow canonical token-layer exceptions
    to propagate.
    """


class JWTUserError(Exception):
    """
    Raised when a JWT subject cannot be resolved to an active user.

    User resolution is intentionally outside TokenClaims.
    """


class JWTRevokedError(TokenInvalidError):
    """
    Compatibility exception for callers that explicitly distinguish
    revoked JWTs.

    Canonical tokens.py currently reports revocation failures through
    TokenInvalidError.
    """


# =============================================================================
# Compatibility constants
# =============================================================================

ACCESS_TOKEN_TYPE = ACCESS_TOKEN
REFRESH_TOKEN_TYPE = REFRESH_TOKEN

VALID_TOKEN_TYPES = frozenset(
    {
        ACCESS_TOKEN,
        REFRESH_TOKEN,
    }
)


# =============================================================================
# User resolution
# =============================================================================


def resolve_user(
    user_id: str,
):
    """
    Resolve a canonical TokenClaims.user_id to an active Django user.

    TokenClaims represents JWT identity and metadata only.

    Application authentication code may resolve that identity to a
    Django user when required.
    """

    if user_id is None:
        raise JWTUserError(
            "JWT user ID is required."
        )

    normalized_user_id = str(user_id).strip()

    if not normalized_user_id:
        raise JWTUserError(
            "JWT user ID cannot be empty."
        )

    User = get_user_model()

    try:
        user = User.objects.get(
            pk=normalized_user_id,
        )

    except (
        User.DoesNotExist,
        ObjectDoesNotExist,
    ) as exc:
        raise JWTUserError(
            "JWT subject does not correspond to a valid user."
        ) from exc

    if not getattr(
        user,
        "is_active",
        True,
    ):
        raise JWTUserError(
            "User account is inactive."
        )

    return user


# =============================================================================
# Canonical validation facade
# =============================================================================


def validate_token(
    token: str,
    *,
    expected_token_type: str | None = None,
    resolve_user_instance: bool = False,
    check_revocation: bool = True,
) -> TokenClaims:
    """
    Compatibility wrapper around univa_jwt.tokens.decode_token().

    The canonical return value is TokenClaims.

    Canonical token validation always includes revocation checking.
    """

    if not check_revocation:
        raise ValueError(
            "check_revocation=False is not supported by the canonical "
            "JWT validation boundary."
        )

    claims = decode_token(
        token,
        expected_token_type=expected_token_type,
    )

    if resolve_user_instance:
        resolve_user(
            claims.user_id,
        )

    return claims


def validate_access_token(
    token: str,
) -> TokenClaims:
    """
    Validate an access token through the canonical token service.
    """

    return _validate_access_token(
        token,
    )


def validate_refresh_token(
    token: str,
) -> TokenClaims:
    """
    Validate a refresh token through the canonical token service.
    """

    return _validate_refresh_token(
        token,
    )


# =============================================================================
# Compatibility claim validation
# =============================================================================


def validate_claims(
    claims: Mapping[str, Any],
) -> tuple[
    str,
    str,
    str,
    int,
    int,
    str,
    str,
]:
    """
    Compatibility helper for callers that still possess a raw claim mapping.

    New code should use TokenClaims directly.

    This function only normalizes an already-created claim mapping.
    It does not authenticate a raw JWT.
    """

    from .claims import validate_claim_structure

    normalized = validate_claim_structure(
        claims,
    )

    return (
        normalized.user_id,
        normalized.jti,
        normalized.token_type,
        int(normalized.issued_at.timestamp()),
        int(normalized.expires_at.timestamp()),
        normalized.issuer,
        normalized.audience,
    )


# =============================================================================
# Compatibility revocation helpers
# =============================================================================

def is_token_revoked(
    *,
    jti: str,
    user_id: str,
    token_type: str,
) -> bool:
    """
    Compatibility wrapper around the canonical revocation service.

    New authentication code should normally validate through tokens.py
    instead of calling this function directly.

    The legacy user_id and token_type parameters are retained for API
    compatibility. Revocation is keyed exclusively by JTI.
    """

    from .revocation import is_jti_revoked

    if not jti:
        raise TokenInvalidError(
            "JWT JTI is required."
        )

    return is_jti_revoked(
        jti,
    )

def ensure_not_revoked(
    *,
    jti: str,
    user_id: str | None = None,
    token_type: str | None = None,
) -> None:
    """
    Compatibility revocation helper.

    Prefer canonical JWT validation through tokens.py.
    """

    if is_token_revoked(
        jti=jti,
        user_id=user_id,
        token_type=token_type,
    ):
        raise JWTRevokedError(
            "JWT has been revoked."
        )


# =============================================================================
# Authorization header extraction
# =============================================================================


def extract_bearer_token(
    authorization_header: str | None,
) -> str | None:
    """
    Extract a Bearer JWT from an Authorization header.

    This function performs extraction only.

    It does not validate the JWT.
    """

    if not authorization_header:
        return None

    if not isinstance(
        authorization_header,
        str,
    ):
        return None

    parts = authorization_header.strip().split()

    if len(parts) != 2:
        return None

    scheme, token = parts

    if scheme.lower() != "bearer":
        return None

    token = token.strip()

    return token or None


# =============================================================================
# WebSocket token extraction
# =============================================================================


def extract_websocket_token(
    scope: Mapping[str, Any],
) -> str | None:
    """
    Extract a JWT from a WebSocket scope.

    Supported locations:

        1. Authorization header
        2. scope["jwt"]
        3. scope["token"]

    Validation is performed exclusively by tokens.py.
    """

    headers = scope.get(
        "headers",
    ) or []

    for header_name, header_value in headers:
        if isinstance(
            header_name,
            bytes,
        ):
            header_name = header_name.decode(
                "latin-1",
                errors="ignore",
            )

        if header_name.lower() != "authorization":
            continue

        if isinstance(
            header_value,
            bytes,
        ):
            header_value = header_value.decode(
                "latin-1",
                errors="ignore",
            )

        token = extract_bearer_token(
            header_value,
        )

        if token:
            return token

    jwt_value = scope.get(
        "jwt",
    )

    if isinstance(
        jwt_value,
        str,
    ) and jwt_value.strip():
        return jwt_value.strip()

    token_value = scope.get(
        "token",
    )

    if isinstance(
        token_value,
        str,
    ) and token_value.strip():
        return token_value.strip()

    return None


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "TokenClaims",
    "JWTValidationError",
    "JWTConfigurationError",
    "JWTMalformedError",
    "JWTExpiredError",
    "JWTClaimsError",
    "JWTTokenTypeError",
    "JWTUserError",
    "JWTRevokedError",
    "ACCESS_TOKEN_TYPE",
    "REFRESH_TOKEN_TYPE",
    "VALID_TOKEN_TYPES",
    "validate_token",
    "validate_access_token",
    "validate_refresh_token",
    "decode_token",
    "decode_access_token",
    "decode_refresh_token",
    "verify_token",
    "resolve_user",
    "validate_claims",
    "is_token_revoked",
    "ensure_not_revoked",
    "extract_bearer_token",
    "extract_websocket_token",
]