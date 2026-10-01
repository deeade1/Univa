# apps/backend/graphq/accounts/mutations/auth.py

from __future__ import annotations

"""
GraphQL authentication mutations for Univa.

ARCHITECTURE
============

This module is a GraphQL adapter.

It MUST NOT implement JWT cryptography, JWT payload construction,
JWT decoding, JWT revocation, or refresh-token rotation.

Canonical authentication boundary:

    GraphQL
        |
        v
    univa_jwt.authentication
        |
        +--> credential authentication
        +--> JWT issuance
        +--> access-token validation
        +--> refresh-token authentication
        +--> refresh-token rotation
        +--> refresh-token revocation
        |
        v
    univa_jwt.tokens
        |
        +--> signing
        +--> decoding
        +--> claim validation
        +--> revocation validation

Canonical JWT representation:

    univa_jwt.claims.TokenClaims

This module therefore does NOT:

    - import PyJWT
    - call jwt.encode()
    - call jwt.decode()
    - construct JWT payloads
    - inspect raw JWT payload dictionaries
    - import univa_jwt.blacklist
    - use the deprecated univa_jwt.models.RefreshToken
    - implement refresh-token rotation
    - implement JWT revocation
    - generate password-reset JWTs

Password reset uses Django's password-reset token mechanism rather
than the authentication JWT subsystem.

Magic links remain owned by MagicLoginToken.

Biometric magic-link behavior remains owned by the biometric mutation
module.
"""

import logging

import graphene
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
)
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.core.mail import send_mail
from django.db.models import Q
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from graphene import Boolean, Field, String, relay
from graphene.types.generic import GenericScalar
from graphql import GraphQLError

from accounts.models.auth import MagicLoginToken
from biometrics.models.verification import FaceVerification
from graphq.accounts.mixin import RateLimitMixin
from graphq.accounts.types import UserNode
from graphq.biometrics.mutations import (
    VerifyFaceForMagicLinkMutation,
)
from univa_jwt.authentication import (
    authenticate_access_token_with_claims,
    authenticate_credentials,
    authenticate_refresh_token,
    issue_token_pair,
    refresh_access_token,
    revoke_refresh_token as revoke_refresh_token_service,
)
from univa_jwt.constants import REFRESH_TOKEN
from univa_jwt.decorators import login_required
from univa_jwt.revocation import revoke_all_for_user

from notifications.events.emitter import emit_and_queue_notification_event
from notifications.events.constants import ACCOUNT_MAGIC_LINK_REQUESTED
from univa_jwt.exceptions import JSONRefreshTokenExpired
from univa_jwt.refresh import RefreshTokenInvalidError



logger = logging.getLogger(__name__)

User = get_user_model()


# ============================================================================
# TEST / COMPATIBILITY SEAMS
# ============================================================================

# Keep these module-level aliases intentionally.

# Existing GraphQL tests patch:
#
#     graphq.accounts.mutations.auth.revoke_refresh_token
#
# Keeping this alias gives the GraphQL adapter a stable patch seam without
# exposing or reimplementing JWT revocation internals here.
revoke_refresh_token = revoke_refresh_token_service


# Existing GraphQL tests patch:
#
#     graphq.accounts.mutations.auth.revoke_all_for_user
#
# This remains a service-level dependency. The GraphQL layer does not inspect
# or manipulate the underlying revocation state.
#
# The imported service is already exposed at module scope and therefore
# remains patchable by the test suite.


# ============================================================================
# HELPERS
# ============================================================================


def _get_request(info):
    """
    Resolve the Django request/context from Graphene ResolveInfo.

    Normal Graphene execution:

        info.context -> Django request

    Direct unit tests may pass the context/request object itself:

        mutate_and_get_payload(None, context, ...)

    Supporting both forms keeps the GraphQL adapter easy to test without
    changing production Graphene behavior.
    """
    return getattr(
        info,
        "context",
        info,
    )


