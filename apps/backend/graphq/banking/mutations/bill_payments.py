# apps/backend/graphq/banking/mutations/bill_payments.py

"""
GraphQL mutations for Banking bill payment models.

Architecture
------------

All money movement is delegated to:

    banking.services.bill_payment_service.BillPaymentService

BillPaymentService posts through:

    banking.models.accounting.AccountingManager.create_double_entry

This module does NOT:
    - post LedgerEntry rows itself
    - create Transaction rows for money movement
    - call Account.balance.debit()/credit()
    - allow clients to set arbitrary status transitions on payments

Metadata CRUD (categories, billers, providers) is exposed for staff.
Bill accounts and bills are owner-scoped. Money movement
(bill payment, airtime, data bundle) is owner-scoped and delegates
to the service.
"""

import logging
from decimal import Decimal

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

from banking.models.bill_payments import (
    AirtimePurchase,
    Bill,
    BillAccount,
    BillCategory,
    Biller,
    BillPayment,
    BillProvider,
    DataBundlePurchase,
)
from banking.models.core import Account
from banking.services.bill_payment_service import BillPaymentService
from graphq.banking.types.bill_payments import (
    AirtimePurchaseNode,
    BillAccountNode,
    BillCategoryNode,
    BillerNode,
    BillNode,
    BillPaymentNode,
    BillProviderNode,
    DataBundlePurchaseNode,
)
from univa_jwt.decorators import login_required


User = get_user_model()
logger = logging.getLogger(__name__)


# ============================================================================
# HELPERS
# ============================================================================

def _user(info):
    user = getattr(info.context, "user", None)
    if not user or not user.is_authenticated:
        raise GraphQLError("Authentication required.")
    return user


def _by_gid(global_id, model, label):
    if not global_id:
        raise GraphQLError(f"{label} ID is required.")
    try:
        _, pk = from_global_id(global_id)
        return model.objects.get(pk=pk)
    except model.DoesNotExist:
        raise GraphQLError(f"{label} not found.")
    except Exception as exc:
        raise GraphQLError(f"Invalid {label} ID.") from exc


def _owner(user, obj, label, field="user"):
    owner = getattr(obj, field, None)
    owner_id = getattr(owner, "pk", None)
    if owner_id != user.pk and not user.is_staff:
        raise GraphQLError(f"You do not own this {label}.")


def _staff(user):
    if not user.is_staff:
        raise GraphQLError("Staff privileges required.")


def _wrap(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except ValidationError as exc:
        raise GraphQLError(str(exc)) from exc


def _parse_date(value):
    if value is None:
        return None
    if hasattr(value, "year"):
        return value
    try:
        return __import__("datetime").date.fromisoformat(str(value))
    except ValueError as exc:
        raise GraphQLError(f"Invalid date: {value!r}.") from exc


# ============================================================================
# BILL CATEGORY MUTATIONS (staff only)
# ============================================================================

class CreateBillCategoryMutation(relay.ClientIDMutation):
    """Create a bill category. Staff only."""

    class Input:
        name = String(required=True)
        slug = String(required=True)
        description = String()
        icon = String()
        is_active = Boolean()

    bill_category = Field(BillCategoryNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)
        _staff(user)

        if BillCategory.objects.filter(name=input["name"]).exists():
            raise GraphQLError("Category with this name already exists.")
        if BillCategory.objects.filter(slug=input["slug"]).exists():
            raise GraphQLError("Category with this slug already exists.")

        category = _wrap(
            BillCategory.objects.create,
            name=input["name"],
            slug=input["slug"],
            description=input.get("description", ""),
            icon=input.get("icon", ""),
            is_active=input.get("is_active", True),
        )

        return cls(
            bill_category=category,
            success=True,
            message="Bill category created.",
        )


class UpdateBillCategoryMutation(relay.ClientIDMutation):
    """Update a bill category. Staff only."""

    class Input:
        bill_category_id = ID(required=True)
        name = String()
        slug = String()
        description = String()
        icon = String()
        is_active = Boolean()

    bill_category = Field(BillCategoryNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)
        _staff(user)

        category = _by_gid(
            input["bill_category_id"], BillCategory, "Bill category"
        )

        if input.get("name"):
            if BillCategory.objects.filter(name=input["name"]).exclude(pk=category.pk).exists():
                raise GraphQLError("Category with this name already exists.")
            category.name = input["name"]

        if input.get("slug"):
            if BillCategory.objects.filter(slug=input["slug"]).exclude(pk=category.pk).exists():
                raise GraphQLError("Category with this slug already exists.")
            category.slug = input["slug"]

        if input.get("description") is not None:
            category.description = input["description"]

        if input.get("icon") is not None:
            category.icon = input["icon"]

        if input.get("is_active") is not None:
            category.is_active = input["is_active"]

        category.save()

        return cls(
            bill_category=category,
            success=True,
            message="Bill category updated.",
        )


class DeleteBillCategoryMutation(relay.ClientIDMutation):
    """Delete a bill category. Staff only. Refused if billers reference it."""

    class Input:
        bill_category_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)
        _staff(user)

        category = _by_gid(
            input["bill_category_id"], BillCategory, "Bill category"
        )

        if category.billers.exists():
            raise GraphQLError(
                "Cannot delete a category with existing billers."
            )

        category.delete()

        return cls(
            success=True,
            message="Bill category deleted.",
        )


