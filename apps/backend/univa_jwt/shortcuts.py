"""
Public shortcuts for Univa JWT.

All functions delegate to the canonical services.
"""

from univa_jwt.authentication import JWTAuthenticationService
from univa_jwt.constants import ACCESS_TOKEN
from univa_jwt.exceptions import TokenError


def get_token(
    user,
    **extra,
):
    """
    Get an access token for a user.
    """

    return JWTAuthenticationService.issue_access_token(
        user,
        **extra,
    )


def get_user_by_token(
    token,
):
    """
    Get a user from an access token.
    """

    return JWTAuthenticationService.authenticate_access_token(
        token,
    )


def get_refresh_token(
    token,
):
    """
    Get a refresh-token compatibility object.

    DEPRECATED:

        Use refresh.rotate_refresh_token()
        or tokens.validate_refresh_token()
        instead.
    """

    from univa_jwt.exceptions import AuthenticationError

    if not token:
        raise AuthenticationError(
            "Refresh token is required."
        )

    try:
        from univa_jwt.tokens import validate_refresh_token
        from univa_jwt.validation import resolve_user

        claims = validate_refresh_token(
            token,
        )

        user = resolve_user(
            claims.user_id,
        )

        class _CompatRefreshToken:
            """
            Compatibility wrapper for legacy callers.

            This is not a database model and must not become a new
            refresh-token implementation.
            """

            def __init__(
                self,
                user,
                token,
                claims,
            ):
                self.user = user
                self.token = token
                self.claims = claims
                self.created = claims.issued_at
                self.revoked = None
                self.user_id = user.pk

            def is_expired(
                self,
            ):
                return self.claims.is_expired

            def is_valid(
                self,
            ):
                return (
                    not self.is_expired()
                    and self.user.is_active
                )

            def revoke(
                self,
                **kwargs,
            ):
                from univa_jwt.revocation import revoke_claims

                return revoke_claims(
                    self.claims,
                )

            def __str__(
                self,
            ):
                return f"RefreshToken<{self.claims.jti}>"

        return _CompatRefreshToken(
            user,
            token,
            claims,
        )

    except TokenError as exc:
        from univa_jwt.exceptions import AuthenticationError

        raise AuthenticationError(
            str(exc),
        ) from exc


def get_token_for_user(
    user,
    token_type=ACCESS_TOKEN,
    **extra,
):
    """
    Get a token for a user.

    Legacy compatibility wrapper.
    """

    if token_type == ACCESS_TOKEN:
        return JWTAuthenticationService.issue_access_token(
            user,
            **extra,
        )

    return JWTAuthenticationService.issue_refresh_token(
        user,
        **extra,
    )


def validate_token_type(
    token: str,
    expected_type: str,
) -> bool:
    """
    Validate a JWT and ensure it has the expected token type.

    This is a compatibility helper.

    Canonical validation belongs to univa_jwt.tokens.
    """

    from univa_jwt.tokens import decode_token

    try:
        decode_token(
            token,
            expected_token_type=expected_type,
        )

    except TokenError:
        return False

    return True


__all__ = [
    "get_token",
    "get_user_by_token",
    "get_refresh_token",
    "get_token_for_user",
    "validate_token_type",
]