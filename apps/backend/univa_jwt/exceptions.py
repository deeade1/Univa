"""
Exceptions raised by the Univa JWT subsystem.

Application code should catch these exceptions instead of depending on
PyJWT exceptions directly.

The JWT subsystem deliberately exposes its own exception hierarchy so
application code remains independent of the underlying cryptographic
library.
"""


class UnivaJWTError(Exception):
    """Base exception for all Univa JWT errors."""


class TokenError(UnivaJWTError):
    """Base exception for token-related errors."""


class TokenEncodeError(TokenError):
    """
    The JWT could not be encoded.

    This represents a failure while creating/signing a JWT and is distinct
    from a failure while decoding or validating an existing JWT.
    """


class TokenDecodeError(TokenError):
    """
    The token could not be decoded.

    This normally represents malformed JWT input or a low-level decoding
    failure.
    """


class TokenExpiredError(TokenError):
    """The token has expired."""


class TokenInvalidError(TokenError):
    """The token is structurally or cryptographically invalid."""


class TokenTypeError(TokenError):
    """The token is not the expected token type."""


class TokenMissingError(TokenError):
    """Authentication token was not supplied."""


class TokenRevokedError(TokenError):
    """The token has been revoked."""


class RefreshTokenError(TokenError):
    """Refresh-token processing failed."""


class RefreshTokenReuseError(RefreshTokenError):
    """
    A refresh token that had already been rotated/revoked was presented
    again.

    This is important for refresh-token rotation security.
    """


class RefreshTokenNotFoundError(RefreshTokenError):
    """No matching server-side refresh-token record exists."""


class RefreshTokenExpiredError(RefreshTokenError):
    """The refresh-token record has expired."""


class JSONRefreshTokenExpired(TokenError):
    """
    Refresh token has expired (legacy compatibility).

    DEPRECATED: Use TokenExpiredError instead.
    """


class AuthenticationError(UnivaJWTError):
    """Authentication failed."""


class InvalidCredentials(AuthenticationError):
    """The provided credentials are invalid."""


class UserNotFound(AuthenticationError):
    """The user could not be found."""


class UserDisabled(AuthenticationError):
    """The user account is disabled."""


class PermissionDenied(UnivaJWTError):
    """The authenticated user lacks permission."""


class WrongUsage(UnivaJWTError):
    """The API was used incorrectly."""


__all__ = [
    "UnivaJWTError",
    "TokenError",
    "TokenEncodeError",
    "TokenDecodeError",
    "TokenExpiredError",
    "TokenInvalidError",
    "TokenTypeError",
    "TokenMissingError",
    "TokenRevokedError",
    "RefreshTokenError",
    "RefreshTokenReuseError",
    "RefreshTokenNotFoundError",
    "RefreshTokenExpiredError",
    "JSONRefreshTokenExpired",
    "AuthenticationError",
    "InvalidCredentials",
    "UserNotFound",
    "UserDisabled",
    "PermissionDenied",
    "WrongUsage",
]