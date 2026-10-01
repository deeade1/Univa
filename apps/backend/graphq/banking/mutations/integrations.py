# apps/backend/graphq/banking/mutations/integrations.py

"""
GraphQL mutations for Banking integrations.

Config mutations are staff-only. Runtime operations (name enquiry,
transfer, retry, test) delegate to:

    banking.services.integration_service.BankAPIIntegrationService
"""

import logging
import uuid
from decimal import Decimal

import graphene
from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from graphene import (
    ID,
    Boolean,
    Decimal as GrapheneDecimal,
    Field,
    Float,
    Int,
    String,
    relay,
)
from graphene.types.generic import GenericScalar
from graphql import GraphQLError
from graphql_relay import from_global_id

from banking.models.integrations import (
    BankAPIIntegration,
    APITransactionLog,
)
from banking.services.integration_service import (
    BankAPIIntegrationService,
)
from graphq.banking.types.integrations import (
    BankAPIIntegrationNode,
    APITransactionLogNode,
)
from univa_jwt.decorators import login_required


logger = logging.getLogger(__name__)


# ============================================================================
# HELPERS
# ============================================================================

def _get_authenticated_user(info):
    user = getattr(info.context, "user", None)
    if not user or not user.is_authenticated:
        raise GraphQLError("Authentication required.")
    return user


def _require_staff(user):
    if not user.is_staff:
        raise GraphQLError("Staff privileges required.")


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


# ============================================================================
# BANK API INTEGRATION MUTATIONS (staff only)
# ============================================================================

class CreateBankAPIIntegrationMutation(relay.ClientIDMutation):
    class Input:
        name = String(required=True)
        provider = String(required=True)
        api_key = String(required=True)
        secret_key = String(required=True)
        base_url = String(required=True)
        is_active = Boolean()
        is_default = Boolean()
        weight = Int()
        max_amount_per_transaction = GrapheneDecimal()
        daily_amount_limit = GrapheneDecimal()
        supported_banks = GenericScalar()

    integration = Field(BankAPIIntegrationNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        _require_staff(user)

        valid_providers = [
            choice[0] for choice in BankAPIIntegration.PROVIDER_CHOICES
        ]
        if input["provider"] not in valid_providers:
            raise GraphQLError(
                f"Invalid provider. Must be one of: "
                f"{', '.join(valid_providers)}"
            )

        if BankAPIIntegration.objects.filter(name=input["name"]).exists():
            raise GraphQLError("Integration with this name already exists.")

        if input.get("is_default", False):
            BankAPIIntegration.objects.filter(is_default=True).update(
                is_default=False
            )

        max_amount = Decimal(
            input.get("max_amount_per_transaction", "500000.00")
        )
        daily_limit = Decimal(
            input.get("daily_amount_limit", "5000000.00")
        )
        if max_amount > daily_limit:
            raise GraphQLError(
                "Max per transaction cannot exceed daily limit."
            )

        try:
            integration = BankAPIIntegration.objects.create(
                name=input["name"],
                provider=input["provider"],
                base_url=input["base_url"],
                is_active=input.get("is_active", True),
                is_default=input.get("is_default", False),
                weight=input.get("weight", 1),
                max_amount_per_transaction=max_amount,
                daily_amount_limit=daily_limit,
                supported_banks=input.get("supported_banks", []),
            )
            integration.api_key = input["api_key"]
            integration.secret_key = input["secret_key"]
            integration.save()
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            integration=integration,
            success=True,
            message="Bank API integration created successfully.",
        )


