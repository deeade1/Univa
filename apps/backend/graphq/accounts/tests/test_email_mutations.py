"""
Tests for GraphQL account email-verification mutations.

Target module:
    graphq.accounts.mutations.email

Architecture under test
-----------------------

GraphQL
    │
    ├── ConfirmEmail
    │       └── accounts.email_service.confirm_email()
    │
    └── ResendConfirmationEmail
            └── accounts.tasks.email.send_confirmation_email_task.delay()
                    │
                    ▼
              email service workflow

These tests intentionally test the GraphQL adapter contract.

They do NOT test:

    - JWT generation
    - verification-token generation
    - signed-token internals
    - verification URL construction
    - email delivery
    - Celery task internals
    - accounts.email_service internals

Those responsibilities belong to their respective modules.
"""

from unittest.mock import Mock, patch

import pytest

from django.contrib.auth import get_user_model
from django.test import TestCase

from graphql import GraphQLError

from accounts.email_service import EmailVerificationError
from graphq.accounts.mutations.email import (
    ConfirmEmail,
    EmailMutations,
    ResendConfirmationEmail,
)


User = get_user_model()


# =============================================================================
# TEST HELPERS
# =============================================================================


class EmailMutationTestMixin:
    """
    Shared test helpers.
    """

    @staticmethod
    def create_user(
        *,
        email="user@example.com",
        email_verified=False,
    ):
        """
        Create a minimal application user.

        Uses create_user() so this remains compatible with the project's
        custom User model as long as it exposes the normal Django manager API.
        """

        user = User.objects.create_user(
            email=email,
            password="TestPassword123!",
        )

        user.email_verified = email_verified
        user.save(
            update_fields=["email_verified"],
        )

        return user


# =============================================================================
# CONFIRM EMAIL
# =============================================================================


@pytest.mark.django_db
class TestConfirmEmailMutation(EmailMutationTestMixin):
    """
    Tests for ConfirmEmail.

    ConfirmEmail is deliberately thin.

    The mutation should delegate token processing entirely to
    accounts.email_service.confirm_email().
    """

    @patch(
        "graphq.accounts.mutations.email.confirm_email"
    )
    def test_confirm_email_delegates_to_email_service(
        self,
        mock_confirm_email,
    ):
        """
        ConfirmEmail must delegate token confirmation to the service.
        """

        user = self.create_user(
            email="verified@example.com",
            email_verified=True,
        )

        result = ConfirmEmail.mutate_and_get_payload(
            None,
            None,
            token="signed-verification-token",
        )

        mock_confirm_email.assert_called_once_with(
            "signed-verification-token",
        )

        assert result.success is True
        assert (
            result.message
            == "Email verified successfully."
        )

        # The service return value is the source of truth.
        assert user.email_verified is True

    def test_confirm_email_requires_token(self):
        """
        A missing token must fail at the GraphQL boundary.
        """

        with pytest.raises(GraphQLError) as exc_info:
            ConfirmEmail.mutate_and_get_payload(
                None,
                None,
            )

        assert (
            str(exc_info.value)
            == "Verification token is required."
        )

    def test_confirm_email_rejects_empty_token(self):
        """
        An empty token must fail before the service is called.
        """

        with patch(
            "graphq.accounts.mutations.email.confirm_email"
        ) as mock_confirm_email:

            with pytest.raises(GraphQLError) as exc_info:
                ConfirmEmail.mutate_and_get_payload(
                    None,
                    None,
                    token="",
                )

        mock_confirm_email.assert_not_called()

        assert (
            str(exc_info.value)
            == "Verification token is required."
        )

    def test_confirm_email_rejects_none_token(self):
        """
        None must fail before reaching the email service.
        """

        with patch(
            "graphq.accounts.mutations.email.confirm_email"
        ) as mock_confirm_email:

            with pytest.raises(GraphQLError) as exc_info:
                ConfirmEmail.mutate_and_get_payload(
                    None,
                    None,
                    token=None,
                )

        mock_confirm_email.assert_not_called()

        assert (
            str(exc_info.value)
            == "Verification token is required."
        )

    @patch(
        "graphq.accounts.mutations.email.confirm_email"
    )
    def test_confirm_email_translates_service_error(
        self,
        mock_confirm_email,
    ):
        """
        EmailVerificationError must become GraphQLError while preserving
        the service-level error message.
        """

        mock_confirm_email.side_effect = (
            EmailVerificationError(
                "Verification token has expired."
            )
        )

        with pytest.raises(GraphQLError) as exc_info:
            ConfirmEmail.mutate_and_get_payload(
                None,
                None,
                token="expired-token",
            )

        mock_confirm_email.assert_called_once_with(
            "expired-token",
        )

        assert (
            str(exc_info.value)
            == "Verification token has expired."
        )

    @patch(
        "graphq.accounts.mutations.email.confirm_email"
    )
    def test_confirm_email_sanitizes_unexpected_exception(
        self,
        mock_confirm_email,
    ):
        """
        Unexpected service exceptions must not leak internal exception
        details through GraphQL.
        """

        mock_confirm_email.side_effect = RuntimeError(
            "database connection password=SECRET"
        )

        with pytest.raises(GraphQLError) as exc_info:
            ConfirmEmail.mutate_and_get_payload(
                None,
                None,
                token="valid-looking-token",
            )

        mock_confirm_email.assert_called_once_with(
            "valid-looking-token",
        )

        assert (
            str(exc_info.value)
            == "Unable to verify email address."
        )

        assert (
            "SECRET"
            not in str(exc_info.value)
        )

    @patch(
        "graphq.accounts.mutations.email.confirm_email"
    )
    def test_confirm_email_returns_completed_message_when_service_user_is_not_verified(
        self,
        mock_confirm_email,
    ):
        """
        The adapter should preserve the existing contract:

            user.email_verified == False
                ->
            "Email verification completed."

        This verifies that the GraphQL response is based on the returned
        service user rather than assuming confirmation always changes the
        flag.
        """

        user = Mock()
        user.email_verified = False

        mock_confirm_email.return_value = user

        result = ConfirmEmail.mutate_and_get_payload(
            None,
            None,
            token="verification-token",
        )

        mock_confirm_email.assert_called_once_with(
            "verification-token",
        )

        assert result.success is True
        assert (
            result.message
            == "Email verification completed."
        )

    @patch(
        "graphq.accounts.mutations.email.confirm_email"
    )
    @patch(
        "graphq.accounts.mutations.email.send_confirmation_email_task"
    )
    def test_confirm_email_does_not_queue_resend_task(
        self,
        mock_task,
        mock_confirm_email,
    ):
        """
        ConfirmEmail must not use the resend task.

        Confirmation is a direct delegation to email_service.confirm_email().
        """

        user = Mock()
        user.email_verified = True

        mock_confirm_email.return_value = user

        result = ConfirmEmail.mutate_and_get_payload(
            None,
            None,
            token="verification-token",
        )

        mock_confirm_email.assert_called_once_with(
            "verification-token",
        )

        mock_task.delay.assert_not_called()

        assert result.success is True


