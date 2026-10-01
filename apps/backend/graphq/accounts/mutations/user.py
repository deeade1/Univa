"""
GraphQL user-management mutations.

ARCHITECTURE
------------

This module owns GraphQL orchestration for account/user operations.

Responsibilities:

    CreateUserMutation
        ├── validate registration input
        ├── create User
        ├── create UserProfile
        ├── assign optional roles
        ├── request canonical authentication JWTs
        └── request canonical email verification

    DeleteUserMutation
        ├── authenticate caller
        ├── authorize deletion
        ├── resolve target user
        ├── optionally transfer supported account data
        ├── revoke authentication refresh tokens
        ├── soft-delete or hard-delete account
        └── create audit record

IMPORTANT ARCHITECTURAL BOUNDARIES
----------------------------------

Authentication JWTs are owned by:

    univa_jwt

Email-verification tokens are owned by:

    accounts.email_service

Therefore this module MUST NOT:

    - generate email-verification JWTs
    - call jwt_encode() for email verification
    - call jwt_payload() for email verification
    - use token_type="activation"
    - implement email-verification token validation
    - construct email-verification URLs
    - decode authentication JWTs
    - access the deprecated RefreshToken model
    - mutate RefreshToken.objects directly

FACE / BIOMETRIC ARCHITECTURAL BOUNDARY
---------------------------------------

FaceEncoding and FaceVerification are NOT account-registration
responsibilities.

They belong to specific Univa domain workflows, such as:

    - real-estate agent verification
    - identity verification
    - other operations that explicitly require biometric verification

Therefore this module MUST NOT:

    - create FaceEncoding records during registration
    - require FaceEncoding during account creation
    - transfer FaceEncoding records as generic account data
    - transfer FaceVerification records as generic account data
    - import face-related domain models
    - make account deletion dependent on face-verification models

A face-related record must only be transferred or handled by the
domain service that owns that particular workflow.
"""

from __future__ import annotations

import logging

import graphene

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone

from graphene import (
    Boolean,
    Field,
    ID,
    List,
    String,
    relay,
)
from graphene.types.generic import GenericScalar

from graphql import GraphQLError

from accounts.email_service import (
    EmailVerificationAlreadyCompletedError,
    EmailVerificationError,
    send_confirmation_email,
)

from accounts.models.profile import UserProfile
from accounts.models.role import Role, UserRole

from graphq.accounts.inputs.role_inputs import UserRoleInput
from graphq.accounts.mixin import (
    MIN_PASSWORD_LENGTH,
    RateLimitMixin,
    TokenGenerationMixin,
)
from graphq.accounts.types import UserNode

from univa_jwt.decorators import login_required


logger = logging.getLogger(__name__)

User = get_user_model()


# =============================================================================
# CREATE USER
# =============================================================================


