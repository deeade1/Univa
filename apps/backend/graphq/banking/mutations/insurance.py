# apps/backend/graphq/banking/mutations/insurance.py

"""
GraphQL mutations for Banking insurance models.

This module contains mutations for:
    - InsuranceProvider: Insurance companies
    - InsuranceProduct: Insurance products offered
    - InsurancePolicy: User's insurance policies
    - InsuranceClaim: Insurance claims filed by users

Money movement
--------------

PurchaseInsurancePolicyMutation and PayInsuranceClaimMutation delegate
to:

    banking.services.insurance_service.InsuranceService

which posts through:

    banking.models.accounting.AccountingManager.create_double_entry

Every other mutation in this module is metadata CRUD and does not
move money. Premiums are computed server-side from the product's
pricing rules — the client never supplies a premium.
"""

import logging
from decimal import Decimal
from datetime import datetime, timedelta
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

from banking.models.core import Account
from banking.models.insurance import (
    InsuranceProvider,
    InsuranceProduct,
    InsurancePolicy,
    InsuranceClaim,
)
from banking.models.payments import Transaction
from banking.services.insurance_service import InsuranceService
from graphq.accounts.types.user import UserNode
from graphq.banking.types.insurance import (
    InsuranceProviderNode,
    InsuranceProductNode,
    InsurancePolicyNode,
    InsuranceClaimNode,
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
# INSURANCE PROVIDER MUTATIONS
# ============================================================================

class CreateInsuranceProviderMutation(relay.ClientIDMutation):
    """Create an insurance provider."""

    class Input:
        name = String(required=True)
        code = String(required=True)
        website = String()
        phone = String()
        email = String()
        is_active = Boolean()

    provider = Field(InsuranceProviderNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        if InsuranceProvider.objects.filter(name=input["name"]).exists():
            raise GraphQLError("Provider with this name already exists.")
        if InsuranceProvider.objects.filter(code=input["code"]).exists():
            raise GraphQLError("Provider with this code already exists.")

        try:
            provider = InsuranceProvider.objects.create(
                name=input["name"],
                code=input["code"],
                website=input.get("website", ""),
                phone=input.get("phone", ""),
                email=input.get("email", ""),
                is_active=input.get("is_active", True),
            )
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            provider=provider,
            success=True,
            message="Insurance provider created successfully.",
        )


class UpdateInsuranceProviderMutation(relay.ClientIDMutation):
    """Update an insurance provider."""

    class Input:
        provider_id = ID(required=True)
        name = String()
        code = String()
        website = String()
        phone = String()
        email = String()
        is_active = Boolean()

    provider = Field(InsuranceProviderNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        provider = _get_model_by_global_id(
            input["provider_id"], InsuranceProvider, "Provider"
        )

        if input.get("name"):
            if (
                InsuranceProvider.objects
                .filter(name=input["name"])
                .exclude(pk=provider.pk)
                .exists()
            ):
                raise GraphQLError(
                    "Provider with this name already exists."
                )
            provider.name = input["name"]

        if input.get("code"):
            if (
                InsuranceProvider.objects
                .filter(code=input["code"])
                .exclude(pk=provider.pk)
                .exists()
            ):
                raise GraphQLError(
                    "Provider with this code already exists."
                )
            provider.code = input["code"]

        if input.get("website") is not None:
            provider.website = input["website"]

        if input.get("phone") is not None:
            provider.phone = input["phone"]

        if input.get("email") is not None:
            provider.email = input["email"]

        if input.get("is_active") is not None:
            provider.is_active = input["is_active"]

        try:
            provider.save()
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            provider=provider,
            success=True,
            message="Insurance provider updated successfully.",
        )


class DeleteInsuranceProviderMutation(relay.ClientIDMutation):
    """Delete an insurance provider."""

    class Input:
        provider_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        provider = _get_model_by_global_id(
            input["provider_id"], InsuranceProvider, "Provider"
        )

        if provider.products.exists():
            raise GraphQLError(
                "Cannot delete provider with existing products."
            )

        provider.delete()

        return cls(
            success=True,
            message="Insurance provider deleted successfully.",
        )


# ============================================================================
# INSURANCE PRODUCT MUTATIONS
# ============================================================================

class CreateInsuranceProductMutation(relay.ClientIDMutation):
    """Create an insurance product."""

    class Input:
        provider_id = ID(required=True)
        name = String(required=True)
        slug = String(required=True)
        insurance_type = String(required=True)
        description = String(required=True)
        coverage_details = GenericScalar()
        exclusions = GenericScalar()
        coverage_amount_min = GrapheneDecimal(required=True)
        coverage_amount_max = GrapheneDecimal(required=True)
        premium_min = GrapheneDecimal(required=True)
        premium_max = GrapheneDecimal(required=True)
        payment_frequency = String(required=True)
        min_tenure_months = Int(required=True)
        max_tenure_months = Int(required=True)
        default_tenure_months = Int(required=True)
        required_documents = GenericScalar()
        eligibility_criteria = GenericScalar()
        is_active = Boolean()

    product = Field(InsuranceProductNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        provider = _get_model_by_global_id(
            input["provider_id"], InsuranceProvider, "Provider"
        )

        valid_types = [
            choice[0] for choice in InsuranceProduct.INSURANCE_TYPES
        ]
        if input["insurance_type"] not in valid_types:
            raise GraphQLError(
                f"Invalid insurance type. Must be one of: "
                f"{', '.join(valid_types)}"
            )

        valid_frequencies = [
            choice[0] for choice in InsuranceProduct.PAYMENT_FREQUENCIES
        ]
        if input["payment_frequency"] not in valid_frequencies:
            raise GraphQLError("Invalid payment frequency.")

        coverage_amount_min = _validate_amount(input["coverage_amount_min"])
        coverage_amount_max = _validate_amount(input["coverage_amount_max"])
        premium_min = _validate_amount(input["premium_min"])
        premium_max = _validate_amount(input["premium_max"])

        if coverage_amount_min > coverage_amount_max:
            raise GraphQLError(
                "Minimum coverage cannot exceed maximum coverage."
            )
        if premium_min > premium_max:
            raise GraphQLError(
                "Minimum premium cannot exceed maximum premium."
            )

        if input["min_tenure_months"] > input["max_tenure_months"]:
            raise GraphQLError(
                "Minimum tenure cannot exceed maximum tenure."
            )
        if not (
            input["min_tenure_months"]
            <= input["default_tenure_months"]
            <= input["max_tenure_months"]
        ):
            raise GraphQLError(
                "Default tenure must be between min and max tenure."
            )

        if InsuranceProduct.objects.filter(slug=input["slug"]).exists():
            raise GraphQLError("Product with this slug already exists.")

        try:
            product = InsuranceProduct.objects.create(
                provider=provider,
                name=input["name"],
                slug=input["slug"],
                insurance_type=input["insurance_type"],
                description=input["description"],
                coverage_details=input.get("coverage_details", {}),
                exclusions=input.get("exclusions", []),
                coverage_amount_min=coverage_amount_min,
                coverage_amount_max=coverage_amount_max,
                premium_min=premium_min,
                premium_max=premium_max,
                payment_frequency=input["payment_frequency"],
                min_tenure_months=input["min_tenure_months"],
                max_tenure_months=input["max_tenure_months"],
                default_tenure_months=input["default_tenure_months"],
                required_documents=input.get("required_documents", []),
                eligibility_criteria=input.get("eligibility_criteria", {}),
                is_active=input.get("is_active", True),
            )
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            product=product,
            success=True,
            message="Insurance product created successfully.",
        )


class UpdateInsuranceProductMutation(relay.ClientIDMutation):
    """Update an insurance product."""

    class Input:
        product_id = ID(required=True)
        name = String()
        slug = String()
        insurance_type = String()
        description = String()
        coverage_details = GenericScalar()
        exclusions = GenericScalar()
        coverage_amount_min = GrapheneDecimal()
        coverage_amount_max = GrapheneDecimal()
        premium_min = GrapheneDecimal()
        premium_max = GrapheneDecimal()
        payment_frequency = String()
        min_tenure_months = Int()
        max_tenure_months = Int()
        default_tenure_months = Int()
        required_documents = GenericScalar()
        eligibility_criteria = GenericScalar()
        is_active = Boolean()

    product = Field(InsuranceProductNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        product = _get_model_by_global_id(
            input["product_id"], InsuranceProduct, "Product"
        )

        if input.get("name"):
            product.name = input["name"]

        if input.get("slug"):
            if (
                InsuranceProduct.objects
                .filter(slug=input["slug"])
                .exclude(pk=product.pk)
                .exists()
            ):
                raise GraphQLError("Product with this slug already exists.")
            product.slug = input["slug"]

        if input.get("insurance_type"):
            valid_types = [
                choice[0] for choice in InsuranceProduct.INSURANCE_TYPES
            ]
            if input["insurance_type"] not in valid_types:
                raise GraphQLError("Invalid insurance type.")
            product.insurance_type = input["insurance_type"]

        if input.get("description") is not None:
            product.description = input["description"]

        if input.get("coverage_details") is not None:
            product.coverage_details = input["coverage_details"]

        if input.get("exclusions") is not None:
            product.exclusions = input["exclusions"]

        if input.get("coverage_amount_min") is not None:
            product.coverage_amount_min = _validate_amount(
                input["coverage_amount_min"]
            )

        if input.get("coverage_amount_max") is not None:
            product.coverage_amount_max = _validate_amount(
                input["coverage_amount_max"]
            )

        if input.get("premium_min") is not None:
            product.premium_min = _validate_amount(input["premium_min"])

        if input.get("premium_max") is not None:
            product.premium_max = _validate_amount(input["premium_max"])

        if input.get("payment_frequency"):
            valid_frequencies = [
                choice[0]
                for choice in InsuranceProduct.PAYMENT_FREQUENCIES
            ]
            if input["payment_frequency"] not in valid_frequencies:
                raise GraphQLError("Invalid payment frequency.")
            product.payment_frequency = input["payment_frequency"]

        if input.get("min_tenure_months") is not None:
            product.min_tenure_months = input["min_tenure_months"]

        if input.get("max_tenure_months") is not None:
            product.max_tenure_months = input["max_tenure_months"]

        if input.get("default_tenure_months") is not None:
            product.default_tenure_months = input["default_tenure_months"]

        if input.get("required_documents") is not None:
            product.required_documents = input["required_documents"]

        if input.get("eligibility_criteria") is not None:
            product.eligibility_criteria = input["eligibility_criteria"]

        if input.get("is_active") is not None:
            product.is_active = input["is_active"]

        try:
            product.save()
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            product=product,
            success=True,
            message="Insurance product updated successfully.",
        )


class DeleteInsuranceProductMutation(relay.ClientIDMutation):
    """Delete an insurance product."""

    class Input:
        product_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        product = _get_model_by_global_id(
            input["product_id"], InsuranceProduct, "Product"
        )

        if product.policies.exists():
            raise GraphQLError(
                "Cannot delete product with existing policies."
            )

        product.delete()

        return cls(
            success=True,
            message="Insurance product deleted successfully.",
        )


# ============================================================================
# INSURANCE POLICY MUTATIONS
# ============================================================================

class PurchaseInsurancePolicyMutation(relay.ClientIDMutation):
    """
    Purchase an insurance policy.

    Delegates to InsuranceService.purchase_policy, which computes the
    premium server-side, posts the principal journal (customer ->
    SUSPENSE), and creates the InsurancePolicy row atomically.

    The premium is NOT accepted from the client. It is derived from
    the product's pricing rules so a client cannot buy a policy at
    an arbitrary price.
    """

    class Input:
        source_account_id = ID(required=True)
        product_id = ID(required=True)
        coverage_amount = GrapheneDecimal(required=True)
        tenure_months = Int(required=True)
        start_date = String()
        beneficiary_name = String()
        beneficiary_relationship = String()
        beneficiary_phone = String()
        additional_info = GenericScalar()

    policy = Field(InsurancePolicyNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        source_account = _get_model_by_global_id(
            input["source_account_id"], Account, "Source account"
        )
        if source_account.user_id != user.pk:
            raise GraphQLError("You do not own this account.")

        product = _get_model_by_global_id(
            input["product_id"], InsuranceProduct, "Product"
        )

        start_date = None
        if input.get("start_date"):
            start_date = _validate_datetime(input["start_date"])

        policy = _wrap(
            InsuranceService.purchase_policy,
            user=user,
            product=product,
            source_account=source_account,
            coverage_amount=input["coverage_amount"],
            tenure_months=input["tenure_months"],
            start_date=start_date,
            beneficiary_name=input.get("beneficiary_name", ""),
            beneficiary_relationship=input.get(
                "beneficiary_relationship", ""
            ),
            beneficiary_phone=input.get("beneficiary_phone", ""),
            additional_info=input.get("additional_info") or {},
        )

        return cls(
            policy=policy,
            success=True,
            message="Insurance policy purchased successfully.",
        )


class UpdateInsurancePolicyMutation(relay.ClientIDMutation):
    """Update an insurance policy (metadata only)."""

    class Input:
        policy_id = ID(required=True)
        beneficiary_name = String()
        beneficiary_relationship = String()
        beneficiary_phone = String()
        additional_info = GenericScalar()
        status = String()
        status_reason = String()

    policy = Field(InsurancePolicyNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        policy = _get_model_by_global_id(
            input["policy_id"], InsurancePolicy, "Policy"
        )

        if policy.user != user:
            raise GraphQLError("You do not own this policy.")

        if input.get("beneficiary_name") is not None:
            policy.beneficiary_name = input["beneficiary_name"]

        if input.get("beneficiary_relationship") is not None:
            policy.beneficiary_relationship = input[
                "beneficiary_relationship"
            ]

        if input.get("beneficiary_phone") is not None:
            policy.beneficiary_phone = input["beneficiary_phone"]

        if input.get("additional_info") is not None:
            policy.additional_info = input["additional_info"]

        if input.get("status"):
            valid_statuses = [
                choice[0] for choice in InsurancePolicy.STATUS_CHOICES
            ]
            if input["status"] not in valid_statuses:
                raise GraphQLError("Invalid status.")
            policy.status = input["status"]

        if input.get("status_reason") is not None:
            policy.status_reason = input["status_reason"]

        try:
            policy.save()
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            policy=policy,
            success=True,
            message="Insurance policy updated successfully.",
        )


class CancelInsurancePolicyMutation(relay.ClientIDMutation):
    """Cancel an insurance policy."""

    class Input:
        policy_id = ID(required=True)
        reason = String()

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        policy = _get_model_by_global_id(
            input["policy_id"], InsurancePolicy, "Policy"
        )

        if policy.user != user:
            raise GraphQLError("You do not own this policy.")

        if policy.status == "CANCELLED":
            raise GraphQLError("Policy is already cancelled.")

        if policy.status == "EXPIRED":
            raise GraphQLError("Cannot cancel an expired policy.")

        policy.status = "CANCELLED"
        policy.status_reason = input.get("reason", "Cancelled by user.")
        policy.save()

        return cls(
            success=True,
            message="Insurance policy cancelled successfully.",
        )


# ============================================================================
# INSURANCE CLAIM MUTATIONS
# ============================================================================

class FileInsuranceClaimMutation(relay.ClientIDMutation):
    """File an insurance claim."""

    class Input:
        policy_id = ID(required=True)
        claim_amount = GrapheneDecimal(required=True)
        incident_date = String(required=True)
        incident_description = String(required=True)
        incident_location = String()
        documents = GenericScalar()
        additional_info = GenericScalar()

    claim = Field(InsuranceClaimNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        policy = _get_model_by_global_id(
            input["policy_id"], InsurancePolicy, "Policy"
        )

        if policy.user != user:
            raise GraphQLError("You do not own this policy.")

        if policy.status != "ACTIVE":
            raise GraphQLError("Policy is not active.")

        claim_amount = _validate_amount(input["claim_amount"])
        if claim_amount > policy.coverage_amount:
            raise GraphQLError(
                f"Claim amount cannot exceed coverage amount of "
                f"{policy.coverage_amount}."
            )

        incident_date = _validate_datetime(input["incident_date"])
        if not incident_date:
            raise GraphQLError("Incident date is required.")
        if incident_date < policy.start_date or incident_date > timezone.now():
            raise GraphQLError(
                "Incident date must be within policy period and not "
                "in the future."
            )

        claim_number = (
            f"CLM-{policy.policy_number}-"
            f"{timezone.now().strftime('%Y%m%d')}-"
            f"{uuid.uuid4().hex[:4].upper()}"
        )

        try:
            claim = InsuranceClaim.objects.create(
                policy=policy,
                user=user,
                claim_number=claim_number,
                claim_amount=claim_amount,
                incident_date=incident_date,
                incident_description=input["incident_description"],
                incident_location=input.get("incident_location", ""),
                documents=input.get("documents", []),
                additional_info=input.get("additional_info", {}),
                status="PENDING",
            )
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            claim=claim,
            success=True,
            message="Insurance claim filed successfully.",
        )


class UpdateInsuranceClaimMutation(relay.ClientIDMutation):
    """Update an insurance claim (status and metadata)."""

    class Input:
        claim_id = ID(required=True)
        status = String()
        status_reason = String()
        reviewer_comments = String()
        approved_amount = GrapheneDecimal()
        provider_reference = String()

    claim = Field(InsuranceClaimNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        claim = _get_model_by_global_id(
            input["claim_id"], InsuranceClaim, "Claim"
        )

        if claim.user != user:
            raise GraphQLError("You do not own this claim.")

        if input.get("status"):
            valid_statuses = [
                choice[0] for choice in InsuranceClaim.STATUS_CHOICES
            ]
            if input["status"] not in valid_statuses:
                raise GraphQLError("Invalid status.")
            claim.status = input["status"]

            if input["status"] == "REVIEWING":
                claim.reviewed_at = timezone.now()
            elif input["status"] == "APPROVED":
                claim.approved_at = timezone.now()
            # PAID is handled by PayInsuranceClaimMutation.

        if input.get("status_reason") is not None:
            claim.status_reason = input["status_reason"]

        if input.get("reviewer_comments") is not None:
            claim.reviewer_comments = input["reviewer_comments"]

        if input.get("approved_amount") is not None:
            claim.approved_amount = Decimal(str(input["approved_amount"]))

        if input.get("provider_reference") is not None:
            claim.provider_reference = input["provider_reference"]

        try:
            claim.save()
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            claim=claim,
            success=True,
            message="Insurance claim updated successfully.",
        )


class ApproveInsuranceClaimMutation(relay.ClientIDMutation):
    """Approve an insurance claim."""

    class Input:
        claim_id = ID(required=True)
        approved_amount = GrapheneDecimal(required=True)
        reviewer_comments = String()

    claim = Field(InsuranceClaimNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        claim = _get_model_by_global_id(
            input["claim_id"], InsuranceClaim, "Claim"
        )

        if claim.user != user:
            raise GraphQLError("You do not own this claim.")

        if claim.status != "REVIEWING":
            raise GraphQLError(
                "Claim must be in REVIEWING status to approve."
            )

        approved_amount = _validate_amount(input["approved_amount"])
        if approved_amount > claim.claim_amount:
            raise GraphQLError(
                "Approved amount cannot exceed claim amount."
            )

        claim.status = "APPROVED"
        claim.approved_amount = approved_amount
        claim.approved_at = timezone.now()
        claim.reviewer_comments = input.get("reviewer_comments", "")
        claim.save()

        return cls(
            claim=claim,
            success=True,
            message="Insurance claim approved successfully.",
        )


class RejectInsuranceClaimMutation(relay.ClientIDMutation):
    """Reject an insurance claim."""

    class Input:
        claim_id = ID(required=True)
        reviewer_comments = String(required=True)
        status_reason = String()

    claim = Field(InsuranceClaimNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        claim = _get_model_by_global_id(
            input["claim_id"], InsuranceClaim, "Claim"
        )

        if claim.user != user:
            raise GraphQLError("You do not own this claim.")

        if claim.status != "REVIEWING":
            raise GraphQLError(
                "Claim must be in REVIEWING status to reject."
            )

        claim.status = "REJECTED"
        claim.reviewer_comments = input["reviewer_comments"]
        claim.status_reason = input.get("status_reason", "Claim rejected.")
        claim.reviewed_at = timezone.now()
        claim.save()

        return cls(
            claim=claim,
            success=True,
            message="Insurance claim rejected.",
        )


class PayInsuranceClaimMutation(relay.ClientIDMutation):
    """
    Pay an approved insurance claim.

    Delegates to InsuranceService.pay_claim, which posts the payout
    journal (SUSPENSE -> destination account) and marks the claim PAID.
    """

    class Input:
        claim_id = ID(required=True)
        destination_account_id = ID(required=True)
        provider_reference = String()

    claim = Field(InsuranceClaimNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        claim = _get_model_by_global_id(
            input["claim_id"], InsuranceClaim, "Claim"
        )
        destination_account = _get_model_by_global_id(
            input["destination_account_id"],
            Account,
            "Destination account",
        )

        claim = _wrap(
            InsuranceService.pay_claim,
            claim=claim,
            destination_account=destination_account,
            provider_reference=input.get("provider_reference", ""),
        )

        return cls(
            claim=claim,
            success=True,
            message="Insurance claim paid successfully.",
        )


# ============================================================================
# MUTATION REGISTRY
# ============================================================================

class InsuranceMutations(graphene.ObjectType):
    # Insurance Provider
    create_insurance_provider = CreateInsuranceProviderMutation.Field()
    update_insurance_provider = UpdateInsuranceProviderMutation.Field()
    delete_insurance_provider = DeleteInsuranceProviderMutation.Field()

    # Insurance Product
    create_insurance_product = CreateInsuranceProductMutation.Field()
    update_insurance_product = UpdateInsuranceProductMutation.Field()
    delete_insurance_product = DeleteInsuranceProductMutation.Field()

    # Insurance Policy
    purchase_insurance_policy = PurchaseInsurancePolicyMutation.Field()
    update_insurance_policy = UpdateInsurancePolicyMutation.Field()
    cancel_insurance_policy = CancelInsurancePolicyMutation.Field()

    # Insurance Claim
    file_insurance_claim = FileInsuranceClaimMutation.Field()
    update_insurance_claim = UpdateInsuranceClaimMutation.Field()
    approve_insurance_claim = ApproveInsuranceClaimMutation.Field()
    reject_insurance_claim = RejectInsuranceClaimMutation.Field()
    pay_insurance_claim = PayInsuranceClaimMutation.Field()


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "CreateInsuranceProviderMutation",
    "UpdateInsuranceProviderMutation",
    "DeleteInsuranceProviderMutation",
    "CreateInsuranceProductMutation",
    "UpdateInsuranceProductMutation",
    "DeleteInsuranceProductMutation",
    "PurchaseInsurancePolicyMutation",
    "UpdateInsurancePolicyMutation",
    "CancelInsurancePolicyMutation",
    "FileInsuranceClaimMutation",
    "UpdateInsuranceClaimMutation",
    "ApproveInsuranceClaimMutation",
    "RejectInsuranceClaimMutation",
    "PayInsuranceClaimMutation",
    "InsuranceMutations",
]