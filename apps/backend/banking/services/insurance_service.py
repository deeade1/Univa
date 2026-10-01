# apps/backend/banking/services/insurance_service.py

"""
Insurance service.

Orchestrates insurance policy purchase and claim payout.

Money movement
--------------

    premium purchase:  customer_account -> SUSPENSE  (premium_amount)
    claim payout:      SUSPENSE -> customer_account  (paid_amount)

SUSPENSE carries the funds between the two legs. In a production
Nigerian insurtech, a per-provider settlement account would replace
SUSPENSE for clearer per-insurer accounting. That refinement can be
introduced by swapping the SUSPENSE account reference here without
touching callers.

Every money movement posts through:

    banking.models.accounting.AccountingManager.create_double_entry
"""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from django.utils import timezone

from banking.models.accounting import AccountingJournal, AccountingManager
from banking.models.core import Account
from banking.models.insurance import (
    InsuranceClaim,
    InsurancePolicy,
    InsuranceProduct,
)
from banking.models.payments import Transaction


logger = logging.getLogger(__name__)

MONEY_QUANTUM = Decimal("0.01")


class InsuranceService:

    # ------------------------------------------------------------------
    # PURCHASE
    # ------------------------------------------------------------------

    @staticmethod
    @db_transaction.atomic
    def purchase_policy(
        *,
        user,
        product: InsuranceProduct,
        source_account: Account,
        coverage_amount,
        tenure_months: int,
        start_date=None,
        beneficiary_name: str = "",
        beneficiary_relationship: str = "",
        beneficiary_phone: str = "",
        additional_info: dict | None = None,
    ) -> InsurancePolicy:
        """
        Purchase an insurance policy.

        Computes the premium server-side from the product's pricing
        rules. Posts:

            customer_account -> SUSPENSE  (premium_amount)

        Returns the persisted InsurancePolicy with the journal linked.
        """
        # --------------------------------------------------------------
        # Basic validation
        # --------------------------------------------------------------
        if user is None or user.pk is None:
            raise ValidationError("User is required.")

        if product is None or product.pk is None:
            raise ValidationError("Insurance product is required.")

        if not product.is_active:
            raise ValidationError("Product is not active.")

        if source_account is None or source_account.pk is None:
            raise ValidationError("Source account is required.")

        if source_account.user_id != user.pk:
            raise ValidationError(
                "Source account does not belong to this user."
            )

        if source_account.is_system_account:
            raise ValidationError(
                "Source account cannot be a system account."
            )

        if source_account.status != Account.STATUS_ACTIVE:
            raise ValidationError("Source account is not active.")

        # --------------------------------------------------------------
        # Coverage validation
        #
        # Product fields are coerced through Decimal(str(...)) so a
        # freshly-created, in-memory product instance with string
        # defaults does not raise TypeError on comparison.
        # --------------------------------------------------------------
        coverage_amount = InsuranceService._validate_amount(coverage_amount)

        product_min = Decimal(str(product.coverage_amount_min)).quantize(
            MONEY_QUANTUM
        )
        product_max = Decimal(str(product.coverage_amount_max)).quantize(
            MONEY_QUANTUM
        )

        if coverage_amount < product_min:
            raise ValidationError(
                f"Coverage amount is below the product minimum of "
                f"{product_min}."
            )

        if coverage_amount > product_max:
            raise ValidationError(
                f"Coverage amount exceeds the product maximum of "
                f"{product_max}."
            )

        # --------------------------------------------------------------
        # Tenure validation
        # --------------------------------------------------------------
        try:
            tenure_months = int(tenure_months)
        except (TypeError, ValueError) as exc:
            raise ValidationError("Invalid tenure.") from exc

        try:
            min_tenure = int(product.min_tenure_months)
            max_tenure = int(product.max_tenure_months)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                "Product tenure configuration is invalid."
            ) from exc

        if not (min_tenure <= tenure_months <= max_tenure):
            raise ValidationError(
                f"Tenure must be between {min_tenure} and "
                f"{max_tenure} months."
            )

        # --------------------------------------------------------------
        # Start date
        #
        # Only enforce "not in the past" when the caller supplied an
        # explicit date. The default path uses timezone.now() and would
        # otherwise reject itself on the microsecond-scale clock drift
        # between the two calls.
        # --------------------------------------------------------------
        if start_date is None:
            start_date = timezone.now()
        elif start_date < timezone.now():
            raise ValidationError("Start date cannot be in the past.")
        
        end_date = start_date + timezone.timedelta(days=tenure_months * 30)
        renewal_date = end_date - timezone.timedelta(days=30)

        # --------------------------------------------------------------
        # Server-side premium
        # --------------------------------------------------------------
        premium_amount = product.calculate_premium(
            coverage_amount=coverage_amount,
            tenure_months=tenure_months,
        )

        if source_account.get_balance() < premium_amount:
            raise ValidationError("Insufficient funds in source account.")

        # --------------------------------------------------------------
        # Journal: customer -> SUSPENSE
        # --------------------------------------------------------------
        suspense_account = AccountingManager.get_suspense_account()

        policy_number = (
            f"POL-{product.provider.code}-"
            f"{timezone.now().strftime('%Y%m')}-"
            f"{uuid.uuid4().hex[:6].upper()}"
        )

        principal_txn = Transaction.objects.create(
            account=source_account,
            amount=premium_amount,
            type=Transaction.TRANSFER,
            narration=(
                f"Insurance premium: {product.provider.name} "
                f"{product.name}"
            ),
            recipient_name=product.provider.name,
            recipient_account_number="",
            status=Transaction.PENDING,
        )

        journal = AccountingManager.create_double_entry(
            transaction=principal_txn,
            debit_account=source_account,
            credit_account=suspense_account,
            amount=premium_amount,
            description=(
                f"Insurance premium {policy_number}: "
                f"{product.provider.name} - {product.name}"
            ),
            journal_type=AccountingJournal.TRANSFER,
            created_by=user,
        )

        principal_txn.journal = journal
        principal_txn.status = Transaction.SUCCESS
        principal_txn.balance_after = source_account.get_balance()
        principal_txn.save(update_fields=[
            "journal", "status", "balance_after", "updated_at",
        ])

        # --------------------------------------------------------------
        # Business record
        # --------------------------------------------------------------
        policy = InsurancePolicy.objects.create(
            user=user,
            product=product,
            policy_number=policy_number,
            coverage_amount=coverage_amount,
            premium_amount=premium_amount,
            tenure_months=tenure_months,
            start_date=start_date,
            end_date=end_date,
            renewal_date=renewal_date,
            beneficiary_name=beneficiary_name,
            beneficiary_relationship=beneficiary_relationship,
            beneficiary_phone=beneficiary_phone,
            status="ACTIVE",
            journal=journal,
            additional_info=additional_info or {},
        )

        logger.info(
            "Insurance policy %s purchased: user=%s provider=%s "
            "coverage=%s premium=%s journal=%s",
            policy.policy_number,
            user.pk,
            product.provider.pk,
            coverage_amount,
            premium_amount,
            journal.pk,
        )

        return policy

    # ------------------------------------------------------------------
    # PAY CLAIM
    # ------------------------------------------------------------------

    @staticmethod
    @db_transaction.atomic
    def pay_claim(
        *,
        claim: InsuranceClaim,
        destination_account: Account,
        provider_reference: str = "",
    ) -> InsuranceClaim:
        """
        Pay an approved insurance claim.

        Posts:

            SUSPENSE -> destination_account  (approved_amount)

        `destination_account` must be the policy holder's account (or
        the beneficiary's account, at the caller's discretion — the
        service does not enforce beneficiary ownership beyond
        requiring an active customer account).
        """
        if claim is None or claim.pk is None:
            raise ValidationError("Claim is required.")

        if claim.status != "APPROVED":
            raise ValidationError(
                "Only approved claims can be paid."
            )

        if claim.paid_amount and claim.paid_amount > Decimal("0.00"):
            raise ValidationError("Claim has already been paid.")

        if destination_account is None or destination_account.pk is None:
            raise ValidationError("Destination account is required.")

        if destination_account.is_system_account:
            raise ValidationError(
                "Destination account cannot be a system account."
            )

        if destination_account.status != Account.STATUS_ACTIVE:
            raise ValidationError("Destination account is not active.")

        payout_amount = (
            claim.approved_amount
            if claim.approved_amount is not None
            else claim.claim_amount
        )

        payout_amount = InsuranceService._validate_amount(payout_amount)

        # --------------------------------------------------------------
        # Journal: SUSPENSE -> destination
        # --------------------------------------------------------------
        suspense_account = AccountingManager.get_suspense_account()

        payout_txn = Transaction.objects.create(
            account=suspense_account,
            amount=payout_amount,
            type=Transaction.TRANSFER,
            narration=(
                f"Insurance claim payout: {claim.claim_number}"
            ),
            recipient_name=(
                claim.user.get_full_name() or claim.user.email
            ),
            recipient_account_number=destination_account.nuban_number,
            status=Transaction.PENDING,
        )

        journal = AccountingManager.create_double_entry(
            transaction=payout_txn,
            debit_account=suspense_account,
            credit_account=destination_account,
            amount=payout_amount,
            description=(
                f"Insurance claim payout {claim.claim_number}: "
                f"{claim.policy.policy_number}"
            ),
            journal_type=AccountingJournal.TRANSFER,
            created_by=claim.user,
        )

        payout_txn.journal = journal
        payout_txn.status = Transaction.SUCCESS
        payout_txn.balance_after = suspense_account.get_balance()
        payout_txn.save(update_fields=[
            "journal", "status", "balance_after", "updated_at",
        ])

        # --------------------------------------------------------------
        # Business record
        # --------------------------------------------------------------
        claim.status = "PAID"
        claim.paid_amount = payout_amount
        claim.paid_at = timezone.now()
        claim.journal = journal
        if provider_reference:
            claim.provider_reference = provider_reference
        claim.save(update_fields=[
            "status", "paid_amount", "paid_at", "journal",
            "provider_reference", "updated_at",
        ])

        logger.info(
            "Insurance claim %s paid: policy=%s amount=%s "
            "destination=%s journal=%s",
            claim.claim_number,
            claim.policy.policy_number,
            payout_amount,
            destination_account.pk,
            journal.pk,
        )

        return claim

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_amount(amount) -> Decimal:
        if amount is None:
            raise ValidationError("Amount is required.")
        try:
            value = Decimal(str(amount))
        except (TypeError, ValueError, ArithmeticError) as exc:
            raise ValidationError("Invalid amount.") from exc
        if not value.is_finite():
            raise ValidationError("Amount must be finite.")
        if value <= Decimal("0.00"):
            raise ValidationError("Amount must be greater than zero.")
        return value.quantize(MONEY_QUANTUM)