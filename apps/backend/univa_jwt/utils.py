"""
Compatibility and application-level helpers for the Univa JWT subsystem.

ARCHITECTURE
------------

The canonical JWT cryptographic boundary is:

    univa_jwt.tokens

Application code must not call PyJWT directly.

This module exists for:

    - authentication-header parsing
    - user lookup
    - refresh-lifetime helpers
    - backwards-compatible wrappers

JWT creation, decoding, validation, token-type validation, and
revocation are delegated to the canonical services.
"""

from __future__ import annotations

from calendar import timegm
from datetime import datetime, timezone as dt_timezone
from functools import wraps
from typing import Any

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from univa_jwt.config import jwt_config
from univa_jwt.constants import ACCESS_TOKEN, REFRESH_TOKEN
from univa_jwt.exceptions import (
    AuthenticationError,
    RefreshTokenError,
    TokenError,
    TokenInvalidError,
)


# =============================================================================
# Token type compatibility
# =============================================================================


def is_access_token(
    token_type: str | None,
) -> bool:
    """Return True when the supplied token type is an access token."""

    return token_type == ACCESS_TOKEN


def is_refresh_token(
    token_type: str | None,
) -> bool:
    """Return True when the supplied token type is a refresh token."""

    return token_type == REFRESH_TOKEN


# =============================================================================
# Authentication header helpers
# =============================================================================


def get_authorization_header(
    request: Any,
) -> str | None:
    """
    Extract a bearer token from a Django HTTP request.

    Returns:
        token string or None

    This helper performs extraction only.

    Token validation belongs to univa_jwt.tokens.
    """

    if request is None:
        return None

    header_name = jwt_config.auth_header_name
    header_prefix = jwt_config.auth_header_prefix

    header = request.META.get(
        header_name,
        "",
    )

    if not header:
        return None

    parts = header.strip().split()

    if len(parts) != 2:
        return None

    if parts[0].lower() != header_prefix.lower():
        return None

    token = parts[1].strip()

    return token or None


def get_credentials(
    request: Any,
) -> str | None:
    """
    Backwards-compatible alias for authorization-header extraction.
    """

    return get_authorization_header(
        request,
    )


# =============================================================================
# User lookup — delegates to canonical validation
# =============================================================================


def get_user_by_token(
    token: str,
) -> Any:
    """
    Resolve the authenticated user from an access token.
    """

    from univa_jwt.tokens import validate_access_token
    from univa_jwt.validation import resolve_user

    claims = validate_access_token(
        token,
    )

    return resolve_user(
        claims.user_id,
    )


def get_user_by_claims(
    claims: Any,
) -> Any:
    """
    Resolve a user from canonical TokenClaims.
    """

    from univa_jwt.validation import resolve_user

    user_id = getattr(
        claims,
        "user_id",
        None,
    )

    if user_id is None:
        raise TokenInvalidError(
            _("JWT is missing the user id claim.")
        )

    return resolve_user(
        user_id,
    )


def get_user_by_payload(
    payload: dict[str, Any],
) -> Any:
    """
    Deprecated compatibility helper.

    This function does not authenticate a JWT.

    The payload must originate from an already validated JWT.

    New code must use:

        get_user_by_token(token)

    or:

        get_user_by_claims(claims)
    """

    if not payload:
        raise TokenInvalidError(
            _("JWT payload is empty.")
        )

    user_id = payload.get(
        "sub",
    )

    if user_id is None:
        user_id = payload.get(
            "id",
        )

    if user_id is None:
        raise TokenInvalidError(
            _("JWT is missing the user id claim.")
        )

    from univa_jwt.validation import resolve_user

    try:
        return resolve_user(
            str(user_id),
        )

    except Exception as exc:
        raise TokenInvalidError(
            _("Unable to resolve JWT user.")
        ) from exc


# =============================================================================
# Refresh-token lifetime helpers
# =============================================================================


def refresh_has_expired(
    orig_iat: int | float | datetime | None,
) -> bool:
    """
    Determine whether a refresh token's original issuance time has
    exceeded the configured refresh-token lifetime.

    ``orig_iat`` may be:

        - Unix timestamp
        - datetime
        - None
    """

    if orig_iat is None:
        return True

    if isinstance(
        orig_iat,
        datetime,
    ):
        if orig_iat.tzinfo is None:
            orig_iat = orig_iat.replace(
                tzinfo=dt_timezone.utc,
            )

        issued_at = orig_iat.astimezone(
            dt_timezone.utc,
        )

        issued_timestamp = timegm(
            issued_at.utctimetuple(),
        )

    else:
        issued_timestamp = float(
            orig_iat,
        )

    now = timegm(
        datetime.now(
            dt_timezone.utc,
        ).utctimetuple()
    )

    expiration = (
        issued_timestamp
        + jwt_config.refresh_token_lifetime.total_seconds()
    )

    return now > expiration


def create_refresh_token(
    user: Any,
) -> Any:
    """
    Create a database-backed refresh-token record.

    IMPORTANT:

    This is different from:

        univa_jwt.tokens.create_refresh_token()

    The database RefreshToken model represents server-side refresh
    state, while tokens.create_refresh_token() represents a signed JWT.

    New refresh-token services should make this distinction explicit.
    """

    if user is None or not getattr(
        user,
        "pk",
        None,
    ):
        raise RefreshTokenError(
            _("Invalid user.")
        )

    if not getattr(
        user,
        "is_active",
        False,
    ):
        raise RefreshTokenError(
            _("User account is disabled.")
        )

    from univa_jwt.models import RefreshToken

    return RefreshToken.objects.create(
        user=user,
    )


# =============================================================================
# Error compatibility decorator
# =============================================================================


def handle_token_errors(
    func,
):
    """
    Convert JWT authentication exceptions into a GraphQL-style
    success=False response for legacy mutation code.

    New services should normally handle domain-specific exceptions
    explicitly.
    """

    @wraps(func)
    def wrapper(
        *args,
        **kwargs,
    ):
        try:
            return func(
                *args,
                **kwargs,
            )

        except (
            TokenError,
            ValidationError,
        ) as exc:
            if not args:
                raise

            mutation = args[0]

            return mutation(
                success=False,
                errors=str(exc),
            )

    return wrapper


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "ACCESS_TOKEN",
    "REFRESH_TOKEN",
    "is_access_token",
    "is_refresh_token",
    "get_authorization_header",
    "get_credentials",
    "get_user_by_token",
    "get_user_by_claims",
    "get_user_by_payload",
    "refresh_has_expired",
    "create_refresh_token",
    "handle_token_errors",
]