# apps/backend/accounts/utils.py

"""
Accounts utility helpers.

ARCHITECTURE
------------

This module contains account-level utility functions.

Authentication JWTs are owned exclusively by:

    univa_jwt

The Accounts application MUST NOT:

    - construct JWT payloads
    - encode JWTs directly
    - decode authentication JWTs
    - maintain refresh-token database records
    - access univa_jwt.models.RefreshToken
    - implement refresh-token rotation
    - implement refresh-token revocation
    - create authentication token claims manually

Canonical authentication boundaries:

    Access token
        -> univa_jwt.tokens.create_access_token()
        or another canonical univa_jwt token factory

    Refresh token
        -> univa_jwt.tokens.create_refresh_token()

Refresh-token rotation:

    -> univa_jwt.refresh

Refresh-token revocation:

    -> univa_jwt.revocation


IMPORTANT
---------

Email-verification tokens are NOT authentication JWTs.

Email verification is owned by:

    accounts.email_service

Therefore:

    generate_verification_token()

is only a generic cryptographically secure random-token helper.

It must NOT be used to create authentication JWTs.
"""


from __future__ import annotations

import secrets

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import models
from django.utils import timezone


# =============================================================================
# VERIFICATION TOKENS
# =============================================================================


def generate_verification_token(
    length: int = 32,
) -> str:
    """
    Generate a cryptographically secure random token.

    This helper generates an opaque random account-level token.

    It is NOT a JWT.

    Email-verification business logic belongs to:

        accounts.email_service

    This function therefore performs no:

        - JWT encoding
        - JWT decoding
        - claim construction
        - token-type assignment
        - token validation
        - URL construction
    """

    if not isinstance(length, int):
        raise TypeError(
            "Token length must be an integer.",
        )

    if length <= 0:
        raise ValueError(
            "Token length must be greater than zero.",
        )

    return secrets.token_urlsafe(
        length,
    )


# =============================================================================
# ROLE HELPERS
# =============================================================================


class RoleMixin:
    """
    Helpers for resolving active user roles.

    This mixin contains no authentication-token logic.
    """

    @property
    def active_roles(self):
        """
        Return a cached set of:

            (app_name, role_name)

        for active, non-expired roles.
        """

        if not hasattr(
            self,
            "_cached_roles",
        ):
            now = timezone.now()

            self._cached_roles = set(
                self.user_roles.filter(
                    is_active=True,
                )
                .filter(
                    models.Q(
                        expires_at__isnull=True,
                    )
                    | models.Q(
                        expires_at__gt=now,
                    )
                )
                .values_list(
                    "role__app_name",
                    "role__name",
                )
            )

        return self._cached_roles

    def has_role(
        self,
        app,
        role_name,
    ):
        """
        Check whether the user has a specific active role.
        """

        return (
            app,
            role_name,
        ) in self.active_roles

    def has_any_role(
        self,
        app,
        roles,
    ):
        """
        Check whether the user has any of the supplied active roles.
        """

        return any(
            (
                app,
                role,
            ) in self.active_roles
            for role in roles
        )

    def get_roles(
        self,
        app=None,
    ):
        """
        Return active, non-expired UserRole records.

        Optionally restrict the queryset to one application.
        """

        now = timezone.now()

        queryset = (
            self.user_roles
            .filter(
                is_active=True,
            )
            .filter(
                models.Q(
                    expires_at__isnull=True,
                )
                | models.Q(
                    expires_at__gt=now,
                )
            )
            .select_related(
                "role",
            )
        )

        if app:
            queryset = queryset.filter(
                role__app_name=app,
            )

        return queryset


# =============================================================================
# CONTACT VALIDATION
# =============================================================================


