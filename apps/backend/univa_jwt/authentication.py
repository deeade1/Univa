"""
Canonical Univa JWT Authentication Service.

This module is the application-level authentication facade for Univa.

ARCHITECTURE
============

JWT cryptographic and semantic validation belongs exclusively to:

    univa_jwt.tokens

Token identity is represented exclusively by:

    univa_jwt.claims.TokenClaims

Django-user resolution belongs to:

    univa_jwt.validation.resolve_user

This service coordinates those canonical primitives for consumers such as:

    - HTTP authentication
    - GraphQL authentication
    - WebSocket authentication
    - Django authentication backends
    - authentication-related application services
"""

from __future__ import annotations

from typing import Any

from django.contrib.auth import authenticate
from django.contrib.auth.models import AnonymousUser

from .claims import TokenClaims
from .exceptions import (
    AuthenticationError,
    InvalidCredentials,
    JSONRefreshTokenExpired,
    UserDisabled,
    UserNotFound,
)
from .refresh import rotate_refresh_token
from .tokens import (
    create_access_token,
    create_refresh_token,
    validate_access_token,
    validate_refresh_token,
)
from .validation import (
    extract_bearer_token,
    resolve_user,
)


class JWTAuthenticationService:
    """
    Canonical application-level JWT authentication facade.

    This class deliberately contains orchestration only.

    JWT validation is delegated to ``univa_jwt.tokens``.
    User resolution is delegated to ``univa_jwt.validation``.
    """

    # =========================================================================
    # Access-token authentication
    # =========================================================================

    @staticmethod
    def authenticate_access_token(
        token: str,
    ):
        """
        Validate an access token and resolve its Django user.

        Returns
        -------
        Django user

        Raises
        ------
        AuthenticationError
            If the token is invalid, expired, revoked, the wrong token
            type, or its subject cannot be resolved.

        Notes
        -----
        All JWT validation is performed by:

            validate_access_token()

        No JWT decoding or claim validation occurs here.
        """

        if not isinstance(
            token,
            str,
        ) or not token.strip():
            raise AuthenticationError(
                "Access token is required."
            )

        try:
            claims = validate_access_token(
                token.strip(),
            )

            user = resolve_user(
                claims.user_id,
            )

        except Exception as exc:
            if isinstance(
                exc,
                AuthenticationError,
            ):
                raise

            raise AuthenticationError(
                "Authentication failed."
            ) from exc

        return user

    # =========================================================================
    # Access-token authentication with claims
    # =========================================================================

    @staticmethod
    def authenticate_access_token_with_claims(
        token: str,
    ) -> tuple[Any, TokenClaims]:
        """
        Validate an access token and return both user and TokenClaims.

        This is the preferred method for transports that need authentication
        context in addition to the Django user.

        Returns
        -------
        tuple[user, TokenClaims]
        """

        if not isinstance(
            token,
            str,
        ) or not token.strip():
            raise AuthenticationError(
                "Access token is required."
            )

        try:
            claims = validate_access_token(
                token.strip(),
            )

            user = resolve_user(
                claims.user_id,
            )

        except Exception as exc:
            if isinstance(
                exc,
                AuthenticationError,
            ):
                raise

            raise AuthenticationError(
                "Authentication failed."
            ) from exc

        return user, claims

    # =========================================================================
    # HTTP request authentication
    # =========================================================================

    @staticmethod
    def authenticate_request(
        request,
    ):
        """
        Authenticate a Django HTTP request.

        Missing credentials are treated as anonymous.

        Invalid credentials are also treated as anonymous here because this
        method is a permissive transport-level helper.

        Strict authorization should use:

            authenticate_access_token()

        or:

            require_authenticated_user()
        """

        authorization_header = request.META.get(
            "HTTP_AUTHORIZATION",
        )

        token = extract_bearer_token(
            authorization_header,
        )

        if not token:
            return AnonymousUser()

        try:
            return JWTAuthenticationService.authenticate_access_token(
                token,
            )
        except AuthenticationError:
            return AnonymousUser()

    # =========================================================================
    # Direct credential authentication
    # =========================================================================

    @staticmethod
    def authenticate_credentials(
        *,
        email: str | None = None,
        phone_number: str | None = None,
        password: str | None = None,
    ):
        """
        Authenticate a user using Django's configured authentication system.

        This is password authentication, not JWT authentication.

        JWT issuance occurs only after successful credential authentication.
        """

        if not password:
            raise InvalidCredentials()

        credentials: dict[str, Any] = {
            "password": password,
        }

        if email:
            credentials["email"] = email

        if phone_number:
            credentials["phone_number"] = phone_number

        user = authenticate(
            **credentials,
        )

        if user is None:
            raise InvalidCredentials()

        if not getattr(
            user,
            "is_active",
            False,
        ):
            raise UserDisabled()

        return user

    # =========================================================================
    # Token issuance
    # =========================================================================

    @staticmethod
    def issue_access_token(
        user,
    ) -> str:
        """
        Issue a canonical access token.

        Token construction belongs exclusively to
        ``univa_jwt.tokens``.

        No caller-supplied JWT claims are accepted here.

        Canonical claims such as:

            sub
            jti
            token_type
            iat
            exp
            iss
            aud

        are created and controlled by the canonical token layer.
        """

        if user is None:
            raise UserNotFound()

        if not getattr(
            user,
            "is_active",
            False,
        ):
            raise UserDisabled()

        token, _claims = create_access_token(
            user_id=str(user.pk),
        )

        return token

    @staticmethod
    def issue_refresh_token(
        user,
    ) -> str:
        """
        Issue a canonical refresh token.

        Token construction belongs exclusively to
        ``univa_jwt.tokens``.

        No caller-supplied JWT claims are accepted here.

        The canonical token layer owns:

            sub
            jti
            token_type
            iat
            exp
            iss
            aud
        """

        if user is None:
            raise UserNotFound()

        if not getattr(
            user,
            "is_active",
            False,
        ):
            raise UserDisabled()

        token, _claims = create_refresh_token(
            user_id=str(user.pk),
        )

        return token

    @staticmethod
    def issue_token_pair(
        user,
    ) -> tuple[str, str]:
        """
        Issue a canonical access/refresh token pair.

        Returns
        -------
        tuple[str, str]
            (access_token, refresh_token)

        JWT construction remains exclusively owned by
        ``univa_jwt.tokens``.

        No caller-supplied JWT claims are accepted.
        """

        if user is None:
            raise UserNotFound()

        if not getattr(
            user,
            "is_active",
            False,
        ):
            raise UserDisabled()

        access_token = (
            JWTAuthenticationService.issue_access_token(
                user,
            )
        )

        refresh_token = (
            JWTAuthenticationService.issue_refresh_token(
                user,
            )
        )

        return (
            access_token,
            refresh_token,
        )

    # =========================================================================
    # Refresh-token validation
    # =========================================================================

    @staticmethod
    def authenticate_refresh_token(
        token: str,
    ) -> tuple[Any, TokenClaims]:
        """
        Validate a refresh token through the canonical token boundary and
        resolve its user.

        This method does NOT rotate the token.
        """

        if not isinstance(
            token,
            str,
        ) or not token.strip():
            raise JSONRefreshTokenExpired()

        try:
            claims = validate_refresh_token(
                token.strip(),
            )

            user = resolve_user(
                claims.user_id,
            )

        except Exception as exc:
            raise JSONRefreshTokenExpired() from exc

        return user, claims

    # =========================================================================
    # Refresh-token rotation
    # =========================================================================

    @staticmethod
    def refresh_access_token(
        refresh_token_value: str,
    ):
        """
        Rotate a refresh token through the canonical refresh service.

        This method intentionally does NOT:

            - query a RefreshToken model
            - inspect a blacklist
            - manually check expiration
            - manually check revocation
            - construct replacement JWTs
            - manually revoke the old token

        Those responsibilities belong to the canonical refresh pipeline.
        """

        if not isinstance(
            refresh_token_value,
            str,
        ) or not refresh_token_value.strip():
            raise JSONRefreshTokenExpired()

        try:
            result = rotate_refresh_token(
                refresh_token_value.strip(),
            )

        except Exception as exc:
            raise JSONRefreshTokenExpired() from exc

        return result

    # =========================================================================
    # Refresh-token revocation
    # =========================================================================

    @staticmethod
    def revoke_refresh_token(
        refresh_token_value: str,
    ) -> bool:
        """
        Revoke a refresh token through the canonical token/revocation layer.

        The canonical implementation is intentionally imported lazily so
        authentication module imports cannot create circular dependencies.
        """

        if not isinstance(
            refresh_token_value,
            str,
        ) or not refresh_token_value.strip():
            return False

        try:
            claims = validate_refresh_token(
                refresh_token_value.strip(),
            )
        except Exception:
            return False

        try:
            from .revocation import revoke_token

            revoke_token(
                jti=claims.jti,
                expires_at=claims.expires_at,
                user_id=claims.user_id,
                token_type=claims.token_type,
            )

            return True

        except Exception:
            return False


