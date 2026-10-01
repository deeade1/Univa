# apps/backend/graphq/banking/mutations/scheduled.py

"""
GraphQL mutations for Banking scheduled models.

This module contains mutations for:
    - ScheduledPayment: Standing orders, recurring transfers, bill payments
    - CreditProduct: Credit products like Quick Loans, Overdrafts
    - SupportTicket: Customer support ticketing system
    - APIKey: API keys for third-party integrations
    - RemittanceProvider: International money transfer providers
    - InternationalTransfer: International money transfer record
    - ExchangeRate: Real-time exchange rates for remittance

Money movement
--------------

InternationalTransfer creation delegates to:

    banking.services.international_transfer_service.InternationalTransferService

which posts the principal and fee journals through
AccountingManager.create_double_entry. Every other mutation in this
module is metadata CRUD and does not move money.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
import secrets
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

from banking.models.scheduled import (
    ScheduledPayment,
    CreditProduct,
    SupportTicket,
    APIKey,
    RemittanceProvider,
    InternationalTransfer,
    ExchangeRate,
)
from banking.models.core import Account
from banking.models.merchant import Merchant
from banking.services.international_transfer_service import (
    InternationalTransferService,
)
from graphq.accounts.types.user import UserNode
from graphq.banking.types.scheduled import (
    ScheduledPaymentNode,
    CreditProductNode,
    SupportTicketNode,
    APIKeyNode,
    RemittanceProviderNode,
    InternationalTransferNode,
    ExchangeRateNode,
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


def _clean_message(exc):
    """Extract a clean single-line message from a ValidationError."""
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


def _validate_amount(amount):
    """Validate and normalize a monetary amount."""
    try:
        amount = Decimal(str(amount))
    except (TypeError, ValueError):
        raise GraphQLError("Invalid amount value.")

    if amount <= Decimal("0.00"):
        raise GraphQLError("Amount must be greater than zero.")

    return amount.quantize(Decimal("0.01"))


def _validate_date(date_str):
    """Validate a date string."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise GraphQLError("Invalid date format. Use YYYY-MM-DD.")


def _validate_datetime(datetime_str):
    """Validate a datetime string."""
    if not datetime_str:
        return None
    try:
        return datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
    except ValueError:
        raise GraphQLError("Invalid datetime format. Use ISO format.")


# ============================================================================
# SCHEDULED PAYMENT MUTATIONS
# ============================================================================

class CreateScheduledPaymentMutation(relay.ClientIDMutation):
    """Create a scheduled payment (standing order)."""

    class Input:
        user_id = ID(required=True)
        source_account_id = ID(required=True)
        beneficiary_name = String(required=True)
        beneficiary_account = String(required=True)
        beneficiary_bank_code = String(required=True)
        amount = GrapheneDecimal(required=True)
        frequency = String(required=True)
        start_date = String(required=True)
        end_date = String()
        is_active = Boolean()

    scheduled_payment = Field(ScheduledPaymentNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        target_user = _get_model_by_global_id(input["user_id"], User, "User")
        source_account = _get_model_by_global_id(
            input["source_account_id"], Account, "Source account"
        )

        if source_account.user != target_user:
            raise GraphQLError("Source account does not belong to this user.")

        valid_frequencies = [
            choice[0] for choice in ScheduledPayment.FREQUENCY_CHOICES
        ]
        if input["frequency"] not in valid_frequencies:
            raise GraphQLError(
                f"Invalid frequency. Must be one of: "
                f"{', '.join(valid_frequencies)}"
            )

        amount = _validate_amount(input["amount"])

        start_date = _validate_date(input["start_date"])
        if not start_date:
            raise GraphQLError("Start date is required.")
        if start_date < timezone.now().date():
            raise GraphQLError("Start date cannot be in the past.")

        end_date = None
        if input.get("end_date"):
            end_date = _validate_date(input["end_date"])
            if end_date and end_date <= start_date:
                raise GraphQLError("End date must be after start date.")

        next_processing = timezone.now()
        if input["frequency"] == "DAILY":
            next_processing = timezone.now() + timedelta(days=1)
        elif input["frequency"] == "WEEKLY":
            next_processing = timezone.now() + timedelta(days=7)
        elif input["frequency"] == "MONTHLY":
            next_processing = timezone.now() + timedelta(days=30)
        elif input["frequency"] == "QUARTERLY":
            next_processing = timezone.now() + timedelta(days=90)
        elif input["frequency"] == "YEARLY":
            next_processing = timezone.now() + timedelta(days=365)

        try:
            scheduled_payment = ScheduledPayment.objects.create(
                user=target_user,
                source_account=source_account,
                beneficiary_name=input["beneficiary_name"],
                beneficiary_account=input["beneficiary_account"],
                beneficiary_bank_code=input["beneficiary_bank_code"],
                amount=amount,
                frequency=input["frequency"],
                start_date=start_date,
                end_date=end_date,
                next_processing=next_processing,
                is_active=input.get("is_active", True),
            )
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            scheduled_payment=scheduled_payment,
            success=True,
            message="Scheduled payment created successfully.",
        )


