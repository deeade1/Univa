"""
Canonical JWT encoding, decoding, validation, and revocation integration
for Univa.

ARCHITECTURE
============

This module is the single JWT cryptographic and validation boundary.

Authentication transports:

    HTTP
    GraphQL
    WebSocket

must all eventually use this module.

Refresh-token services must also use this module.

Application code must NOT call PyJWT directly.

Canonical JWT claims:

    sub         Subject / Django user ID
    jti         Unique JWT ID
    token_type  "access" or "refresh"
    iat         Issued-at timestamp
    exp         Expiration timestamp
    iss         Issuer
    aud         Audience

Validation pipeline:

    raw JWT
        │
        ▼
    PyJWT signature/standard validation
        │
        ▼
    canonical claim validation
        │
        ▼
    token-type validation
        │
        ▼
    revocation validation
        │
        ▼
    TokenClaims

The revocation check deliberately occurs only after the JWT has been
cryptographically and semantically validated.

This prevents untrusted raw JWT data from being passed into the
revocation subsystem.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

import jwt
from jwt import (
    DecodeError,
    ExpiredSignatureError,
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidTokenError,
)

from .claims import (
    TokenClaims,
    build_claims,
    validate_claim_structure,
)
from .config import jwt_config
from .constants import (
    ACCESS_TOKEN,
    REFRESH_TOKEN,
)
from .exceptions import (
    TokenDecodeError,
    TokenEncodeError,
    TokenExpiredError,
    TokenInvalidError,
    TokenTypeError,
)
from .revocation import (
    RevocationStorageError,
    is_token_revoked,
)


# =============================================================================
# Internal helpers
# =============================================================================


def _now() -> datetime:
    """
    Return the current timezone-aware UTC datetime.
    """

    return datetime.now(timezone.utc)


def _encode(
    payload: Mapping[str, Any],
) -> str:
    """
    Cryptographically sign a JWT payload.

    This is intentionally private.

    Public callers should use:

        create_access_token()
        create_refresh_token()
    """

    if not isinstance(
        payload,
        Mapping,
    ):
        raise TokenEncodeError(
            "JWT payload must be a mapping."
        )

    try:
        token = jwt.encode(
            dict(payload),
            jwt_config.signing_key,
            algorithm=jwt_config.algorithm,
        )

    except Exception as exc:
        raise TokenEncodeError(
            "Unable to encode JWT."
        ) from exc

    if not isinstance(
        token,
        str,
    ):
        raise TokenEncodeError(
            "JWT encoder returned an invalid token."
        )

    token = token.strip()

    if not token:
        raise TokenEncodeError(
            "JWT encoder returned an empty token."
        )

    return token


def _decode(
    token: str,
) -> dict[str, Any]:
    """
    Cryptographically decode and validate a JWT.

    This function is intentionally limited to cryptographic and
    PyJWT-standard validation.

    Semantic validation happens in:

        validate_claim_structure()
    """

    if not isinstance(
        token,
        str,
    ):
        raise TokenInvalidError(
            "JWT must be a string."
        )

    token = token.strip()

    if not token:
        raise TokenInvalidError(
            "JWT cannot be empty."
        )

    required_claims = [
        "exp",
        "iat",
    ]

    if jwt_config.require_jti:
        required_claims.append(
            jwt_config.jti_claim,
        )

    options: dict[str, Any] = {
        "verify_signature": True,
        "verify_exp": jwt_config.verify_expiration,
        "verify_iss": jwt_config.verify_issuer,
        "verify_aud": jwt_config.verify_audience,
        "require": required_claims,
    }

    try:
        payload = jwt.decode(
            token,
            jwt_config.signing_key,
            algorithms=[
                jwt_config.algorithm,
            ],
            issuer=(
                jwt_config.issuer
                if jwt_config.verify_issuer
                else None
            ),
            audience=(
                jwt_config.audience
                if jwt_config.verify_audience
                else None
            ),
            options=options,
            leeway=jwt_config.leeway,
        )

    except ExpiredSignatureError as exc:
        raise TokenExpiredError(
            "JWT has expired."
        ) from exc

    except InvalidAudienceError as exc:
        raise TokenInvalidError(
            "JWT audience is invalid."
        ) from exc

    except InvalidIssuerError as exc:
        raise TokenInvalidError(
            "JWT issuer is invalid."
        ) from exc

    except DecodeError as exc:
        raise TokenDecodeError(
            "JWT could not be decoded."
        ) from exc

    except InvalidTokenError as exc:
        raise TokenInvalidError(
            "JWT is invalid."
        ) from exc

    if not isinstance(
        payload,
        dict,
    ):
        raise TokenInvalidError(
            "JWT payload must be a JSON object."
        )

    return payload


def _validate_token_type(
    claims: TokenClaims,
    expected_token_type: str | None,
) -> TokenClaims:
    """
    Ensure a validated token has the expected token type.
    """

    if expected_token_type is None:
        return claims

    actual_token_type = getattr(
        claims,
        "token_type",
        None,
    )

    if actual_token_type != expected_token_type:
        raise TokenTypeError(
            "JWT token type is invalid."
        )

    return claims


def _check_revocation(
    claims: TokenClaims,
) -> None:
    """
    Check server-side revocation state.

    This is deliberately fail-closed.

    If Redis/cache cannot determine whether the token is revoked,
    authentication must fail rather than treating the token as valid.
    """

    try:
        revoked = is_token_revoked(
            claims,
        )

    except RevocationStorageError as exc:
        raise TokenInvalidError(
            "Unable to verify JWT revocation state."
        ) from exc

    if revoked:
        raise TokenInvalidError(
            "JWT has been revoked."
        )


# =============================================================================
# Token creation
# =============================================================================


def create_token(
    *,
    user_id: Any,
    token_type: str,
    lifetime,
    jti: str | None = None,
) -> tuple[str, TokenClaims]:
    """
    Create and sign a canonical Univa JWT.

    Returns:

        (encoded_token, normalized_claims)
    """

    if token_type not in {
        ACCESS_TOKEN,
        REFRESH_TOKEN,
    }:
        raise TokenTypeError(
            f"Unsupported token type: {token_type!r}."
        )

    if user_id is None:
        raise TokenInvalidError(
            "JWT user ID is required."
        )

    if lifetime is None:
        raise TokenInvalidError(
            "JWT lifetime is required."
        )

    issued_at = _now()
    expires_at = issued_at + lifetime

    payload = build_claims(
        user_id=user_id,
        token_type=token_type,
        issued_at=issued_at,
        expires_at=expires_at,
        jti=jti,
    )

    token = _encode(
        payload,
    )

    claims = validate_claim_structure(
        payload,
        expected_token_type=token_type,
    )

    return token, claims


def create_access_token(
    *,
    user_id: Any,
) -> tuple[str, TokenClaims]:
    """
    Create an access JWT.
    """

    return create_token(
        user_id=user_id,
        token_type=ACCESS_TOKEN,
        lifetime=jwt_config.access_token_lifetime,
    )


def create_refresh_token(
    *,
    user_id: Any,
    jti: str | None = None,
) -> tuple[str, TokenClaims]:
    """
    Create a refresh JWT.

    A caller may provide a JTI so that a server-side refresh-token
    record can be associated with the exact JWT.
    """

    return create_token(
        user_id=user_id,
        token_type=REFRESH_TOKEN,
        lifetime=jwt_config.refresh_token_lifetime,
        jti=jti,
    )


# =============================================================================
# Canonical validation
# =============================================================================


def decode_token(
    token: str,
    *,
    expected_token_type: str | None = None,
) -> TokenClaims:
    """
    Canonically validate a JWT.

    This is the central validation path used by:

        HTTP
        GraphQL
        WebSocket
        refresh-token services

    Validation order:

        1. Signature
        2. Algorithm
        3. exp
        4. iat
        5. iss
        6. aud
        7. Canonical claim structure
        8. Expected token type
        9. Server-side revocation
    """

    if expected_token_type not in {
        None,
        ACCESS_TOKEN,
        REFRESH_TOKEN,
    }:
        raise TokenTypeError(
            f"Unsupported expected token type: "
            f"{expected_token_type!r}."
        )

    payload = _decode(
        token,
    )

    try:
        claims = validate_claim_structure(
            payload,
            expected_token_type=expected_token_type,
        )

    except TokenTypeError:
        raise

    except Exception as exc:
        raise TokenInvalidError(
            "JWT claims are invalid."
        ) from exc

    claims = _validate_token_type(
        claims,
        expected_token_type,
    )

    _check_revocation(
        claims,
    )

    return claims


def validate_access_token(
    token: str,
) -> TokenClaims:
    """
    Canonically validate an access token.

    This is the public API used by HTTP, GraphQL, and WebSocket
    authentication middleware.
    """

    return decode_token(
        token,
        expected_token_type=ACCESS_TOKEN,
    )


def validate_refresh_token(
    token: str,
) -> TokenClaims:
    """
    Canonically validate a refresh token.

    Refresh-token rotation must use this function rather than
    decoding the JWT independently.
    """

    return decode_token(
        token,
        expected_token_type=REFRESH_TOKEN,
    )


def decode_access_token(
    token: str,
) -> TokenClaims:
    """
    Backwards-compatible explicit access-token decoder.

    Internally this uses the same canonical validation path as
    validate_access_token().
    """

    return validate_access_token(
        token,
    )


def decode_refresh_token(
    token: str,
) -> TokenClaims:
    """
    Backwards-compatible explicit refresh-token decoder.

    Internally this uses the same canonical validation path as
    validate_refresh_token().
    """

    return validate_refresh_token(
        token,
    )


# =============================================================================
# Lightweight verification
# =============================================================================


def verify_token(
    token: str,
    *,
    expected_token_type: str | None = None,
) -> bool:
    """
    Return True only when the token passes the complete validation
    pipeline.

    Revocation and storage failures are treated as invalid.

    This helper intentionally hides authentication exceptions from
    callers performing a boolean validity check.
    """

    try:
        decode_token(
            token,
            expected_token_type=expected_token_type,
        )

    except (
        TokenInvalidError,
        TokenExpiredError,
        TokenDecodeError,
        TokenTypeError,
    ):
        return False

    return True


# =============================================================================
# Lifetime helpers
# =============================================================================


def token_remaining_lifetime(
    claims: TokenClaims,
) -> int:
    """
    Return remaining token lifetime in seconds.

    Returns zero when the token has expired.
    """

    remaining = (
        claims.expires_at - _now()
    ).total_seconds()

    return max(
        0,
        int(remaining),
    )


def is_token_expired(
    claims: TokenClaims,
) -> bool:
    """
    Return True when a normalized token has expired.
    """

    return claims.expires_at <= _now()


# =============================================================================
# Public API
# =============================================================================


__all__ = [
    "create_token",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "decode_access_token",
    "decode_refresh_token",
    "validate_access_token",
    "validate_refresh_token",
    "verify_token",
    "token_remaining_lifetime",
    "is_token_expired",
]