"""
WebSocket JWT authentication middleware.

Responsibilities
----------------
This middleware is intentionally limited to the WebSocket transport
boundary.

It is responsible for:

    1. Extracting credentials from the WebSocket scope.
    2. Passing the raw access token to the canonical
       JWTAuthenticationService.
    3. Attaching the authenticated user and canonical TokenClaims
       to the scope.

It does NOT:

    - decode JWTs
    - verify JWT signatures
    - validate JWT claims
    - check token type
    - implement revocation
    - resolve users directly
    - maintain a second authentication implementation

All JWT authentication belongs to:

    univa_jwt.authentication.JWTAuthenticationService

Anonymous requests remain supported.

However, once credentials are supplied, authentication failures are
NOT silently converted into AnonymousUser. This prevents invalid
credentials from being treated as an unauthenticated request.
"""

from __future__ import annotations

import logging
from typing import Any

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

from univa_jwt.authentication import JWTAuthenticationService
from univa_jwt.exceptions import AuthenticationError
from univa_jwt.middleware import (
    JWT_AUTHENTICATED_ATTRIBUTE,
    JWT_CLAIMS_ATTRIBUTE,
    JWT_USER_ATTRIBUTE,
)



logger = logging.getLogger(__name__)


class WebSocketAuthMiddleware:
    """
    Authenticate WebSocket connections using the canonical JWT service.

    Authentication lifecycle:

        WebSocket scope
             |
             v
        extract_token()
             |
             v
        raw JWT
             |
             v
        JWTAuthenticationService
             |
             +---- user
             |
             +---- TokenClaims
             |
             v
        scope["user"]
        scope["univa_jwt"]
        scope["univa_jwt_authenticated"]

    No token:

        scope["user"] = AnonymousUser()
        scope["univa_jwt"] = None
        scope["univa_jwt_authenticated"] = False
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(
        self,
        scope: dict[str, Any],
        receive,
        send,
    ):
        """
        Authenticate WebSocket scope before passing it downstream.
        """

        if scope.get("type") != "websocket":
            return await self.inner(
                scope,
                receive,
                send,
            )

        # ---------------------------------------------------------------------
        # Establish deterministic anonymous state.
        # ---------------------------------------------------------------------

        scope[JWT_USER_ATTRIBUTE] = AnonymousUser()
        scope[JWT_CLAIMS_ATTRIBUTE] = None
        scope[JWT_AUTHENTICATED_ATTRIBUTE] = False

        # ---------------------------------------------------------------------
        # Extract credentials.
        # ---------------------------------------------------------------------

        token = self.extract_token(
            scope,
        )

        # ---------------------------------------------------------------------
        # No credentials means anonymous WebSocket.
        #
        # This is intentionally allowed.
        # ---------------------------------------------------------------------

        if not token:
            return await self.inner(
                scope,
                receive,
                send,
            )

        # ---------------------------------------------------------------------
        # Authenticate the supplied access token.
        #
        # IMPORTANT: We use the async-safe authenticate() method which wraps
        # the ORM access in database_sync_to_async.
        #
        # AuthenticationError is deliberately allowed to propagate.
        # ---------------------------------------------------------------------

        try:
            user, claims = await self.authenticate(
                token,
            )

        except AuthenticationError:
            logger.info(
                "WebSocket JWT authentication failed."
            )
            raise

        except Exception as exc:
            logger.exception(
                "Unexpected WebSocket JWT authentication failure."
            )

            raise AuthenticationError(
                "Authentication failed."
            ) from exc

        # ---------------------------------------------------------------------
        # Attach canonical authentication state.
        # ---------------------------------------------------------------------

        scope[JWT_USER_ATTRIBUTE] = user
        scope[JWT_CLAIMS_ATTRIBUTE] = claims
        scope[JWT_AUTHENTICATED_ATTRIBUTE] = True

        return await self.inner(
            scope,
            receive,
            send,
        )

    # =========================================================================
    # Credential extraction
    # =========================================================================

    @staticmethod
    def extract_token(
        scope: dict[str, Any],
    ) -> str | None:
        """
        Extract an access token from supported WebSocket credential
        locations.

        Supported locations:

            1. connection_params
            2. Authorization header

        Query-string tokens are intentionally NOT supported.

        Query-string credentials are undesirable because URLs can be
        logged, cached, copied, or exposed through intermediary systems.
        """

        # ---------------------------------------------------------------------
        # 1. GraphQL/WebSocket connection parameters
        # ---------------------------------------------------------------------

        connection_params = scope.get(
            "connection_params",
        )

        if isinstance(
            connection_params,
            dict,
        ):
            token = (
                connection_params.get(
                    "authorization",
                )
                or connection_params.get(
                    "Authorization",
                )
                or connection_params.get(
                    "token",
                )
            )

            token = WebSocketAuthMiddleware._normalize_token(
                token,
            )

            if token:
                return token

        # ---------------------------------------------------------------------
        # 2. Authorization header
        # ---------------------------------------------------------------------

        headers = scope.get(
            "headers",
            [],
        )

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

            token = WebSocketAuthMiddleware._normalize_token(
                header_value,
            )

            if token:
                return token

        return None

    # =========================================================================
    # Token normalization
    # =========================================================================

    @staticmethod
    def _normalize_token(
        value: Any,
    ) -> str | None:
        """
        Normalize a credential value into a raw JWT.

        This function performs extraction only.

        It does NOT validate the JWT.
        """

        if not isinstance(
            value,
            str,
        ):
            return None

        value = value.strip()

        if not value:
            return None

        parts = value.split()

        # -------------------------------------------------------------
        # Explicit Bearer authentication.
        # -------------------------------------------------------------

        if len(parts) == 2:
            scheme, token = parts

            if scheme.lower() == "bearer":
                token = token.strip()
                return token or None

            return None

        # -------------------------------------------------------------
        # Raw token supplied through connection_params["token"].
        # -------------------------------------------------------------

        if len(parts) == 1:
            return parts[0]

        return None

    # =========================================================================
    # Canonical authentication
    # =========================================================================

    @staticmethod
    @database_sync_to_async
    def authenticate(
        token: str,
    ):
        """
        Authenticate an access token through the canonical service.

        This function is intentionally synchronous internally because
        JWTAuthenticationService may resolve the Django user through
        the synchronous ORM.

        database_sync_to_async safely moves that work out of the async
        WebSocket event loop.

        Returns
        -------
        tuple
            (user, TokenClaims)

        Raises
        ------
        AuthenticationError
            If the supplied credentials cannot authenticate.

        No authentication exception is swallowed here.
        """

        # DIRECTLY use JWTAuthenticationService - this avoids going through
        # middleware.authenticate_token() which would try to resolve the user
        # synchronously in the async context.
        return JWTAuthenticationService.authenticate_access_token_with_claims(
            token,
        )


# =============================================================================
# Convenience wrapper
# =============================================================================


def JWTWebSocketMiddleware(inner):
    """
    Convenience factory compatible with Channels middleware stacks.
    """

    return WebSocketAuthMiddleware(
        inner,
    )


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "JWT_USER_ATTRIBUTE",
    "JWT_CLAIMS_ATTRIBUTE",
    "JWT_AUTHENTICATED_ATTRIBUTE",
    "WebSocketAuthMiddleware",
    "JWTWebSocketMiddleware",
]