class CreateUserMutation(
    RateLimitMixin,
    TokenGenerationMixin,
    relay.ClientIDMutation,
):
    """
    Create a new user account.

    Registration supports either:

        email
        OR
        phone number

    but never requires both.

    Authentication tokens are generated exclusively through
    TokenGenerationMixin.

    Email verification is delegated exclusively to
    accounts.email_service.

    Face/biometric verification is intentionally NOT part of registration.
    """

    class Input:
        contact = String(
            required=True,
            description="Email address or phone number.",
        )

        password = String(
            required=True,
            description="Account password.",
        )

        roles = List(
            UserRoleInput,
            required=False,
            description="Optional roles to assign to the new user.",
        )

        send_verification = Boolean(
            default_value=True,
            description=(
                "Send an email verification message when applicable."
            ),
        )

        metadata = GenericScalar(
            required=False,
            description="Optional user metadata.",
        )

    user = Field(UserNode)

    token = String()

    refresh_token = String()

    verification_sent = Boolean()

    # =========================================================================
    # CONTACT VALIDATION
    # =========================================================================

    @classmethod
    def validate_contact(
        cls,
        contact: str,
    ) -> str:
        """
        Validate whether the supplied contact is an email address
        or an international phone number.

        Returns:

            "email"
            or
            "phone"
        """

        contact = contact.strip()

        if not contact:
            raise GraphQLError(
                "Contact is required."
            )

        # ---------------------------------------------------------------------
        # Email
        # ---------------------------------------------------------------------

        if "@" in contact:
            try:
                validate_email(contact)

            except ValidationError as exc:
                raise GraphQLError(
                    "Please provide a valid email address."
                ) from exc

            return "email"

        # ---------------------------------------------------------------------
        # Phone
        # ---------------------------------------------------------------------

        if not contact.startswith("+"):
            raise GraphQLError(
                "Phone number must include the country code."
            )

        if len(contact) < 8:
            raise GraphQLError(
                "Phone number is too short."
            )

        return "phone"

    # =========================================================================
    # MUTATION
    # =========================================================================

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(
        cls,
        root,
        info,
        **input,
    ):
        """
        Create the user, profile, optional roles, authentication tokens,
        and optional email-verification message.

        Face/biometric processing is deliberately excluded from account
        registration.
        """

        request = info.context

        # ---------------------------------------------------------------------
        # Rate limiting
        # ---------------------------------------------------------------------

        ip_address = (
            request.META.get("REMOTE_ADDR")
            or "unknown"
        )

        cls.check_rate_limit(
            f"signup_ip_{ip_address}",
            limit=10,
            window=3600,
        )

        # ---------------------------------------------------------------------
        # Normalize contact
        # ---------------------------------------------------------------------

        contact = (
            input.get("contact")
            or ""
        ).strip()

        contact_type = cls.validate_contact(
            contact,
        )

        if contact_type == "email":
            contact = contact.lower()

        # ---------------------------------------------------------------------
        # Check for existing user
        # ---------------------------------------------------------------------

        if contact_type == "email":
            existing_user = (
                User.objects
                .filter(
                    email__iexact=contact,
                )
                .first()
            )

        else:
            existing_user = (
                User.objects
                .filter(
                    phone_number=contact,
                )
                .first()
            )

        if existing_user:
            raise GraphQLError(
                "A user with this contact already exists."
            )

        # ---------------------------------------------------------------------
        # Validate password
        # ---------------------------------------------------------------------

        password = input.get("password")

        if not password:
            raise GraphQLError(
                "Password is required."
            )

        if len(password) < MIN_PASSWORD_LENGTH:
            raise GraphQLError(
                f"Password must be at least "
                f"{MIN_PASSWORD_LENGTH} characters."
            )

        # ---------------------------------------------------------------------
        # Create user
        # ---------------------------------------------------------------------

        user_kwargs = {
            "password": password,
        }

        if contact_type == "email":
            user_kwargs["email"] = contact
            user_kwargs["phone_number"] = None

        else:
            user_kwargs["email"] = None
            user_kwargs["phone_number"] = contact

        try:
            user = User.objects.create_user(
                **user_kwargs,
            )

        except Exception as exc:
            logger.exception(
                "Failed to create user during registration."
            )

            raise GraphQLError(
                "Unable to create user account."
            ) from exc

        # ---------------------------------------------------------------------
        # Optional metadata
        # ---------------------------------------------------------------------

        metadata = input.get("metadata")

        if metadata is not None:
            user.metadata = metadata

            user.save(
                update_fields=[
                    "metadata",
                ],
            )

        # ---------------------------------------------------------------------
        # Create profile
        # ---------------------------------------------------------------------

        UserProfile.objects.get_or_create(
            user=user,
        )

        # ---------------------------------------------------------------------
        # Assign requested roles
        # ---------------------------------------------------------------------

        roles = input.get("roles") or []

        for role_input in roles:
            role_name = role_input.role_name
            app_name = role_input.app_name

            try:
                role = Role.objects.get(
                    name=role_name,
                    app_name=app_name,
                )

            except Role.DoesNotExist as exc:
                raise GraphQLError(
                    f"Role '{role_name}' was not found "
                    f"in app '{app_name}'."
                ) from exc

            UserRole.objects.create(
                user=user,
                role=role,
                is_active=getattr(
                    role_input,
                    "is_active",
                    True,
                ),
                expires_at=getattr(
                    role_input,
                    "expires_at",
                    None,
                ),
                created_by=user,
            )

        # ---------------------------------------------------------------------
        # Generate canonical authentication JWTs
        # ---------------------------------------------------------------------
        #
        # Authentication token issuance belongs exclusively to:
        #
        #     TokenGenerationMixin
        #
        # which delegates to univa_jwt.
        #
        # These tokens are completely independent from email-verification
        # tokens.
        # ---------------------------------------------------------------------

        try:
            token, refresh_token = cls.generate_tokens(
                user=user,
                request=request,
            )

        except Exception as exc:
            logger.exception(
                "Failed to generate authentication tokens "
                "for newly created user %s.",
                user.pk,
            )

            raise GraphQLError(
                "Unable to initialize authentication session."
            ) from exc

        # ---------------------------------------------------------------------
        # Email verification
        # ---------------------------------------------------------------------

        verification_sent = False

        if (
            input.get(
                "send_verification",
                True,
            )
            and contact_type == "email"
        ):
            try:
                send_confirmation_email(
                    user,
                )

                verification_sent = True

            except EmailVerificationAlreadyCompletedError:
                verification_sent = False

            except EmailVerificationError as exc:
                logger.warning(
                    "Email verification could not be sent "
                    "for user %s: %s",
                    user.pk,
                    exc,
                )

                verification_sent = False

            except Exception:
                logger.exception(
                    "Unexpected failure while sending email "
                    "verification for user %s.",
                    user.pk,
                )

                verification_sent = False

        # ---------------------------------------------------------------------
        # Return Relay payload
        # ---------------------------------------------------------------------

        return cls(
            user=user,
            token=token,
            refresh_token=refresh_token,
            verification_sent=verification_sent,
        )