def _get_context(info):
    """
    Return the GraphQL/Django context object.

    In Graphene-Django the Django request is normally stored in
    ``info.context``.

    Direct unit tests may pass the request/context object itself.
    """
    return _get_request(info)


def _get_ip_address(info):
    """
    Safely extract the client IP address.

    Supports both normal Graphene ResolveInfo and direct unit-test
    context objects.
    """
    request = _get_request(info)

    meta = getattr(
        request,
        "META",
        {},
    )

    return meta.get(
        "REMOTE_ADDR",
        "unknown",
    )


def _graphql_authentication_error(
    exc: Exception,
) -> GraphQLError:
    """
    Convert an internal authentication exception into a GraphQL error.

    Internal implementation details are intentionally hidden from the
    GraphQL client.
    """
    logger.warning(
        "Authentication operation failed: %s",
        exc,
        exc_info=True,
    )

    return GraphQLError(
        "Authentication request could not be completed."
    )


# ============================================================================
# SIGN IN
# ============================================================================


class ObtainJSONWebTokenMutation(
    RateLimitMixin,
    relay.ClientIDMutation,
):
    """
    Authenticate a user using email or phone plus password.

    JWT issuance is delegated entirely to
    ``univa_jwt.authentication``.
    """

    class Input:
        contact = String(
            required=True,
        )

        password = String(
            required=True,
        )

        remember_me = Boolean(
            default_value=False,
        )

    token = String()
    refresh_token = String()
    user = Field(UserNode)

    @classmethod
    def mutate_and_get_payload(
        cls,
        root,
        info,
        **input,
    ):
        contact = (
            input.get("contact")
            or ""
        ).strip()

        if not contact:
            raise GraphQLError(
                "Contact is required."
            )

        password = input.get(
            "password"
        )

        if not password:
            raise GraphQLError(
                "Password is required."
            )

        request = _get_request(info)
        ip_address = _get_ip_address(info)

        # Per-contact + IP protection.
        cls.check_rate_limit(
            f"auth_attempt:{contact}",
            limit=3,
            window=300,
            identifier=ip_address,
        )

        # Global authentication protection.
        cls.check_global_rate_limit(
            request,
            "authentication",
            limit=10,
            window=900,
        )

        try:
            user = authenticate_credentials(
                email=(
                    contact
                    if "@" in contact
                    else None
                ),
                phone_number=(
                    contact
                    if "@" not in contact
                    else None
                ),
                password=password,
            )

        except Exception as exc:
            failed_key = (
                f"auth_failures:{contact}"
            )

            failures = (
                cache.get(
                    failed_key,
                    0,
                )
                + 1
            )

            cache.set(
                failed_key,
                failures,
                900,
            )

            if failures >= 5:
                raise GraphQLError(
                    "Too many failed attempts. "
                    "Please try again later."
                ) from exc

            raise GraphQLError(
                "Invalid credentials."
            ) from exc

        if user is None:
            raise GraphQLError(
                "Invalid credentials."
            )

        if not getattr(
            user,
            "is_active",
            True,
        ):
            raise GraphQLError(
                "Account inactive."
            )

        cache.delete(
            f"auth_failures:{contact}"
        )

        try:
            access_token, refresh_token = (
                issue_token_pair(
                    user,
                )
            )

        except Exception as exc:
            logger.exception(
                "JWT issuance failed for user %s.",
                user.pk,
            )

            raise GraphQLError(
                "Authentication could not be completed."
            ) from exc

        user.last_login = timezone.now()

        user.save(
            update_fields=[
                "last_login",
            ]
        )

        user_logged_in.send(
            sender=cls,
            request=request,
            user=user,
        )

        return cls(
            token=access_token,
            refresh_token=refresh_token,
            user=user,
        )


# ============================================================================
# REFRESH TOKEN
# ============================================================================