class UpdateBankAPIIntegrationMutation(relay.ClientIDMutation):
    class Input:
        integration_id = ID(required=True)
        name = String()
        provider = String()
        api_key = String()
        secret_key = String()
        base_url = String()
        is_active = Boolean()
        is_default = Boolean()
        weight = Int()
        max_amount_per_transaction = GrapheneDecimal()
        daily_amount_limit = GrapheneDecimal()
        supported_banks = GenericScalar()

    integration = Field(BankAPIIntegrationNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        _require_staff(user)

        integration = _get_model_by_global_id(
            input["integration_id"],
            BankAPIIntegration,
            "Integration",
        )

        if input.get("name"):
            if (
                BankAPIIntegration.objects
                .filter(name=input["name"])
                .exclude(pk=integration.pk)
                .exists()
            ):
                raise GraphQLError(
                    "Integration with this name already exists."
                )
            integration.name = input["name"]

        if input.get("provider"):
            valid_providers = [
                choice[0]
                for choice in BankAPIIntegration.PROVIDER_CHOICES
            ]
            if input["provider"] not in valid_providers:
                raise GraphQLError("Invalid provider.")
            integration.provider = input["provider"]

        if input.get("api_key"):
            integration.api_key = input["api_key"]

        if input.get("secret_key"):
            integration.secret_key = input["secret_key"]

        if input.get("base_url"):
            integration.base_url = input["base_url"]

        if input.get("is_active") is not None:
            integration.is_active = input["is_active"]

        if input.get("is_default") is not None:
            if input["is_default"]:
                (
                    BankAPIIntegration.objects
                    .filter(is_default=True)
                    .exclude(pk=integration.pk)
                    .update(is_default=False)
                )
            integration.is_default = input["is_default"]

        if input.get("weight") is not None:
            integration.weight = input["weight"]

        if input.get("max_amount_per_transaction") is not None:
            max_amount = Decimal(
                str(input["max_amount_per_transaction"])
            )
            if max_amount > integration.daily_amount_limit:
                raise GraphQLError(
                    "Max per transaction cannot exceed daily limit."
                )
            integration.max_amount_per_transaction = max_amount

        if input.get("daily_amount_limit") is not None:
            daily_limit = Decimal(str(input["daily_amount_limit"]))
            if integration.max_amount_per_transaction > daily_limit:
                raise GraphQLError(
                    "Daily limit cannot be less than max per transaction."
                )
            integration.daily_amount_limit = daily_limit

        if input.get("supported_banks") is not None:
            integration.supported_banks = input["supported_banks"]

        try:
            integration.save()
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            integration=integration,
            success=True,
            message="Bank API integration updated successfully.",
        )


class DeleteBankAPIIntegrationMutation(relay.ClientIDMutation):
    class Input:
        integration_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        _require_staff(user)

        integration = _get_model_by_global_id(
            input["integration_id"],
            BankAPIIntegration,
            "Integration",
        )

        if integration.api_logs.exists():
            integration.is_active = False
            integration.save(update_fields=["is_active"])
            return cls(
                success=True,
                message="Integration deactivated due to existing logs.",
            )

        integration.delete()

        return cls(
            success=True,
            message="Bank API integration deleted successfully.",
        )


