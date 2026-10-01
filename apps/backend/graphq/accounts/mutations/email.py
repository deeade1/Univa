"""
GraphQL mutations for account email verification.

ARCHITECTURE
------------

Email verification is owned exclusively by:

    accounts.email_service

This GraphQL module is a transport-layer adapter.

It MUST NOT:

    - generate verification tokens
    - validate signed tokens directly
    - construct verification URLs
    - manipulate verification-token payloads
    - depend on univa_jwt
    - implement email-verification business logic
    - send verification emails directly

Responsibilities
----------------

ConfirmEmail
    Delegates token confirmation to:

        accounts.email_service.confirm_email()

ResendConfirmationEmail
    Resolves the account and schedules:

        accounts.tasks.email.send_confirmation_email_task

The Celery task then delegates the actual email-verification workflow
to:

    accounts.email_service.resend_confirmation_email()

Therefore the dependency direction is:

    GraphQL
        │
        ├── confirm_email()
        │
        └── send_confirmation_email_task.delay()
                    │
                    ▼
            email_service
                    │
                    └── resend_confirmation_email()
"""

from __future__ import annotations

import graphene
from graphene import relay
from graphql import GraphQLError

from accounts.email_service import (
    EmailVerificationError,
    confirm_email,
)
from accounts.models.user import User
from accounts.tasks.email import send_confirmation_email_task


# =============================================================================
# Confirm Email
# =============================================================================


class ConfirmEmail(relay.ClientIDMutation):
    """
    Confirm a user's email address using a signed verification token.

    Token validation and account verification are delegated entirely to:

        accounts.email_service.confirm_email()
    """

    class Input:
        token = graphene.String(
            required=True,
        )

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    def mutate_and_get_payload(
        cls,
        root,
        info,
        **input,
    ):
        token = input.get("token")

        if not token:
            raise GraphQLError(
                "Verification token is required."
            )

        try:
            user = confirm_email(token)

        except EmailVerificationError as exc:
            raise GraphQLError(
                str(exc)
            ) from exc

        except Exception as exc:
            raise GraphQLError(
                "Unable to verify email address."
            ) from exc

        return cls(
            success=True,
            message=(
                "Email verified successfully."
                if user.email_verified
                else "Email verification completed."
            ),
        )


# =============================================================================
# Resend Confirmation Email
# =============================================================================


class ResendConfirmationEmail(relay.ClientIDMutation):
    """
    Queue an account email-verification message.

    This mutation deliberately does not:

        - generate a verification token
        - validate a verification token
        - construct a verification URL
        - send an email
        - determine whether the email is already verified

    Those responsibilities belong to:

        accounts.email_service

    The asynchronous execution boundary is:

        send_confirmation_email_task.delay(user.pk)
    """

    class Input:
        email = graphene.String(
            required=True,
        )

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    def mutate_and_get_payload(
        cls,
        root,
        info,
        **input,
    ):
        email = input.get("email")

        if not email:
            raise GraphQLError(
                "Email address is required."
            )

        normalized_email = email.strip()

        if not normalized_email:
            raise GraphQLError(
                "Email address is required."
            )

        try:
            user = User.objects.get(
                email__iexact=normalized_email,
            )

        except User.DoesNotExist as exc:
            raise GraphQLError(
                "No account exists with that email."
            ) from exc

        # ---------------------------------------------------------------------
        # Queue the verification email.
        #
        # GraphQL intentionally does not call the service directly.
        #
        # The task is responsible for asynchronous orchestration and delegates
        # the actual verification-email workflow to email_service.
        # ---------------------------------------------------------------------

        try:
            send_confirmation_email_task.delay(user.pk)

        except Exception as exc:
            raise GraphQLError(
                "Unable to queue the verification email."
            ) from exc

        return cls(
            success=True,
            message="Verification email has been queued.",
        )


# =============================================================================
# Email Mutations
# =============================================================================


class EmailMutations(graphene.ObjectType):
    """
    Email-verification mutations exposed by the account GraphQL API.
    """

    confirm_email = ConfirmEmail.Field()
    resend_confirmation_email = ResendConfirmationEmail.Field()


# =============================================================================
# Public API
# =============================================================================


__all__ = [
    "ConfirmEmail",
    "ResendConfirmationEmail",
    "EmailMutations",
]