# ============================================================================
# BILLER MUTATIONS (staff only)
# ============================================================================

class CreateBillerMutation(relay.ClientIDMutation):
    """Create a biller. Staff only."""

    class Input:
        name = String(required=True)
        slug = String(required=True)
        category_id = ID(required=True)
        code = String(required=True)
        description = String()
        api_endpoint = String()
        api_key = String()
        webhook_url = String()
        fee_percentage = GrapheneDecimal()
        fee_fixed = GrapheneDecimal()
        min_amount = GrapheneDecimal()
        max_amount = GrapheneDecimal()
        is_active = Boolean()

    biller = Field(BillerNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)
        _staff(user)

        category = _by_gid(
            input["category_id"], BillCategory, "Category"
        )

        if Biller.objects.filter(name=input["name"]).exists():
            raise GraphQLError("Biller with this name already exists.")
        if Biller.objects.filter(code=input["code"]).exists():
            raise GraphQLError("Biller with this code already exists.")

        biller = _wrap(
            Biller.objects.create,
            name=input["name"],
            slug=input["slug"],
            category=category,
            code=input["code"],
            description=input.get("description", ""),
            api_endpoint=input.get("api_endpoint", ""),
            api_key=input.get("api_key", ""),
            webhook_url=input.get("webhook_url", ""),
            fee_percentage=Decimal(input.get("fee_percentage", "0.00")),
            fee_fixed=Decimal(input.get("fee_fixed", "0.00")),
            min_amount=Decimal(input.get("min_amount", "0.00")),
            max_amount=(
                Decimal(input["max_amount"])
                if input.get("max_amount")
                else None
            ),
            is_active=input.get("is_active", True),
        )

        return cls(
            biller=biller,
            success=True,
            message="Biller created.",
        )


class UpdateBillerMutation(relay.ClientIDMutation):
    """Update a biller. Staff only."""

    class Input:
        biller_id = ID(required=True)
        name = String()
        slug = String()
        category_id = ID()
        code = String()
        description = String()
        api_endpoint = String()
        api_key = String()
        webhook_url = String()
        fee_percentage = GrapheneDecimal()
        fee_fixed = GrapheneDecimal()
        min_amount = GrapheneDecimal()
        max_amount = GrapheneDecimal()
        is_active = Boolean()

    biller = Field(BillerNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)
        _staff(user)

        biller = _by_gid(input["biller_id"], Biller, "Biller")

        if input.get("name"):
            if Biller.objects.filter(name=input["name"]).exclude(pk=biller.pk).exists():
                raise GraphQLError("Biller with this name already exists.")
            biller.name = input["name"]

        if input.get("slug"):
            if Biller.objects.filter(slug=input["slug"]).exclude(pk=biller.pk).exists():
                raise GraphQLError("Biller with this slug already exists.")
            biller.slug = input["slug"]

        if input.get("category_id"):
            biller.category = _by_gid(
                input["category_id"], BillCategory, "Category"
            )

        if input.get("code"):
            if Biller.objects.filter(code=input["code"]).exclude(pk=biller.pk).exists():
                raise GraphQLError("Biller with this code already exists.")
            biller.code = input["code"]

        if input.get("description") is not None:
            biller.description = input["description"]
        if input.get("api_endpoint") is not None:
            biller.api_endpoint = input["api_endpoint"]
        if input.get("api_key") is not None:
            biller.api_key = input["api_key"]
        if input.get("webhook_url") is not None:
            biller.webhook_url = input["webhook_url"]

        if input.get("fee_percentage") is not None:
            biller.fee_percentage = Decimal(input["fee_percentage"])
        if input.get("fee_fixed") is not None:
            biller.fee_fixed = Decimal(input["fee_fixed"])
        if input.get("min_amount") is not None:
            biller.min_amount = Decimal(input["min_amount"])
        if input.get("max_amount") is not None:
            biller.max_amount = (
                Decimal(input["max_amount"]) if input["max_amount"] else None
            )

        if input.get("is_active") is not None:
            biller.is_active = input["is_active"]

        biller.save()

        return cls(biller=biller, success=True, message="Biller updated.")