def validate_contact_info(
    contact,
):
    """
    Validate an email address or phone number.

    Returns
    -------

    str
        ``"email"`` or ``"phone_number"``.

    Raises
    ------

    ValueError
        If the supplied contact is invalid.
    """

    if not isinstance(
        contact,
        str,
    ):
        raise ValueError(
            "Contact must be a string.",
        )

    contact = contact.strip()

    if not contact:
        raise ValueError(
            "Contact is required.",
        )

    try:
        # ---------------------------------------------------------------------
        # Email
        # ---------------------------------------------------------------------

        if "@" in contact:
            validate_email(
                contact,
            )

            return "email"

        # ---------------------------------------------------------------------
        # Phone
        # ---------------------------------------------------------------------

        if not contact.startswith("+"):
            raise ValidationError(
                "Phone number must include country code.",
            )

        if len(contact) < 8:
            raise ValidationError(
                "Phone number too short.",
            )

        return "phone_number"

    except ValidationError as exc:
        raise ValueError(
            str(exc),
        ) from exc


# =============================================================================
# PASSWORD VALIDATION
# =============================================================================


def validate_password_strength(
    password,
):
    """
    Validate the configured minimum password length.

    This helper intentionally performs only account-password validation.

    Authentication token logic does not belong here.
    """

    if not isinstance(
        password,
        str,
    ):
        raise ValueError(
            "Password must be a string.",
        )

    if len(password) < settings.MIN_PASSWORD_LENGTH:
        raise ValueError(
            (
                "Password must be at least "
                f"{settings.MIN_PASSWORD_LENGTH} characters."
            )
        )

    # Additional password-strength rules can be added here.


# =============================================================================
# JWT ISSUANCE
# =============================================================================


def generate_tokens(
    user,
    request=None,
):
    """
    Generate canonical authentication tokens for a user.

    This function is intentionally a thin Accounts compatibility
    boundary.

    ALL JWT implementation remains inside ``univa_jwt``.

    Access token:

        univa_jwt.tokens.create_access_token()

    Refresh token:

        univa_jwt.tokens.create_refresh_token()

    Parameters
    ----------

    user:
        Django user instance.

    request:
        Accepted for backwards compatibility.

        The canonical JWT service does not currently require the request,
        so it is intentionally ignored.

    Returns
    -------

    tuple[str, str]
        ``(access_token, refresh_token)``

    Raises
    ------

    ValueError
        If the user is missing, unsaved, or inactive.

    IMPORTANT
    ---------

    This function does NOT:

        - construct JWT payloads
        - call jwt.encode()
        - call jwt_decode()
        - call jwt_payload()
        - access RefreshToken.objects
        - import univa_jwt.models.RefreshToken
        - create deprecated database-backed refresh-token records
        - perform refresh-token rotation
        - revoke refresh tokens

    Those responsibilities belong exclusively to ``univa_jwt``.
    """

    # ``request`` is intentionally retained in the public signature for
    # backwards compatibility with existing Accounts callers.
    del request

    # -------------------------------------------------------------------------
    # Validate user
    # -------------------------------------------------------------------------

    if user is None:
        raise ValueError(
            "User is required.",
        )

    user_id = getattr(
        user,
        "pk",
        None,
    )

    if user_id is None:
        raise ValueError(
            "User must have a primary key.",
        )

    if not getattr(
        user,
        "is_active",
        False,
    ):
        raise ValueError(
            "User account is disabled.",
        )

    # -------------------------------------------------------------------------
    # Canonical JWT service
    # -------------------------------------------------------------------------
    #
    # Import locally so accounts.utils does not create an unnecessary
    # module-import dependency during Django startup.
    #
    # The JWT implementation remains entirely inside univa_jwt.
    # -------------------------------------------------------------------------

    from univa_jwt.tokens import (
        create_access_token,
        create_refresh_token,
    )

    # -------------------------------------------------------------------------
    # Access token
    # -------------------------------------------------------------------------

    access_token, _access_claims = create_access_token(
        user_id=str(user_id),
    )

    # -------------------------------------------------------------------------
    # Refresh token
    # -------------------------------------------------------------------------

    refresh_token, _refresh_claims = create_refresh_token(
        user_id=str(user_id),
    )

    return (
        access_token,
        refresh_token,
    )


# =============================================================================
# PUBLIC API
# =============================================================================


__all__ = [
    "generate_verification_token",
    "RoleMixin",
    "validate_contact_info",
    "validate_password_strength",
    "generate_tokens",
]
