# apps/backend/graphq/banking/mutations/payment_gateways.py

"""
GraphQL mutations for payment gateways and USSD.

Config mutations are staff-only. Gateway operations, USSD session
processing, and USSD operations delegate to
banking.services.payment_gateway_service.
"""

import logging
from decimal import Decimal

import graphene
from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from django.utils import timezone
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

from banking.models.payment_gateways import (
    PaymentGateway,
    USSDOperation,
    USSDSession,
)
from banking.services.payment_gateway_service import (
    GatewayRouter,
    PaymentGatewayService,
    USSDService,
)
from graphq.banking.types.payment_gateways import (
    PaymentGatewayNode,
    USSDOperationNode,
    USSDSessionNode,
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


def _validate_phone_number(phone):
    if not phone:
        raise GraphQLError("Phone number is required.")
    phone = ''.join(filter(str.isdigit, phone))
    if len(phone) < 10:
        raise GraphQLError("Invalid phone number.")
    return phone


# ============================================================================
# PAYMENT GATEWAY MUTATIONS (staff only)
# ============================================================================

class CreatePaymentGatewayMutation(relay.ClientIDMutation):
    class Input:
        name = String(required=True)
        provider = String(required=True)
        public_key = String(required=True)
        secret_key = String(required=True)
        base_url = String(required=True)
        encryption_key = String()
        is_active = Boolean()
        is_default = Boolean()
        weight = Int()
        supports_transfer = Boolean()
        supports_collection = Boolean()
        supports_ussd = Boolean()
        supports_card = Boolean()
        supports_bank_account = Boolean()
        requests_per_minute = Int()
        daily_transaction_limit = GrapheneDecimal()
        config = GenericScalar()

    gateway = Field(PaymentGatewayNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        _require_staff(user)

        valid_providers = [
            choice[0] for choice in PaymentGateway.PROVIDER_CHOICES
        ]
        if input["provider"] not in valid_providers:
            raise GraphQLError(
                f"Invalid provider. Must be one of: "
                f"{', '.join(valid_providers)}"
            )

        if PaymentGateway.objects.filter(name=input["name"]).exists():
            raise GraphQLError(
                "Gateway with this name already exists."
            )

        if input.get("is_default", False):
            PaymentGateway.objects.filter(is_default=True).update(
                is_default=False
            )

        try:
            gateway = PaymentGateway.objects.create(
                name=input["name"],
                provider=input["provider"],
                base_url=input["base_url"],
                is_active=input.get("is_active", True),
                is_default=input.get("is_default", False),
                weight=input.get("weight", 1),
                supports_transfer=input.get("supports_transfer", True),
                supports_collection=input.get(
                    "supports_collection", True
                ),
                supports_ussd=input.get("supports_ussd", False),
                supports_card=input.get("supports_card", False),
                supports_bank_account=input.get(
                    "supports_bank_account", True
                ),
                requests_per_minute=input.get(
                    "requests_per_minute", 60
                ),
                daily_transaction_limit=Decimal(
                    str(input.get(
                        "daily_transaction_limit", "5000000.00"
                    ))
                ),
                config=input.get("config", {}),
            )
            gateway.public_key = input["public_key"]
            gateway.secret_key = input["secret_key"]
            if input.get("encryption_key"):
                gateway.encryption_key = input["encryption_key"]
            gateway.save()
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            gateway=gateway,
            success=True,
            message="Payment gateway created successfully.",
        )


class UpdatePaymentGatewayMutation(relay.ClientIDMutation):
    class Input:
        gateway_id = ID(required=True)
        name = String()
        provider = String()
        public_key = String()
        secret_key = String()
        base_url = String()
        encryption_key = String()
        is_active = Boolean()
        is_default = Boolean()
        weight = Int()
        supports_transfer = Boolean()
        supports_collection = Boolean()
        supports_ussd = Boolean()
        supports_card = Boolean()
        supports_bank_account = Boolean()
        requests_per_minute = Int()
        daily_transaction_limit = GrapheneDecimal()
        config = GenericScalar()

    gateway = Field(PaymentGatewayNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        _require_staff(user)

        gateway = _get_model_by_global_id(
            input["gateway_id"], PaymentGateway, "Gateway"
        )

        if input.get("name"):
            if (
                PaymentGateway.objects
                .filter(name=input["name"])
                .exclude(pk=gateway.pk)
                .exists()
            ):
                raise GraphQLError(
                    "Gateway with this name already exists."
                )
            gateway.name = input["name"]

        if input.get("provider"):
            valid_providers = [
                choice[0] for choice in PaymentGateway.PROVIDER_CHOICES
            ]
            if input["provider"] not in valid_providers:
                raise GraphQLError("Invalid provider.")
            gateway.provider = input["provider"]

        if input.get("public_key"):
            gateway.public_key = input["public_key"]

        if input.get("secret_key"):
            gateway.secret_key = input["secret_key"]

        if input.get("encryption_key"):
            gateway.encryption_key = input["encryption_key"]

        if input.get("base_url"):
            gateway.base_url = input["base_url"]

        if input.get("is_active") is not None:
            gateway.is_active = input["is_active"]

        if input.get("is_default") is not None:
            if input["is_default"]:
                PaymentGateway.objects.filter(
                    is_default=True
                ).exclude(pk=gateway.pk).update(is_default=False)
            gateway.is_default = input["is_default"]

        for field in [
            "weight",
            "supports_transfer",
            "supports_collection",
            "supports_ussd",
            "supports_card",
            "supports_bank_account",
            "requests_per_minute",
        ]:
            if input.get(field) is not None:
                setattr(gateway, field, input[field])

        if input.get("daily_transaction_limit") is not None:
            gateway.daily_transaction_limit = Decimal(
                str(input["daily_transaction_limit"])
            )

        if input.get("config") is not None:
            gateway.config = input["config"]

        try:
            gateway.save()
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            gateway=gateway,
            success=True,
            message="Payment gateway updated successfully.",
        )


class DeletePaymentGatewayMutation(relay.ClientIDMutation):
    class Input:
        gateway_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        _require_staff(user)

        gateway = _get_model_by_global_id(
            input["gateway_id"], PaymentGateway, "Gateway"
        )

        if (
            gateway.is_default
            and PaymentGateway.objects.filter(is_default=True).count() <= 1
        ):
            raise GraphQLError(
                "Cannot delete the only default gateway."
            )

        gateway.is_active = False
        gateway.save(update_fields=["is_active"])

        return cls(
            success=True,
            message="Payment gateway deactivated.",
        )


class SetDefaultGatewayMutation(relay.ClientIDMutation):
    class Input:
        gateway_id = ID(required=True)

    gateway = Field(PaymentGatewayNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        _require_staff(user)

        gateway = _get_model_by_global_id(
            input["gateway_id"], PaymentGateway, "Gateway"
        )

        PaymentGateway.objects.filter(is_default=True).update(
            is_default=False
        )

        gateway.is_default = True
        gateway.save(update_fields=["is_default"])

        return cls(
            gateway=gateway,
            success=True,
            message="Gateway set as default successfully.",
        )


class UpdateGatewayMetricsMutation(relay.ClientIDMutation):
    class Input:
        gateway_id = ID(required=True)
        success_rate = Float()
        average_response_time = Float()
        uptime_percentage = Float()

    gateway = Field(PaymentGatewayNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        _require_staff(user)

        gateway = _get_model_by_global_id(
            input["gateway_id"], PaymentGateway, "Gateway"
        )

        if input.get("success_rate") is not None:
            gateway.success_rate = input["success_rate"]

        if input.get("average_response_time") is not None:
            gateway.average_response_time = input[
                "average_response_time"
            ]

        if input.get("uptime_percentage") is not None:
            gateway.uptime_percentage = input["uptime_percentage"]

        gateway.save()

        return cls(
            gateway=gateway,
            success=True,
            message="Gateway metrics updated successfully.",
        )


# ============================================================================
# GATEWAY OPERATIONS
# ============================================================================

class GatewayTransferMutation(relay.ClientIDMutation):
    class Input:
        from_account = String(required=True)
        to_account = String(required=True)
        bank_code = String(required=True)
        amount = GrapheneDecimal(required=True)
        narration = String(required=True)
        gateway_id = ID()

    result = GenericScalar()
    success = Boolean()
    message = String()
    reference = String()
    provider_reference = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        amount = _validate_amount(input["amount"])

        if input.get("gateway_id"):
            gateway = _get_model_by_global_id(
                input["gateway_id"], PaymentGateway, "Gateway"
            )
            if not gateway.is_active:
                raise GraphQLError("Gateway is not active.")
        else:
            gateway = GatewayRouter.get_best_gateway(
                "BANK_TRANSFER", amount, input["bank_code"]
            )
            if not gateway:
                raise GraphQLError("No suitable gateway available.")

        service = PaymentGatewayService(gateway)
        try:
            result = service.transfer_funds(
                from_account=input["from_account"],
                to_account=input["to_account"],
                bank_code=input["bank_code"],
                amount=amount,
                narration=input["narration"],
            )
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc
        except Exception as exc:
            raise GraphQLError(f"Transfer failed: {exc}") from exc

        return cls(
            result=result,
            success=result.get("success", False),
            message=(
                "Transfer completed."
                if result.get("success")
                else "Transfer failed."
            ),
            reference=result.get("reference"),
            provider_reference=result.get("provider_reference"),
        )


class InitiateUSSDPaymentMutation(relay.ClientIDMutation):
    class Input:
        amount = GrapheneDecimal(required=True)
        phone_number = String(required=True)
        provider_code = String(required=True)

    result = GenericScalar()
    success = Boolean()
    message = String()
    ussd_code = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        amount = _validate_amount(input["amount"])
        phone = _validate_phone_number(input["phone_number"])

        service = PaymentGatewayService()
        try:
            result = service.initiate_ussd_payment(
                amount=amount,
                phone_number=phone,
                provider_code=input["provider_code"],
            )
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc
        except Exception as exc:
            raise GraphQLError(
                f"USSD payment initiation failed: {exc}"
            ) from exc

        return cls(
            result=result,
            success=result.get("success", False),
            message=(
                "USSD payment initiated."
                if result.get("success")
                else "USSD payment initiation failed."
            ),
            ussd_code=result.get("ussd_code"),
        )


# ============================================================================
# USSD SESSION MUTATIONS
# ============================================================================

class ProcessUSSDSessionMutation(relay.ClientIDMutation):
    class Input:
        phone_number = String(required=True)
        ussd_code = String(required=True)
        session_id = String()

    result = GenericScalar()
    success = Boolean()
    message = String()
    session = Field(USSDSessionNode)

    @classmethod
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        phone = _validate_phone_number(input["phone_number"])

        service = USSDService()
        try:
            result = service.process_ussd_request(
                phone_number=phone,
                ussd_code=input["ussd_code"],
                session_id=input.get("session_id"),
            )
        except NotImplementedError as exc:
            return cls(
                success=False,
                message=str(exc),
                result={
                    "response": (
                        "This USSD operation is not yet available."
                    ),
                    "continue_session": False,
                },
            )
        except Exception as exc:
            logger.exception("USSD processing failed")
            return cls(
                success=False,
                message=str(exc),
                result={
                    "response": (
                        "An error occurred. Please try again."
                    ),
                    "continue_session": False,
                },
            )

        session = USSDSession.objects.filter(
            phone_number=phone,
            is_active=True,
        ).order_by('-created_at').first()

        if session:
            USSDOperation.objects.create(
                session=session,
                operation_type='OTHER',
                ussd_code=input["ussd_code"],
                input_text=input["ussd_code"],
                response_text=result.get("response", ""),
                is_successful=True,
            )

        return cls(
            success=True,
            message="USSD request processed.",
            result=result,
            session=session,
        )


class EndUSSDSessionMutation(relay.ClientIDMutation):
    class Input:
        session_id = String(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        try:
            session = USSDSession.objects.get(
                session_id=input["session_id"]
            )
        except USSDSession.DoesNotExist:
            raise GraphQLError("USSD session not found.")

        session.is_active = False
        session.save(update_fields=["is_active"])

        return cls(
            success=True,
            message="USSD session ended.",
        )


class CreateUSSDOperationMutation(relay.ClientIDMutation):
    class Input:
        session_id = ID(required=True)
        operation_type = String(required=True)
        ussd_code = String(required=True)
        input_text = String(required=True)
        response_text = String(required=True)
        is_successful = Boolean()
        error_message = String()
        transaction_ref = String()

    operation = Field(USSDOperationNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        session = _get_model_by_global_id(
            input["session_id"], USSDSession, "USSD session"
        )

        valid_types = [
            choice[0] for choice in USSDOperation.OPERATION_TYPES
        ]
        if input["operation_type"] not in valid_types:
            raise GraphQLError(
                f"Invalid operation type. Must be one of: "
                f"{', '.join(valid_types)}"
            )

        try:
            operation = USSDOperation.objects.create(
                session=session,
                operation_type=input["operation_type"],
                ussd_code=input["ussd_code"],
                input_text=input["input_text"],
                response_text=input["response_text"],
                is_successful=input.get("is_successful", True),
                error_message=input.get("error_message", ""),
                transaction_ref=input.get("transaction_ref", ""),
            )
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            operation=operation,
            success=True,
            message="USSD operation logged successfully.",
        )


# ============================================================================
# MUTATION REGISTRY
# ============================================================================

class PaymentGatewayMutations(graphene.ObjectType):
    create_payment_gateway = CreatePaymentGatewayMutation.Field()
    update_payment_gateway = UpdatePaymentGatewayMutation.Field()
    delete_payment_gateway = DeletePaymentGatewayMutation.Field()
    set_default_gateway = SetDefaultGatewayMutation.Field()
    update_gateway_metrics = UpdateGatewayMetricsMutation.Field()

    gateway_transfer = GatewayTransferMutation.Field()
    initiate_ussd_payment = InitiateUSSDPaymentMutation.Field()

    process_ussd_session = ProcessUSSDSessionMutation.Field()
    end_ussd_session = EndUSSDSessionMutation.Field()
    create_ussd_operation = CreateUSSDOperationMutation.Field()


__all__ = [
    "CreatePaymentGatewayMutation",
    "UpdatePaymentGatewayMutation",
    "DeletePaymentGatewayMutation",
    "SetDefaultGatewayMutation",
    "UpdateGatewayMetricsMutation",
    "GatewayTransferMutation",
    "InitiateUSSDPaymentMutation",
    "ProcessUSSDSessionMutation",
    "EndUSSDSessionMutation",
    "CreateUSSDOperationMutation",
    "PaymentGatewayMutations",
]