class DeleteBillerMutation(relay.ClientIDMutation):
    """Delete a biller. Staff only. Refused if payments reference it."""

    class Input:
        biller_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)
        _staff(user)

        biller = _by_gid(input["biller_id"], Biller, "Biller")

        if biller.payments.exists():
            raise GraphQLError("Cannot delete a biller with existing payments.")

        biller.delete()

        return cls(success=True, message="Biller deleted.")


# ============================================================================
# BILL PROVIDER MUTATIONS (staff only)
# ============================================================================

class CreateBillProviderMutation(relay.ClientIDMutation):
    """Create a bill provider. Staff only."""

    class Input:
        name = String(required=True)
        provider_type = String(required=True)
        provider_code = String(required=True)
        is_active = Boolean()
        api_endpoint = String()
        api_key = String()
        validation_required = Boolean()
        supports_auto_debit = Boolean()
        supports_one_time_payment = Boolean()
        service_states = GenericScalar()
        service_cities = GenericScalar()

    bill_provider = Field(BillProviderNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)
        _staff(user)

        valid_types = [c[0] for c in BillProvider.PROVIDER_TYPES]
        if input["provider_type"] not in valid_types:
            raise GraphQLError(
                f"Invalid provider_type. Must be one of: {', '.join(valid_types)}"
            )

        if BillProvider.objects.filter(provider_code=input["provider_code"]).exists():
            raise GraphQLError("Provider with this code already exists.")

        provider = _wrap(
            BillProvider.objects.create,
            name=input["name"],
            provider_type=input["provider_type"],
            provider_code=input["provider_code"],
            is_active=input.get("is_active", True),
            api_endpoint=input.get("api_endpoint", ""),
            api_key=input.get("api_key", ""),
            validation_required=input.get("validation_required", True),
            supports_auto_debit=input.get("supports_auto_debit", False),
            supports_one_time_payment=input.get("supports_one_time_payment", True),
            service_states=input.get("service_states", []),
            service_cities=input.get("service_cities", []),
        )

        return cls(
            bill_provider=provider,
            success=True,
            message="Bill provider created.",
        )


class UpdateBillProviderMutation(relay.ClientIDMutation):
    """Update a bill provider. Staff only."""

    class Input:
        bill_provider_id = ID(required=True)
        name = String()
        provider_type = String()
        provider_code = String()
        is_active = Boolean()
        api_endpoint = String()
        api_key = String()
        validation_required = Boolean()
        supports_auto_debit = Boolean()
        supports_one_time_payment = Boolean()
        service_states = GenericScalar()
        service_cities = GenericScalar()

    bill_provider = Field(BillProviderNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)
        _staff(user)

        provider = _by_gid(
            input["bill_provider_id"], BillProvider, "Bill provider"
        )

        if input.get("name"):
            provider.name = input["name"]
        if input.get("provider_type"):
            valid = [c[0] for c in BillProvider.PROVIDER_TYPES]
            if input["provider_type"] not in valid:
                raise GraphQLError("Invalid provider_type.")
            provider.provider_type = input["provider_type"]
        if input.get("provider_code"):
            if BillProvider.objects.filter(provider_code=input["provider_code"]).exclude(pk=provider.pk).exists():
                raise GraphQLError("Provider with this code already exists.")
            provider.provider_code = input["provider_code"]
        if input.get("is_active") is not None:
            provider.is_active = input["is_active"]
        if input.get("api_endpoint") is not None:
            provider.api_endpoint = input["api_endpoint"]
        if input.get("api_key") is not None:
            provider.api_key = input["api_key"]
        if input.get("validation_required") is not None:
            provider.validation_required = input["validation_required"]
        if input.get("supports_auto_debit") is not None:
            provider.supports_auto_debit = input["supports_auto_debit"]
        if input.get("supports_one_time_payment") is not None:
            provider.supports_one_time_payment = input["supports_one_time_payment"]
        if input.get("service_states") is not None:
            provider.service_states = input["service_states"]
        if input.get("service_cities") is not None:
            provider.service_cities = input["service_cities"]

        provider.save()

        return cls(
            bill_provider=provider,
            success=True,
            message="Bill provider updated.",
        )


