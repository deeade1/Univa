# apps/backend/graphq/banking/mutations/qr_payments.py

"""
GraphQL mutations for Banking QR payment models.

This module contains mutations for:
    - QRCode: QR codes for payments (OPay-style)
    - QRTransaction: Transactions via QR code scanning

Money movement
--------------

All money movement is delegated to:

    banking.services.qr_service.QRService.pay_via_qr

which posts through:

    banking.models.accounting.AccountingManager.create_double_entry

This module does NOT:
    - post LedgerEntry rows itself
    - create Transaction rows for money movement
    - allow clients to set arbitrary status transitions on transactions

QR metadata CRUD (create/update/delete/regenerate QR codes) is
owner-scoped. QR payment initiation is owner-scoped and delegates to
the service.
"""

import base64
import logging
import uuid
from datetime import datetime
from decimal import Decimal

import graphene
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from django.utils import timezone
from graphene import ID, Boolean, Decimal as GrapheneDecimal, Field, Int, String, relay
from graphql import GraphQLError
from graphql_relay import from_global_id

from banking.models.core import Account
from banking.models.merchant import Merchant
from banking.models.qr_payments import QRCode, QRTransaction
from banking.services.qr_service import QRService
from graphq.banking.types.qr_payments import (
    QRCodeNode,
    QRTransactionNode,
)
from univa_jwt.decorators import login_required

User = get_user_model()
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


def _get_model_by_global_id(global_id, model, model_name):
    """Get a model instance by Relay global ID."""
    if not global_id:
        raise GraphQLError(f"{model_name} ID is required.")

    try:
        _, pk = from_global_id(global_id)
        return model.objects.get(pk=pk)
    except model.DoesNotExist:
        raise GraphQLError(f"{model_name} not found.")
    except Exception as exc:
        raise GraphQLError(f"Invalid {model_name} ID.") from exc


def _validate_amount(amount):
    """Validate and normalize a monetary amount."""
    try:
        amount = Decimal(str(amount))
    except (TypeError, ValueError):
        raise GraphQLError("Invalid amount value.")

    if amount <= Decimal("0.00"):
        raise GraphQLError("Amount must be greater than zero.")

    return amount.quantize(Decimal("0.01"))


def _validate_datetime(datetime_str):
    """Validate a datetime string."""
    if not datetime_str:
        return None
    try:
        return datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
    except ValueError:
        raise GraphQLError("Invalid datetime format. Use ISO format.")


def _clean_message(exc):
    """
    Extract a clean single-line message from a ValidationError.

    Django's ValidationError.__str__ returns the list repr for
    multi-message errors, e.g. "['Cannot pay yourself.']". We want
    just the first message so GraphQL clients see clean text.
    """
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


def _raise_graphql(exc):
    """Raise a GraphQLError with a clean message from a ValidationError."""
    raise GraphQLError(_clean_message(exc)) from exc


# ============================================================================
# QR CODE MUTATIONS (metadata only)
# ============================================================================