# =============================================================================
# RESEND CONFIRMATION EMAIL
# =============================================================================


@pytest.mark.django_db
class TestResendConfirmationEmailMutation(
    EmailMutationTestMixin,
):
    """
    Tests for ResendConfirmationEmail.

    The GraphQL mutation should:

        1. validate the supplied email
        2. resolve the User
        3. queue send_confirmation_email_task.delay(user.pk)

    It must not execute the email-verification service itself.
    """

    @patch(
        "graphq.accounts.mutations.email.send_confirmation_email_task"
    )
    def test_resend_confirmation_email_queues_task(
        self,
        mock_task,
    ):
        """
        A valid account email should queue the Celery task.
        """

        user = self.create_user(
            email="user@example.com",
        )

        result = (
            ResendConfirmationEmail
            .mutate_and_get_payload(
                None,
                None,
                email="user@example.com",
            )
        )

        mock_task.delay.assert_called_once_with(
            user.pk,
        )

        assert result.success is True
        assert (
            result.message
            == "Verification email has been queued."
        )

    @patch(
        "graphq.accounts.mutations.email.send_confirmation_email_task"
    )
    def test_resend_confirmation_email_is_case_insensitive(
        self,
        mock_task,
    ):
        """
        Email lookup must use email__iexact.
        """

        user = self.create_user(
            email="User@Example.com",
        )

        result = (
            ResendConfirmationEmail
            .mutate_and_get_payload(
                None,
                None,
                email="USER@EXAMPLE.COM",
            )
        )

        mock_task.delay.assert_called_once_with(
            user.pk,
        )

        assert result.success is True

    @patch(
        "graphq.accounts.mutations.email.send_confirmation_email_task"
    )
    def test_resend_confirmation_email_strips_whitespace(
        self,
        mock_task,
    ):
        """
        Surrounding whitespace must be removed before account lookup.
        """

        user = self.create_user(
            email="user@example.com",
        )

        result = (
            ResendConfirmationEmail
            .mutate_and_get_payload(
                None,
                None,
                email="  user@example.com  ",
            )
        )

        mock_task.delay.assert_called_once_with(
            user.pk,
        )

        assert result.success is True

    def test_resend_confirmation_email_requires_email(self):
        """
        Missing email must fail before querying the database.
        """

        with pytest.raises(GraphQLError) as exc_info:
            ResendConfirmationEmail.mutate_and_get_payload(
                None,
                None,
            )

        assert (
            str(exc_info.value)
            == "Email address is required."
        )

    def test_resend_confirmation_email_rejects_empty_email(
        self,
    ):
        """
        Empty email must fail before task scheduling.
        """

        with patch(
            "graphq.accounts.mutations.email.send_confirmation_email_task"
        ) as mock_task:

            with pytest.raises(GraphQLError) as exc_info:
                (
                    ResendConfirmationEmail
                    .mutate_and_get_payload(
                        None,
                        None,
                        email="",
                    )
                )

        mock_task.delay.assert_not_called()

        assert (
            str(exc_info.value)
            == "Email address is required."
        )

    def test_resend_confirmation_email_rejects_whitespace_email(
        self,
    ):
        """
        Whitespace-only email must fail before account lookup.
        """

        with patch(
            "graphq.accounts.mutations.email.send_confirmation_email_task"
        ) as mock_task:

            with pytest.raises(GraphQLError) as exc_info:
                (
                    ResendConfirmationEmail
                    .mutate_and_get_payload(
                        None,
                        None,
                        email="     ",
                    )
                )

        mock_task.delay.assert_not_called()

        assert (
            str(exc_info.value)
            == "Email address is required."
        )

    @patch(
        "graphq.accounts.mutations.email.send_confirmation_email_task"
    )
    def test_resend_confirmation_email_rejects_unknown_account(
        self,
        mock_task,
    ):
        """
        An unknown email must not queue a task.
        """

        with pytest.raises(GraphQLError) as exc_info:
            (
                ResendConfirmationEmail
                .mutate_and_get_payload(
                    None,
                    None,
                    email="missing@example.com",
                )
            )

        mock_task.delay.assert_not_called()

        assert (
            str(exc_info.value)
            == "No account exists with that email."
        )

    @patch(
        "graphq.accounts.mutations.email.send_confirmation_email_task"
    )
    def test_resend_confirmation_email_translates_queue_failure(
        self,
        mock_task,
    ):
        """
        Celery scheduling failures must be translated into a safe
        GraphQL error.
        """

        user = self.create_user(
            email="queue-failure@example.com",
        )

        mock_task.delay.side_effect = RuntimeError(
            "broker password=SECRET"
        )

        with pytest.raises(GraphQLError) as exc_info:
            (
                ResendConfirmationEmail
                .mutate_and_get_payload(
                    None,
                    None,
                    email=user.email,
                )
            )

        mock_task.delay.assert_called_once_with(
            user.pk,
        )

        assert (
            str(exc_info.value)
            == "Unable to queue the verification email."
        )

        assert (
            "SECRET"
            not in str(exc_info.value)
        )

    @patch(
        "graphq.accounts.mutations.email.send_confirmation_email_task"
    )
    def test_resend_confirmation_email_does_not_call_email_service_directly(
        self,
        mock_task,
    ):
        """
        The GraphQL adapter must stop at the Celery boundary.

        The email service belongs inside the task, not inside this mutation.
        """

        user = self.create_user(
            email="architecture@example.com",
        )

        with patch(
            "graphq.accounts.mutations.email.confirm_email"
        ) as mock_confirm_email:

            result = (
                ResendConfirmationEmail
                .mutate_and_get_payload(
                    None,
                    None,
                    email=user.email,
                )
            )

        mock_task.delay.assert_called_once_with(
            user.pk,
        )

        mock_confirm_email.assert_not_called()

        assert result.success is True


# =============================================================================
# MUTATION REGISTRY
# =============================================================================


class TestEmailMutationsRegistry(TestCase):
    """
    Verify that the public EmailMutations registry exposes exactly the
    expected email-verification mutations.
    """

    def test_email_mutations_registry_contains_confirm_email(self):
        """
        confirm_email must be registered.
        """

        field = EmailMutations._meta.fields.get(
            "confirm_email"
        )

        assert field is not None

    def test_email_mutations_registry_contains_resend_confirmation_email(
        self,
    ):
        """
        resend_confirmation_email must be registered.
        """

        field = EmailMutations._meta.fields.get(
            "resend_confirmation_email"
        )

        assert field is not None

    def test_email_mutations_registry_contains_only_expected_mutations(
        self,
    ):
        """
        This registry currently owns exactly the two email-verification
        mutations.
        """

        assert set(
            EmailMutations._meta.fields.keys()
        ) == {
            "confirm_email",
            "resend_confirmation_email",
        }