class DeleteBillProviderMutation(relay.ClientIDMutation):
    """Delete a bill provider. Staff only. Refused if accounts reference it."""

    class Input:
        bill_provider_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)
        _staff(user)

        provider = _by_gid(
            input["bill_provider_id"], BillProvider, "Bill provider"
        )

        if provider.billaccount_set.exists():
            raise GraphQLError(
                "Cannot delete a provider with existing bill accounts."
            )

        provider.delete()

        return cls(success=True, message="Bill provider deleted.")


# ============================================================================
# BILL ACCOUNT MUTATIONS (owner-scoped)
# ============================================================================

class CreateBillAccountMutation(relay.ClientIDMutation):
    """Create a bill account for the current user."""

    class Input:
        provider_id = ID(required=True)
        account_number = String(required=True)
        account_name = String(required=True)
        customer_name = String()
        address = String()
        state = String(required=True)
        city = String(required=True)
        auto_pay_enabled = Boolean()
        auto_pay_threshold = GrapheneDecimal()
        auto_pay_source_account_id = ID()

    bill_account = Field(BillAccountNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)

        provider = _by_gid(
            input["provider_id"], BillProvider, "Bill provider"
        )

        if BillAccount.objects.filter(
            user=user,
            provider=provider,
            account_number=input["account_number"],
        ).exists():
            raise GraphQLError(
                "Bill account already exists for this user and provider."
            )

        source_account = None
        if input.get("auto_pay_source_account_id"):
            source_account = _by_gid(
                input["auto_pay_source_account_id"], Account, "Source account"
            )
            if source_account.user_id != user.pk:
                raise GraphQLError("Source account does not belong to you.")

        bill_account = _wrap(
            BillAccount.objects.create,
            user=user,
            provider=provider,
            account_number=input["account_number"],
            account_name=input["account_name"],
            customer_name=input.get("customer_name", ""),
            address=input.get("address", ""),
            state=input["state"],
            city=input["city"],
            auto_pay_enabled=input.get("auto_pay_enabled", False),
            auto_pay_threshold=Decimal(input.get("auto_pay_threshold", "0.00")),
            auto_pay_source_account=source_account,
            is_validated=False,
        )

        return cls(
            bill_account=bill_account,
            success=True,
            message="Bill account created.",
        )


class UpdateBillAccountMutation(relay.ClientIDMutation):
    """Update a bill account owned by the current user."""

    class Input:
        bill_account_id = ID(required=True)
        account_name = String()
        customer_name = String()
        address = String()
        state = String()
        city = String()
        auto_pay_enabled = Boolean()
        auto_pay_threshold = GrapheneDecimal()
        auto_pay_source_account_id = ID()
        is_validated = Boolean()

    bill_account = Field(BillAccountNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)

        bill_account = _by_gid(
            input["bill_account_id"], BillAccount, "Bill account"
        )
        _owner(user, bill_account, "bill account")

        if input.get("account_name"):
            bill_account.account_name = input["account_name"]
        if input.get("customer_name") is not None:
            bill_account.customer_name = input["customer_name"]
        if input.get("address") is not None:
            bill_account.address = input["address"]
        if input.get("state"):
            bill_account.state = input["state"]
        if input.get("city"):
            bill_account.city = input["city"]
        if input.get("auto_pay_enabled") is not None:
            bill_account.auto_pay_enabled = input["auto_pay_enabled"]
        if input.get("auto_pay_threshold") is not None:
            bill_account.auto_pay_threshold = Decimal(input["auto_pay_threshold"])
        if input.get("auto_pay_source_account_id"):
            source = _by_gid(
                input["auto_pay_source_account_id"], Account, "Source account"
            )
            if source.user_id != user.pk:
                raise GraphQLError("Source account does not belong to you.")
            bill_account.auto_pay_source_account = source

        if input.get("is_validated") is not None:
            _staff(user)
            bill_account.is_validated = input["is_validated"]
            if input["is_validated"]:
                bill_account.validated_at = timezone.now()

        bill_account.save()

        return cls(
            bill_account=bill_account,
            success=True,
            message="Bill account updated.",
        )


