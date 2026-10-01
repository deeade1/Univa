"""
GraphQL JWT authentication middleware for Univa.

This module is intentionally thin.

JWT cryptography, claim validation, token-type validation, revocation,
and Django user resolution are owned by:

    univa_jwt.middleware
        │
        ▼
    univa_jwt.tokens
        │
        ▼
    univa_jwt.revocation

GraphQL must NOT:

    - decode JWTs directly
    - import PyJWT
    - inspect JWT claims directly
    - implement revocation checks
    - implement token expiration checks
    - silently convert an invalid supplied token into AnonymousUser

Authentication behavior
-----------------------

No Authorization header:

    AnonymousUser

Valid Bearer token:

    authenticated User

Invalid / expired / revoked Bearer token:

    JWTAuthenticationError

The distinction between missing credentials and invalid credentials is
preserved so public GraphQL operations can remain anonymous while
explicitly invalid credentials are rejected.

This middleware therefore acts only as a GraphQL transport adapter.
"""

from __future__ import annotations

from typing import Any

from univa_jwt.middleware import (
    JWT_AUTHENTICATED_ATTRIBUTE,
    JWTAuthenticationError,
    authenticate_request,
)


class JWTAuthMiddleware:
    """
    Graphene middleware that establishes JWT authentication state.

    Authentication is delegated entirely to:

        univa_jwt.middleware.authenticate_request()

    That function is the canonical HTTP/GraphQL authentication entry
    point and ultimately delegates JWT validation to:

        univa_jwt.tokens.validate_access_token()

    The GraphQL layer therefore shares exactly the same JWT validation
    and revocation behavior as HTTP and WebSocket authentication.
    """

    def resolve(
        self,
        next_,
        root: Any,
        info: Any,
        **kwargs: Any,
    ):
        """
        Authenticate the GraphQL request before resolving the field.

        `info.context` is expected to be the Django HttpRequest.

        Missing credentials are intentionally allowed so public GraphQL
        fields can execute anonymously.

        If credentials are explicitly supplied but invalid, the canonical
        authentication layer raises JWTAuthenticationError. That error
        is deliberately allowed to propagate rather than being converted
        into anonymous authentication.
        """

        request = getattr(
            info,
            "context",
            None,
        )

        if request is None:
            raise JWTAuthenticationError(
                "GraphQL request context is unavailable.",
            )

        # ------------------------------------------------------------------
        # Avoid repeating authentication if another middleware layer has
        # already established it for this request.
        #
        # authenticate_request() itself is also idempotent, but checking
        # here makes the GraphQL adapter explicit and avoids unnecessary
        # work on every field resolver.
        # ------------------------------------------------------------------

        if not getattr(
            request,
            JWT_AUTHENTICATED_ATTRIBUTE,
            False,
        ):
            authenticate_request(
                request,
            )

        return next_(
            root,
            info,
            **kwargs,
        )


# Ensure the class is exported
__all__ = [
    "JWTAuthMiddleware",
]