# =============================================================================
# DELETE USER
# =============================================================================


class DeleteUserMutation(
    relay.ClientIDMutation,
):
    """
    Delete or deactivate a user account.

    Authentication is enforced through the canonical univa_jwt
    login_required decorator.

    Normal deletion:

        soft deletion

    Permanent deletion:

        hard deletion

    Hard deletion is restricted to superusers.

    Generic account deletion does NOT manage domain-specific biometric
    records. FaceEncoding and FaceVerification belong to the domain
    workflows that created and own them.

    IMPORTANT:

    This mutation does NOT access the deprecated:

        univa_jwt.models.RefreshToken

    model.

    Refresh-token revocation is delegated entirely to the canonical
    univa_jwt revocation service.
    """

    class Input:
        user_id = ID(
            required=True,
            description="Relay global ID of the user to delete.",
        )

        hard_delete = Boolean(
            default_value=False,
            description=(
                "Permanently delete the account. "
                "Only superusers may perform hard deletion."
            ),
        )

        transfer_data_to = ID(
            required=False,
            description=(
                "Relay global ID of the user receiving "
                "transferable account data."
            ),
        )

        reason = String(
            required=False,
            description="Reason for the deletion operation.",
        )

    success = Boolean(
        required=True,
    )

    message = String()

    # =========================================================================
    # MUTATION
    # =========================================================================

    @classmethod
    @login_required
    @transaction.atomic
    def mutate_and_get_payload(
        cls,
        root,
        info,
        **input,
    ):
        """
        Delete or deactivate a user.
        """

        request = info.context

        current_user = getattr(
            request,
            "user",
            None,
        )

        # ---------------------------------------------------------------------
        # Authentication
        # ---------------------------------------------------------------------

        if (
            current_user is None
            or not current_user.is_authenticated
        ):
            raise GraphQLError(
                "Authentication required."
            )

        # ---------------------------------------------------------------------
        # Resolve target user
        # ---------------------------------------------------------------------

        target_user = cls.get_user_from_global_id(
            info,
            input["user_id"],
        )

        if target_user is None:
            raise GraphQLError(
                "User not found."
            )

        # ---------------------------------------------------------------------
        # Permission validation
        # ---------------------------------------------------------------------

        if (
            target_user == current_user
            and not current_user.is_superuser
        ):
            raise GraphQLError(
                "You cannot delete your own account."
            )

        if not current_user.is_superuser:
            if not current_user.has_perm(
                "accounts.delete_user"
            ):
                raise GraphQLError(
                    "You don't have permission to delete users."
                )

        # ---------------------------------------------------------------------
        # Resolve transfer recipient
        # ---------------------------------------------------------------------

        transfer_user = None

        transfer_user_id = input.get(
            "transfer_data_to",
        )

        if transfer_user_id:
            transfer_user = cls.get_user_from_global_id(
                info,
                transfer_user_id,
            )

            if transfer_user is None:
                raise GraphQLError(
                    "Transfer recipient user not found."
                )

            if transfer_user == target_user:
                raise GraphQLError(
                    "Cannot transfer data to the same user "
                    "being deleted."
                )

            if not transfer_user.is_active:
                raise GraphQLError(
                    "Transfer recipient must be an active user."
                )

        # ---------------------------------------------------------------------
        # Audit before destructive operation
        # ---------------------------------------------------------------------

        cls.create_audit_log(
            actor=current_user,
            target_user=target_user,
            input_data=input,
        )

        # ---------------------------------------------------------------------
        # Hard deletion
        # ---------------------------------------------------------------------

        if input.get(
            "hard_delete",
            False,
        ):
            if not current_user.is_superuser:
                raise GraphQLError(
                    "Only superusers can permanently delete users."
                )

            return cls.hard_delete_user(
                target_user,
                transfer_user,
            )

        # ---------------------------------------------------------------------
        # Soft deletion
        # ---------------------------------------------------------------------

        return cls.soft_delete_user(
            target_user,
            transfer_user,
        )

    # =========================================================================
    # GLOBAL ID RESOLUTION
    # =========================================================================

    @staticmethod
    def get_user_from_global_id(
        info,
        global_id,
    ):
        """
        Resolve a Relay global ID to a User instance.
        """

        try:
            target_user = (
                relay.Node.get_node_from_global_id(
                    info,
                    global_id,
                    only_type=UserNode,
                )
            )

        except Exception:
            return None

        if target_user is None:
            return None

        if not isinstance(
            target_user,
            User,
        ):
            return None

        return target_user

    # =========================================================================
    # REFRESH-TOKEN REVOCATION
    # =========================================================================

    @staticmethod
    def revoke_user_refresh_tokens(
        user,
    ):
        """
        Revoke all active refresh tokens belonging to a user.

        IMPORTANT
        ---------

        This method intentionally does NOT query or mutate:

            univa_jwt.models.RefreshToken

        The canonical JWT revocation service owns refresh-token
        revocation state and semantics.
        """

        if user is None:
            raise ValueError(
                "User is required for refresh-token revocation."
            )

        # ---------------------------------------------------------------------
        # Import lazily to keep the GraphQL/accounts module dependent on the
        # public JWT service boundary rather than its internal storage model.
        # ---------------------------------------------------------------------

        from univa_jwt.constants import REFRESH_TOKEN
        from univa_jwt.revocation import revoke_all_for_user

        try:
            result = revoke_all_for_user(
                user_id=str(
                    user.pk,
                ),
                token_type=REFRESH_TOKEN,
            )

        except Exception as exc:
            logger.exception(
                "Failed to revoke refresh tokens for user %s.",
                user.pk,
            )

            raise GraphQLError(
                "Unable to revoke authentication credentials."
            ) from exc

        # The canonical revocation service may return an integer count,
        # queryset-like result, boolean, or None depending on implementation.
        #
        # Normalize that boundary for callers without making assumptions
        # about its internal storage implementation.

        if isinstance(
            result,
            bool,
        ):
            return int(result)

        if isinstance(
            result,
            int,
        ):
            return result

        if result is None:
            return 0

        try:
            return int(result)

        except (
            TypeError,
            ValueError,
        ):
            return 0

    # =========================================================================
    # HARD DELETE
    # =========================================================================

    @classmethod
    def hard_delete_user(
        cls,
        user,
        transfer_user=None,
    ):
        """
        Permanently delete a user.

        Authentication refresh tokens are revoked through the canonical
        univa_jwt revocation service before the account is deleted.
        """

        user_id = user.pk

        # ---------------------------------------------------------------------
        # Revoke authentication refresh tokens
        # ---------------------------------------------------------------------
        #
        # NEVER use:
        #
        #     RefreshToken.objects.filter(...)
        #
        # The deprecated RefreshToken model is not part of the GraphQL
        # account-management boundary.
        # ---------------------------------------------------------------------

        cls.revoke_user_refresh_tokens(
            user,
        )

        # ---------------------------------------------------------------------
        # Transfer supported account data
        # ---------------------------------------------------------------------

        if transfer_user:
            cls._transfer_optional_related_data(
                user,
                transfer_user,
            )

        # ---------------------------------------------------------------------
        # Delete user
        # ---------------------------------------------------------------------

        user.delete()

        return cls(
            success=True,
            message=(
                f"User {user_id} and all related data "
                "were permanently deleted."
            ),
        )

    # =========================================================================
    # SOFT DELETE
    # =========================================================================

    @classmethod
    def soft_delete_user(
        cls,
        user,
        transfer_user=None,
    ):
        """
        Deactivate a user while retaining the account record.

        Authentication refresh tokens are revoked through the canonical
        univa_jwt revocation service.
        """

        user_id = user.pk

        # ---------------------------------------------------------------------
        # Transfer supported account data
        # ---------------------------------------------------------------------

        if transfer_user:
            cls._transfer_optional_related_data(
                user,
                transfer_user,
            )

        # ---------------------------------------------------------------------
        # Revoke authentication refresh tokens
        # ---------------------------------------------------------------------

        cls.revoke_user_refresh_tokens(
            user,
        )

        # ---------------------------------------------------------------------
        # Deactivate account
        # ---------------------------------------------------------------------

        user.is_active = False

        # ---------------------------------------------------------------------
        # Preserve original values safely while preventing reuse of
        # account identifiers.
        # ---------------------------------------------------------------------

        if user.email:
            user.email = (
                f"deleted_{user_id}_{user.email}"
            )

        if user.phone_number:
            user.phone_number = (
                f"deleted_{user_id}_{user.phone_number}"
            )

        user.set_unusable_password()

        update_fields = [
            "is_active",
            "email",
            "phone_number",
            "password",
        ]

        # ---------------------------------------------------------------------
        # Clear email verification state
        # ---------------------------------------------------------------------

        if hasattr(
            user,
            "email_verified",
        ):
            user.email_verified = False

            update_fields.append(
                "email_verified",
            )

        if hasattr(
            user,
            "email_verified_at",
        ):
            user.email_verified_at = None

            update_fields.append(
                "email_verified_at",
            )

        user.save(
            update_fields=update_fields,
        )

        return cls(
            success=True,
            message=(
                f"User {user_id} was successfully "
                "deactivated."
            ),
        )

    # =========================================================================
    # OPTIONAL RELATED ACCOUNT DATA TRANSFER
    # =========================================================================

    @staticmethod
    def _transfer_optional_related_data(
        user,
        transfer_user,
    ):
        """
        Transfer optional account-owned records.

        This method intentionally handles only data that belongs to the
        accounts domain or has explicitly been designated as transferable
        account data.

        Domain-specific records are NOT transferred here.

        In particular, this method MUST NOT handle:

            FaceEncoding
            FaceVerification

        Those records belong to specific identity/verification workflows
        and must be handled by their owning domain service.
        """

        # ---------------------------------------------------------------------
        # Addresses
        # ---------------------------------------------------------------------

        try:
            from accounts.models.address import Address

            Address.objects.filter(
                user=user,
            ).update(
                user=transfer_user,
            )

        except ImportError:
            logger.debug(
                "Accounts Address model is unavailable; "
                "skipping address transfer."
            )

        # ---------------------------------------------------------------------
        # User profile images
        # ---------------------------------------------------------------------

        try:
            from accounts.models.profile import UserProfileImage

            UserProfileImage.objects.filter(
                user=user,
            ).update(
                user=transfer_user,
            )

        except ImportError:
            logger.debug(
                "UserProfileImage model is unavailable; "
                "skipping profile-image transfer."
            )

        # ---------------------------------------------------------------------
        # IMPORTANT
        # ---------------------------------------------------------------------
        #
        # NO FaceEncoding import.
        #
        # NO FaceVerification import.
        #
        # NO biometric transfer.
        #
        # These records are intentionally outside generic account
        # deletion/transfer orchestration.
        # ---------------------------------------------------------------------

    # =========================================================================
    # AUDIT LOG
    # =========================================================================

    @classmethod
    def create_audit_log(
        cls,
        actor,
        target_user,
        input_data,
    ):
        """
        Create an audit record when the audit model is available.

        The audit application owns AuditLog.

        Accounts therefore imports it lazily instead of creating a hard
        module-level dependency.
        """

        try:
            from audit.models.log import AuditLog

        except ImportError:
            logger.warning(
                "AuditLog model is not available. "
                "Skipping user deletion audit."
            )

            return

        AuditLog.objects.create(
            actor=actor,
            action="delete_user",
            target_user=target_user,
            data={
                "hard_delete": input_data.get(
                    "hard_delete",
                    False,
                ),
                "transfer_to": input_data.get(
                    "transfer_data_to",
                ),
                "reason": input_data.get(
                    "reason",
                ),
                "at": timezone.now().isoformat(),
            },
        )


# =============================================================================
# USER MANAGEMENT MUTATIONS REGISTRY
# =============================================================================


class UserMutations(
    graphene.ObjectType,
):
    """
    User-management mutation registry.
    """

    create_user = CreateUserMutation.Field()

    delete_user = DeleteUserMutation.Field()