class DeleteBillAccountMutation(relay.ClientIDMutation):
    """Delete a bill account owned by the current user."""

    class Input:
        bill_account_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)

        bill_account = _by_gid(
            input["bill_account_id"], BillAccount, "Bill account"
        )
        _owner(user, bill_account, "bill account")

        if bill_account.bill_set.exists():
            raise GraphQLError(
                "Cannot delete a bill account with existing bills."
            )

        bill_account.delete()

        return cls(success=True, message="Bill account deleted.")


# ============================================================================
# BILL MUTATIONS (owner-scoped)
# ============================================================================

class CreateBillMutation(relay.ClientIDMutation):
    """Create a bill instance."""

    class Input:
        bill_account_id = ID(required=True)
        billing_period_start = String(required=True)
        billing_period_end = String(required=True)
        due_date = String(required=True)
        total_amount = GrapheneDecimal(required=True)
        provider_reference = String()
        breakdown = GenericScalar()

    bill = Field(BillNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)

        bill_account = _by_gid(
            input["bill_account_id"], BillAccount, "Bill account"
        )
        _owner(user, bill_account, "bill account")

        start = _parse_date(input["billing_period_start"])
        end = _parse_date(input["billing_period_end"])
        due = _parse_date(input["due_date"])

        if not (start and end and due):
            raise GraphQLError("Billing period and due date are required.")
        if start > end:
            raise GraphQLError("Billing period start cannot be after end.")
        if due < end:
            raise GraphQLError("Due date cannot be before billing period end.")

        total_amount = Decimal(str(input["total_amount"]))

        bill = _wrap(
            Bill.objects.create,
            bill_account=bill_account,
            billing_period_start=start,
            billing_period_end=end,
            due_date=due,
            total_amount=total_amount,
            provider_reference=input.get("provider_reference", ""),
            breakdown=input.get("breakdown", {}),
            status="PENDING",
        )

        return cls(bill=bill, success=True, message="Bill created.")


class UpdateBillMutation(relay.ClientIDMutation):
    """Update a bill owned by the current user."""

    class Input:
        bill_id = ID(required=True)
        total_amount = GrapheneDecimal()
        due_date = String()
        breakdown = GenericScalar()
        status = String()
        payment_reference = String()

    bill = Field(BillNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)

        bill = _by_gid(input["bill_id"], Bill, "Bill")
        _owner(user, bill.bill_account, "bill account")

        if input.get("total_amount"):
            bill.total_amount = Decimal(str(input["total_amount"]))

        if input.get("due_date"):
            bill.due_date = _parse_date(input["due_date"])

        if input.get("breakdown") is not None:
            bill.breakdown = input["breakdown"]

        if input.get("status"):
            valid = [c[0] for c in Bill.BILL_STATUS]
            if input["status"] not in valid:
                raise GraphQLError("Invalid status.")
            bill.status = input["status"]
            if input["status"] == "PAID":
                bill.paid_at = timezone.now()

        if input.get("payment_reference") is not None:
            bill.payment_reference = input["payment_reference"]

        bill.save()

        return cls(bill=bill, success=True, message="Bill updated.")


class DeleteBillMutation(relay.ClientIDMutation):
    """Delete a bill owned by the current user."""

    class Input:
        bill_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)

        bill = _by_gid(input["bill_id"], Bill, "Bill")
        _owner(user, bill.bill_account, "bill account")

        if bill.status == "PAID":
            raise GraphQLError("Cannot delete a paid bill.")

        bill.delete()

        return cls(success=True, message="Bill deleted.")


# ============================================================================
# BILL PAYMENT MUTATIONS (money movement)
# ============================================================================