class CreateQRCodeMutation(relay.ClientIDMutation):
    """Create a QR code for payments."""

    class Input:
        qr_type = String(required=True)
        merchant_id = ID()
        fixed_amount = GrapheneDecimal()
        description = String()
        max_uses = Int()
        max_amount_per_use = GrapheneDecimal()
        expires_at = String()
        reference = String()

    qr_code = Field(QRCodeNode)
    qr_image_base64 = String()
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        # Validate QR type
        valid_types = [choice[0] for choice in QRCode.QR_TYPES]
        if input["qr_type"] not in valid_types:
            raise GraphQLError(
                f"Invalid QR type. Must be one of: {', '.join(valid_types)}"
            )

        # Get merchant if provided
        merchant = None
        if input.get("merchant_id"):
            merchant = _get_model_by_global_id(
                input["merchant_id"], Merchant, "Merchant"
            )
            if merchant.user != user:
                raise GraphQLError("You do not own this merchant.")

        # Validate fixed amount for STATIC QR
        fixed_amount = None
        if input.get("fixed_amount"):
            fixed_amount = _validate_amount(input["fixed_amount"])
            if input["qr_type"] == "DYNAMIC" and fixed_amount:
                raise GraphQLError("Dynamic QR codes cannot have a fixed amount.")
            if input["qr_type"] == "STATIC" and not fixed_amount:
                raise GraphQLError("Static QR codes must have a fixed amount.")

        # Validate max amount per use
        max_amount_per_use = Decimal(
            str(input.get("max_amount_per_use", "500000.00"))
        )
        if max_amount_per_use <= Decimal("0.00"):
            raise GraphQLError("Max amount per use must be greater than zero.")

        # Validate max uses
        max_uses = input.get("max_uses", 1)
        if max_uses < 0:
            raise GraphQLError("Max uses cannot be negative.")

        # Validate expiry date
        expires_at = None
        if input.get("expires_at"):
            expires_at = _validate_datetime(input["expires_at"])
            if expires_at and expires_at <= timezone.now():
                raise GraphQLError("Expiry date must be in the future.")

        # Generate QR ID and reference
        qr_id = f"QR-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        reference = input.get("reference") or (
            f"QRREF-{timezone.now().strftime('%Y%m%d')}-"
            f"{uuid.uuid4().hex[:6].upper()}"
        )

        try:
            qr_code = QRCode.objects.create(
                qr_id=qr_id,
                qr_type=input["qr_type"],
                creator=user,
                merchant=merchant,
                fixed_amount=fixed_amount,
                description=input.get("description", ""),
                reference=reference,
                max_uses=max_uses,
                max_amount_per_use=max_amount_per_use,
                expires_at=expires_at,
                is_active=True,
            )

            # Generate QR image
            qr_code.generate_qr_data()
            qr_code.save()

            # Convert QR image to base64 for response
            qr_image_base64 = None
            if qr_code.qr_image:
                with qr_code.qr_image.open("rb") as img_file:
                    qr_image_base64 = base64.b64encode(
                        img_file.read()
                    ).decode("utf-8")

        except ValidationError as exc:
            _raise_graphql(exc)

        return cls(
            qr_code=qr_code,
            qr_image_base64=qr_image_base64,
            success=True,
            message="QR code created successfully.",
        )