# =============================================================================
# Module-level convenience functions
# =============================================================================


def authenticate_access_token(
    token: str,
):
    """Module-level compatibility wrapper."""

    return JWTAuthenticationService.authenticate_access_token(
        token,
    )


def authenticate_access_token_with_claims(
    token: str,
) -> tuple[Any, TokenClaims]:
    """Module-level compatibility wrapper returning user and claims."""

    return JWTAuthenticationService.authenticate_access_token_with_claims(
        token,
    )


def authenticate_request(
    request,
):
    """Module-level compatibility wrapper."""

    return JWTAuthenticationService.authenticate_request(
        request,
    )


def authenticate_credentials(
    *,
    email: str | None = None,
    phone_number: str | None = None,
    password: str | None = None,
):
    """Module-level compatibility wrapper."""

    return JWTAuthenticationService.authenticate_credentials(
        email=email,
        phone_number=phone_number,
        password=password,
    )


def issue_access_token(
    user,
) -> str:
    """Module-level compatibility wrapper."""

    return JWTAuthenticationService.issue_access_token(
        user,
    )


def issue_refresh_token(
    user,
) -> str:
    """Module-level compatibility wrapper."""

    return JWTAuthenticationService.issue_refresh_token(
        user,
    )


def issue_token_pair(
    user,
) -> tuple[str, str]:
    """Module-level compatibility wrapper."""

    return JWTAuthenticationService.issue_token_pair(
        user,
    )


def authenticate_refresh_token(
    token: str,
) -> tuple[Any, TokenClaims]:
    """Module-level compatibility wrapper."""

    return JWTAuthenticationService.authenticate_refresh_token(
        token,
    )


def refresh_access_token(
    refresh_token_value: str,
):
    """Module-level compatibility wrapper."""

    return JWTAuthenticationService.refresh_access_token(
        refresh_token_value,
    )


def revoke_refresh_token(
    refresh_token_value: str,
) -> bool:
    """Module-level compatibility wrapper."""

    return JWTAuthenticationService.revoke_refresh_token(
        refresh_token_value,
    )


__all__ = [
    "JWTAuthenticationService",
    "authenticate_access_token",
    "authenticate_access_token_with_claims",
    "authenticate_request",
    "authenticate_credentials",
    "issue_access_token",
    "issue_refresh_token",
    "issue_token_pair",
    "authenticate_refresh_token",
    "refresh_access_token",
    "revoke_refresh_token",
]