class CreateBillPaymentMutation(relay.ClientIDMutation):
    """
    Pay a bill.

    Delegates to BillPaymentService.pay_bill, which posts the
    principal journal and (if applicable) the fee journal, and
    creates the BillPayment row atomically.
    """

    class Input:
        source_account_id = ID(required=True)
        biller_id = ID(required=True)
        amount = GrapheneDecimal(required=True)
        customer_id = String(required=True)
        customer_name = String()
        customer_email = String()
        customer_phone = String()
        bill_type = String()
        reference = String()
        metadata = GenericScalar()

    bill_payment = Field(BillPaymentNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)

        source_account = _by_gid(
            input["source_account_id"], Account, "Source account"
        )
        biller = _by_gid(input["biller_id"], Biller, "Biller")

        bill_type = input.get("bill_type", "other")
        valid_types = [c[0] for c in BillPayment.BILL_TYPES]
        if bill_type not in valid_types:
            raise GraphQLError(
                f"Invalid bill_type. Must be one of: {', '.join(valid_types)}"
            )

        service = BillPaymentService()
        payment = _wrap(
            service.pay_bill,
            user=user,
            source_account=source_account,
            biller=biller,
            amount=Decimal(str(input["amount"])),
            customer_id=input["customer_id"],
            customer_name=input.get("customer_name", ""),
            customer_email=input.get("customer_email", ""),
            customer_phone=input.get("customer_phone", ""),
            bill_type=bill_type,
            reference=input.get("reference"),
            metadata=input.get("metadata") or {},
        )

        return cls(
            bill_payment=payment,
            success=True,
            message="Bill payment successful.",
        )


class CreateAirtimePurchaseMutation(relay.ClientIDMutation):
    """
    Purchase airtime.

    Delegates to BillPaymentService.purchase_airtime.
    """

    class Input:
        source_account_id = ID(required=True)
        operator = String(required=True)
        phone_number = String(required=True)
        amount = GrapheneDecimal(required=True)
        reference = String()
        metadata = GenericScalar()

    airtime_purchase = Field(AirtimePurchaseNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)

        source_account = _by_gid(
            input["source_account_id"], Account, "Source account"
        )

        service = BillPaymentService()
        purchase = _wrap(
            service.purchase_airtime,
            user=user,
            source_account=source_account,
            operator=input["operator"],
            phone_number=input["phone_number"],
            amount=Decimal(str(input["amount"])),
            reference=input.get("reference"),
            metadata=input.get("metadata") or {},
        )

        return cls(
            airtime_purchase=purchase,
            success=True,
            message="Airtime purchase successful.",
        )


class CreateDataBundlePurchaseMutation(relay.ClientIDMutation):
    """
    Purchase a data bundle.

    Delegates to BillPaymentService.purchase_data_bundle.
    """

    class Input:
        source_account_id = ID(required=True)
        operator = String(required=True)
        phone_number = String(required=True)
        bundle_name = String(required=True)
        data_amount = String(required=True)
        data_type = String(required=True)
        price = GrapheneDecimal(required=True)
        validity_days = Int(required=True)
        reference = String()
        metadata = GenericScalar()

    data_bundle_purchase = Field(DataBundlePurchaseNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)

        source_account = _by_gid(
            input["source_account_id"], Account, "Source account"
        )

        service = BillPaymentService()
        purchase = _wrap(
            service.purchase_data_bundle,
            user=user,
            source_account=source_account,
            operator=input["operator"],
            phone_number=input["phone_number"],
            bundle_name=input["bundle_name"],
            data_amount=input["data_amount"],
            data_type=input["data_type"],
            price=Decimal(str(input["price"])),
            validity_days=input["validity_days"],
            reference=input.get("reference"),
            metadata=input.get("metadata") or {},
        )

        return cls(
            data_bundle_purchase=purchase,
            success=True,
            message="Data bundle purchase successful.",
        )


# ============================================================================
# RETRY MUTATIONS (no money movement — status only)
# ============================================================================