class UpdateQRCodeMutation(relay.ClientIDMutation):
    """Update a QR code."""

    class Input:
        qr_code_id = ID(required=True)
        description = String()
        max_uses = Int()
        max_amount_per_use = GrapheneDecimal()
        expires_at = String()
        is_active = Boolean()

    qr_code = Field(QRCodeNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        qr_code = _get_model_by_global_id(input["qr_code_id"], QRCode, "QR code")

        if qr_code.creator != user:
            raise GraphQLError("You do not own this QR code.")

        if input.get("description") is not None:
            qr_code.description = input["description"]

        if input.get("max_uses") is not None:
            if input["max_uses"] < 0:
                raise GraphQLError("Max uses cannot be negative.")
            if input["max_uses"] < qr_code.current_uses:
                raise GraphQLError("Max uses cannot be less than current uses.")
            qr_code.max_uses = input["max_uses"]

        if input.get("max_amount_per_use") is not None:
            max_amount = Decimal(str(input["max_amount_per_use"]))
            if max_amount <= Decimal("0.00"):
                raise GraphQLError("Max amount per use must be greater than zero.")
            qr_code.max_amount_per_use = max_amount

        if input.get("expires_at") is not None:
            if input["expires_at"]:
                expires_at = _validate_datetime(input["expires_at"])
                if expires_at and expires_at <= timezone.now():
                    raise GraphQLError("Expiry date must be in the future.")
                qr_code.expires_at = expires_at
            else:
                qr_code.expires_at = None

        if input.get("is_active") is not None:
            qr_code.is_active = input["is_active"]

        try:
            qr_code.save()
        except ValidationError as exc:
            _raise_graphql(exc)

        return cls(
            qr_code=qr_code,
            success=True,
            message="QR code updated successfully.",
        )


class DeleteQRCodeMutation(relay.ClientIDMutation):
    """Delete a QR code (soft delete by deactivating)."""

    class Input:
        qr_code_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        qr_code = _get_model_by_global_id(input["qr_code_id"], QRCode, "QR code")

        if qr_code.creator != user:
            raise GraphQLError("You do not own this QR code.")

        # Soft delete by deactivating
        qr_code.is_active = False
        qr_code.save(update_fields=["is_active"])

        return cls(
            success=True,
            message="QR code deactivated successfully.",
        )


class RegenerateQRCodeMutation(relay.ClientIDMutation):
    """Regenerate a QR code image."""

    class Input:
        qr_code_id = ID(required=True)

    qr_code = Field(QRCodeNode)
    qr_image_base64 = String()
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        qr_code = _get_model_by_global_id(input["qr_code_id"], QRCode, "QR code")

        if qr_code.creator != user:
            raise GraphQLError("You do not own this QR code.")

        # Regenerate QR data and image
        qr_code.generate_qr_data()
        qr_code.save()

        # Convert QR image to base64
        qr_image_base64 = None
        if qr_code.qr_image:
            with qr_code.qr_image.open("rb") as img_file:
                qr_image_base64 = base64.b64encode(
                    img_file.read()
                ).decode("utf-8")

        return cls(
            qr_code=qr_code,
            qr_image_base64=qr_image_base64,
            success=True,
            message="QR code regenerated successfully.",
        )


# ============================================================================
# QR TRANSACTION MUTATIONS (money movement)
# ============================================================================

class PayViaQRCodeMutation(relay.ClientIDMutation):
    """
    Pay a QR code.

    Delegates to QRService.pay_via_qr, which posts the principal
    journal (payer_account -> payee_account), creates the Transaction
    and QRTransaction rows, and increments QR usage, all atomically.
    """

    class Input:
        qr_code_id = ID(required=True)
        payer_account_id = ID(required=True)
        amount = GrapheneDecimal()          # required only for non-STATIC QRs
        scanned_location = String()
        device_id = String()

    qr_transaction = Field(QRTransactionNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        qr_code = _get_model_by_global_id(
            input["qr_code_id"], QRCode, "QR code"
        )
        payer_account = _get_model_by_global_id(
            input["payer_account_id"], Account, "Payer account"
        )

        if payer_account.user_id != user.pk:
            raise GraphQLError("You do not own this account.")

        qr_transaction = _wrap(
            QRService.pay_via_qr,
            scanner_user=user,
            qr_code=qr_code,
            payer_account=payer_account,
            amount=input.get("amount"),
            scanned_location=input.get("scanned_location", ""),
            device_id=input.get("device_id", ""),
        )

        return cls(
            qr_transaction=qr_transaction,
            success=True,
            message="QR payment successful.",
        )


class FailQRTransactionMutation(relay.ClientIDMutation):
    """
    Fail a QR transaction.

    Status-only transition. Does NOT move money. Intended for marking
    a PENDING intent as failed (e.g. client-side abort after a scan
    but before payment). The primary path, PayViaQRCodeMutation, posts
    money atomically and never leaves PENDING rows behind.
    """

    class Input:
        qr_transaction_id = ID(required=True)
        reason = String(required=True)

    qr_transaction = Field(QRTransactionNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        qr_transaction = _get_model_by_global_id(
            input["qr_transaction_id"], QRTransaction, "QR transaction"
        )

        if qr_transaction.payer != user:
            raise GraphQLError("You do not own this transaction.")

        if qr_transaction.status != "PENDING":
            raise GraphQLError(
                f"Transaction is already {qr_transaction.status}."
            )

        qr_transaction.status = "FAILED"
        qr_transaction.failure_reason = input["reason"]
        qr_transaction.save()

        return cls(
            qr_transaction=qr_transaction,
            success=True,
            message="QR transaction failed.",
        )


# ============================================================================
# MUTATION REGISTRY
# ============================================================================

class QRMutations(graphene.ObjectType):
    # QR Code (metadata)
    create_qr_code = CreateQRCodeMutation.Field()
    update_qr_code = UpdateQRCodeMutation.Field()
    delete_qr_code = DeleteQRCodeMutation.Field()
    regenerate_qr_code = RegenerateQRCodeMutation.Field()

    # QR Transaction (money movement + status)
    pay_via_qr_code = PayViaQRCodeMutation.Field()
    fail_qr_transaction = FailQRTransactionMutation.Field()


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # QR Code
    "CreateQRCodeMutation",
    "UpdateQRCodeMutation",
    "DeleteQRCodeMutation",
    "RegenerateQRCodeMutation",

    # QR Transaction
    "PayViaQRCodeMutation",
    "FailQRTransactionMutation",

    # Registry
    "QRMutations",
]