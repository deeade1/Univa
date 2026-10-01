# apps/backend/banking/services/bill_payment_service.py

"""
Bill payment, airtime, and data bundle orchestration service.

Every money movement flows through:

    BillPaymentService
        -> AccountingManager.create_double_entry
            -> AccountingJournal
            -> LedgerEntry (debit)
            -> LedgerEntry (credit)

Account model uses Univa's convention:

    balance = SUM(CREDIT) - SUM(DEBIT)
    DEBIT  decreases an account balance
    CREDIT increases an account balance

Journals posted by this service:

    bill payment:      source_account -> SUSPENSE  (principal)
                       source_account -> FEE       (fee, if any)
    airtime purchase:  source_account -> SUSPENSE  (principal)
                       source_account -> FEE       (fee, if any)
    data bundle:       source_account -> SUSPENSE  (principal)

Each business record carries `journal` and (where applicable)
`fee_journal` FKs so any record can be traced back to the ledger.

This service performs NO external provider HTTP calls. Actual
provider integration (biller APIs, telco APIs) belongs in a
separate orchestration layer. This service records the money
movement atomically and returns the created business record.
"""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from django.utils import timezone

from banking.models.accounting import (
    AccountingJournal,
    AccountingManager,
)
from banking.models.bill_payments import (
    AirtimePurchase,
    Biller,
    BillPayment,
    DataBundlePurchase,
)
from banking.models.core import Account
from banking.models.payments import Transaction
from banking.services import notification_service as notify


logger = logging.getLogger(__name__)

MONEY_QUANTUM = Decimal("0.01")