class UpdateScheduledPaymentMutation(relay.ClientIDMutation):
    """Update a scheduled payment."""

    class Input:
        scheduled_payment_id = ID(required=True)
        beneficiary_name = String()
        beneficiary_account = String()
        beneficiary_bank_code = String()
        amount = GrapheneDecimal()
        frequency = String()
        end_date = String()
        is_active = Boolean()

    scheduled_payment = Field(ScheduledPaymentNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        scheduled_payment = _get_model_by_global_id(
            input["scheduled_payment_id"], ScheduledPayment, "Scheduled payment"
        )

        if scheduled_payment.user != user:
            raise GraphQLError("You do not own this scheduled payment.")

        if input.get("beneficiary_name"):
            scheduled_payment.beneficiary_name = input["beneficiary_name"]

        if input.get("beneficiary_account"):
            scheduled_payment.beneficiary_account = input["beneficiary_account"]

        if input.get("beneficiary_bank_code"):
            scheduled_payment.beneficiary_bank_code = input[
                "beneficiary_bank_code"
            ]

        if input.get("amount"):
            scheduled_payment.amount = _validate_amount(input["amount"])

        if input.get("frequency"):
            valid_frequencies = [
                choice[0] for choice in ScheduledPayment.FREQUENCY_CHOICES
            ]
            if input["frequency"] not in valid_frequencies:
                raise GraphQLError("Invalid frequency.")
            scheduled_payment.frequency = input["frequency"]

        if input.get("end_date") is not None:
            if input["end_date"]:
                end_date = _validate_date(input["end_date"])
                if end_date <= scheduled_payment.start_date:
                    raise GraphQLError("End date must be after start date.")
                scheduled_payment.end_date = end_date
            else:
                scheduled_payment.end_date = None

        if input.get("is_active") is not None:
            scheduled_payment.is_active = input["is_active"]

        try:
            scheduled_payment.save()
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            scheduled_payment=scheduled_payment,
            success=True,
            message="Scheduled payment updated successfully.",
        )


class DeleteScheduledPaymentMutation(relay.ClientIDMutation):
    """Delete a scheduled payment."""

    class Input:
        scheduled_payment_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        scheduled_payment = _get_model_by_global_id(
            input["scheduled_payment_id"], ScheduledPayment, "Scheduled payment"
        )

        if scheduled_payment.user != user:
            raise GraphQLError("You do not own this scheduled payment.")

        scheduled_payment.delete()

        return cls(
            success=True,
            message="Scheduled payment deleted successfully.",
        )


# ============================================================================
# CREDIT PRODUCT MUTATIONS
# ============================================================================

class CreateCreditProductMutation(relay.ClientIDMutation):
    """Create a credit product. Staff only."""

    class Input:
        name = String(required=True)
        product_type = String(required=True)
        min_amount = GrapheneDecimal(required=True)
        max_amount = GrapheneDecimal(required=True)
        interest_rate = GrapheneDecimal(required=True)
        tenor_days = Int(required=True)
        eligibility_criteria = GenericScalar()

    credit_product = Field(CreditProductNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        if not user.is_staff and not user.is_superuser:
            raise GraphQLError("Only admins can create credit products.")

        valid_types = [choice[0] for choice in CreditProduct.PRODUCT_TYPES]
        if input["product_type"] not in valid_types:
            raise GraphQLError("Invalid product type.")

        min_amount = _validate_amount(input["min_amount"])
        max_amount = _validate_amount(input["max_amount"])
        if min_amount > max_amount:
            raise GraphQLError(
                "Minimum amount cannot exceed maximum amount."
            )

        interest_rate = Decimal(str(input["interest_rate"]))
        if interest_rate < 0:
            raise GraphQLError("Interest rate cannot be negative.")

        if input["tenor_days"] <= 0:
            raise GraphQLError("Tenor days must be greater than zero.")

        try:
            credit_product = CreditProduct.objects.create(
                name=input["name"],
                product_type=input["product_type"],
                min_amount=min_amount,
                max_amount=max_amount,
                interest_rate=interest_rate,
                tenor_days=input["tenor_days"],
                eligibility_criteria=input.get("eligibility_criteria", {}),
            )
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            credit_product=credit_product,
            success=True,
            message="Credit product created successfully.",
        )


