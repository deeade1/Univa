# apps/backend/graphq/banking/mutations/compliance.py

"""
GraphQL mutations for Banking compliance models.

Money movement
--------------

CreateATMCardMutation delegates to
banking.services.compliance_service.CardService.request_card
(posts customer -> FEE).

CreateATMTransactionMutation delegates to
banking.services.compliance_service.ATMService
(posts customer -> SETTLEMENT for withdrawals,
       SETTLEMENT -> customer for deposits).

UpdateATMTransactionMutation is restricted to status-only
transitions (pending -> failed). It does NOT post the ledger.
"""

import logging
from datetime import datetime
from decimal import Decimal
import uuid

import graphene
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from django.utils import timezone
from graphene import (
    ID,
    Boolean,
    Decimal as GrapheneDecimal,
    Field,
    Int,
    String,
    relay,
)
from graphene.types.generic import GenericScalar
from graphql import GraphQLError
from graphql_relay import from_global_id

from banking.models.compliance import (
    ATMCard,
    ATMTransaction,
    CardIssuance,
    Contact,
    CurrencyExchangeRate,
    Webhook,
    WebhookDelivery,
)
from banking.models.core import Account
from banking.services.compliance_service import (
    ATMService,
    CardService,
)
from graphq.accounts.types.user import UserNode
from graphq.banking.types.compliance import (
    ATMCardNode,
    ATMTransactionNode,
    CardIssuanceNode,
    ContactNode,
    CurrencyExchangeRateNode,
    WebhookDeliveryNode,
    WebhookNode,
)
from univa_jwt.decorators import login_required

User = get_user_model()
logger = logging.getLogger(__name__)


# ============================================================================
# HELPERS
# ============================================================================

def _get_authenticated_user(info):
    user = getattr(info.context, "user", None)
    if not user or not user.is_authenticated:
        raise GraphQLError("Authentication required.")
    return user


def _get_model_by_global_id(global_id, model, model_name):
    if not global_id:
        raise GraphQLError(f"{model_name} ID is required.")
    try:
        _, pk = from_global_id(global_id)
        return model.objects.get(pk=pk)
    except model.DoesNotExist:
        raise GraphQLError(f"{model_name} not found.")
    except Exception as exc:
        raise GraphQLError(f"Invalid {model_name} ID.") from exc


def _clean_message(exc):
    messages = getattr(exc, "messages", None)
    if messages:
        return str(messages[0])
    return str(exc)