class RefreshTokenMutation(
    relay.ClientIDMutation,
):
    """
    Rotate a refresh JWT and issue a replacement access token.

    Refresh-token validation and rotation are owned entirely by
    ``univa_jwt.authentication``.

    IMPORTANT
    ---------

    Do not call ``authenticate_refresh_token()`` here before calling
    ``refresh_access_token()``.

    ``refresh_access_token()`` is already the canonical service operation
    responsible for validating the supplied refresh token and performing
    the rotation.

    Performing a second authentication here would:

        1. duplicate authentication logic;
        2. make the GraphQL adapter depend on internal validation behavior;
        3. cause unnecessary JWT decoding;
        4. make adapter tests fail when using mocked refresh tokens;
        5. violate the single authentication boundary.

    Therefore this mutation delegates the complete operation to
    ``refresh_access_token()``.
    """

    class Input:
        refresh_token = String(
            required=True,
        )

    token = String()
    refresh_token = String()

    @classmethod
    def mutate_and_get_payload(
        cls,
        root,
        info,
        **input,
    ):
        raw_refresh_token = (
            input.get("refresh_token")
            or ""
        ).strip()

        if not raw_refresh_token:
            raise GraphQLError(
                "Refresh token is required."
            )

        try:
            rotation = refresh_access_token(raw_refresh_token)
            return cls(
                token=rotation.access_token,
                refresh_token=rotation.refresh_token,
            )

        except (RefreshTokenInvalidError, JSONRefreshTokenExpired) as exc:
            logger.info("Refresh token rejected: %s", exc)
            raise GraphQLError(
                "Refresh token is invalid or has been revoked."
            ) from exc

        except AttributeError as exc:
            # This is a code bug in the adapter, not a client problem.
            logger.exception(
                "RefreshTokenRotation missing expected attribute. "
                "Adapter/service contract mismatch."
            )
            raise GraphQLError(
                "Authentication request could not be completed."
            ) from exc

        except Exception as exc:
            raise _graphql_authentication_error(exc) from exc
# ============================================================================
# REVOKE ONE REFRESH TOKEN
# ============================================================================


class RevokeTokenMutation(
    relay.ClientIDMutation,
):
    """
    Revoke a refresh JWT.

    Revocation is delegated to
    ``univa_jwt.authentication``.
    """

    class Input:
        refresh_token = String(
            required=True,
        )

    success = Boolean()

    @classmethod
    def mutate_and_get_payload(
        cls,
        root,
        info,
        **input,
    ):
        raw_refresh_token = (
            input.get("refresh_token")
            or ""
        ).strip()

        if not raw_refresh_token:
            raise GraphQLError(
                "Refresh token is required."
            )

        try:
            success = revoke_refresh_token_service(
                raw_refresh_token,
            )

            if not success:
                raise GraphQLError(
                    "Unable to revoke refresh token."
                )

            return cls(
                success=True,
            )

        except GraphQLError:
            raise

        except Exception as exc:
            raise _graphql_authentication_error(
                exc
            ) from exc


# ============================================================================
# VERIFY TOKEN
# ============================================================================


class VerifyTokenMutation(
    relay.ClientIDMutation,
):
    """
    Verify a canonical Univa access JWT.

    JWT validation and claim extraction are delegated to
    ``univa_jwt.authentication``.

    This GraphQL adapter does not decode JWTs directly.
    """

    payload = GenericScalar()

    valid = graphene.Boolean(
        required=True,
    )

    user = graphene.Field(
        UserNode,
    )

    expires_at = graphene.DateTime()

    class Input:
        token = graphene.String(
            required=True,
        )

    @classmethod
    def mutate_and_get_payload(
        cls,
        root,
        info,
        **input,
    ):
        token = (
            input.get("token")
            or ""
        ).strip()

        if not token:
            return cls(
                valid=False,
                payload={
                    "error": "Token is required.",
                },
                user=None,
                expires_at=None,
            )

        try:
            user, claims = (
                authenticate_access_token_with_claims(
                    token,
                )
            )

            return cls(
                valid=True,
                payload={
                    "sub": claims.user_id,
                    "jti": claims.jti,
                    "token_type": claims.token_type,
                    "iat": int(
                        claims.issued_at.timestamp()
                    ),
                    "exp": int(
                        claims.expires_at.timestamp()
                    ),
                    "iss": claims.issuer,
                    "aud": claims.audience,
                },
                user=user,
                expires_at=claims.expires_at,
            )

        except Exception:
            logger.info(
                "JWT verification failed.",
                exc_info=True,
            )

            return cls(
                valid=False,
                payload={
                    "error": (
                        "Invalid or expired token."
                    ),
                },
                user=None,
                expires_at=None,
            )


