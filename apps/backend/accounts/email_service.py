"""
Accounts email verification service.

ARCHITECTURE
------------

This module is the canonical owner of email-verification tokens.

Email-verification tokens are ACCOUNT tokens, not authentication JWTs.

Therefore:

    accounts.email_service
        ├── generate verification token
        ├── validate verification token
        ├── resolve user
        ├── mark email as verified
        ├── build verification URL
        ├── send verification email
        └── resend verification email

Authentication JWTs remain exclusively owned by:

    univa_jwt

This module MUST NOT:
    - create access JWTs
    - create refresh JWTs
    - decode authentication JWTs
    - use token_type="activation"
    - depend on univa_jwt
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.mail import send_mail
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


logger = logging.getLogger(__name__)

UserModel = get_user_model()


# =============================================================================
# Configuration
# =============================================================================

DEFAULT_VERIFICATION_TIMEOUT_HOURS = 24

EMAIL_VERIFICATION_PURPOSE = "email_verification"

EMAIL_VERIFICATION_SALT = "accounts.email-verification"


def _verification_timeout_seconds() -> int:
    """
    Return the configured email-verification lifetime in seconds.

    The application may configure:

        ACCOUNT_VERIFICATION_TIMEOUT_HOURS

    in Django settings.

    Defaults to 24 hours.
    """

    hours = getattr(
        settings,
        "ACCOUNT_VERIFICATION_TIMEOUT_HOURS",
        DEFAULT_VERIFICATION_TIMEOUT_HOURS,
    )

    try:
        hours = float(hours)
    except (TypeError, ValueError):
        logger.warning(
            "Invalid ACCOUNT_VERIFICATION_TIMEOUT_HOURS=%r. "
            "Falling back to %s hours.",
            hours,
            DEFAULT_VERIFICATION_TIMEOUT_HOURS,
        )
        hours = DEFAULT_VERIFICATION_TIMEOUT_HOURS

    if hours <= 0:
        logger.warning(
            "ACCOUNT_VERIFICATION_TIMEOUT_HOURS must be greater than zero. "
            "Falling back to %s hours.",
            DEFAULT_VERIFICATION_TIMEOUT_HOURS,
        )
        hours = DEFAULT_VERIFICATION_TIMEOUT_HOURS

    return int(hours * 60 * 60)


def _verification_timeout_hours() -> int:
    """
    Return the configured verification lifetime for user-facing messaging.
    """

    seconds = _verification_timeout_seconds()

    return max(1, seconds // (60 * 60))


# =============================================================================
# Exceptions
# =============================================================================


class EmailVerificationError(Exception):
    """
    Base exception for account email-verification failures.
    """


class EmailVerificationTokenError(EmailVerificationError):
    """
    Raised when an email-verification token is invalid or expired.
    """


class EmailVerificationAlreadyCompletedError(EmailVerificationError):
    """
    Raised when an operation requires an unverified email address but
    the user's email is already verified.
    """


class EmailVerificationConfigurationError(EmailVerificationError):
    """
    Raised when email verification cannot be configured safely.
    """


# =============================================================================
# Token payload
# =============================================================================


@dataclass(frozen=True, slots=True)
class EmailVerificationClaims:
    """
    Normalized claims extracted from an email-verification token.
    """

    user_id: str
    purpose: str


# =============================================================================
# Signer
# =============================================================================


EMAIL_VERIFICATION_SIGNER = TimestampSigner(
    salt=EMAIL_VERIFICATION_SALT,
)


# =============================================================================
# Internal helpers
# =============================================================================


def _require_user(user: Any) -> Any:
    """
    Validate that a user-like object has the minimum state required by
    the email-verification service.
    """

    if user is None:
        raise EmailVerificationError(_("User is required."))

    if not getattr(user, "pk", None):
        raise EmailVerificationError(_("User must have a primary key."))

    return user


def _require_user_email(user: Any) -> str:
    """
    Return a normalized user email address.

    Email verification is only meaningful for users that have an email.
    """

    email = getattr(user, "email", None)

    if not email:
        raise EmailVerificationError(
            _("This account does not have an email address.")
        )

    email = str(email).strip()

    if not email:
        raise EmailVerificationError(
            _("This account does not have an email address.")
        )

    return email


def _build_signed_value(user: Any) -> str:
    """
    Build the canonical signed value.

    The purpose is included inside the signed value so that a token
    generated for email verification cannot be interpreted as an
    unrelated account token.
    """

    _require_user(user)

    return f"{EMAIL_VERIFICATION_PURPOSE}:{user.pk}"


def _parse_signed_value(value: str) -> EmailVerificationClaims:
    """
    Parse and validate the signed token payload.

    Expected format:

        email_verification:<user_id>
    """

    if not isinstance(value, str) or not value:
        raise EmailVerificationTokenError(
            _("Invalid verification token.")
        )

    try:
        purpose, user_id = value.split(":", 1)
    except ValueError as exc:
        raise EmailVerificationTokenError(
            _("Invalid verification token.")
        ) from exc

    if purpose != EMAIL_VERIFICATION_PURPOSE:
        raise EmailVerificationTokenError(
            _("Invalid verification token purpose.")
        )

    if not user_id:
        raise EmailVerificationTokenError(
            _("Invalid verification token.")
        )

    return EmailVerificationClaims(
        user_id=user_id,
        purpose=purpose,
    )


def _resolve_user(user_id: str) -> Any:
    """
    Resolve the Django user represented by a validated verification token.
    """

    try:
        user = UserModel.objects.get(pk=user_id)
    except (UserModel.DoesNotExist, ValueError, TypeError) as exc:
        raise EmailVerificationTokenError(
            _("The account associated with this verification token was not found.")
        ) from exc

    if not getattr(user, "is_active", True):
        raise EmailVerificationTokenError(
            _("This account is inactive.")
        )

    return user


def _frontend_url() -> str:
    """
    Return the configured frontend base URL.

    The trailing slash is removed so URL construction remains predictable.
    """

    frontend = getattr(settings, "FRONTEND_URL", None)

    if not frontend:
        raise EmailVerificationConfigurationError(
            _(
                "FRONTEND_URL is not configured. "
                "Email verification cannot generate a verification URL."
            )
        )

    return str(frontend).rstrip("/")


# =============================================================================
# Token generation
# =============================================================================


def generate_confirmation_token(user: Any) -> str:
    """
    Generate a signed, timestamped email-verification token.

    IMPORTANT:
        This is NOT a JWT.

    The token is scoped to:

        email_verification

    and is validated only by this service.
    """

    _require_user(user)

    value = _build_signed_value(user)

    return EMAIL_VERIFICATION_SIGNER.sign(value)


# =============================================================================
# Token validation
# =============================================================================


def verify_confirmation_token(
    token: str,
    *,
    mark_verified: bool = False,
) -> Any:
    """
    Validate an email-verification token and return the associated user.

    Args:
        token:
            Signed email-verification token.

        mark_verified:
            When True, atomically mark the user's email as verified after
            successful token validation.

    Returns:
        The validated User instance.

    Raises:
        EmailVerificationTokenError:
            If the token is invalid, expired, malformed, or references
            an unavailable account.
    """

    if not isinstance(token, str):
        raise EmailVerificationTokenError(
            _("Invalid verification token.")
        )

    token = token.strip()

    if not token:
        raise EmailVerificationTokenError(
            _("Verification token is required.")
        )

    max_age = _verification_timeout_seconds()

    try:
        signed_value = EMAIL_VERIFICATION_SIGNER.unsign(
            token,
            max_age=max_age,
        )
    except SignatureExpired as exc:
        raise EmailVerificationTokenError(
            _("Verification link has expired.")
        ) from exc
    except BadSignature as exc:
        raise EmailVerificationTokenError(
            _("Invalid verification token.")
        ) from exc

    claims = _parse_signed_value(signed_value)

    user = _resolve_user(claims.user_id)

    if getattr(user, "email_verified", False):
        return user

    if mark_verified:
        _mark_email_verified(user)

    return user


# =============================================================================
# Email verification state
# =============================================================================


def _mark_email_verified(user: Any) -> Any:
    """
    Mark a user's email as verified.

    Prefer the domain model's verify_email() method when available so the
    User model remains responsible for its own state transition.
    """

    verify_email = getattr(user, "verify_email", None)

    if callable(verify_email):
        verify_email()
        return user

    # Defensive fallback for compatibility with older User implementations.
    user.email_verified = True

    if hasattr(user, "email_verified_at"):
        user.email_verified_at = timezone.now()

        user.save(
            update_fields=[
                "email_verified",
                "email_verified_at",
            ]
        )
    else:
        user.save(
            update_fields=[
                "email_verified",
            ]
        )

    return user


def confirm_email(token: str) -> Any:
    """
    Public application API for completing email verification.

    This is the preferred function for GraphQL/HTTP confirmation consumers.

    Returns:
        The verified User instance.
    """

    user = verify_confirmation_token(
        token,
        mark_verified=False,
    )

    if not getattr(user, "email_verified", False):
        _mark_email_verified(user)

    return user


# =============================================================================
# Verification URL
# =============================================================================


def build_confirmation_url(
    user: Any,
    token: str,
) -> str:
    """
    Build the canonical frontend email-verification URL.

    Canonical route:

        /auth/confirmmail?token=<token>
    """

    _require_user(user)

    if not isinstance(token, str) or not token.strip():
        raise EmailVerificationTokenError(
            _("Verification token is required.")
        )

    frontend = _frontend_url()

    return (
        f"{frontend}/auth/confirmmail"
        f"?token={token}"
    )


# =============================================================================
# Email content
# =============================================================================


def build_confirmation_subject() -> str:
    """
    Return the email-verification subject.
    """

    return "Verify your Univa email"


def build_confirmation_message(
    user: Any,
    verification_url: str,
) -> str:
    """
    Build the plain-text email-verification message.
    """

    _require_user(user)

    timeout_hours = _verification_timeout_hours()

    return (
        f"Hello,\n\n"
        f"Please verify the email address associated with your Univa account "
        f"by clicking the link below:\n\n"
        f"{verification_url}\n\n"
        f"This verification link expires in {timeout_hours} hours.\n\n"
        f"If you did not create this account, you can safely ignore this email.\n\n"
        f"Regards,\n"
        f"The Univa Team"
    )


# =============================================================================
# Send verification email
# =============================================================================


def send_confirmation_email(user: Any) -> str:
    """
    Generate and send an email-verification message.

    Returns:
        The generated verification token.

    Raises:
        EmailVerificationAlreadyCompletedError:
            If the email is already verified.
        EmailVerificationError:
            If the user/email/configuration is invalid.
    """

    _require_user(user)

    if getattr(user, "email_verified", False):
        raise EmailVerificationAlreadyCompletedError(
            _("Email has already been verified.")
        )

    email = _require_user_email(user)

    token = generate_confirmation_token(user)

    verification_url = build_confirmation_url(
        user,
        token,
    )

    subject = build_confirmation_subject()

    message = build_confirmation_message(
        user,
        verification_url,
    )

    from_email = getattr(
        settings,
        "DEFAULT_FROM_EMAIL",
        None,
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=from_email,
        recipient_list=[email],
        fail_silently=False,
    )

    logger.info(
        "Email verification message sent.",
        extra={
            "user_id": str(user.pk),
        },
    )

    return token


# =============================================================================
# Resend verification email
# =============================================================================


def resend_confirmation_email(user: Any) -> str:
    """
    Generate and send a fresh email-verification message.

    Resending intentionally generates a new timestamped signed token.
    Previous tokens remain independently valid until they expire because
    TimestampSigner is stateless.

    If single-use invalidation is required later, that should be implemented
    as an explicit account-verification token model rather than introducing
    JWT semantics into this service.
    """

    _require_user(user)

    if getattr(user, "email_verified", False):
        raise EmailVerificationAlreadyCompletedError(
            _("Email has already been verified.")
        )

    return send_confirmation_email(user)


# =============================================================================
# Public API
# =============================================================================


__all__ = [
    "EMAIL_VERIFICATION_PURPOSE",
    "EMAIL_VERIFICATION_SALT",
    "EmailVerificationClaims",
    "EmailVerificationError",
    "EmailVerificationTokenError",
    "EmailVerificationAlreadyCompletedError",
    "EmailVerificationConfigurationError",
    "generate_confirmation_token",
    "verify_confirmation_token",
    "confirm_email",
    "build_confirmation_url",
    "build_confirmation_subject",
    "build_confirmation_message",
    "send_confirmation_email",
    "resend_confirmation_email",
]