class UpdateCreditProductMutation(relay.ClientIDMutation):
    """Update a credit product. Staff only."""

    class Input:
        credit_product_id = ID(required=True)
        name = String()
        product_type = String()
        min_amount = GrapheneDecimal()
        max_amount = GrapheneDecimal()
        interest_rate = GrapheneDecimal()
        tenor_days = Int()
        eligibility_criteria = GenericScalar()

    credit_product = Field(CreditProductNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        if not user.is_staff and not user.is_superuser:
            raise GraphQLError("Only admins can update credit products.")

        credit_product = _get_model_by_global_id(
            input["credit_product_id"], CreditProduct, "Credit product"
        )

        if input.get("name"):
            credit_product.name = input["name"]

        if input.get("product_type"):
            valid_types = [
                choice[0] for choice in CreditProduct.PRODUCT_TYPES
            ]
            if input["product_type"] not in valid_types:
                raise GraphQLError("Invalid product type.")
            credit_product.product_type = input["product_type"]

        if input.get("min_amount"):
            min_amount = _validate_amount(input["min_amount"])
            if min_amount > credit_product.max_amount:
                raise GraphQLError(
                    "Minimum amount cannot exceed maximum amount."
                )
            credit_product.min_amount = min_amount

        if input.get("max_amount"):
            max_amount = _validate_amount(input["max_amount"])
            if credit_product.min_amount > max_amount:
                raise GraphQLError(
                    "Minimum amount cannot exceed maximum amount."
                )
            credit_product.max_amount = max_amount

        if input.get("interest_rate"):
            interest_rate = Decimal(str(input["interest_rate"]))
            if interest_rate < 0:
                raise GraphQLError("Interest rate cannot be negative.")
            credit_product.interest_rate = interest_rate

        if input.get("tenor_days"):
            if input["tenor_days"] <= 0:
                raise GraphQLError("Tenor days must be greater than zero.")
            credit_product.tenor_days = input["tenor_days"]

        if input.get("eligibility_criteria") is not None:
            credit_product.eligibility_criteria = input[
                "eligibility_criteria"
            ]

        try:
            credit_product.save()
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            credit_product=credit_product,
            success=True,
            message="Credit product updated successfully.",
        )


class DeleteCreditProductMutation(relay.ClientIDMutation):
    """Delete a credit product. Staff only."""

    class Input:
        credit_product_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        if not user.is_staff and not user.is_superuser:
            raise GraphQLError("Only admins can delete credit products.")

        credit_product = _get_model_by_global_id(
            input["credit_product_id"], CreditProduct, "Credit product"
        )

        credit_product.delete()

        return cls(
            success=True,
            message="Credit product deleted successfully.",
        )


# ============================================================================
# SUPPORT TICKET MUTATIONS
# ============================================================================

class CreateSupportTicketMutation(relay.ClientIDMutation):
    """Create a support ticket."""

    class Input:
        user_id = ID(required=True)
        subject = String(required=True)
        description = String(required=True)
        category = String(required=True)
        priority = String(required=True)

    support_ticket = Field(SupportTicketNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        target_user = _get_model_by_global_id(input["user_id"], User, "User")

        valid_priorities = [
            choice[0] for choice in SupportTicket.PRIORITY_CHOICES
        ]
        if input["priority"] not in valid_priorities:
            raise GraphQLError("Invalid priority.")

        ticket_id = (
            f"TKT-{timezone.now().strftime('%Y%m%d')}-"
            f"{uuid.uuid4().hex[:6].upper()}"
        )

        try:
            support_ticket = SupportTicket.objects.create(
                user=target_user,
                ticket_id=ticket_id,
                subject=input["subject"],
                description=input["description"],
                category=input["category"],
                priority=input["priority"],
                status="OPEN",
            )
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            support_ticket=support_ticket,
            success=True,
            message="Support ticket created successfully.",
        )