# ============================================================================
# LOGOUT
# ============================================================================


class LogoutMutation(
    relay.ClientIDMutation,
):
    """
    Logout the currently authenticated user.

    The GraphQL layer does not maintain a refresh-token table.

    When a refresh token is supplied:

        1. the canonical authentication service authenticates it;
        2. ownership is checked against the current user;
        3. revocation is delegated to the canonical revocation service.

    The GraphQL layer never decodes the JWT itself.
    """

    class Input:
        refresh_token = String(
            required=False,
        )

    success = Boolean()

    @classmethod
    @login_required
    def mutate_and_get_payload(
        cls,
        root,
        info,
        **input,
    ):
        request = _get_request(info)

        user = request.user

        raw_refresh_token = (
            input.get("refresh_token")
            or getattr(
                request,
                "refresh_token",
                None,
            )
        )

        if raw_refresh_token:
            raw_refresh_token = (
                raw_refresh_token.strip()
            )

            if raw_refresh_token:
                try:
                    refresh_user, _claims = (
                        authenticate_refresh_token(
                            raw_refresh_token,
                        )
                    )

                    if (
                        refresh_user.pk
                        != user.pk
                    ):
                        raise GraphQLError(
                            "Logout could not be completed."
                        )

                    success = revoke_refresh_token(
                        raw_refresh_token,
                    )

                    if not success:
                        raise GraphQLError(
                            "Logout could not be completed."
                        )

                except GraphQLError:
                    raise

                except Exception as exc:
                    logger.warning(
                        "Unable to revoke refresh token "
                        "during logout for user %s: %s",
                        user.pk,
                        exc,
                        exc_info=True,
                    )

                    raise GraphQLError(
                        "Logout could not be completed."
                    ) from exc

        user_logged_out.send(
            sender=cls,
            request=request,
            user=user,
        )

        return cls(
            success=True,
        )


# ============================================================================
# REVOKE ALL TOKENS
# ============================================================================


class RevokeAllTokensMutation(
    relay.ClientIDMutation,
):
    """
    Revoke all active refresh tokens for the authenticated user.

    The canonical JWT revocation service owns all server-side
    revocation state.

    This GraphQL adapter does not access the deprecated
    ``RefreshToken`` model.
    """

    class Input:
        pass

    revoked_count = graphene.Int()

    @classmethod
    @login_required
    def mutate_and_get_payload(
        cls,
        root,
        info,
        **input,
    ):
        request = _get_request(info)

        user_id = str(
            request.user.pk
        )

        try:
            count = revoke_all_for_user(
                user_id=user_id,
                token_type=REFRESH_TOKEN,
            )

        except Exception as exc:
            logger.exception(
                "Unable to revoke all refresh tokens "
                "for user %s.",
                user_id,
            )

            raise GraphQLError(
                "Unable to revoke all refresh tokens."
            ) from exc

        return cls(
            revoked_count=count,
        )


# ============================================================================
# PASSWORD RESET
# ============================================================================