class BillPaymentService:
    """
    Orchestration service for ledger-backed bill / airtime / data payments.
    """

    # ------------------------------------------------------------------
    # BILL PAYMENT
    # ------------------------------------------------------------------

    @db_transaction.atomic
    def pay_bill(
        self,
        *,
        user,
        source_account: Account,
        biller: Biller,
        amount,
        customer_id: str,
        customer_name: str = "",
        customer_email: str = "",
        customer_phone: str = "",
        bill_type: str = "other",
        reference: str | None = None,
        metadata: dict | None = None,
    ) -> BillPayment:
        """
        Pay a bill.

        Posts one journal for the principal and, if the biller
        charges a fee, a second journal for the fee.

        Journal principal:  source_account -> SUSPENSE
        Journal fee:        source_account -> FEE
        """
        amount = self._validate_amount(amount)
        self._validate_source_account(user, source_account)

        if biller is None:
            raise ValidationError("Biller is required.")
        if not biller.is_active:
            raise ValidationError("Biller is not active.")

        # Biller-configured validation.
        try:
            biller.validate_amount(amount)
        except ValidationError:
            raise

        fee = biller.calculate_fee(amount)
        total = amount + fee

        if source_account.get_balance() < total:
            raise ValidationError("Insufficient funds in source account.")

        if not reference:
            reference = f"BP-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        # --------------------------------------------------------------
        # Principal journal.
        # --------------------------------------------------------------

        principal_txn = Transaction.objects.create(
            account=source_account,
            amount=amount,
            type=Transaction.BILL_PAYMENT,
            narration=f"Bill payment: {biller.name}",
            recipient_name=customer_name or biller.name,
            recipient_account_number=customer_id,
            status=Transaction.PENDING,
        )

        principal_journal = AccountingManager.create_double_entry(
            transaction=principal_txn,
            debit_account=source_account,
            credit_account=AccountingManager.get_suspense_account(),
            amount=amount,
            description=f"Bill payment to {biller.name}",
            journal_type=AccountingJournal.TRANSFER,
            created_by=user,
        )

        principal_txn.journal = principal_journal
        principal_txn.status = Transaction.SUCCESS
        principal_txn.balance_after = source_account.get_balance()
        principal_txn.save(update_fields=[
            "journal", "status", "balance_after", "updated_at",
        ])

        # --------------------------------------------------------------
        # Fee journal (only if fee > 0).
        # --------------------------------------------------------------

        fee_journal = None
        if fee > Decimal("0.00"):
            fee_txn = Transaction.objects.create(
                account=source_account,
                amount=fee,
                type=Transaction.FEE,
                narration=f"Bill payment fee: {biller.name}",
                fee=fee,
                status=Transaction.PENDING,
            )

            fee_journal = AccountingManager.create_double_entry(
                transaction=fee_txn,
                debit_account=source_account,
                credit_account=AccountingManager.get_fee_account(),
                amount=fee,
                description=f"Bill payment fee for {biller.name}",
                journal_type=AccountingJournal.FEE,
                created_by=user,
            )

            fee_txn.journal = fee_journal
            fee_txn.status = Transaction.SUCCESS
            fee_txn.balance_after = source_account.get_balance()
            fee_txn.save(update_fields=[
                "journal", "status", "balance_after", "updated_at",
            ])

        # --------------------------------------------------------------
        # Business record.
        # --------------------------------------------------------------

        payment = BillPayment.objects.create(
            user=user,
            account=source_account,
            biller=biller,
            bill_type=bill_type,
            provider=biller.name,
            customer_id=customer_id,
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone,
            amount=amount,
            fee=fee,
            total_amount=total,
            reference=reference,
            status=BillPayment.SUCCESS,
            initiated_at=timezone.now(),
            processed_at=timezone.now(),
            completed_at=timezone.now(),
            metadata=metadata or {},
            transaction=principal_txn,
            journal=principal_journal,
            fee_journal=fee_journal,
        )

        notify.emit_bill_payment_successful(user=user, payment=payment)

        return payment

    # ------------------------------------------------------------------
    # AIRTIME
    # ------------------------------------------------------------------

    @db_transaction.atomic
    def purchase_airtime(
        self,
        *,
        user,
        source_account: Account,
        operator: str,
        phone_number: str,
        amount,
        reference: str | None = None,
        metadata: dict | None = None,
    ) -> AirtimePurchase:
        """
        Purchase airtime.

        Fee is computed from the amount using a fixed schedule.

        Journal principal:  source_account -> SUSPENSE
        Journal fee:        source_account -> FEE
        """
        amount = self._validate_amount(amount)
        self._validate_source_account(user, source_account)

        if operator not in {c[0] for c in AirtimePurchase.OPERATORS}:
            raise ValidationError(f"Invalid operator: {operator}.")

        phone = self._validate_phone(phone_number)

        fee = self._airtime_fee(amount)
        total = amount + fee

        if source_account.get_balance() < total:
            raise ValidationError("Insufficient funds in source account.")

        if not reference:
            reference = f"AT-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        principal_txn = Transaction.objects.create(
            account=source_account,
            amount=amount,
            type=Transaction.AIRTIME,
            narration=f"Airtime purchase: {operator}",
            recipient_phone=phone,
            status=Transaction.PENDING,
        )

        principal_journal = AccountingManager.create_double_entry(
            transaction=principal_txn,
            debit_account=source_account,
            credit_account=AccountingManager.get_suspense_account(),
            amount=amount,
            description=f"Airtime purchase: {operator}",
            journal_type=AccountingJournal.TRANSFER,
            created_by=user,
        )

        principal_txn.journal = principal_journal
        principal_txn.status = Transaction.SUCCESS
        principal_txn.balance_after = source_account.get_balance()
        principal_txn.save(update_fields=[
            "journal", "status", "balance_after", "updated_at",
        ])

        fee_journal = None
        if fee > Decimal("0.00"):
            fee_txn = Transaction.objects.create(
                account=source_account,
                amount=fee,
                type=Transaction.FEE,
                narration=f"Airtime fee: {operator}",
                fee=fee,
                status=Transaction.PENDING,
            )

            fee_journal = AccountingManager.create_double_entry(
                transaction=fee_txn,
                debit_account=source_account,
                credit_account=AccountingManager.get_fee_account(),
                amount=fee,
                description=f"Airtime purchase fee: {operator}",
                journal_type=AccountingJournal.FEE,
                created_by=user,
            )

            fee_txn.journal = fee_journal
            fee_txn.status = Transaction.SUCCESS
            fee_txn.balance_after = source_account.get_balance()
            fee_txn.save(update_fields=[
                "journal", "status", "balance_after", "updated_at",
            ])

        purchase = AirtimePurchase.objects.create(
            user=user,
            account=source_account,
            phone_number=phone,
            operator=operator,
            amount=amount,
            fee=fee,
            total_amount=total,
            reference=reference,
            status=AirtimePurchase.SUCCESS,
            initiated_at=timezone.now(),
            processing_at=timezone.now(),
            completed_at=timezone.now(),
            metadata=metadata or {},
            transaction=principal_txn,
            journal=principal_journal,
            fee_journal=fee_journal,
        )

        notify.emit_airtime_purchase_successful(
            user=user, purchase=purchase,
        )

        return purchase

    # ------------------------------------------------------------------
    # DATA BUNDLE
    # ------------------------------------------------------------------

    @db_transaction.atomic
    def purchase_data_bundle(
        self,
        *,
        user,
        source_account: Account,
        operator: str,
        phone_number: str,
        bundle_name: str,
        data_amount: str,
        data_type: str,
        price,
        validity_days: int,
        reference: str | None = None,
        metadata: dict | None = None,
    ) -> DataBundlePurchase:
        """
        Purchase a data bundle.

        Journal: source_account -> SUSPENSE
        """
        price = self._validate_amount(price)
        self._validate_source_account(user, source_account)

        if operator not in {c[0] for c in AirtimePurchase.OPERATORS}:
            raise ValidationError(f"Invalid operator: {operator}.")
        if data_type not in {c[0] for c in DataBundlePurchase.DATA_TYPES}:
            raise ValidationError(f"Invalid data_type: {data_type}.")
        if validity_days <= 0:
            raise ValidationError("validity_days must be positive.")

        phone = self._validate_phone(phone_number)

        if source_account.get_balance() < price:
            raise ValidationError("Insufficient funds in source account.")

        if not reference:
            reference = f"DB-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        txn = Transaction.objects.create(
            account=source_account,
            amount=price,
            type=Transaction.AIRTIME,  # closest existing type
            narration=f"Data bundle: {bundle_name}",
            recipient_phone=phone,
            status=Transaction.PENDING,
        )

        journal = AccountingManager.create_double_entry(
            transaction=txn,
            debit_account=source_account,
            credit_account=AccountingManager.get_suspense_account(),
            amount=price,
            description=f"Data bundle purchase: {bundle_name}",
            journal_type=AccountingJournal.TRANSFER,
            created_by=user,
        )

        txn.journal = journal
        txn.status = Transaction.SUCCESS
        txn.balance_after = source_account.get_balance()
        txn.save(update_fields=[
            "journal", "status", "balance_after", "updated_at",
        ])

        purchase = DataBundlePurchase.objects.create(
            user=user,
            account=source_account,
            transaction=txn,
            phone_number=phone,
            operator=operator,
            bundle_name=bundle_name,
            data_amount=data_amount,
            data_type=data_type,
            price=price,
            validity_days=validity_days,
            status="SUCCESS",
            completed_at=timezone.now(),
            metadata=metadata or {},
            journal=journal,
        )

        notify.emit_data_bundle_purchase_successful(
            user=user, purchase=purchase,
        )

        return purchase

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

    @staticmethod
    def _validate_source_account(user, source_account: Account) -> None:
        if source_account is None:
            raise ValidationError("Source account is required.")
        if source_account.pk is None:
            raise ValidationError("Source account must be persisted.")
        if source_account.is_system_account:
            raise ValidationError("Source account cannot be a system account.")
        if source_account.user_id != user.pk:
            raise ValidationError(
                "Source account does not belong to this user."
            )
        if source_account.status != Account.STATUS_ACTIVE:
            raise ValidationError("Source account is not active.")

    @staticmethod
    def _validate_phone(phone_number: str) -> str:
        if not phone_number:
            raise ValidationError("Phone number is required.")
        digits = "".join(c for c in str(phone_number) if c.isdigit())
        if len(digits) < 10:
            raise ValidationError("Invalid phone number.")
        return digits

    @staticmethod
    def _airtime_fee(amount: Decimal) -> Decimal:
        """
        Fee schedule used by AirtimePurchase.calculate_fee().
        Kept in sync with the model method for consistency.
        """
        if amount <= Decimal("50.00"):
            return Decimal("5.00")
        if amount <= Decimal("100.00"):
            return Decimal("7.00")
        if amount <= Decimal("500.00"):
            return Decimal("10.00")
        if amount <= Decimal("1000.00"):
            return Decimal("15.00")
        return Decimal("20.00")