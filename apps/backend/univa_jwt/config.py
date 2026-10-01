# apps/backend/univa_jwt/config.py

"""
Univa JWT configuration.

This module provides a typed, centralized configuration interface for
the Univa JWT subsystem.

Important architectural rule:

    Django settings define configuration.
    univa_jwt.config exposes that configuration.
    The rest of univa_jwt must NOT read django.conf.settings directly.

This keeps JWT configuration centralized and makes the token system easier
to test and evolve.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Final

from django.conf import settings


DEFAULT_ALGORITHM: Final[str] = "HS256"
DEFAULT_ISSUER: Final[str] = "univa-backend"
DEFAULT_AUDIENCE: Final[str] = "univa-client"
DEFAULT_AUTH_HEADER_PREFIX: Final[str] = "Bearer"

DEFAULT_ACCESS_TOKEN_MINUTES: Final[int] = 30
DEFAULT_REFRESH_TOKEN_DAYS: Final[int] = 7
DEFAULT_LEEWAY: Final[int] = 5


@dataclass(frozen=True, slots=True)
class JWTConfig:
    """
    Immutable runtime configuration for Univa JWT.

    No token-generation or validation logic belongs here.
    """

    # Cryptography
    algorithm: str
    signing_key: str

    # JWT metadata
    issuer: str
    audience: str

    # Token lifetimes
    access_token_lifetime: timedelta
    refresh_token_lifetime: timedelta

    # HTTP authentication
    auth_header_prefix: str

    # Claims
    user_id_claim: str
    token_type_claim: str
    jti_claim: str

    # Validation
    verify_expiration: bool
    verify_issuer: bool
    verify_audience: bool
    require_jti: bool
    require_token_type: bool
    leeway: int

    # Refresh-token security
    rotate_refresh_tokens: bool
    revoke_refresh_on_rotation: bool
    require_refresh_token_revocation_check: bool


def _get_settings() -> dict:
    """
    Return the raw UNIVA_JWT configuration.

    This is intentionally the only direct settings access in this module.
    """

    value = getattr(settings, "UNIVA_JWT", None)

    if not isinstance(value, dict):
        raise RuntimeError(
            "UNIVA_JWT is not configured in Django settings."
        )

    return value


def _require_string(
    config: dict,
    key: str,
    default: str | None = None,
) -> str:
    """
    Read a required string configuration value.
    """

    value = config.get(key, default)

    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(
            f"UNIVA_JWT['{key}'] must be a non-empty string."
        )

    return value.strip()


def _require_bool(
    config: dict,
    key: str,
    default: bool,
) -> bool:
    """
    Read a boolean configuration value.
    """

    value = config.get(key, default)

    if not isinstance(value, bool):
        raise RuntimeError(
            f"UNIVA_JWT['{key}'] must be a boolean."
        )

    return value


def _require_positive_int(
    config: dict,
    key: str,
    default: int,
    *,
    minimum: int = 0,
) -> int:
    """
    Read and validate an integer configuration value.
    """

    value = config.get(key, default)

    if isinstance(value, bool) or not isinstance(value, int):
        raise RuntimeError(
            f"UNIVA_JWT['{key}'] must be an integer."
        )

    if value < minimum:
        raise RuntimeError(
            f"UNIVA_JWT['{key}'] must be >= {minimum}."
        )

    return value


def load_config() -> JWTConfig:
    """
    Load and validate the complete JWT configuration.

    This function intentionally performs validation at startup/runtime
    instead of allowing malformed JWT configuration to fail later during
    authentication.
    """

    raw = _get_settings()

    algorithm = _require_string(
        raw,
        "ALGORITHM",
        DEFAULT_ALGORITHM,
    )

    signing_key = _require_string(
        raw,
        "SIGNING_KEY",
    )

    issuer = _require_string(
        raw,
        "ISSUER",
        DEFAULT_ISSUER,
    )

    audience = _require_string(
        raw,
        "AUDIENCE",
        DEFAULT_AUDIENCE,
    )

    auth_header_prefix = _require_string(
        raw,
        "AUTH_HEADER_PREFIX",
        DEFAULT_AUTH_HEADER_PREFIX,
    )

    access_minutes = _require_positive_int(
        raw,
        "ACCESS_TOKEN_LIFETIME_MINUTES",
        DEFAULT_ACCESS_TOKEN_MINUTES,
        minimum=1,
    )

    refresh_days = _require_positive_int(
        raw,
        "REFRESH_TOKEN_LIFETIME_DAYS",
        DEFAULT_REFRESH_TOKEN_DAYS,
        minimum=1,
    )

    leeway = _require_positive_int(
        raw,
        "LEEWAY",
        DEFAULT_LEEWAY,
        minimum=0,
    )

    user_id_claim = _require_string(
        raw,
        "USER_ID_CLAIM",
        "sub",
    )

    token_type_claim = _require_string(
        raw,
        "TOKEN_TYPE_CLAIM",
        "token_type",
    )

    jti_claim = _require_string(
        raw,
        "JTI_CLAIM",
        "jti",
    )

    config = JWTConfig(
        algorithm=algorithm,
        signing_key=signing_key,
        issuer=issuer,
        audience=audience,

        access_token_lifetime=timedelta(
            minutes=access_minutes,
        ),

        refresh_token_lifetime=timedelta(
            days=refresh_days,
        ),

        auth_header_prefix=auth_header_prefix,

        user_id_claim=user_id_claim,
        token_type_claim=token_type_claim,
        jti_claim=jti_claim,

        verify_expiration=_require_bool(
            raw,
            "VERIFY_EXPIRATION",
            True,
        ),

        verify_issuer=_require_bool(
            raw,
            "VERIFY_ISSUER",
            True,
        ),

        verify_audience=_require_bool(
            raw,
            "VERIFY_AUDIENCE",
            True,
        ),

        require_jti=_require_bool(
            raw,
            "REQUIRE_JTI",
            True,
        ),

        require_token_type=_require_bool(
            raw,
            "REQUIRE_TOKEN_TYPE",
            True,
        ),

        leeway=leeway,

        rotate_refresh_tokens=_require_bool(
            raw,
            "ROTATE_REFRESH_TOKENS",
            True,
        ),

        revoke_refresh_on_rotation=_require_bool(
            raw,
            "REVOKE_REFRESH_ON_ROTATION",
            True,
        ),

        require_refresh_token_revocation_check=_require_bool(
            raw,
            "REQUIRE_REFRESH_TOKEN_REVOCATION_CHECK",
            True,
        ),
    )

    _validate_config(config)

    return config


def _validate_config(config: JWTConfig) -> None:
    """
    Validate relationships between JWT configuration values.
    """

    if config.access_token_lifetime >= config.refresh_token_lifetime:
        raise RuntimeError(
            "UNIVA_JWT access-token lifetime must be shorter than "
            "the refresh-token lifetime."
        )

    if config.require_jti and not config.jti_claim:
        raise RuntimeError(
            "JTI claim is required but JTI_CLAIM is empty."
        )

    if config.require_token_type and not config.token_type_claim:
        raise RuntimeError(
            "Token type validation is enabled but TOKEN_TYPE_CLAIM "
            "is empty."
        )


jwt_config = load_config()