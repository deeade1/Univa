# apps/backend/univa_jwt/middleware.py

"""
Canonical Univa JWT authentication boundary.

This module provides the transport-level authentication boundary for:

    HTTP
    WebSocket
    GraphQL

The cryptographic and semantic JWT validation boundary remains:

    univa_jwt.tokens

This module MUST NOT:

    - decode JWTs directly
    - import PyJWT
    - validate JWT claims itself
    - implement revocation
    - implement refresh-token rotation
    - maintain another JWT representation

Its responsibilities are limited to:

    1. Extracting credentials.
    2. Calling canonical token validation.
    3. Resolving the authenticated user.
    4. Attaching canonical TokenClaims.
    5. Translating lower-level failures into AuthenticationError.

Authentication policy:

    No credentials
        -> anonymous

    Invalid credentials
        -> AuthenticationError

    Valid access token
        -> authenticated user

Refresh tokens are NEVER accepted by this module.
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Mapping

from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest, HttpResponse

from .claims import TokenClaims
from .exceptions import (
    AuthenticationError,
    TokenDecodeError,
    TokenExpiredError,
    TokenInvalidError,
    TokenTypeError,
)
from .tokens import validate_access_token
from .validation import resolve_user


logger = logging.getLogger(__name__)


# =============================================================================
# Public exception compatibility alias
# =============================================================================
#
# There is intentionally NO second JWTAuthenticationError class.
#
# AuthenticationError is the canonical exception in exceptions.py.
#
# This alias exists because middleware callers and older integrations may
# import JWTAuthenticationError from this module.
# =============================================================================

JWTAuthenticationError = AuthenticationError


# =============================================================================
# Constants
# =============================================================================


WEBSOCKET_AUTHORIZATION_HEADER = b"authorization"

AUTHORIZATION_HEADER = "HTTP_AUTHORIZATION"

JWT_AUTHENTICATED_ATTRIBUTE = "univa_jwt_authenticated"

WEBSOCKET_AUTHORIZATION_HEADER = b"authorization"

JWT_USER_ATTRIBUTE = "user"
JWT_CLAIMS_ATTRIBUTE = "univa_jwt"

# =============================================================================
# Authorization header parsing
# =============================================================================


def parse_authorization_header(
    authorization_header: str | bytes | None,
) -> tuple[str | None, bool]:
    """
    Parse an HTTP Authorization header.

    Returns
    -------
    tuple[str | None, bool]

        token:
            Extracted Bearer token, or None.

        supplied:
            Whether credentials were actually supplied.

    Behavior
    --------
    No header:
        (None, False)

    Empty header:
        (None, False)

    Valid Bearer header:
        (token, True)

    Any malformed or unsupported supplied header:
        raises JWTAuthenticationError

    The parser performs extraction only.

    JWT validation is performed by validate_access_token().
    """

    if authorization_header is None:
        return None, False

    if isinstance(
        authorization_header,
        bytes,
    ):
        authorization_header = authorization_header.decode(
            "latin-1",
            errors="replace",
        )

    if not isinstance(
        authorization_header,
        str,
    ):
        raise JWTAuthenticationError(
            "Invalid Authorization header."
        )

    header = authorization_header.strip()

    if not header:
        return None, False

    parts = header.split()

    if len(parts) != 2:
        raise JWTAuthenticationError(
            "Invalid Authorization header."
        )

    scheme, token = parts

    if scheme.lower() != "bearer":
        raise JWTAuthenticationError(
            "Unsupported authentication scheme."
        )

    token = token.strip()

    if not token:
        raise JWTAuthenticationError(
            "Bearer token is required."
        )

    return token, True


# =============================================================================
# HTTP token extraction
# =============================================================================


def extract_http_token(
    request: HttpRequest,
) -> tuple[str | None, bool]:
    """
    Extract the Bearer token from a Django HTTP request.

    Returns
    -------
    (token, supplied)

    No Authorization header:
        (None, False)

    Valid Bearer credentials:
        (token, True)

    Invalid Authorization header:
        raises JWTAuthenticationError
    """

    authorization_header = request.META.get(
        AUTHORIZATION_HEADER,
    )

    return parse_authorization_header(
        authorization_header,
    )


# =============================================================================
# Compatibility extraction helper
# =============================================================================


def extract_bearer_token(
    authorization_header: str | bytes | None,
) -> str | None:
    """
    Compatibility helper returning only the extracted token.

    Unlike parse_authorization_header(), this function intentionally hides
    the supplied flag.

    Malformed supplied credentials still raise JWTAuthenticationError.
    """

    token, _ = parse_authorization_header(
        authorization_header,
    )

    return token


# =============================================================================
# WebSocket token extraction
# =============================================================================


def extract_websocket_token(
    scope: Mapping[str, Any],
) -> tuple[str | None, bool]:
    """
    Extract a Bearer token from a WebSocket ASGI scope.

    Supported authentication source:

        scope["headers"]

    Authorization query-string tokens are intentionally NOT supported.

    Returns
    -------
    (token, supplied)

    No Authorization header:
        (None, False)

    Valid Authorization header:
        (token, True)

    Invalid Authorization header:
        raises JWTAuthenticationError
    """

    headers = scope.get(
        "headers",
    ) or []

    authorization_header: str | bytes | None = None

    for header_name, header_value in headers:

        if isinstance(
            header_name,
            bytes,
        ):
            normalized_name = header_name.decode(
                "latin-1",
                errors="ignore",
            ).lower()
        else:
            normalized_name = str(
                header_name
            ).lower()

        if normalized_name != "authorization":
            continue

        authorization_header = header_value
        break

    return parse_authorization_header(
        authorization_header,
    )


# =============================================================================
# Canonical direct authentication
# =============================================================================


def authenticate_token(
    token: str,
) -> tuple[Any, TokenClaims]:
    """
    Authenticate a raw access JWT.

    This is the canonical direct authentication boundary.

    Pipeline:

        raw JWT
            |
            v
        validate_access_token()
            |
            v
        TokenClaims
            |
            v
        resolve_user()
            |
            v
        Django user

    Refresh tokens are rejected by validate_access_token().
    """

    try:
        claims = validate_access_token(
            token,
        )

    except (
        TokenExpiredError,
        TokenInvalidError,
        TokenDecodeError,
        TokenTypeError,
    ) as exc:

        logger.info(
            "Rejected invalid Univa JWT during direct authentication: %s",
            type(exc).__name__,
        )

        raise JWTAuthenticationError(
            "Authentication failed."
        ) from exc

    except Exception as exc:

        logger.exception(
            "Unexpected error during Univa JWT authentication."
        )

        raise JWTAuthenticationError(
            "Authentication failed."
        ) from exc

    try:
        user = resolve_user(
            claims.user_id,
        )

    except Exception as exc:

        logger.info(
            "Rejected Univa JWT because its subject could not be resolved: %s",
            type(exc).__name__,
        )

        raise JWTAuthenticationError(
            "Authentication failed."
        ) from exc

    if not getattr(
        user,
        "is_authenticated",
        False,
    ):
        raise JWTAuthenticationError(
            "Authentication failed."
        )

    return user, claims


# =============================================================================
# HTTP authentication
# =============================================================================


def authenticate_request(
    request: HttpRequest,
):
    """
    Authenticate a Django HTTP request.

    Behavior
    --------

    No credentials:
        AnonymousUser

    Valid access token:
        authenticated user

    Invalid credentials:
        JWTAuthenticationError

    The authentication result is cached on the request so repeated
    authentication calls do not repeatedly parse or validate the JWT.
    """

    # -------------------------------------------------------------------------
    # Reuse existing authentication state.
    # -------------------------------------------------------------------------

    if getattr(
        request,
        "_univa_jwt_authentication_complete",
        False,
    ):
        return getattr(
            request,
            "user",
            AnonymousUser(),
        )

    # -------------------------------------------------------------------------
    # Mark authentication as processed only after extraction succeeds.
    # -------------------------------------------------------------------------

    token, supplied = extract_http_token(
        request,
    )

    # -------------------------------------------------------------------------
    # Anonymous request.
    # -------------------------------------------------------------------------

    
    if not supplied or not token:
        # Preserve Django session authentication.
        if not getattr(request.user, "is_authenticated", False):
            request.user = AnonymousUser()

        request.jwt_claims = None

        request.univa_jwt = None
        request.univa_jwt_user_id = None
        request.univa_jwt_jti = None
        request.univa_jwt_token_type = None
        request.univa_jwt_issued_at = None
        request.univa_jwt_expires_at = None
        request.univa_jwt_issuer = None
        request.univa_jwt_audience = None

        request._univa_jwt_authentication_complete = True

        return request.user
    
    # -------------------------------------------------------------------------
    # Authenticate supplied credentials.
    # -------------------------------------------------------------------------

    user, claims = authenticate_token(
        token,
    )

    # -------------------------------------------------------------------------
    # Attach canonical request state.
    # -------------------------------------------------------------------------

    request.user = user

    request.jwt_claims = claims

    request.univa_jwt = claims
    request.univa_jwt_user_id = claims.user_id
    request.univa_jwt_jti = claims.jti
    request.univa_jwt_token_type = claims.token_type
    request.univa_jwt_issued_at = claims.issued_at
    request.univa_jwt_expires_at = claims.expires_at
    request.univa_jwt_issuer = claims.issuer
    request.univa_jwt_audience = claims.audience

    request._univa_jwt_authentication_complete = True

    return user


# =============================================================================
# Authentication state helper
# =============================================================================


def is_authenticated(
    user: Any,
) -> bool:
    """
    Return True when the supplied object represents an authenticated user.
    """

    return bool(
        user
        and getattr(
            user,
            "is_authenticated",
            False,
        )
    )


# =============================================================================
# Strict authentication helper
# =============================================================================


def require_authenticated_user(
    request: HttpRequest,
):
    """
    Require an authenticated HTTP request.

    Anonymous requests raise JWTAuthenticationError.

    This function is the authorization boundary used by protected
    application operations.
    """

    user = authenticate_request(
        request,
    )

    if not is_authenticated(
        user,
    ):
        raise JWTAuthenticationError(
            "Authentication is required."
        )

    return user


# =============================================================================
# Request context helpers
# =============================================================================


def get_authenticated_user(
    request: HttpRequest,
):
    """
    Return the authenticated user or None.
    """

    user = authenticate_request(
        request,
    )

    if not is_authenticated(
        user,
    ):
        return None

    return user


def get_jwt_context(
    request: HttpRequest,
) -> TokenClaims | None:
    """
    Return canonical TokenClaims attached to the request.
    """

    # Ensure authentication has occurred.
    authenticate_request(
        request,
    )

    claims = getattr(
        request,
        "jwt_claims",
        None,
    )

    if isinstance(
        claims,
        TokenClaims,
    ):
        return claims

    return None


def get_jwt_claims(
    request: HttpRequest,
) -> TokenClaims | None:
    """
    Compatibility alias for get_jwt_context().
    """

    return get_jwt_context(
        request,
    )


# =============================================================================
# Django middleware
# =============================================================================


class UnivaJWTMiddleware:
    """
    Django HTTP middleware.

    Authentication is attempted for requests carrying Bearer credentials.

    Requests without credentials remain anonymous.

    Invalid supplied credentials raise JWTAuthenticationError.
    """

    def __init__(
        self,
        get_response: Callable[
            [HttpRequest],
            HttpResponse,
        ],
    ) -> None:
        self.get_response = get_response

    def __call__(
        self,
        request: HttpRequest,
    ) -> HttpResponse:
        import logging
        logging.getLogger(__name__).error(
            "=== MW IN === path=%s auth=%r cookie_session=%r user_before=%r",
            request.path,
            (request.META.get("HTTP_AUTHORIZATION") or "")[:60],
            "sessionid" in getattr(request, "COOKIES", {}),
            getattr(request, "user", None),
        )

        authenticate_request(request)

        logging.getLogger(__name__).error(
            "=== MW OUT === user_after=%r",
            getattr(request, "user", None),
        )

        return self.get_response(request)

    def authenticate(
        self,
        request: HttpRequest,
    ):
        """
        Explicit compatibility entry point.
        """

        return authenticate_request(
            request,
        )

    @staticmethod
    def is_authenticated(
        request: HttpRequest,
    ) -> bool:
        """
        Return whether the request has an authenticated user.
        """

        return is_authenticated(
            getattr(
                request,
                "user",
                None,
            )
        )




# =============================================================================
# Public API
# =============================================================================
__all__ = [
    # Constants
    "AUTHORIZATION_HEADER",
    "WEBSOCKET_AUTHORIZATION_HEADER",
    "JWT_AUTHENTICATED_ATTRIBUTE",
    "JWT_USER_ATTRIBUTE",
    "JWT_CLAIMS_ATTRIBUTE",

    # Exceptions
    "JWTAuthenticationError",

    # Header parsing
    "parse_authorization_header",
    "extract_bearer_token",
    "extract_http_token",
    "extract_websocket_token",

    # Authentication
    "authenticate_token",
    "authenticate_request",
    "is_authenticated",
    "require_authenticated_user",

    # Context
    "get_authenticated_user",
    "get_jwt_context",
    "get_jwt_claims",

    # Middleware
    "UnivaJWTMiddleware",
    
]
