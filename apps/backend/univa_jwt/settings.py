"""
Deprecated compatibility facade for Univa JWT settings.

The canonical configuration lives in:

    univa_jwt.config.jwt_config

New code must import jwt_config directly.
"""

from __future__ import annotations

import warnings

from univa_jwt.config import jwt_config


class _DeprecatedJWTSettings:
    """
    Read-only compatibility facade for legacy JWT setting names.

    All values come from the canonical JWTConfig instance.
    """

    _LEGACY_TO_CANONICAL = {
        "UNIVA_JWT_ALGORITHM": "algorithm",
        "UNIVA_JWT_SECRET_KEY": "signing_key",
        "UNIVA_JWT_EXPIRATION_DELTA": "access_token_lifetime",
        "UNIVA_JWT_REFRESH_EXPIRATION_DELTA": "refresh_token_lifetime",
        "UNIVA_JWT_AUTH_HEADER_NAME": "auth_header_name",
        "UNIVA_JWT_AUTH_HEADER_PREFIX": "auth_header_prefix",
        "UNIVA_JWT_CACHE_PREFIX": "cache_prefix",
        "UNIVA_JWT_ISSUER": "issuer",
        "UNIVA_JWT_AUDIENCE": "audience",
        "UNIVA_JWT_LEEWAY": "leeway",
        "UNIVA_JWT_TOKEN_TYPE_CLAIM": "token_type_claim",
        "UNIVA_JWT_JTI_CLAIM": "jti_claim",
        "UNIVA_JWT_USER_ID_CLAIM": "user_id_claim",
        "UNIVA_JWT_ROTATE_REFRESH_TOKENS": "rotate_refresh_tokens",
        "UNIVA_JWT_REVOKE_REFRESH_ON_ROTATION": (
            "revoke_refresh_on_rotation"
        ),
        "UNIVA_JWT_REQUIRE_REFRESH_TOKEN_REVOCATION_CHECK": (
            "require_refresh_token_revocation_check"
        ),
    }

    def __getattr__(self, name: str):
        canonical_name = self._LEGACY_TO_CANONICAL.get(
            name,
        )

        if canonical_name is None:
            raise AttributeError(
                f"{self.__class__.__name__!s} "
                f"has no attribute {name!r}"
            )

        warnings.warn(
            (
                f"Settings attribute {name} is deprecated. "
                f"Use univa_jwt.config.jwt_config."
                f"{canonical_name} instead."
            ),
            DeprecationWarning,
            stacklevel=2,
        )

        return getattr(
            jwt_config,
            canonical_name,
        )

    def __setattr__(
        self,
        name: str,
        value,
    ) -> None:
        raise AttributeError(
            f"JWT settings are immutable. Cannot set {name!r}."
        )


jwt_settings = _DeprecatedJWTSettings()


__all__ = [
    "jwt_settings",
]