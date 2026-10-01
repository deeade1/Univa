"""
Compatibility facade for legacy blacklist imports.

All revocation functionality now lives in:

    univa_jwt.revocation

This file will be removed once all imports are migrated.
"""

import warnings

from univa_jwt.revocation import (
    is_jti_revoked,
    is_token_revoked,
    revoke_jti,
    revoke_token,
)

warnings.warn(
    "univa_jwt.blacklist is deprecated. Use univa_jwt.revocation instead.",
    DeprecationWarning,
    stacklevel=2,
)


class DefaultBlacklistHandler:
    """Deprecated compatibility class."""

    @classmethod
    def set(cls, refresh_token_obj):
        """
        Deprecated: use revocation.revoke_jti().

        DEPRECATED: This method will be removed in a future version.
        """
        warnings.warn(
            "Blacklist.set() is deprecated. Use revocation.revoke_jti().",
            DeprecationWarning,
            stacklevel=2,
        )

        # Extract JTI from the model if it has one
        jti = getattr(refresh_token_obj, "jti", None)

        if jti:
            # Try to get expiration from the model
            expires_at = getattr(refresh_token_obj, "created", None)

            if expires_at is None:
                expires_at = getattr(refresh_token_obj, "expires_at", None)

            if expires_at:
                revoke_jti(
                    jti=jti,
                    expires_at=expires_at,
                    user_id=getattr(refresh_token_obj, "user_id", None),
                    token_type="refresh",
                )

    @classmethod
    def is_blacklisted(cls, refresh_token):
        """
        Deprecated: use revocation.is_jti_revoked().

        DEPRECATED: This method will be removed in a future version.
        """
        warnings.warn(
            "Blacklist.is_blacklisted() is deprecated. "
            "Use revocation.is_jti_revoked().",
            DeprecationWarning,
            stacklevel=2,
        )

        return is_jti_revoked(refresh_token)


Blacklist = DefaultBlacklistHandler


__all__ = ["DefaultBlacklistHandler", "Blacklist"]