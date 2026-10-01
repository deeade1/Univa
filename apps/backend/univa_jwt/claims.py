# apps/backend/univa_jwt/claims.py

"""
Canonical JWT claims for Univa.

This module defines the structure of every JWT issued by Univa.

Canonical payload:

    {
        "sub": "<user id>",
        "jti": "<unique token id>",
        "token_type": "access" | "refresh",
        "iat": <issued-at timestamp>,
        "exp": <expiration timestamp>,
        "iss": "univa-backend",
        "aud": "univa-client",
    }

Architecture
------------

claims.py
    |
    +-- creates canonical claims
    +-- validates claim structure
    +-- extracts identity/token metadata
    |
    v
tokens.py
    |
    +-- signs JWT
    +-- decodes JWT
    +-- performs cryptographic/standard validation
    |
    v
HTTP / GraphQL / WebSocket
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4

from .config import jwt_config
from .constants import ACCESS_TOKEN, REFRESH_TOKEN
from .exceptions import (
    TokenInvalidError,
    TokenTypeError,
)


@dataclass(frozen=True, slots=True)
class TokenClaims:
    """
    Normalized representation of a validated JWT.

    Application code should prefer this object instead of repeatedly
    accessing raw dictionary claims.
    """

    user_id: str
    jti: str
    token_type: str
    issued_at: datetime
    expires_at: datetime
    issuer: str
    audience: str

    @property
    def subject(self) -> str:
        """
        Compatibility alias for user_id.

        DEPRECATED: Use user_id instead.
        """
        return self.user_id

    @property
    def is_access_token(self) -> bool:
        """Return True when this is an access token."""
        return self.token_type == ACCESS_TOKEN

    @property
    def is_refresh_token(self) -> bool:
        """Return True when this is a refresh token."""
        return self.token_type == REFRESH_TOKEN

    @property
    def is_expired(self) -> bool:
        """Return True when the token expiration is in the past."""
        return self.expires_at <= datetime.now(timezone.utc)


def _utc_timestamp(value: datetime) -> int:
    """
    Convert an aware datetime into a Unix timestamp.
    """

    if value.tzinfo is None:
        raise ValueError(
            "JWT datetime values must be timezone-aware."
        )

    return int(value.timestamp())


def _utc_datetime(value: Any, claim_name: str) -> datetime:
    """
    Convert a JWT NumericDate value into an aware UTC datetime.
    """

    if isinstance(value, bool):
        raise TokenInvalidError(
            f"JWT claim '{claim_name}' must be a numeric timestamp."
        )

    if not isinstance(value, (int, float)):
        raise TokenInvalidError(
            f"JWT claim '{claim_name}' must be a numeric timestamp."
        )

    try:
        return datetime.fromtimestamp(
            float(value),
            tz=timezone.utc,
        )
    except (OverflowError, OSError, ValueError) as exc:
        raise TokenInvalidError(
            f"JWT claim '{claim_name}' contains an invalid timestamp."
        ) from exc


def _normalize_user_id(user_id: Any) -> str:
    """
    Normalize the user identifier used in the `sub` claim.
    """

    if user_id is None:
        raise ValueError("user_id is required.")

    value = str(user_id).strip()

    if not value:
        raise ValueError("user_id cannot be empty.")

    return value


def _normalize_jti(jti: Any) -> str:
    """
    Normalize a JWT ID.

    A JTI is generated automatically when one is not supplied.
    """

    if jti is None:
        return str(uuid4())

    value = str(jti).strip()

    if not value:
        raise ValueError("jti cannot be empty.")

    return value


def build_claims(
    *,
    user_id: Any,
    token_type: str,
    issued_at: datetime,
    expires_at: datetime,
    jti: str | None = None,
) -> dict[str, Any]:
    """
    Build the canonical JWT claim dictionary.

    This function does not sign the token.

    Parameters
    ----------
    user_id:
        User primary key.

    token_type:
        Either "access" or "refresh".

    issued_at:
        Token issue time.

    expires_at:
        Token expiration time.

    jti:
        Optional token identifier. Generated automatically when omitted.
    """

    if token_type not in {
        ACCESS_TOKEN,
        REFRESH_TOKEN,
    }:
        raise TokenTypeError(
            f"Unsupported token type: {token_type!r}."
        )

    if issued_at.tzinfo is None:
        raise ValueError(
            "issued_at must be timezone-aware."
        )

    if expires_at.tzinfo is None:
        raise ValueError(
            "expires_at must be timezone-aware."
        )

    if expires_at <= issued_at:
        raise ValueError(
            "expires_at must be later than issued_at."
        )

    user_id_value = _normalize_user_id(user_id)
    jti_value = _normalize_jti(jti)

    return {
        jwt_config.user_id_claim: user_id_value,
        jwt_config.jti_claim: jti_value,
        jwt_config.token_type_claim: token_type,

        "iat": _utc_timestamp(issued_at),
        "exp": _utc_timestamp(expires_at),

        "iss": jwt_config.issuer,
        "aud": jwt_config.audience,
    }


def validate_claim_structure(
    payload: Mapping[str, Any],
    *,
    expected_token_type: str | None = None,
) -> TokenClaims:
    """
    Validate and normalize the semantic JWT claims.

    Cryptographic validation is performed by tokens.py before this function
    should normally be called.

    This function nevertheless performs strict structural validation so that
    malformed payloads cannot enter the application layer.
    """

    if not isinstance(payload, Mapping):
        raise TokenInvalidError(
            "JWT payload must be a mapping."
        )

    user_id = payload.get(jwt_config.user_id_claim)

    if user_id is None:
        raise TokenInvalidError(
            f"JWT is missing required claim "
            f"'{jwt_config.user_id_claim}'."
        )

    user_id = str(user_id).strip()

    if not user_id:
        raise TokenInvalidError(
            "JWT subject cannot be empty."
        )

    jti = payload.get(jwt_config.jti_claim)

    if jwt_config.require_jti and not jti:
        raise TokenInvalidError(
            f"JWT is missing required claim "
            f"'{jwt_config.jti_claim}'."
        )

    jti = str(jti).strip() if jti is not None else ""

    token_type = payload.get(jwt_config.token_type_claim)

    if jwt_config.require_token_type and not token_type:
        raise TokenInvalidError(
            f"JWT is missing required claim "
            f"'{jwt_config.token_type_claim}'."
        )

    if token_type not in {
        ACCESS_TOKEN,
        REFRESH_TOKEN,
    }:
        raise TokenTypeError(
            f"Invalid JWT token type: {token_type!r}."
        )

    if expected_token_type is not None:
        if token_type != expected_token_type:
            raise TokenTypeError(
                "JWT token type does not match the expected type."
            )

    issued_at = payload.get("iat")

    if issued_at is None:
        raise TokenInvalidError(
            "JWT is missing required claim 'iat'."
        )

    expires_at = payload.get("exp")

    if expires_at is None:
        raise TokenInvalidError(
            "JWT is missing required claim 'exp'."
        )

    issued_at_dt = _utc_datetime(
        issued_at,
        "iat",
    )

    expires_at_dt = _utc_datetime(
        expires_at,
        "exp",
    )

    if expires_at_dt <= issued_at_dt:
        raise TokenInvalidError(
            "JWT expiration must be later than issuance time."
        )

    issuer = payload.get("iss")

    if jwt_config.verify_issuer:
        if issuer != jwt_config.issuer:
            raise TokenInvalidError(
                "JWT issuer is invalid."
            )

    issuer = str(issuer or "")

    audience = payload.get("aud")

    if jwt_config.verify_audience:
        if isinstance(audience, (list, tuple, set)):
            valid_audience = (
                jwt_config.audience in audience
            )
        else:
            valid_audience = (
                audience == jwt_config.audience
            )

        if not valid_audience:
            raise TokenInvalidError(
                "JWT audience is invalid."
            )

    if isinstance(audience, (list, tuple, set)):
        audience_value = (
            str(jwt_config.audience)
        )
    else:
        audience_value = str(audience or "")

    return TokenClaims(
        user_id=user_id,
        jti=jti,
        token_type=token_type,
        issued_at=issued_at_dt,
        expires_at=expires_at_dt,
        issuer=issuer,
        audience=audience_value,
    )


def get_user_id(payload: Mapping[str, Any]) -> str:
    """
    Extract the authenticated user's ID from a validated payload.
    """

    value = payload.get(jwt_config.user_id_claim)

    if value is None:
        raise TokenInvalidError(
            f"JWT is missing '{jwt_config.user_id_claim}'."
        )

    value = str(value).strip()

    if not value:
        raise TokenInvalidError(
            "JWT user ID cannot be empty."
        )

    return value


def get_jti(payload: Mapping[str, Any]) -> str:
    """
    Extract the JWT ID from a validated payload.
    """

    value = payload.get(jwt_config.jti_claim)

    if not value:
        raise TokenInvalidError(
            f"JWT is missing '{jwt_config.jti_claim}'."
        )

    return str(value)


def get_token_type(payload: Mapping[str, Any]) -> str:
    """
    Extract and validate the token type.
    """

    value = payload.get(
        jwt_config.token_type_claim
    )

    if value not in {
        ACCESS_TOKEN,
        REFRESH_TOKEN,
    }:
        raise TokenTypeError(
            f"Invalid JWT token type: {value!r}."
        )

    return str(value)