class UpdateSupportTicketMutation(relay.ClientIDMutation):
    """Update a support ticket."""

    class Input:
        support_ticket_id = ID(required=True)
        status = String()
        priority = String()
        assigned_to_id = ID()
        resolution = String()

    support_ticket = Field(SupportTicketNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        support_ticket = _get_model_by_global_id(
            input["support_ticket_id"], SupportTicket, "Support ticket"
        )

        if support_ticket.user != user:
            raise GraphQLError("You do not own this support ticket.")

        if input.get("status"):
            valid_statuses = [
                "OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"
            ]
            if input["status"] not in valid_statuses:
                raise GraphQLError("Invalid status.")
            support_ticket.status = input["status"]

        if input.get("priority"):
            valid_priorities = [
                choice[0] for choice in SupportTicket.PRIORITY_CHOICES
            ]
            if input["priority"] not in valid_priorities:
                raise GraphQLError("Invalid priority.")
            support_ticket.priority = input["priority"]

        if input.get("assigned_to_id"):
            assigned_user = _get_model_by_global_id(
                input["assigned_to_id"], User, "Assigned user"
            )
            support_ticket.assigned_to = assigned_user

        if input.get("resolution") is not None:
            support_ticket.resolution = input["resolution"]

        try:
            support_ticket.save()
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            support_ticket=support_ticket,
            success=True,
            message="Support ticket updated successfully.",
        )


class DeleteSupportTicketMutation(relay.ClientIDMutation):
    """Delete a support ticket."""

    class Input:
        support_ticket_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        support_ticket = _get_model_by_global_id(
            input["support_ticket_id"], SupportTicket, "Support ticket"
        )

        if support_ticket.user != user:
            raise GraphQLError("You do not own this support ticket.")

        support_ticket.delete()

        return cls(
            success=True,
            message="Support ticket deleted successfully.",
        )


# ============================================================================
# API KEY MUTATIONS
# ============================================================================

class CreateAPIKeyMutation(relay.ClientIDMutation):
    """Create an API key for third-party integrations."""

    class Input:
        merchant_id = ID(required=True)
        permissions = GenericScalar()
        rate_limit = Int()
        webhook_url = String()

    api_key = Field(APIKeyNode)
    key = String()
    secret = String()
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        merchant = _get_model_by_global_id(
            input["merchant_id"], Merchant, "Merchant"
        )

        if merchant.user != user:
            raise GraphQLError("You do not own this merchant.")

        api_key = f"ak_{secrets.token_urlsafe(32)}"
        api_secret = f"sk_{secrets.token_urlsafe(48)}"

        try:
            api_key_obj = APIKey.objects.create(
                merchant=merchant,
                key=api_key,
                secret=api_secret,
                permissions=input.get("permissions", ["read"]),
                rate_limit=input.get("rate_limit", 100),
                webhook_url=input.get("webhook_url", ""),
                is_active=True,
            )
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            api_key=api_key_obj,
            key=api_key,
            secret=api_secret,
            success=True,
            message="API key created successfully.",
        )


class UpdateAPIKeyMutation(relay.ClientIDMutation):
    """Update an API key."""

    class Input:
        api_key_id = ID(required=True)
        permissions = GenericScalar()
        rate_limit = Int()
        webhook_url = String()
        is_active = Boolean()

    api_key = Field(APIKeyNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        api_key = _get_model_by_global_id(
            input["api_key_id"], APIKey, "API key"
        )

        if api_key.merchant.user != user:
            raise GraphQLError("You do not own this API key.")

        if input.get("permissions") is not None:
            api_key.permissions = input["permissions"]

        if input.get("rate_limit") is not None:
            if input["rate_limit"] <= 0:
                raise GraphQLError("Rate limit must be greater than zero.")
            api_key.rate_limit = input["rate_limit"]

        if input.get("webhook_url") is not None:
            api_key.webhook_url = input["webhook_url"]

        if input.get("is_active") is not None:
            api_key.is_active = input["is_active"]

        try:
            api_key.save()
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            api_key=api_key,
            success=True,
            message="API key updated successfully.",
        )


class DeleteAPIKeyMutation(relay.ClientIDMutation):
    """Delete an API key."""

    class Input:
        api_key_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        api_key = _get_model_by_global_id(
            input["api_key_id"], APIKey, "API key"
        )

        if api_key.merchant.user != user:
            raise GraphQLError("You do not own this API key.")

        api_key.delete()

        return cls(
            success=True,
            message="API key deleted successfully.",
        )


# ============================================================================
# REMITTANCE PROVIDER MUTATIONS
# ============================================================================

