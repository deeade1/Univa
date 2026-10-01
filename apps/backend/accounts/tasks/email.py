# apps/backend/accounts/tasks/email.py

"""
Celery tasks for account email operations.

ARCHITECTURE
------------

Email-verification business logic is owned exclusively by:

    accounts.email_service

This module is an asynchronous orchestration layer.

It MUST NOT:

    - generate verification tokens
    - validate verification tokens
    - decode signed-token payloads
    - construct verification URLs
    - mark accounts as verified
    - implement email-verification business rules

The canonical resend workflow is:

    GraphQL
        │
        ▼
    send_confirmation_email_task
        │
        ▼
    accounts.email_service.resend_confirmation_email()
        │
        ├── check verification state
        ├── generate signed token
        ├── construct verification URL
        ├── send email
        └── return token

Authentication JWTs remain completely outside this workflow.
"""

from __future__ import annotations

import logging

from celery import shared_task

from accounts.email_service import (
    EmailVerificationAlreadyCompletedError,
    resend_confirmation_email,
)
from accounts.models.user import User


logger = logging.getLogger(__name__)


# =============================================================================
# Send / Resend Confirmation Email
# =============================================================================


@shared_task(
    bind=True,
    name="accounts.tasks.email.send_confirmation_email",
    max_retries=5,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def send_confirmation_email_task(
    self,
    user_id: int,
) -> str | None:
    """
    Send an account email-verification message asynchronously.

    Parameters
    ----------
    user_id:
        Primary key of the User whose verification email should be sent.

    Returns
    -------
    str | None
        The verification token returned by
        ``accounts.email_service.resend_confirmation_email()``.

        ``None`` is returned when the email has already been verified.

    Notes
    -----
    The task deliberately contains no email-verification business logic.

    Token generation, token semantics, URL construction, verification
    state, and actual email delivery all remain inside the service layer.
    """

    # -------------------------------------------------------------------------
    # Resolve the account.
    #
    # A missing user is a permanent condition. There is no reason to retry
    # the task because another attempt cannot make the user appear.
    # -------------------------------------------------------------------------

    try:
        user = User.objects.get(pk=user_id)

    except User.DoesNotExist:
        logger.warning(
            "Unable to send confirmation email: user does not exist.",
            extra={
                "user_id": user_id,
                "task_id": self.request.id,
            },
        )

        return None

    # -------------------------------------------------------------------------
    # Delegate the complete verification-email workflow to the service.
    # -------------------------------------------------------------------------

    try:
        verification_token = resend_confirmation_email(user)

    except EmailVerificationAlreadyCompletedError:
        # ---------------------------------------------------------------------
        # Already verified is a normal terminal state.
        #
        # Retrying would be pointless and could generate unnecessary work.
        # ---------------------------------------------------------------------

        logger.info(
            "Skipping confirmation email: email is already verified.",
            extra={
                "user_id": user_id,
                "task_id": self.request.id,
            },
        )

        return None

    except Exception:
        # ---------------------------------------------------------------------
        # Do not swallow failures.
        #
        # EmailVerificationError and provider/infrastructure failures are
        # allowed to propagate so Celery can mark the task as failed.
        #
        # We intentionally do NOT use:
        #
        #     autoretry_for=(Exception,)
        #
        # because that would retry programming errors and permanent
        # configuration failures indiscriminately.
        #
        # Once the email provider's transient exception hierarchy is
        # finalized, specific exceptions can be configured for retry.
        # ---------------------------------------------------------------------

        logger.exception(
            "Failed to send account confirmation email.",
            extra={
                "user_id": user_id,
                "task_id": self.request.id,
            },
        )

        raise

    logger.info(
        "Account confirmation email sent successfully.",
        extra={
            "user_id": user_id,
            "task_id": self.request.id,
        },
    )

    return verification_token


__all__ = [
    "send_confirmation_email_task",
]