def _wrap(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except ValidationError as exc:
        raise GraphQLError(_clean_message(exc)) from exc


def _validate_amount(amount):
    try:
        amount = Decimal(str(amount))
    except (TypeError, ValueError):
        raise GraphQLError("Invalid amount value.")
    if amount <= Decimal("0.00"):
        raise GraphQLError("Amount must be greater than zero.")
    return amount.quantize(Decimal("0.01"))


def _validate_pin(pin):
    if not pin:
        raise GraphQLError("PIN is required.")
    if not pin.isdigit() or len(pin) != 4:
        raise GraphQLError("PIN must be exactly 4 digits.")
    return pin


def _validate_cvv(cvv):
    if not cvv:
        raise GraphQLError("CVV is required.")
    if not cvv.isdigit() or len(cvv) != 3:
        raise GraphQLError("CVV must be exactly 3 digits.")
    return cvv


# ============================================================================
# WEBHOOK MUTATIONS
# ============================================================================

class CreateWebhookMutation(relay.ClientIDMutation):
    class Input:
        url = String(required=True)
        event_type = String(required=True)
        secret = String(required=True)
        description = String()
        is_active = Boolean()

    webhook = Field(WebhookNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        valid_events = [choice[0] for choice in Webhook.EVENT_TYPES]
        if input["event_type"] not in valid_events:
            raise GraphQLError(
                f"Invalid event type. Must be one of: "
                f"{', '.join(valid_events)}"
            )

        if Webhook.objects.filter(
            url=input["url"], event_type=input["event_type"]
        ).exists():
            raise GraphQLError(
                "Webhook already exists for this URL and event type."
            )

        try:
            webhook = Webhook.objects.create(
                url=input["url"],
                event_type=input["event_type"],
                secret=input["secret"],
                description=input.get("description", ""),
                is_active=input.get("is_active", True),
            )
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            webhook=webhook,
            success=True,
            message="Webhook created successfully.",
        )


class UpdateWebhookMutation(relay.ClientIDMutation):
    class Input:
        webhook_id = ID(required=True)
        url = String()
        event_type = String()
        secret = String()
        description = String()
        is_active = Boolean()

    webhook = Field(WebhookNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        webhook = _get_model_by_global_id(
            input["webhook_id"], Webhook, "Webhook"
        )

        if input.get("url"):
            webhook.url = input["url"]

        if input.get("event_type"):
            valid_events = [
                choice[0] for choice in Webhook.EVENT_TYPES
            ]
            if input["event_type"] not in valid_events:
                raise GraphQLError("Invalid event type.")
            webhook.event_type = input["event_type"]

        if input.get("secret"):
            webhook.secret = input["secret"]

        if input.get("description") is not None:
            webhook.description = input["description"]

        if input.get("is_active") is not None:
            webhook.is_active = input["is_active"]

        try:
            webhook.save()
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            webhook=webhook,
            success=True,
            message="Webhook updated successfully.",
        )


class DeleteWebhookMutation(relay.ClientIDMutation):
    class Input:
        webhook_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        webhook = _get_model_by_global_id(
            input["webhook_id"], Webhook, "Webhook"
        )
        webhook.delete()
        return cls(
            success=True,
            message="Webhook deleted successfully.",
        )


# ============================================================================
# CURRENCY EXCHANGE RATE MUTATIONS
# ============================================================================

class CreateCurrencyExchangeRateMutation(relay.ClientIDMutation):
    class Input:
        base_currency = String(required=True)
        target_currency = String(required=True)
        rate = GrapheneDecimal(required=True)

    exchange_rate = Field(CurrencyExchangeRateNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        if input["base_currency"] == input["target_currency"]:
            raise GraphQLError(
                "Base and target currencies must be different."
            )

        rate = Decimal(str(input["rate"]))
        if rate <= Decimal("0"):
            raise GraphQLError(
                "Exchange rate must be greater than zero."
            )

        if CurrencyExchangeRate.objects.filter(
            base_currency=input["base_currency"],
            target_currency=input["target_currency"],
        ).exists():
            raise GraphQLError(
                "Exchange rate already exists for this pair."
            )

        try:
            exchange_rate = CurrencyExchangeRate.objects.create(
                base_currency=input["base_currency"],
                target_currency=input["target_currency"],
                rate=rate,
            )
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            exchange_rate=exchange_rate,
            success=True,
            message="Exchange rate created successfully.",
        )


class UpdateCurrencyExchangeRateMutation(relay.ClientIDMutation):
    class Input:
        exchange_rate_id = ID(required=True)
        rate = GrapheneDecimal(required=True)

    exchange_rate = Field(CurrencyExchangeRateNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        exchange_rate = _get_model_by_global_id(
            input["exchange_rate_id"],
            CurrencyExchangeRate,
            "Exchange rate",
        )

        rate = Decimal(str(input["rate"]))
        if rate <= Decimal("0"):
            raise GraphQLError(
                "Exchange rate must be greater than zero."
            )

        exchange_rate.rate = rate
        exchange_rate.save()

        return cls(
            exchange_rate=exchange_rate,
            success=True,
            message="Exchange rate updated successfully.",
        )


class DeleteCurrencyExchangeRateMutation(relay.ClientIDMutation):
    class Input:
        exchange_rate_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        exchange_rate = _get_model_by_global_id(
            input["exchange_rate_id"],
            CurrencyExchangeRate,
            "Exchange rate",
        )
        exchange_rate.delete()
        return cls(
            success=True,
            message="Exchange rate deleted successfully.",
        )


# ============================================================================
# CONTACT MUTATIONS
# ============================================================================

class CreateContactMutation(relay.ClientIDMutation):
    class Input:
        user_id = ID(required=True)
        account_number = String()
        bank_name = String()
        is_beneficiary = Boolean()

    contact = Field(ContactNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        target_user = _get_model_by_global_id(
            input["user_id"], User, "User"
        )

        if Contact.objects.filter(
            user=target_user,
            account_number=input.get("account_number", ""),
        ).exists():
            raise GraphQLError(
                "Contact already exists with this account number."
            )

        try:
            contact = Contact.objects.create(
                user=target_user,
                account_number=input.get("account_number", ""),
                bank_name=input.get("bank_name", ""),
                is_beneficiary=input.get("is_beneficiary", False),
            )
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            contact=contact,
            success=True,
            message="Contact created successfully.",
        )


class UpdateContactMutation(relay.ClientIDMutation):
    class Input:
        contact_id = ID(required=True)
        account_number = String()
        bank_name = String()
        is_beneficiary = Boolean()

    contact = Field(ContactNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        contact = _get_model_by_global_id(
            input["contact_id"], Contact, "Contact"
        )

        if contact.user != user:
            raise GraphQLError("You do not own this contact.")

        if input.get("account_number") is not None:
            contact.account_number = input["account_number"]

        if input.get("bank_name") is not None:
            contact.bank_name = input["bank_name"]

        if input.get("is_beneficiary") is not None:
            contact.is_beneficiary = input["is_beneficiary"]

        try:
            contact.save()
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            contact=contact,
            success=True,
            message="Contact updated successfully.",
        )


class DeleteContactMutation(relay.ClientIDMutation):
    class Input:
        contact_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        contact = _get_model_by_global_id(
            input["contact_id"], Contact, "Contact"
        )

        if contact.user != user:
            raise GraphQLError("You do not own this contact.")

        contact.delete()

        return cls(
            success=True,
            message="Contact deleted successfully.",
        )


# ============================================================================
# ATM CARD MUTATIONS
# ============================================================================

class CreateATMCardMutation(relay.ClientIDMutation):
    """
    Request a new ATM card.

    Delegates to CardService.request_card, which posts the issuance
    fee journal (customer -> FEE) and creates the ATMCard and
    CardIssuance rows atomically.
    """

    class Input:
        account_id = ID(required=True)
        card_type = String(required=True)
        delivery_address = String()

    card = Field(ATMCardNode)
    issuance = Field(CardIssuanceNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        account = _get_model_by_global_id(
            input["account_id"], Account, "Account"
        )

        result = _wrap(
            CardService.request_card,
            user=user,
            account=account,
            card_type=input["card_type"],
            delivery_address=input.get("delivery_address", ""),
            requested_by=user,
        )

        return cls(
            card=result.get("card"),
            issuance=result.get("issuance"),
            success=True,
            message=result.get("message", ""),
        )


class ActivateATMCardMutation(relay.ClientIDMutation):
    class Input:
        card_id = ID(required=True)
        activation_code = String(required=True)

    card = Field(ATMCardNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        card = _get_model_by_global_id(
            input["card_id"], ATMCard, "ATM card"
        )

        if card.user != user:
            raise GraphQLError("You do not own this card.")

        result = _wrap(
            CardService.activate_card,
            card_id=card.pk,
            activation_code=input["activation_code"],
            activated_by=user,
        )

        return cls(
            card=result.get("card"),
            success=result.get("success", False),
            message=result.get("message", ""),
        )


class BlockATMCardMutation(relay.ClientIDMutation):
    class Input:
        card_id = ID(required=True)
        reason = String()

    card = Field(ATMCardNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        card = _get_model_by_global_id(
            input["card_id"], ATMCard, "ATM card"
        )

        if card.user != user:
            raise GraphQLError("You do not own this card.")

        result = _wrap(
            CardService.block_card,
            card_id=card.pk,
            reason=input.get("reason", ""),
            blocked_by=user,
        )

        return cls(
            card=result.get("card"),
            success=result.get("success", False),
            message=result.get("message", ""),
        )


class UnblockATMCardMutation(relay.ClientIDMutation):
    class Input:
        card_id = ID(required=True)

    card = Field(ATMCardNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        card = _get_model_by_global_id(
            input["card_id"], ATMCard, "ATM card"
        )

        if card.user != user:
            raise GraphQLError("You do not own this card.")

        result = _wrap(
            CardService.unblock_card,
            card_id=card.pk,
            unblocked_by=user,
        )

        return cls(
            card=result.get("card"),
            success=result.get("success", False),
            message=result.get("message", ""),
        )


class SetATMCardPINMutation(relay.ClientIDMutation):
    class Input:
        card_id = ID(required=True)
        current_pin = String()
        new_pin = String(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        card = _get_model_by_global_id(
            input["card_id"], ATMCard, "ATM card"
        )

        if card.user != user:
            raise GraphQLError("You do not own this card.")

        new_pin = _validate_pin(input["new_pin"])

        if input.get("current_pin"):
            if not card.check_pin(input["current_pin"]):
                raise GraphQLError("Current PIN is incorrect.")

        card.set_pin(new_pin)
        card.save()

        return cls(
            success=True,
            message="PIN set successfully.",
        )


class VerifyATMCardPINMutation(relay.ClientIDMutation):
    class Input:
        card_id = ID(required=True)
        pin = String(required=True)

    success = Boolean()
    message = String()
    is_valid = Boolean()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        card = _get_model_by_global_id(
            input["card_id"], ATMCard, "ATM card"
        )

        if card.user != user:
            raise GraphQLError("You do not own this card.")

        pin = _validate_pin(input["pin"])
        is_valid = card.check_pin(pin)

        return cls(
            success=True,
            message=(
                "PIN verified successfully."
                if is_valid
                else "Invalid PIN."
            ),
            is_valid=is_valid,
        )


# ============================================================================
# ATM TRANSACTION MUTATIONS
# ============================================================================

class CreateATMTransactionMutation(relay.ClientIDMutation):
    """
    Record an ATM transaction.

    Delegates to ATMService. Withdrawals post customer -> SETTLEMENT.
    Deposits post SETTLEMENT -> customer. Non-monetary transactions
    (balance inquiry, PIN change) post no ledger.
    """

    class Input:
        card_id = ID()
        account_id = ID(required=True)
        transaction_type = String(required=True)
        amount = GrapheneDecimal()
        terminal_id = String()
        location = String()

    atm_transaction = Field(ATMTransactionNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        account = _get_model_by_global_id(
            input["account_id"], Account, "Account"
        )

        card = None
        if input.get("card_id"):
            card = _get_model_by_global_id(
                input["card_id"], ATMCard, "ATM card"
            )

        transaction_type = input["transaction_type"]

        if transaction_type == ATMTransaction.WITHDRAWAL:
            atm_transaction = _wrap(
                ATMService.process_withdrawal,
                account=account,
                amount=input.get("amount"),
                card=card,
                user=user,
                terminal_id=input.get("terminal_id", ""),
                location=input.get("location", ""),
                processed_by=user,
            )
        elif transaction_type == ATMTransaction.DEPOSIT:
            atm_transaction = _wrap(
                ATMService.process_deposit,
                account=account,
                amount=input.get("amount"),
                card=card,
                user=user,
                terminal_id=input.get("terminal_id", ""),
                location=input.get("location", ""),
                processed_by=user,
            )
        elif transaction_type in (
            ATMTransaction.BALANCE_INQUIRY,
            ATMTransaction.PIN_CHANGE,
        ):
            atm_transaction = _wrap(
                ATMService.record_non_monetary,
                account=account,
                transaction_type=transaction_type,
                card=card,
                user=user,
                terminal_id=input.get("terminal_id", ""),
                location=input.get("location", ""),
                processed_by=user,
            )
        else:
            raise GraphQLError(
                f"Unsupported transaction type: {transaction_type}."
            )

        return cls(
            atm_transaction=atm_transaction,
            success=True,
            message="ATM transaction recorded successfully.",
        )


class UpdateATMTransactionMutation(relay.ClientIDMutation):
    """
    Status-only transition for a pending ATM transaction.

    Only 'pending -> failed' is permitted. Completed transactions and
    any transition that would mark a pending transaction as completed
    must go through CreateATMTransactionMutation (which posts the
    ledger).
    """

    class Input:
        atm_transaction_id = ID(required=True)
        status = String(required=True)

    atm_transaction = Field(ATMTransactionNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        atm_transaction = _get_model_by_global_id(
            input["atm_transaction_id"],
            ATMTransaction,
            "ATM transaction",
        )

        if atm_transaction.user != user:
            raise GraphQLError("You do not own this transaction.")

        if atm_transaction.status != ATMTransaction.PENDING:
            raise GraphQLError(
                "Only pending ATM transactions can be updated."
            )

        new_status = input["status"]
        if new_status not in (
            ATMTransaction.PENDING,
            ATMTransaction.FAILED,
        ):
            raise GraphQLError(
                "Only 'pending' or 'failed' statuses are permitted here."
            )

        atm_transaction.status = new_status
        atm_transaction.verified_by = user
        atm_transaction.save(update_fields=[
            "status", "verified_by", "updated_at",
        ] if hasattr(atm_transaction, "updated_at") else [
            "status", "verified_by",
        ])

        return cls(
            atm_transaction=atm_transaction,
            success=True,
            message="ATM transaction updated successfully.",
        )


# ============================================================================
# CARD ISSUANCE MUTATIONS
# ============================================================================

class UpdateCardIssuanceMutation(relay.ClientIDMutation):
    class Input:
        card_issuance_id = ID(required=True)
        status = String()
        tracking_number = String()
        estimated_delivery = String()
        actual_delivery = String()

    card_issuance = Field(CardIssuanceNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        issuance = _get_model_by_global_id(
            input["card_issuance_id"], CardIssuance, "Card issuance"
        )

        if issuance.card.user != user:
            raise GraphQLError("You do not own this card issuance.")

        if input.get("status"):
            valid_statuses = [
                'REQUESTED', 'PROCESSING', 'PRODUCED',
                'SHIPPED', 'DELIVERED', 'ACTIVATED', 'CANCELLED',
            ]
            if input["status"] not in valid_statuses:
                raise GraphQLError(
                    f"Invalid status. Must be one of: "
                    f"{', '.join(valid_statuses)}"
                )
            issuance.status = input["status"]

            if input["status"] == "SHIPPED":
                issuance.shipped_by = user
            elif input["status"] == "PROCESSING":
                issuance.processed_by = user

        if input.get("tracking_number") is not None:
            issuance.tracking_number = input["tracking_number"]

        if input.get("estimated_delivery"):
            try:
                issuance.estimated_delivery = datetime.strptime(
                    input["estimated_delivery"], "%Y-%m-%d"
                ).date()
            except ValueError:
                raise GraphQLError(
                    "Invalid date format. Use YYYY-MM-DD."
                )

        if input.get("actual_delivery"):
            try:
                issuance.actual_delivery = datetime.strptime(
                    input["actual_delivery"], "%Y-%m-%d"
                ).date()
            except ValueError:
                raise GraphQLError(
                    "Invalid date format. Use YYYY-MM-DD."
                )

        try:
            issuance.save()
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            card_issuance=issuance,
            success=True,
            message="Card issuance updated successfully.",
        )


class CancelCardIssuanceMutation(relay.ClientIDMutation):
    class Input:
        card_issuance_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        issuance = _get_model_by_global_id(
            input["card_issuance_id"], CardIssuance, "Card issuance"
        )

        if issuance.card.user != user:
            raise GraphQLError("You do not own this card issuance.")

        if issuance.status in ["SHIPPED", "DELIVERED", "ACTIVATED"]:
            raise GraphQLError(
                "Cannot cancel a card that has already been shipped "
                "or activated."
            )

        issuance.status = "CANCELLED"
        issuance.save()

        return cls(
            success=True,
            message="Card issuance cancelled successfully.",
        )


# ============================================================================
# MUTATION REGISTRY
# ============================================================================

class ComplianceMutations(graphene.ObjectType):
    # Webhook
    create_webhook = CreateWebhookMutation.Field()
    update_webhook = UpdateWebhookMutation.Field()
    delete_webhook = DeleteWebhookMutation.Field()

    # Currency Exchange Rate
    create_currency_exchange_rate = CreateCurrencyExchangeRateMutation.Field()
    update_currency_exchange_rate = UpdateCurrencyExchangeRateMutation.Field()
    delete_currency_exchange_rate = DeleteCurrencyExchangeRateMutation.Field()

    # Contact
    create_contact = CreateContactMutation.Field()
    update_contact = UpdateContactMutation.Field()
    delete_contact = DeleteContactMutation.Field()

    # ATM Card
    create_atm_card = CreateATMCardMutation.Field()
    activate_atm_card = ActivateATMCardMutation.Field()
    block_atm_card = BlockATMCardMutation.Field()
    unblock_atm_card = UnblockATMCardMutation.Field()
    set_atm_card_pin = SetATMCardPINMutation.Field()
    verify_atm_card_pin = VerifyATMCardPINMutation.Field()

    # ATM Transaction
    create_atm_transaction = CreateATMTransactionMutation.Field()
    update_atm_transaction = UpdateATMTransactionMutation.Field()

    # Card Issuance
    update_card_issuance = UpdateCardIssuanceMutation.Field()
    cancel_card_issuance = CancelCardIssuanceMutation.Field()


__all__ = [
    "CreateWebhookMutation",
    "UpdateWebhookMutation",
    "DeleteWebhookMutation",
    "CreateCurrencyExchangeRateMutation",
    "UpdateCurrencyExchangeRateMutation",
    "DeleteCurrencyExchangeRateMutation",
    "CreateContactMutation",
    "UpdateContactMutation",
    "DeleteContactMutation",
    "CreateATMCardMutation",
    "ActivateATMCardMutation",
    "BlockATMCardMutation",
    "UnblockATMCardMutation",
    "SetATMCardPINMutation",
    "VerifyATMCardPINMutation",
    "CreateATMTransactionMutation",
    "UpdateATMTransactionMutation",
    "UpdateCardIssuanceMutation",
    "CancelCardIssuanceMutation",
    "ComplianceMutations",
]