class RetryBillPaymentMutation(relay.ClientIDMutation):
    """
    Reset a failed bill payment to PENDING for retry.

    Does NOT move money. A separate `createBillPayment` call will
    perform the actual money movement.
    """

    class Input:
        bill_payment_id = ID(required=True)

    bill_payment = Field(BillPaymentNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)

        payment = _by_gid(
            input["bill_payment_id"], BillPayment, "Bill payment"
        )
        _owner(user, payment, "bill payment")

        if payment.status not in (BillPayment.FAILED, BillPayment.CANCELLED):
            raise GraphQLError(
                "Only failed or cancelled payments can be retried."
            )
        if payment.retry_count >= 3:
            raise GraphQLError("Maximum retry attempts reached.")

        payment.retry_count += 1
        payment.last_retry_at = timezone.now()
        payment.status = BillPayment.PENDING
        payment.status_reason = "Queued for retry."
        payment.save(update_fields=[
            "retry_count", "last_retry_at", "status",
            "status_reason", "updated_at",
        ])

        return cls(
            bill_payment=payment,
            success=True,
            message="Bill payment queued for retry.",
        )


class RetryAirtimePurchaseMutation(relay.ClientIDMutation):
    """Reset a failed airtime purchase to PENDING for retry."""

    class Input:
        airtime_purchase_id = ID(required=True)

    airtime_purchase = Field(AirtimePurchaseNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _user(info)

        purchase = _by_gid(
            input["airtime_purchase_id"], AirtimePurchase, "Airtime purchase"
        )
        _owner(user, purchase, "airtime purchase")

        if purchase.status not in (
            AirtimePurchase.FAILED,
            AirtimePurchase.CANCELLED,
        ):
            raise GraphQLError(
                "Only failed or cancelled purchases can be retried."
            )
        if purchase.retry_count >= 3:
            raise GraphQLError("Maximum retry attempts reached.")

        purchase.retry_count += 1
        purchase.last_retry_at = timezone.now()
        purchase.status = AirtimePurchase.PENDING
        purchase.status_reason = "Queued for retry."
        purchase.save(update_fields=[
            "retry_count", "last_retry_at", "status",
            "status_reason", "updated_at",
        ])

        return cls(
            airtime_purchase=purchase,
            success=True,
            message="Airtime purchase queued for retry.",
        )


# ============================================================================
# MUTATION REGISTRY
# ============================================================================

class BillPaymentMutations(graphene.ObjectType):
    # Bill Category (staff)
    create_bill_category = CreateBillCategoryMutation.Field()
    update_bill_category = UpdateBillCategoryMutation.Field()
    delete_bill_category = DeleteBillCategoryMutation.Field()

    # Biller (staff)
    create_biller = CreateBillerMutation.Field()
    update_biller = UpdateBillerMutation.Field()
    delete_biller = DeleteBillerMutation.Field()

    # Bill Provider (staff)
    create_bill_provider = CreateBillProviderMutation.Field()
    update_bill_provider = UpdateBillProviderMutation.Field()
    delete_bill_provider = DeleteBillProviderMutation.Field()

    # Bill Account (owner)
    create_bill_account = CreateBillAccountMutation.Field()
    update_bill_account = UpdateBillAccountMutation.Field()
    delete_bill_account = DeleteBillAccountMutation.Field()

    # Bill (owner)
    create_bill = CreateBillMutation.Field()
    update_bill = UpdateBillMutation.Field()
    delete_bill = DeleteBillMutation.Field()

    # Bill Payment (money movement)
    create_bill_payment = CreateBillPaymentMutation.Field()
    retry_bill_payment = RetryBillPaymentMutation.Field()

    # Airtime Purchase (money movement)
    create_airtime_purchase = CreateAirtimePurchaseMutation.Field()
    retry_airtime_purchase = RetryAirtimePurchaseMutation.Field()

    # Data Bundle Purchase (money movement)
    create_data_bundle_purchase = CreateDataBundlePurchaseMutation.Field()


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "CreateBillCategoryMutation",
    "UpdateBillCategoryMutation",
    "DeleteBillCategoryMutation",
    "CreateBillerMutation",
    "UpdateBillerMutation",
    "DeleteBillerMutation",
    "CreateBillProviderMutation",
    "UpdateBillProviderMutation",
    "DeleteBillProviderMutation",
    "CreateBillAccountMutation",
    "UpdateBillAccountMutation",
    "DeleteBillAccountMutation",
    "CreateBillMutation",
    "UpdateBillMutation",
    "DeleteBillMutation",
    "CreateBillPaymentMutation",
    "RetryBillPaymentMutation",
    "CreateAirtimePurchaseMutation",
    "RetryAirtimePurchaseMutation",
    "CreateDataBundlePurchaseMutation",
    "BillPaymentMutations",
]