class SendPasswordResetMutation(
    RateLimitMixin,
    relay.ClientIDMutation,
):
    """
    Send a Django password-reset link.

    Password-reset tokens are deliberately NOT authentication JWTs.

    This prevents the account-password-reset flow from introducing
    a non-canonical "reset" JWT token type into univa_jwt.
    """

    class Input:
        email = String(
            required=True,
        )

    success = Boolean()

    @classmethod
    def mutate_and_get_payload(
        cls,
        root,
        info,
        **input,
    ):
        email = (
            input.get("email")
            or ""
        ).strip().lower()

        if not email:
            raise GraphQLError(
                "Email is required."
            )

        cls.check_rate_limit(
            f"pwd_reset:{email}",
            limit=3,
            window=3600,
        )

        user = (
            User.objects
            .filter(
                email__iexact=email,
                is_active=True,
            )
            .first()
        )

        # Always return success for a syntactically valid request.
        # This prevents account enumeration.
        if user is None:
            return cls(
                success=True,
            )

        uid = urlsafe_base64_encode(
            force_bytes(
                user.pk
            )
        )

        token = (
            default_token_generator.make_token(
                user
            )
        )

        reset_url = (
            f"{settings.FRONTEND_URL}"
            f"/reset-password/"
            f"?uid={uid}"
            f"&token={token}"
        )

        try:
            send_mail(
                subject="Password Reset Request",
                message=(
                    "Click the link below to reset "
                    "your password:\n\n"
                    f"{reset_url}"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[
                    user.email,
                ],
                fail_silently=False,
            )

        except Exception as exc:
            logger.exception(
                "Password-reset email delivery failed "
                "for user %s.",
                user.pk,
            )

            raise GraphQLError(
                "Unable to send password reset email."
            ) from exc

        return cls(
            success=True,
        )


# ============================================================================
# MAGIC LINK DELIVERY FUNCTIONS (NOTIFICATION-BASED)
# ============================================================================

def send_magic_link_email(user, token) -> None:
    """
    Deliver a magic login link via the notification system.

    This function delegates to the canonical notification event emitter.
    The actual email delivery is handled by the notification system's
    email channel.
    """
    try:
        emit_and_queue_notification_event(
            event_type=ACCOUNT_MAGIC_LINK_REQUESTED,
            module="account",
            actor=user,
            object_type="User",
            object_id=user.id,
            payload={
                "contact": user.email,
                "channel": "email",
                "token": token.token,
                "expires_at": token.expires_at.isoformat(),
                "redirect_to": token.redirect_to,
                "security_context": {
                    "device_fingerprint": token.device_fingerprint,
                    "browser_fingerprint": token.browser_fingerprint,
                    "ip_address": token.ip_address,
                }
            }
        )
        logger.info("Magic link email queued: user_id=%s", user.pk)

    except Exception as exc:
        logger.exception("Failed to queue magic link email: user_id=%s", user.pk)
        raise GraphQLError("Unable to send magic link.") from exc


def send_magic_link_sms(user, token) -> None:
    """
    Deliver a magic login link via the notification system.

    This function delegates to the canonical notification event emitter.
    The actual SMS delivery is handled by the notification system's
    SMS channel.
    """
    try:
        emit_and_queue_notification_event(
            event_type=ACCOUNT_MAGIC_LINK_REQUESTED,
            module="account",
            actor=user,
            object_type="User",
            object_id=user.id,
            payload={
                "contact": user.phone_number,
                "channel": "sms",
                "token": token.token,
                "expires_at": token.expires_at.isoformat(),
                "redirect_to": token.redirect_to,
                "security_context": {
                    "device_fingerprint": token.device_fingerprint,
                    "browser_fingerprint": token.browser_fingerprint,
                    "ip_address": token.ip_address,
                }
            }
        )
        logger.info("Magic link SMS queued: user_id=%s", user.pk)

    except Exception as exc:
        logger.exception("Failed to queue magic link SMS: user_id=%s", user.pk)
        raise GraphQLError("Unable to send magic link.") from exc


# ============================================================================
# MAGIC LINK MUTATIONS
# ============================================================================


class SendMagicLinkMutation(
    relay.ClientIDMutation,
):
    """
    Send a magic login link to email or phone.

    Magic-link token generation belongs to MagicLoginToken.
    """

    class Input:
        contact = String(required=True)
        redirect_to = String(required=False)
        channel = String(required=False, default_value="email")

    success = Boolean()
    message = String()

    @classmethod
    def mutate_and_get_payload(
        cls,
        root,
        info,
        **input,
    ):
        contact = input.get("contact", "").strip()
        channel = input.get("channel", "email").lower().strip()

        if not contact:
            raise GraphQLError("Contact is required.")

        if channel not in {"email", "sms"}:
            raise GraphQLError("Invalid magic-link channel.")

        request = _get_request(info)

        cache_key = f"magic_link:{channel}:{contact}"

        if cache.get(cache_key):
            raise GraphQLError(
                "Please wait before requesting another magic link."
            )

        user = (
            User.objects
            .filter(Q(email__iexact=contact) | Q(phone_number=contact))
            .first()
        )

        if user is None:
            # Avoid exposing account existence.
            return cls(
                success=True,
                message="If the account exists, a magic link will be sent.",
            )

        try:
            token = MagicLoginToken.create_for_user(
                user=user,
                request=request,
                redirect_to=input.get("redirect_to"),
            )

            if channel == "email" and user.email:
                send_magic_link_email(user, token)
                message = "Magic link sent to your email."

            elif channel == "sms" and user.phone_number:
                send_magic_link_sms(user, token)
                message = "Magic link sent via SMS."

            else:
                raise GraphQLError("Requested contact method is not available.")

            cache.set(cache_key, True, 60)

            return cls(
                success=True,
                message=message,
            )

        except GraphQLError:
            raise

        except Exception as exc:
            logger.exception("Magic-link delivery failed for user %s.", user.pk)
            raise GraphQLError("Unable to send magic link.") from exc


# ============================================================================
# VERIFY MAGIC LINK
# ============================================================================


class VerifyMagicLinkMutation(
    relay.ClientIDMutation,
):
    """
    Validate a MagicLoginToken.

    This mutation does not issue JWTs. JWT issuance belongs to the
    dedicated biometric/general magic-link completion mutation.
    """

    class Input:
        token = String(required=True)
        purpose = String(required=False)

    valid = Boolean()
    requires_face_verification = Boolean()
    requires_liveness_check = Boolean()
    user = Field(UserNode)
    message = String()
    device_match = String()

    @classmethod
    def mutate_and_get_payload(
        cls,
        root,
        info,
        **input,
    ):
        raw_token = input.get("token", "").strip()

        if not raw_token:
            return cls(
                valid=False,
                requires_face_verification=False,
                requires_liveness_check=False,
                user=None,
                message="Token is required.",
                device_match="unknown",
            )

        request = _get_request(info)

        try:
            token = MagicLoginToken.validate_token(
                raw_token,
                purpose=input.get("purpose"),
                request=request,
            )

            device_match = "unknown"

            if token.device_fingerprint:
                current_fingerprint = (
                    MagicLoginToken._generate_device_fingerprint(
                        MagicLoginToken._get_device_info(request)
                    )
                )

                device_match = (
                    "matched"
                    if current_fingerprint == token.device_fingerprint
                    else "mismatch"
                )

            logger.info(
                "Magic-link verification: device=%s user=%s",
                device_match,
                token.user.pk,
            )

            face_verification = (
                FaceVerification.objects
                .filter(
                    user=token.user,
                    is_verified=True,
                )
                .first()
            )

            return cls(
                valid=True,
                requires_face_verification=bool(face_verification),
                requires_liveness_check=(
                    face_verification.verification_channel == "liveness"
                    if face_verification
                    else False
                ),
                user=token.user,
                message="Token is valid.",
                device_match=device_match,
            )

        except ValueError as exc:
            logger.warning("Magic-link verification failed: %s", exc)
            return cls(
                valid=False,
                requires_face_verification=False,
                requires_liveness_check=False,
                user=None,
                message=str(exc),
                device_match="unknown",
            )

        except Exception:
            logger.exception("Unexpected magic-link verification failure.")
            return cls(
                valid=False,
                requires_face_verification=False,
                requires_liveness_check=False,
                user=None,
                message="Unable to verify magic link.",
                device_match="unknown",
            )


# ============================================================================
# RESEND MAGIC LINK
# ============================================================================


class ResendMagicLinkMutation(
    RateLimitMixin,
    relay.ClientIDMutation,
):
    """
    Resend a magic link with cooldown protection.
    """

    class Input:
        contact = String(required=True)
        channel = String(default_value="email")

    success = Boolean()
    message = String()

    @classmethod
    def mutate_and_get_payload(
        cls,
        root,
        info,
        **input,
    ):
        contact = input.get("contact", "").strip()
        channel = input.get("channel", "email").lower().strip()

        if not contact:
            raise GraphQLError("Contact is required.")

        if channel not in {"email", "sms"}:
            raise GraphQLError("Invalid magic-link channel.")

        request = _get_request(info)

        cache_key = f"resend_magic_link:{channel}:{contact}"

        last_sent = cache.get(cache_key)

        if last_sent:
            cooldown = getattr(settings, "MAGIC_LINK_RESEND_COOLDOWN", 60)
            elapsed = (timezone.now() - last_sent).total_seconds()

            if elapsed < cooldown:
                remaining = cooldown - elapsed
                raise GraphQLError(
                    f"Please wait {remaining:.0f} seconds "
                    "before requesting another link."
                )

        user = (
            User.objects
            .filter(Q(email__iexact=contact) | Q(phone_number=contact))
            .first()
        )

        if user is None:
            return cls(
                success=True,
                message="If the account exists, a new magic link will be sent.",
            )

        try:
            token = MagicLoginToken.create_for_user(
                user=user,
                request=request,
            )

            if channel == "email" and user.email:
                send_magic_link_email(user, token)
                message = "New magic link sent to your email."

            elif channel == "sms" and user.phone_number:
                send_magic_link_sms(user, token)
                message = "New magic link sent via SMS."

            else:
                raise GraphQLError("Requested contact method is not available.")

            cooldown = getattr(settings, "MAGIC_LINK_RESEND_COOLDOWN", 60)
            cache.set(cache_key, timezone.now(), cooldown)

            return cls(
                success=True,
                message=message,
            )

        except GraphQLError:
            raise

        except Exception as exc:
            logger.exception("Magic-link resend failed for user %s.", user.pk)
            raise GraphQLError("Unable to resend magic link.") from exc


# ============================================================================
# ACCOUNT MUTATIONS REGISTRY
# ============================================================================


class AuthenticationMutations(
    graphene.ObjectType,
):
    """
    Authentication mutation registry.

    This class only exposes GraphQL adapters.

    Authentication business logic remains in the appropriate services.
    """

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    sign_in = (
        ObtainJSONWebTokenMutation.Field()
    )

    refresh_token = (
        RefreshTokenMutation.Field()
    )

    revoke_token = (
        RevokeTokenMutation.Field()
    )

    verify_token = (
        VerifyTokenMutation.Field()
    )

    logout = (
        LogoutMutation.Field()
    )

    revoke_all_tokens = (
        RevokeAllTokensMutation.Field()
    )

    send_password_reset = (
        SendPasswordResetMutation.Field()
    )

    # ------------------------------------------------------------------
    # Magic links
    # ------------------------------------------------------------------

    send_magic_link = (
        SendMagicLinkMutation.Field()
    )

    verify_magic_link = (
        VerifyMagicLinkMutation.Field()
    )

    resend_magic_link = (
        ResendMagicLinkMutation.Field()
    )

    # ------------------------------------------------------------------
    # Biometric magic-link authentication
    #
    # The biometric mutation itself owns the biometric workflow.
    # This registry merely exposes it.
    # ------------------------------------------------------------------

    verify_face_for_magic_link = (
        VerifyFaceForMagicLinkMutation.Field()
    )