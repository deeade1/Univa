"""
Tests for GraphQL account user mutations.

Focused coverage:
    - CreateUserMutation contact validation
    - email normalization
    - phone validation
    - duplicate contact protection
    - password validation
    - user/profile creation
    - role assignment
    - email verification behavior
    - canonical JWT token boundary

Architectural boundaries
------------------------

Authentication JWT issuance is tested only through the canonical
CreateUserMutation.generate_tokens() boundary.

Email verification is tested through:

    accounts.email_service.send_confirmation_email()

These tests intentionally do NOT test:

    - univa_jwt.utils.jwt_encode()
    - univa_jwt.utils.jwt_payload()
    - token_type="activation"
    - verification-token payload construction
    - verification URL construction
    - direct send_mail() calls from the GraphQL mutation

Email-verification token ownership belongs exclusively to
accounts.email_service.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from graphql import GraphQLError

from accounts.models.profile import UserProfile
from accounts.models.role import Role, UserRole

from graphq.accounts.inputs import UserRoleInput
from graphq.accounts.mutations.user import CreateUserMutation
from accounts.email_service import (
    EmailVerificationAlreadyCompletedError,
    EmailVerificationError,
)



User = get_user_model()


# =============================================================================
# CONTACT VALIDATION
# =============================================================================


class CreateUserMutationContactValidationTests(TestCase):
    """Tests for CreateUserMutation contact validation."""

    def test_valid_email_is_detected(self):
        result = CreateUserMutation.validate_contact(
            "user@example.com",
        )

        self.assertEqual(
            result,
            "email",
        )

    def test_valid_phone_is_detected(self):
        result = CreateUserMutation.validate_contact(
            "+2348012345678",
        )

        self.assertEqual(
            result,
            "phone",
        )

    def test_email_is_case_insensitive(self):
        result = CreateUserMutation.validate_contact(
            "USER@EXAMPLE.COM",
        )

        self.assertEqual(
            result,
            "email",
        )

    def test_empty_contact_is_rejected(self):
        with self.assertRaises(GraphQLError):
            CreateUserMutation.validate_contact("")

    def test_whitespace_only_contact_is_rejected(self):
        with self.assertRaises(GraphQLError):
            CreateUserMutation.validate_contact("   ")

    def test_invalid_email_is_rejected(self):
        with self.assertRaises(GraphQLError):
            CreateUserMutation.validate_contact(
                "invalid-email",
            )

    def test_phone_without_country_code_is_rejected(self):
        with self.assertRaises(GraphQLError):
            CreateUserMutation.validate_contact(
                "08012345678",
            )

    def test_short_phone_number_is_rejected(self):
        with self.assertRaises(GraphQLError):
            CreateUserMutation.validate_contact(
                "+123",
            )


# =============================================================================
# USER CREATION
# =============================================================================


class CreateUserMutationTests(TestCase):
    """Tests for actual user creation."""

    def setUp(self):
        self.request = MagicMock()

        self.request.META = {
            "REMOTE_ADDR": "127.0.0.1",
        }

    @patch.object(
        CreateUserMutation,
        "check_rate_limit",
    )
    @patch.object(
        CreateUserMutation,
        "generate_tokens",
        return_value=(
            "access-token",
            "refresh-token",
        ),
    )
    def test_create_user_with_email(
        self,
        mock_generate_tokens,
        mock_check_rate_limit,
    ):
        result = CreateUserMutation.mutate_and_get_payload(
            None,
            SimpleNamespace(
                context=self.request,
            ),
            contact="USER@EXAMPLE.COM",
            password="StrongPassword123!",
            roles=[],
            send_verification=False,
            metadata=None,
        )

        user = result.user

        self.assertIsNotNone(user)

        self.assertEqual(
            user.email,
            "user@example.com",
        )

        self.assertIsNone(
            user.phone_number,
        )

        self.assertEqual(
            result.token,
            "access-token",
        )

        self.assertEqual(
            result.refresh_token,
            "refresh-token",
        )

        self.assertFalse(
            result.verification_sent,
        )

        self.assertTrue(
            UserProfile.objects.filter(
                user=user,
            ).exists(),
        )

        mock_check_rate_limit.assert_called_once()

        mock_generate_tokens.assert_called_once_with(
            user=user,
            request=self.request,
        )

    @patch.object(
        CreateUserMutation,
        "check_rate_limit",
    )
    @patch.object(
        CreateUserMutation,
        "generate_tokens",
        return_value=(
            "access-token",
            "refresh-token",
        ),
    )
    def test_create_user_with_phone(
        self,
        mock_generate_tokens,
        mock_check_rate_limit,
    ):
        result = CreateUserMutation.mutate_and_get_payload(
            None,
            SimpleNamespace(
                context=self.request,
            ),
            contact="+2348012345678",
            password="StrongPassword123!",
            roles=[],
            send_verification=True,
            metadata=None,
        )

        user = result.user

        self.assertIsNotNone(user)

        self.assertEqual(
            user.phone_number,
            "+2348012345678",
        )

        self.assertIsNone(
            user.email,
        )

        self.assertTrue(
            UserProfile.objects.filter(
                user=user,
            ).exists(),
        )

        # Phone registration must never attempt email verification.
        self.assertFalse(
            result.verification_sent,
        )

        mock_check_rate_limit.assert_called_once()

        mock_generate_tokens.assert_called_once_with(
            user=user,
            request=self.request,
        )

    @patch.object(
        CreateUserMutation,
        "check_rate_limit",
    )
    def test_duplicate_email_is_rejected(
        self,
        mock_check_rate_limit,
    ):
        User.objects.create_user(
            email="existing@example.com",
            password="StrongPassword123!",
        )

        with self.assertRaises(GraphQLError) as context:
            CreateUserMutation.mutate_and_get_payload(
                None,
                SimpleNamespace(
                    context=self.request,
                ),
                contact="EXISTING@EXAMPLE.COM",
                password="AnotherStrongPassword123!",
                roles=[],
                send_verification=False,
                metadata=None,
            )

        self.assertIn(
            "already exists",
            str(context.exception),
        )

        mock_check_rate_limit.assert_called_once()

    @patch.object(
        CreateUserMutation,
        "check_rate_limit",
    )
    def test_duplicate_phone_is_rejected(
        self,
        mock_check_rate_limit,
    ):
        User.objects.create_user(
            phone_number="+2348012345678",
            password="StrongPassword123!",
        )

        with self.assertRaises(GraphQLError) as context:
            CreateUserMutation.mutate_and_get_payload(
                None,
                SimpleNamespace(
                    context=self.request,
                ),
                contact="+2348012345678",
                password="AnotherStrongPassword123!",
                roles=[],
                send_verification=False,
                metadata=None,
            )

        self.assertIn(
            "already exists",
            str(context.exception),
        )

        mock_check_rate_limit.assert_called_once()

    @patch.object(
        CreateUserMutation,
        "check_rate_limit",
    )
    def test_short_password_is_rejected(
        self,
        mock_check_rate_limit,
    ):
        with self.assertRaises(GraphQLError) as context:
            CreateUserMutation.mutate_and_get_payload(
                None,
                SimpleNamespace(
                    context=self.request,
                ),
                contact="user@example.com",
                password="short",
                roles=[],
                send_verification=False,
                metadata=None,
            )

        self.assertIn(
            "Password must be at least",
            str(context.exception),
        )

        self.assertFalse(
            User.objects.filter(
                email="user@example.com",
            ).exists(),
        )

        mock_check_rate_limit.assert_called_once()


# =============================================================================
# ROLE ASSIGNMENT
# =============================================================================


class CreateUserMutationRoleTests(TestCase):
    """Tests for role assignment during registration."""

    def setUp(self):
        self.request = MagicMock()

        self.request.META = {
            "REMOTE_ADDR": "127.0.0.1",
        }

        self.role = Role.objects.create(
            name="driver",
            app_name="transport",
        )

    @patch.object(
        CreateUserMutation,
        "check_rate_limit",
    )
    @patch.object(
        CreateUserMutation,
        "generate_tokens",
        return_value=(
            "access-token",
            "refresh-token",
        ),
    )
    def test_role_is_assigned_to_new_user(
        self,
        mock_generate_tokens,
        mock_check_rate_limit,
    ):
        """
        A valid requested role is assigned to the new user.

        mutate_and_get_payload() is being invoked directly, so the
        role input is represented by a normal Python object rather
        than a Graphene InputObjectType instance.
        """

        role_input = SimpleNamespace(
            role_name="driver",
            app_name="transport",
            is_active=True,
            expires_at=None,
        )

        result = CreateUserMutation.mutate_and_get_payload(
            None,
            SimpleNamespace(
                context=self.request,
            ),
            contact="driver@example.com",
            password="StrongPassword123!",
            roles=[
                role_input,
            ],
            send_verification=False,
            metadata=None,
        )

        user = result.user

        user_role = UserRole.objects.get(
            user=user,
            role=self.role,
        )

        self.assertTrue(
            user_role.is_active,
        )

        self.assertIsNone(
            user_role.expires_at,
        )

        mock_check_rate_limit.assert_called_once()

        mock_generate_tokens.assert_called_once_with(
            user=user,
            request=self.request,
        )

    @patch.object(
        CreateUserMutation,
        "check_rate_limit",
    )
    @patch.object(
        CreateUserMutation,
        "generate_tokens",
        return_value=(
            "access-token",
            "refresh-token",
        ),
    )
    def test_role_can_be_created_inactive(
        self,
        mock_generate_tokens,
        mock_check_rate_limit,
    ):
        """
        A requested role may explicitly be created inactive.
        """

        role_input = SimpleNamespace(
            role_name="driver",
            app_name="transport",
            is_active=False,
            expires_at=None,
        )

        result = CreateUserMutation.mutate_and_get_payload(
            None,
            SimpleNamespace(
                context=self.request,
            ),
            contact="inactive@example.com",
            password="StrongPassword123!",
            roles=[
                role_input,
            ],
            send_verification=False,
            metadata=None,
        )

        user_role = UserRole.objects.get(
            user=result.user,
            role=self.role,
        )

        self.assertFalse(
            user_role.is_active,
        )

        self.assertIsNone(
            user_role.expires_at,
        )

        mock_check_rate_limit.assert_called_once()

        mock_generate_tokens.assert_called_once_with(
            user=result.user,
            request=self.request,
        )

    @patch.object(
        CreateUserMutation,
        "check_rate_limit",
    )
    def test_nonexistent_role_is_rejected(
        self,
        mock_check_rate_limit,
    ):
        """
        Registration must fail when a requested role does not exist.
        """

        role_input = SimpleNamespace(
            role_name="does-not-exist",
            app_name="transport",
            is_active=True,
            expires_at=None,
        )

        with self.assertRaises(
            GraphQLError,
        ) as context:
            CreateUserMutation.mutate_and_get_payload(
                None,
                SimpleNamespace(
                    context=self.request,
                ),
                contact="role@example.com",
                password="StrongPassword123!",
                roles=[
                    role_input,
                ],
                send_verification=False,
                metadata=None,
            )

        self.assertIn(
            "was not found",
            str(context.exception),
        )

        self.assertFalse(
            User.objects.filter(
                email="role@example.com",
            ).exists()
        )

        mock_check_rate_limit.assert_called_once()

# =============================================================================
# EMAIL VERIFICATION
# =============================================================================


class CreateUserMutationVerificationTests(TestCase):
    """
    Tests for email verification through accounts.email_service.

    These tests deliberately mock the canonical email-verification
    service boundary.

    The GraphQL mutation must NOT know anything about:

        - JWT encoding
        - JWT payloads
        - activation token types
        - verification token structure
        - verification URLs
        - direct email transport

    The only contract tested here is:

        CreateUserMutation
            -> accounts.email_service.send_confirmation_email()
    """

    def setUp(self):
        self.request = MagicMock()

        self.request.META = {
            "REMOTE_ADDR": "127.0.0.1",
        }

    @patch(
        "graphq.accounts.mutations.user.send_confirmation_email",
        return_value="verification-token",
    )
    @patch.object(
        CreateUserMutation,
        "check_rate_limit",
    )
    @patch.object(
        CreateUserMutation,
        "generate_tokens",
        return_value=(
            "access-token",
            "refresh-token",
        ),
    )
    def test_verification_service_is_called_for_email_registration(
        self,
        mock_generate_tokens,
        mock_check_rate_limit,
        mock_send_confirmation_email,
    ):
        result = CreateUserMutation.mutate_and_get_payload(
            None,
            SimpleNamespace(
                context=self.request,
            ),
            contact="VERIFY@EXAMPLE.COM",
            password="StrongPassword123!",
            roles=[],
            send_verification=True,
            metadata=None,
        )

        user = result.user

        self.assertEqual(
            user.email,
            "verify@example.com",
        )

        mock_send_confirmation_email.assert_called_once_with(
            user,
        )

        self.assertTrue(
            result.verification_sent,
        )

        mock_generate_tokens.assert_called_once_with(
            user=user,
            request=self.request,
        )

        mock_check_rate_limit.assert_called_once()

    @patch(
        "graphq.accounts.mutations.user.send_confirmation_email",
        return_value="verification-token",
    )
    @patch.object(
        CreateUserMutation,
        "check_rate_limit",
    )
    @patch.object(
        CreateUserMutation,
        "generate_tokens",
        return_value=(
            "access-token",
            "refresh-token",
        ),
    )
    def test_verification_service_is_not_called_when_disabled(
        self,
        mock_generate_tokens,
        mock_check_rate_limit,
        mock_send_confirmation_email,
    ):
        result = CreateUserMutation.mutate_and_get_payload(
            None,
            SimpleNamespace(
                context=self.request,
            ),
            contact="verify@example.com",
            password="StrongPassword123!",
            roles=[],
            send_verification=False,
            metadata=None,
        )

        mock_send_confirmation_email.assert_not_called()

        self.assertFalse(
            result.verification_sent,
        )

        mock_generate_tokens.assert_called_once_with(
            user=result.user,
            request=self.request,
        )

        mock_check_rate_limit.assert_called_once()

    @patch(
        "graphq.accounts.mutations.user.send_confirmation_email",
    )
    @patch.object(
        CreateUserMutation,
        "check_rate_limit",
    )
    @patch.object(
        CreateUserMutation,
        "generate_tokens",
        return_value=(
            "access-token",
            "refresh-token",
        ),
    )
    def test_verification_service_is_not_called_for_phone_registration(
        self,
        mock_generate_tokens,
        mock_check_rate_limit,
        mock_send_confirmation_email,
    ):
        result = CreateUserMutation.mutate_and_get_payload(
            None,
            SimpleNamespace(
                context=self.request,
            ),
            contact="+2348012345678",
            password="StrongPassword123!",
            roles=[],
            send_verification=True,
            metadata=None,
        )

        mock_send_confirmation_email.assert_not_called()

        self.assertFalse(
            result.verification_sent,
        )

        mock_generate_tokens.assert_called_once_with(
            user=result.user,
            request=self.request,
        )

        mock_check_rate_limit.assert_called_once()

    @patch(
        "graphq.accounts.mutations.user.send_confirmation_email",
        side_effect=Exception(
            "SMTP provider unavailable",
        ),
    )
    @patch.object(
        CreateUserMutation,
        "check_rate_limit",
    )
    @patch.object(
        CreateUserMutation,
        "generate_tokens",
        return_value=(
            "access-token",
            "refresh-token",
        ),
    )
    def test_verification_service_failure_does_not_fail_registration(
        self,
        mock_generate_tokens,
        mock_check_rate_limit,
        mock_send_confirmation_email,
    ):
        result = CreateUserMutation.mutate_and_get_payload(
            None,
            SimpleNamespace(
                context=self.request,
            ),
            contact="failure@example.com",
            password="StrongPassword123!",
            roles=[],
            send_verification=True,
            metadata=None,
        )

        self.assertIsNotNone(
            result.user,
        )

        self.assertTrue(
            User.objects.filter(
                pk=result.user.pk,
            ).exists(),
        )

        self.assertFalse(
            result.verification_sent,
        )

        mock_send_confirmation_email.assert_called_once_with(
            result.user,
        )

        mock_generate_tokens.assert_called_once_with(
            user=result.user,
            request=self.request,
        )

        mock_check_rate_limit.assert_called_once()

    @patch(
        "graphq.accounts.mutations.user.send_confirmation_email",
        side_effect=EmailVerificationAlreadyCompletedError(
            "Email is already verified.",
        ),
    )
    @patch.object(
        CreateUserMutation,
        "check_rate_limit",
    )
    @patch.object(
        CreateUserMutation,
        "generate_tokens",
        return_value=(
            "access-token",
            "refresh-token",
        ),
    )
    def test_already_verified_email_is_handled_by_service_boundary(
        self,
        mock_generate_tokens,
        mock_check_rate_limit,
        mock_send_confirmation_email,
    ):
        result = CreateUserMutation.mutate_and_get_payload(
            None,
            SimpleNamespace(
                context=self.request,
            ),
            contact="already@example.com",
            password="StrongPassword123!",
            roles=[],
            send_verification=True,
            metadata=None,
        )

        self.assertIsNotNone(
            result.user,
        )

        self.assertFalse(
            result.verification_sent,
        )

        mock_send_confirmation_email.assert_called_once_with(
            result.user,
        )

        mock_generate_tokens.assert_called_once_with(
            user=result.user,
            request=self.request,
        )

        mock_check_rate_limit.assert_called_once()


# =============================================================================
# JWT TOKEN BOUNDARY
# =============================================================================


class CreateUserMutationTokenBoundaryTests(TestCase):
    """
    Ensure authentication token issuance remains behind the canonical
    TokenGenerationMixin boundary.
    """

    def setUp(self):
        self.request = MagicMock()

        self.request.META = {
            "REMOTE_ADDR": "127.0.0.1",
        }

    @patch.object(
        CreateUserMutation,
        "check_rate_limit",
    )
    @patch.object(
        CreateUserMutation,
        "generate_tokens",
        return_value=(
            "access-token",
            "refresh-token",
        ),
    )
    def test_create_user_uses_generate_tokens_boundary(
        self,
        mock_generate_tokens,
        mock_check_rate_limit,
    ):
        result = CreateUserMutation.mutate_and_get_payload(
            None,
            SimpleNamespace(
                context=self.request,
            ),
            contact="token@example.com",
            password="StrongPassword123!",
            roles=[],
            send_verification=False,
            metadata=None,
        )

        mock_generate_tokens.assert_called_once_with(
            user=result.user,
            request=self.request,
        )

        self.assertEqual(
            result.token,
            "access-token",
        )

        self.assertEqual(
            result.refresh_token,
            "refresh-token",
        )

        mock_check_rate_limit.assert_called_once()


# =============================================================================
# EMAIL VERIFICATION ARCHITECTURAL BOUNDARY
# =============================================================================


class CreateUserMutationEmailVerificationBoundaryTests(TestCase):
    """
    Regression tests protecting the email-verification architecture.

    The GraphQL mutation must delegate email verification to
    accounts.email_service rather than implementing JWT-based activation
    tokens itself.
    """

    def setUp(self):
        self.request = MagicMock()

        self.request.META = {
            "REMOTE_ADDR": "127.0.0.1",
        }

    @patch(
        "graphq.accounts.mutations.user.send_confirmation_email",
        return_value="verification-token",
    )
    @patch.object(
        CreateUserMutation,
        "check_rate_limit",
    )
    @patch.object(
        CreateUserMutation,
        "generate_tokens",
        return_value=(
            "access-token",
            "refresh-token",
        ),
    )
    def test_email_verification_uses_service_boundary_only(
        self,
        mock_generate_tokens,
        mock_check_rate_limit,
        mock_send_confirmation_email,
    ):
        result = CreateUserMutation.mutate_and_get_payload(
            None,
            SimpleNamespace(
                context=self.request,
            ),
            contact="boundary@example.com",
            password="StrongPassword123!",
            roles=[],
            send_verification=True,
            metadata=None,
        )

        mock_send_confirmation_email.assert_called_once_with(
            result.user,
        )

        self.assertTrue(
            result.verification_sent,
        )

        # Authentication JWT issuance remains a separate boundary.
        mock_generate_tokens.assert_called_once_with(
            user=result.user,
            request=self.request,
        )

        # The verification service is independent of authentication JWT
        # generation.
        self.assertNotEqual(
            "verification-token",
            result.token,
        )

        self.assertNotEqual(
            "verification-token",
            result.refresh_token,
        )

        mock_check_rate_limit.assert_called_once()



# =============================================================================
# IMPORTS USED BY MOCKED SERVICE EXCEPTIONS
# =============================================================================

from accounts.email_service import (
    EmailVerificationAlreadyCompletedError,
)
