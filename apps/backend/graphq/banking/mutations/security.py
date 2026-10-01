# apps/backend/graphq/banking/mutations/security.py

"""
GraphQL mutations for Banking security models.

PIN operations all delegate to BankingSecurity, which is the SINGLE
SOURCE OF TRUTH for banking PINs.

    SetBankingPinMutation    set/change a PIN
    VerifyPinMutation        verify a PIN
    PinLoginMutation         authenticate via trusted device + PIN

The Account model does NOT store PINs. Any code that reads
user.profile.check_pin() is stale and unsafe — UserProfile is a
presentation-layer extension, not the banking PIN store.
"""

import logging

import graphene
from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from graphene import Boolean, Field, ID, String, relay
from graphql import GraphQLError

from banking.models.security import BankingSecurity
from biometrics.models.device import BiometricDevice
from graphq.accounts.mixin import RateLimitMixin, TokenGenerationMixin
from graphq.accounts.types.user import UserNode
from univa_jwt.decorators import login_required


logger = logging.getLogger(__name__)


# ============================================================================
# HELPERS
# ============================================================================

def _get_authenticated_user(info):
    """Return the authenticated Django user."""
    user = getattr(info.context, "user", None)
    if not user or not user.is_authenticated:
        raise GraphQLError("Authentication required.")
    return user


def _clean_message(exc):
    """Return a clean single-line message from a ValidationError."""
    messages = getattr(exc, "messages", None)
    if messages:
        return str(messages[0])
    return str(exc)


def _wrap(fn, *args, **kwargs):
    """Convert service-layer ValidationError into GraphQLError."""
    try:
        return fn(*args, **kwargs)
    except ValidationError as exc:
        raise GraphQLError(_clean_message(exc)) from exc


def _get_banking_security(user):
    """
    Return the user's BankingSecurity row, creating one if absent.

    BankingSecurity is the SINGLE SOURCE OF TRUTH for banking PINs.
    """
    security, _ = BankingSecurity.objects.get_or_create(user=user)
    return security


def _validate_pin(pin):
    if not pin:
        raise GraphQLError("PIN is required.")
    if len(pin) != 4 or not pin.isdigit():
        raise GraphQLError("PIN must be exactly 4 digits.")
    return pin


# ============================================================================
# SET BANKING PIN
# ============================================================================

class SetBankingPinMutation(relay.ClientIDMutation):
    """
    Set or change the user's banking PIN.

    Delegates to BankingSecurity.set_pin, which handles hashing,
    attempt reset, and lockout clearing atomically.
    """

    class Input:
        pin = String(required=True)
        current_pin = String()

    success = Boolean(required=True)
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        pin = _validate_pin(input.get("pin"))
        current_pin = input.get("current_pin")

        security = _get_banking_security(user)

        # If changing an existing PIN, verify the current one first.
        # check_pin raises ValidationError on failure; it never
        # returns False.
        if current_pin:
            if not security.has_pin:
                raise GraphQLError(
                    "No PIN is currently set. Omit current_pin to set one."
                )
            _wrap(security.check_pin, current_pin)

        _wrap(security.set_pin, pin)

        logger.info(
            "Banking PIN set: user=%s had_pin=%s",
            user.pk,
            security.has_pin,
        )

        return cls(
            success=True,
            message=(
                "PIN set successfully."
                if not current_pin
                else "PIN changed successfully."
            ),
        )


# ============================================================================
# VERIFY PIN
# ============================================================================

class VerifyPinMutation(relay.ClientIDMutation):
    """Verify the authenticated user's PIN."""

    class Input:
        pin = String(required=True)

    success = Boolean(required=True)
    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        pin = _validate_pin(input.get("pin"))

        try:
            security = BankingSecurity.objects.get(user=user)
        except BankingSecurity.DoesNotExist:
            raise GraphQLError(
                "No PIN set for this account."
            )

        if not security.has_pin:
            raise GraphQLError("No PIN set for this account.")

        # check_pin raises on failure; it never returns False.
        _wrap(security.check_pin, pin)

        return cls(
            success=True,
            message="PIN verified successfully.",
        )


# ============================================================================
# PIN LOGIN
# ============================================================================

class PinLoginMutation(
    RateLimitMixin,
    TokenGenerationMixin,
    relay.ClientIDMutation,
):
    """
    Authenticate using a registered trusted device and banking PIN.

    The device must exist and be trusted. The PIN is verified against
    BankingSecurity (not UserProfile).
    """

    class Input:
        device_id = String(required=True)
        pin = String(required=True)

    token = String()
    refresh_token = String()
    user = Field(UserNode)
    success = Boolean(required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        device_id = (input.get("device_id") or "").strip()
        pin = input.get("pin")

        if not device_id:
            raise GraphQLError("Device ID is required.")

        if not pin:
            raise GraphQLError("PIN is required.")

        cls.check_rate_limit(
            f"pin_login:{device_id}",
            limit=5,
            window=300,
        )

        device = (
            BiometricDevice.objects
            .select_related("user")
            .filter(device_id=device_id, trusted=True)
            .first()
        )

        if device is None:
            raise GraphQLError("Unrecognized or untrusted device.")

        user = device.user

        try:
            security = BankingSecurity.objects.get(user=user)
        except BankingSecurity.DoesNotExist:
            raise GraphQLError("No PIN set for this account.")

        if not security.has_pin:
            raise GraphQLError("No PIN set for this account.")

        _wrap(security.check_pin, pin)

        device.mark_used()

        token, refresh_token = cls.generate_tokens(
            user,
            request=info.context,
        )

        return cls(
            token=token,
            refresh_token=refresh_token,
            user=user,
            success=True,
        )


# ============================================================================
# MUTATION REGISTRY
# ============================================================================

class SecurityMutations(graphene.ObjectType):
    set_banking_pin = SetBankingPinMutation.Field()
    verify_pin = VerifyPinMutation.Field()
    pin_login = PinLoginMutation.Field()


__all__ = [
    "SetBankingPinMutation",
    "VerifyPinMutation",
    "PinLoginMutation",
    "SecurityMutations",
]