class CreateRemittanceProviderMutation(relay.ClientIDMutation):
    """Create a remittance provider. Staff only."""

    class Input:
        name = String(required=True)
        provider_code = String(required=True)
        supported_countries = GenericScalar()
        supported_currencies = GenericScalar()
        transfer_methods = GenericScalar()
        fee_structure = GenericScalar()
        exchange_margin = GrapheneDecimal()
        min_amount = GrapheneDecimal()
        max_amount = GrapheneDecimal()
        daily_limit = GrapheneDecimal()
        api_endpoint = String()
        api_key = String()
        api_secret = String()
        is_active = Boolean()

    remittance_provider = Field(RemittanceProviderNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        if not user.is_staff and not user.is_superuser:
            raise GraphQLError(
                "Only admins can create remittance providers."
            )

        if RemittanceProvider.objects.filter(
            provider_code=input["provider_code"]
        ).exists():
            raise GraphQLError("Provider with this code already exists.")

        try:
            provider = RemittanceProvider.objects.create(
                name=input["name"],
                provider_code=input["provider_code"],
                supported_countries=input.get("supported_countries", []),
                supported_currencies=input.get("supported_currencies", []),
                transfer_methods=input.get("transfer_methods", []),
                fee_structure=input.get("fee_structure", {}),
                exchange_margin=Decimal(
                    str(input.get("exchange_margin", "1.00"))
                ),
                min_amount=Decimal(str(input.get("min_amount", "10.00"))),
                max_amount=Decimal(str(input.get("max_amount", "10000.00"))),
                daily_limit=Decimal(
                    str(input.get("daily_limit", "50000.00"))
                ),
                api_endpoint=input.get("api_endpoint", ""),
                api_key=input.get("api_key", ""),
                api_secret=input.get("api_secret", ""),
                is_active=input.get("is_active", True),
            )
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            remittance_provider=provider,
            success=True,
            message="Remittance provider created successfully.",
        )


class UpdateRemittanceProviderMutation(relay.ClientIDMutation):
    """Update a remittance provider. Staff only."""

    class Input:
        remittance_provider_id = ID(required=True)
        name = String()
        provider_code = String()
        supported_countries = GenericScalar()
        supported_currencies = GenericScalar()
        transfer_methods = GenericScalar()
        fee_structure = GenericScalar()
        exchange_margin = GrapheneDecimal()
        min_amount = GrapheneDecimal()
        max_amount = GrapheneDecimal()
        daily_limit = GrapheneDecimal()
        api_endpoint = String()
        api_key = String()
        api_secret = String()
        is_active = Boolean()

    remittance_provider = Field(RemittanceProviderNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        if not user.is_staff and not user.is_superuser:
            raise GraphQLError(
                "Only admins can update remittance providers."
            )

        provider = _get_model_by_global_id(
            input["remittance_provider_id"],
            RemittanceProvider,
            "Remittance provider",
        )

        if input.get("name"):
            provider.name = input["name"]

        if input.get("provider_code"):
            if RemittanceProvider.objects.filter(
                provider_code=input["provider_code"]
            ).exclude(pk=provider.pk).exists():
                raise GraphQLError(
                    "Provider with this code already exists."
                )
            provider.provider_code = input["provider_code"]

        if input.get("supported_countries") is not None:
            provider.supported_countries = input["supported_countries"]

        if input.get("supported_currencies") is not None:
            provider.supported_currencies = input["supported_currencies"]

        if input.get("transfer_methods") is not None:
            provider.transfer_methods = input["transfer_methods"]

        if input.get("fee_structure") is not None:
            provider.fee_structure = input["fee_structure"]

        if input.get("exchange_margin") is not None:
            provider.exchange_margin = Decimal(
                str(input["exchange_margin"])
            )

        if input.get("min_amount") is not None:
            provider.min_amount = Decimal(str(input["min_amount"]))

        if input.get("max_amount") is not None:
            provider.max_amount = Decimal(str(input["max_amount"]))

        if input.get("daily_limit") is not None:
            provider.daily_limit = Decimal(str(input["daily_limit"]))

        if input.get("api_endpoint") is not None:
            provider.api_endpoint = input["api_endpoint"]

        if input.get("api_key") is not None:
            provider.api_key = input["api_key"]

        if input.get("api_secret") is not None:
            provider.api_secret = input["api_secret"]

        if input.get("is_active") is not None:
            provider.is_active = input["is_active"]

        try:
            provider.save()
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            remittance_provider=provider,
            success=True,
            message="Remittance provider updated successfully.",
        )