class SetDefaultIntegrationMutation(relay.ClientIDMutation):
    class Input:
        integration_id = ID(required=True)

    integration = Field(BankAPIIntegrationNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        _require_staff(user)

        integration = _get_model_by_global_id(
            input["integration_id"],
            BankAPIIntegration,
            "Integration",
        )

        BankAPIIntegration.objects.filter(is_default=True).update(
            is_default=False
        )

        integration.is_default = True
        integration.save(update_fields=["is_default"])

        return cls(
            integration=integration,
            success=True,
            message="Integration set as default successfully.",
        )


# ============================================================================
# API TRANSACTION LOG MUTATIONS
# ============================================================================

class RetryAPITransactionMutation(relay.ClientIDMutation):
    class Input:
        api_log_id = ID(required=True)

    api_log = Field(APITransactionLogNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        _require_staff(user)

        api_log = _get_model_by_global_id(
            input["api_log_id"],
            APITransactionLog,
            "API log",
        )

        try:
            result = BankAPIIntegrationService.retry_log(api_log=api_log)
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        api_log.refresh_from_db()

        return cls(
            api_log=api_log,
            success=result.get("success", False),
            message=(
                "API transaction retried successfully."
                if result.get("success")
                else "API transaction retry failed."
            ),
        )


# ============================================================================
# BANK API OPERATION MUTATIONS
# ============================================================================

class NameEnquiryMutation(relay.ClientIDMutation):
    class Input:
        account_number = String(required=True)
        bank_code = String(required=True)
        provider_name = String()

    result = GenericScalar()
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        try:
            result = BankAPIIntegrationService.name_enquiry(
                account_number=input["account_number"],
                bank_code=input["bank_code"],
                provider_name=input.get("provider_name"),
            )
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            result=result.get("data"),
            success=result.get("success", False),
            message=(
                "Name enquiry completed."
                if result.get("success")
                else "Name enquiry failed."
            ),
        )


class BankTransferMutation(relay.ClientIDMutation):
    class Input:
        from_account = String(required=True)
        to_account = String(required=True)
        amount = GrapheneDecimal(required=True)
        narration = String(required=True)
        provider_name = String()

    result = GenericScalar()
    success = Boolean()
    message = String()
    reference = String()
    external_reference = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        amount = _validate_amount(input["amount"])

        try:
            result = BankAPIIntegrationService.transfer_funds(
                from_account=input["from_account"],
                to_account=input["to_account"],
                amount=amount,
                narration=input["narration"],
                provider_name=input.get("provider_name"),
            )
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            result=result.get("data"),
            success=result.get("success", False),
            message=(
                "Transfer completed."
                if result.get("success")
                else "Transfer failed."
            ),
            reference=result.get("reference"),
            external_reference=result.get("external_reference"),
        )


class TestIntegrationMutation(relay.ClientIDMutation):
    class Input:
        integration_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        _require_staff(user)

        integration = _get_model_by_global_id(
            input["integration_id"],
            BankAPIIntegration,
            "Integration",
        )

        success, message = BankAPIIntegrationService.test_connection(
            integration
        )

        return cls(success=success, message=message)


class UpdateIntegrationMetricsMutation(relay.ClientIDMutation):
    class Input:
        integration_id = ID(required=True)
        success_rate = Float()
        average_response_time = Float()

    integration = Field(BankAPIIntegrationNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        _require_staff(user)

        integration = _get_model_by_global_id(
            input["integration_id"],
            BankAPIIntegration,
            "Integration",
        )

        if input.get("success_rate") is not None:
            integration.success_rate = input["success_rate"]

        if input.get("average_response_time") is not None:
            integration.average_response_time = input[
                "average_response_time"
            ]

        integration.save(update_fields=[
            "success_rate", "average_response_time",
        ])

        return cls(
            integration=integration,
            success=True,
            message="Integration metrics updated successfully.",
        )


# ============================================================================
# MUTATION REGISTRY
# ============================================================================

class IntegrationsMutations(graphene.ObjectType):
    create_bank_api_integration = CreateBankAPIIntegrationMutation.Field()
    update_bank_api_integration = UpdateBankAPIIntegrationMutation.Field()
    delete_bank_api_integration = DeleteBankAPIIntegrationMutation.Field()
    set_default_integration = SetDefaultIntegrationMutation.Field()
    test_integration = TestIntegrationMutation.Field()
    update_integration_metrics = UpdateIntegrationMetricsMutation.Field()

    retry_api_transaction = RetryAPITransactionMutation.Field()

    name_enquiry = NameEnquiryMutation.Field()
    bank_transfer = BankTransferMutation.Field()


__all__ = [
    "CreateBankAPIIntegrationMutation",
    "UpdateBankAPIIntegrationMutation",
    "DeleteBankAPIIntegrationMutation",
    "SetDefaultIntegrationMutation",
    "TestIntegrationMutation",
    "UpdateIntegrationMetricsMutation",
    "RetryAPITransactionMutation",
    "NameEnquiryMutation",
    "BankTransferMutation",
    "IntegrationsMutations",
]