class DeleteRemittanceProviderMutation(relay.ClientIDMutation):
    """Delete a remittance provider. Staff only."""

    class Input:
        remittance_provider_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        if not user.is_staff and not user.is_superuser:
            raise GraphQLError(
                "Only admins can delete remittance providers."
            )

        provider = _get_model_by_global_id(
            input["remittance_provider_id"],
            RemittanceProvider,
            "Remittance provider",
        )

        provider.delete()

        return cls(
            success=True,
            message="Remittance provider deleted successfully.",
        )


# ============================================================================
# INTERNATIONAL TRANSFER MUTATIONS (money movement)
# ============================================================================

class CreateInternationalTransferMutation(relay.ClientIDMutation):
    """
    Create an international transfer.

    Delegates to InternationalTransferService.initiate_transfer, which
    posts the principal journal (customer -> SETTLEMENT) and the fee
    journal (customer -> FEE), creates the Transaction rows, and links
    both journals back to the InternationalTransfer record.
    """

    class Input:
        sender_id = ID(required=True)
        source_account_id = ID(required=True)
        provider_id = ID(required=True)
        transfer_type = String(required=True)
        source_amount = GrapheneDecimal(required=True)
        source_currency = String(required=True)
        target_currency = String(required=True)
        exchange_rate = GrapheneDecimal(required=True)
        provider_fee = GrapheneDecimal()
        platform_fee = GrapheneDecimal()
        payout_method = String(required=True)
        recipient_name = String(required=True)
        recipient_phone = String(required=True)
        recipient_email = String()
        recipient_country = String(required=True)
        recipient_bank = String()
        recipient_account = String()
        purpose_of_remittance = String()
        source_of_funds = String()

    international_transfer = Field(InternationalTransferNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        sender = _get_model_by_global_id(
            input["sender_id"], User, "Sender"
        )
        if sender.pk != user.pk:
            raise GraphQLError(
                "You can only create transfers as yourself."
            )

        source_account = _get_model_by_global_id(
            input["source_account_id"], Account, "Source account"
        )
        if source_account.user_id != user.pk:
            raise GraphQLError("You do not own this account.")

        provider = _get_model_by_global_id(
            input["provider_id"], RemittanceProvider, "Provider"
        )

        transfer = _wrap(
            InternationalTransferService.initiate_transfer,
            sender=user,
            source_account=source_account,
            provider=provider,
            transfer_type=input["transfer_type"],
            source_amount=input["source_amount"],
            source_currency=input["source_currency"],
            target_currency=input["target_currency"],
            exchange_rate=input["exchange_rate"],
            payout_method=input["payout_method"],
            recipient_name=input["recipient_name"],
            recipient_phone=input["recipient_phone"],
            recipient_email=input.get("recipient_email", ""),
            recipient_country=input.get("recipient_country", ""),
            recipient_bank=input.get("recipient_bank", ""),
            recipient_account=input.get("recipient_account", ""),
            purpose_of_remittance=input.get("purpose_of_remittance", ""),
            source_of_funds=input.get("source_of_funds", ""),
            provider_fee=input.get("provider_fee"),
            platform_fee=input.get("platform_fee"),
        )

        return cls(
            international_transfer=transfer,
            success=True,
            message="International transfer created successfully.",
        )


class UpdateInternationalTransferMutation(relay.ClientIDMutation):
    """Update an international transfer (status and tracking)."""

    class Input:
        international_transfer_id = ID(required=True)
        status = String()
        external_reference = String()
        estimated_delivery = String()
        delivered_at = String()

    international_transfer = Field(InternationalTransferNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        transfer = _get_model_by_global_id(
            input["international_transfer_id"],
            InternationalTransfer,
            "International transfer",
        )

        if transfer.sender != user:
            raise GraphQLError("You do not own this transfer.")

        if input.get("status"):
            valid_statuses = [
                choice[0]
                for choice in InternationalTransfer.STATUS_CHOICES
            ]
            if input["status"] not in valid_statuses:
                raise GraphQLError("Invalid status.")
            transfer.status = input["status"]

            if input["status"] == "PROCESSING":
                transfer.initiated_at = timezone.now()
            elif input["status"] == "COMPLETED":
                transfer.completed_at = timezone.now()

        if input.get("external_reference") is not None:
            transfer.external_reference = input["external_reference"]

        if input.get("estimated_delivery"):
            transfer.estimated_delivery = _validate_datetime(
                input["estimated_delivery"]
            )

        if input.get("delivered_at"):
            transfer.delivered_at = _validate_datetime(input["delivered_at"])

        try:
            transfer.save()
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            international_transfer=transfer,
            success=True,
            message="International transfer updated successfully.",
        )


class DeleteInternationalTransferMutation(relay.ClientIDMutation):
    """Delete a pending or cancelled international transfer."""

    class Input:
        international_transfer_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        transfer = _get_model_by_global_id(
            input["international_transfer_id"],
            InternationalTransfer,
            "International transfer",
        )

        if transfer.sender != user:
            raise GraphQLError("You do not own this transfer.")

        if transfer.status not in ["PENDING", "CANCELLED"]:
            raise GraphQLError(
                "Only pending or cancelled transfers can be deleted."
            )

        transfer.delete()

        return cls(
            success=True,
            message="International transfer deleted successfully.",
        )


# ============================================================================
# EXCHANGE RATE MUTATIONS
# ============================================================================

class CreateExchangeRateMutation(relay.ClientIDMutation):
    """Create an exchange rate. Staff only."""

    class Input:
        base_currency = String(required=True)
        target_currency = String(required=True)
        buy_rate = GrapheneDecimal(required=True)
        sell_rate = GrapheneDecimal(required=True)
        mid_rate = GrapheneDecimal(required=True)
        provider_buy_rate = GrapheneDecimal()
        provider_sell_rate = GrapheneDecimal()
        provider_id = ID()
        next_update = String(required=True)

    exchange_rate = Field(ExchangeRateNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        if not user.is_staff and not user.is_superuser:
            raise GraphQLError(
                "Only admins can create exchange rates."
            )

        if input["base_currency"] == input["target_currency"]:
            raise GraphQLError(
                "Base and target currencies must be different."
            )

        buy_rate = Decimal(str(input["buy_rate"]))
        sell_rate = Decimal(str(input["sell_rate"]))
        mid_rate = Decimal(str(input["mid_rate"]))

        if buy_rate <= 0 or sell_rate <= 0 or mid_rate <= 0:
            raise GraphQLError("Exchange rates must be greater than zero.")

        provider = None
        if input.get("provider_id"):
            provider = _get_model_by_global_id(
                input["provider_id"],
                RemittanceProvider,
                "Remittance provider",
            )

        next_update = _validate_datetime(input["next_update"])
        if not next_update:
            raise GraphQLError("Next update date is required.")
        if next_update <= timezone.now():
            raise GraphQLError("Next update must be in the future.")

        try:
            exchange_rate = ExchangeRate.objects.create(
                base_currency=input["base_currency"],
                target_currency=input["target_currency"],
                buy_rate=buy_rate,
                sell_rate=sell_rate,
                mid_rate=mid_rate,
                provider_buy_rate=Decimal(
                    str(input.get("provider_buy_rate", buy_rate))
                ),
                provider_sell_rate=Decimal(
                    str(input.get("provider_sell_rate", sell_rate))
                ),
                provider=provider,
                next_update=next_update,
                is_active=True,
            )
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            exchange_rate=exchange_rate,
            success=True,
            message="Exchange rate created successfully.",
        )


class UpdateExchangeRateMutation(relay.ClientIDMutation):
    """Update an exchange rate. Staff only."""

    class Input:
        exchange_rate_id = ID(required=True)
        buy_rate = GrapheneDecimal()
        sell_rate = GrapheneDecimal()
        mid_rate = GrapheneDecimal()
        provider_buy_rate = GrapheneDecimal()
        provider_sell_rate = GrapheneDecimal()
        provider_id = ID()
        next_update = String()
        is_active = Boolean()

    exchange_rate = Field(ExchangeRateNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        if not user.is_staff and not user.is_superuser:
            raise GraphQLError(
                "Only admins can update exchange rates."
            )

        exchange_rate = _get_model_by_global_id(
            input["exchange_rate_id"], ExchangeRate, "Exchange rate"
        )

        if input.get("buy_rate"):
            buy_rate = Decimal(str(input["buy_rate"]))
            if buy_rate <= 0:
                raise GraphQLError("Buy rate must be greater than zero.")
            exchange_rate.buy_rate = buy_rate

        if input.get("sell_rate"):
            sell_rate = Decimal(str(input["sell_rate"]))
            if sell_rate <= 0:
                raise GraphQLError("Sell rate must be greater than zero.")
            exchange_rate.sell_rate = sell_rate

        if input.get("mid_rate"):
            mid_rate = Decimal(str(input["mid_rate"]))
            if mid_rate <= 0:
                raise GraphQLError("Mid rate must be greater than zero.")
            exchange_rate.mid_rate = mid_rate

        if input.get("provider_buy_rate") is not None:
            exchange_rate.provider_buy_rate = (
                Decimal(str(input["provider_buy_rate"]))
                if input["provider_buy_rate"]
                else None
            )

        if input.get("provider_sell_rate") is not None:
            exchange_rate.provider_sell_rate = (
                Decimal(str(input["provider_sell_rate"]))
                if input["provider_sell_rate"]
                else None
            )

        if input.get("provider_id"):
            provider = _get_model_by_global_id(
                input["provider_id"],
                RemittanceProvider,
                "Remittance provider",
            )
            exchange_rate.provider = provider

        if input.get("next_update"):
            next_update = _validate_datetime(input["next_update"])
            if next_update <= timezone.now():
                raise GraphQLError("Next update must be in the future.")
            exchange_rate.next_update = next_update

        if input.get("is_active") is not None:
            exchange_rate.is_active = input["is_active"]

        try:
            exchange_rate.save()
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            exchange_rate=exchange_rate,
            success=True,
            message="Exchange rate updated successfully.",
        )


class DeleteExchangeRateMutation(relay.ClientIDMutation):
    """Delete an exchange rate. Staff only."""

    class Input:
        exchange_rate_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        if not user.is_staff and not user.is_superuser:
            raise GraphQLError(
                "Only admins can delete exchange rates."
            )

        exchange_rate = _get_model_by_global_id(
            input["exchange_rate_id"], ExchangeRate, "Exchange rate"
        )

        exchange_rate.delete()

        return cls(
            success=True,
            message="Exchange rate deleted successfully.",
        )


# ============================================================================
# MUTATION REGISTRY
# ============================================================================

class ScheduledMutations(graphene.ObjectType):
    # Scheduled Payment
    create_scheduled_payment = CreateScheduledPaymentMutation.Field()
    update_scheduled_payment = UpdateScheduledPaymentMutation.Field()
    delete_scheduled_payment = DeleteScheduledPaymentMutation.Field()

    # Credit Product
    create_credit_product = CreateCreditProductMutation.Field()
    update_credit_product = UpdateCreditProductMutation.Field()
    delete_credit_product = DeleteCreditProductMutation.Field()

    # Support Ticket
    create_support_ticket = CreateSupportTicketMutation.Field()
    update_support_ticket = UpdateSupportTicketMutation.Field()
    delete_support_ticket = DeleteSupportTicketMutation.Field()

    # API Key
    create_api_key = CreateAPIKeyMutation.Field()
    update_api_key = UpdateAPIKeyMutation.Field()
    delete_api_key = DeleteAPIKeyMutation.Field()

    # Remittance Provider
    create_remittance_provider = CreateRemittanceProviderMutation.Field()
    update_remittance_provider = UpdateRemittanceProviderMutation.Field()
    delete_remittance_provider = DeleteRemittanceProviderMutation.Field()

    # International Transfer
    create_international_transfer = CreateInternationalTransferMutation.Field()
    update_international_transfer = UpdateInternationalTransferMutation.Field()
    delete_international_transfer = DeleteInternationalTransferMutation.Field()

    # Exchange Rate
    create_exchange_rate = CreateExchangeRateMutation.Field()
    update_exchange_rate = UpdateExchangeRateMutation.Field()
    delete_exchange_rate = DeleteExchangeRateMutation.Field()


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "CreateScheduledPaymentMutation",
    "UpdateScheduledPaymentMutation",
    "DeleteScheduledPaymentMutation",
    "CreateCreditProductMutation",
    "UpdateCreditProductMutation",
    "DeleteCreditProductMutation",
    "CreateSupportTicketMutation",
    "UpdateSupportTicketMutation",
    "DeleteSupportTicketMutation",
    "CreateAPIKeyMutation",
    "UpdateAPIKeyMutation",
    "DeleteAPIKeyMutation",
    "CreateRemittanceProviderMutation",
    "UpdateRemittanceProviderMutation",
    "DeleteRemittanceProviderMutation",
    "CreateInternationalTransferMutation",
    "UpdateInternationalTransferMutation",
    "DeleteInternationalTransferMutation",
    "CreateExchangeRateMutation",
    "UpdateExchangeRateMutation",
    "DeleteExchangeRateMutation",
    "ScheduledMutations",
]