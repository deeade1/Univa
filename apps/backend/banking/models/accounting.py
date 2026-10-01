"""
Banking accounting and financial-record models.

Production accounting architecture
===================================

Univa uses a ledger-first accounting architecture.

Authoritative financial hierarchy:

    Account
        │
        └── LedgerEntry
                │
                └── AccountingJournal

Rules
-----

1. Account is the canonical financial-account identity.
2. Account NEVER stores a monetary balance.
3. LedgerEntry is the authoritative financial record.
4. AccountingJournal groups related ledger postings.
5. Every posted journal must balance.
6. Ledger entries are immutable after creation.
7. Financial operations are atomic.
8. Account rows are locked before posting.
9. Account locks are acquired in deterministic order.
10. SystemAccount is metadata only and never stores money.
11. FloatAccount represents an external-bank relationship and
    reconciliation state only.
12. CurrencyWallet represents currency/account metadata only.
    It does NOT maintain a competing balance.
13. Customer balances are calculated from LedgerEntry.
14. No accounting operation may silently create an unbalanced journal.
15. Business authorization and accounting posting are separate concerns.
16. System accounts may go negative. Customer accounts may not.

Accounting convention
---------------------

For Univa:

    DEBIT  -> decreases an account balance
    CREDIT -> increases an account balance

Therefore:

    balance = SUM(CREDIT) - SUM(DEBIT)

This convention must remain consistent throughout the banking domain.
"""

import uuid
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib.postgres.indexes import BTreeIndex, GinIndex
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db import transaction as db_transaction
from django.db.models import JSONField, Q, Sum
from django.utils import timezone

from .core import Account
from .payments import Transaction


# ============================================================================
# CONSTANTS
# ============================================================================

MONEY_ZERO = Decimal("0.00")
MONEY_QUANTUM = Decimal("0.01")


def quantize_money(value):
    """
    Normalize a monetary Decimal to two decimal places.
    """
    return Decimal(value).quantize(MONEY_QUANTUM)


# ============================================================================
# LEDGER ENTRY
# ============================================================================


class LedgerEntry(models.Model):
    """
    Immutable double-entry accounting posting.

    LedgerEntry is the authoritative financial record.

    IMPORTANT
    ---------

    balance_after is retained as a historical/materialized snapshot for
    statements and operational efficiency.

    It is NOT the source of truth.

    The authoritative balance is always:

        SUM(CREDIT amounts) - SUM(DEBIT amounts)

    over the applicable ledger entries.

    LedgerEntry objects are immutable after creation.
    """

    DEBIT = "debit"
    CREDIT = "credit"

    ENTRY_TYPES = [
        (DEBIT, "Debit"),
        (CREDIT, "Credit"),
    ]

    journal = models.ForeignKey(
        "AccountingJournal",
        on_delete=models.PROTECT,
        related_name="entries",
        db_index=True,
    )

    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="ledger_entries",
        db_index=True,
    )

    entry_type = models.CharField(
        max_length=10,
        choices=ENTRY_TYPES,
        db_index=True,
    )

    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01")),
        ],
    )

    balance_after = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text=(
            "Historical balance snapshot after this posting. "
            "This is not an independent balance source. "
            "May be negative for system accounts."
        ),
    )

    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.PROTECT,
        related_name="ledger_entries",
        null=True,
        blank=True,
    )

    reference = models.CharField(
        max_length=80,
        unique=True,
        db_index=True,
    )

    description = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        ordering = [
            "created_at",
            "id",
        ]

        indexes = [
            BTreeIndex(
                fields=[
                    "account",
                    "created_at",
                ],
                name="bank_led_account_created_idx",
            ),
            BTreeIndex(
                fields=[
                    "entry_type",
                    "created_at",
                ],
                name="bank_led_type_created_idx",
            ),
            BTreeIndex(
                fields=[
                    "transaction",
                ],
                name="bank_led_transaction_idx",
            ),
            BTreeIndex(
                fields=[
                    "journal",
                ],
                name="bank_led_journal_idx",
            ),
            GinIndex(
                fields=[
                    "description",
                ],
                name="banking_led_description_gin",
                opclasses=[
                    "gin_trgm_ops",
                ],
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=Decimal("0.00")),
                name="ledger_amount_positive",
            ),
            # NOTE:
            #
            # The previous `ledger_balance_after_nonnegative` constraint
            # has been removed. It prevented any ledger entry from having
            # a negative balance_after, which is correct for customer
            # accounts but wrong for system accounts (SETTLEMENT,
            # SUSPENSE, FEE, REVENUE), which legitimately swing negative.
            #
            # Postgres cannot evaluate a CHECK constraint that spans a
            # relation (account__is_system_account), so we cannot add a
            # conditional constraint at the database level. Instead:
            #
            #   - Customer accounts: protected by the runtime check in
            #     AccountingManager.create_double_entry (see below).
            #   - System accounts: permitted to go negative.
            #
            # If you need a belt-and-suspenders safeguard for customer
            # accounts later, add a `clean()` check on LedgerEntry.save()
            # that inspects `self.account.is_system_account`.
        ]

    def __str__(self):
        return (
            f"{self.entry_type.upper()} "
            f"{self.amount} - {self.account}"
        )

    def clean(self):
        super().clean()

        if self.amount is None:
            raise ValidationError(
                {
                    "amount": "Ledger entry amount is required."
                }
            )

        if self.amount <= MONEY_ZERO:
            raise ValidationError(
                {
                    "amount": "Ledger entry amount must be greater than zero."
                }
            )

        if self.entry_type not in {
            self.DEBIT,
            self.CREDIT,
        }:
            raise ValidationError(
                {
                    "entry_type": "Invalid ledger entry type."
                }
            )

        if self.journal_id is not None:
            journal = (
                self.journal
                if hasattr(self, "_state")
                else None
            )

            if journal is not None and journal.is_balanced:
                raise ValidationError(
                    "Entries cannot be added to a balanced journal."
                )

    def save(self, *args, **kwargs):
        """
        Ledger entries are append-only.

        Updates are prohibited once an entry has been posted.
        """

        if self.pk is not None:
            raise ValidationError(
                "Ledger entries are immutable and cannot be modified."
            )

        self.amount = quantize_money(self.amount)
        self.balance_after = quantize_money(self.balance_after)

        self.full_clean()

        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        Financial ledger entries must never be deleted.

        Corrections must be performed through a reversal journal.
        """

        raise ValidationError(
            "Ledger entries are immutable and cannot be deleted. "
            "Create a reversal journal instead."
        )


# ============================================================================
# ACCOUNTING JOURNAL
# ============================================================================


class AccountingJournal(models.Model):
    """
    Immutable accounting journal header.

    A journal represents one accounting event.

    A journal may initially exist while entries are being posted, but it
    must be marked balanced before the enclosing accounting transaction
    commits.

    Once balanced, the journal and all of its entries are immutable.
    """

    TRANSFER = "TRANSFER"
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    FEE = "FEE"
    INTEREST = "INTEREST"
    REVERSAL = "REVERSAL"
    ADJUSTMENT = "ADJUSTMENT"
    SETTLEMENT = "SETTLEMENT"

    JOURNAL_TYPES = [
        (TRANSFER, "Funds Transfer"),
        (DEPOSIT, "Deposit"),
        (WITHDRAWAL, "Withdrawal"),
        (FEE, "Fee Collection"),
        (INTEREST, "Interest Accrual"),
        (REVERSAL, "Transaction Reversal"),
        (ADJUSTMENT, "Accounting Adjustment"),
        (SETTLEMENT, "Settlement"),
    ]

    journal_type = models.CharField(
        max_length=20,
        choices=JOURNAL_TYPES,
        db_index=True,
    )

    reference = models.CharField(
        max_length=80,
        unique=True,
        db_index=True,
    )

    description = models.TextField(
        blank=True,
    )

    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01")),
        ],
    )

    is_balanced = models.BooleanField(
        default=False,
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_banking_journals",
    )

    class Meta:
        ordering = [
            "-created_at",
            "-id",
        ]

        indexes = [
            BTreeIndex(
                fields=[
                    "journal_type",
                    "created_at",
                ],
                name="bank_journal_type_created_idx",
            ),
            BTreeIndex(
                fields=[
                    "is_balanced",
                ],
                name="bank_journal_balanced_idx",
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=Q(total_amount__gt=Decimal("0.00")),
                name="bank_journal_total_positive",
            ),
        ]

    def __str__(self):
        return (
            f"{self.journal_type} - "
            f"{self.reference}"
        )

    def calculate_totals(self):
        """
        Calculate journal debit and credit totals directly from LedgerEntry.

        This method never trusts total_amount or is_balanced.
        """

        totals = (
            self.entries
            .values("entry_type")
            .annotate(total=Sum("amount"))
        )

        debit_total = MONEY_ZERO
        credit_total = MONEY_ZERO

        for row in totals:
            total = (
                Decimal(row["total"])
                if row["total"] is not None
                else MONEY_ZERO
            )

            if row["entry_type"] == LedgerEntry.DEBIT:
                debit_total = total

            elif row["entry_type"] == LedgerEntry.CREDIT:
                credit_total = total

        return (
            quantize_money(debit_total),
            quantize_money(credit_total),
        )

    def verify_balance(self):
        """
        Verify the journal directly from its ledger entries.
        """

        debit_total, credit_total = self.calculate_totals()

        return (
            debit_total == credit_total
            and debit_total == quantize_money(self.total_amount)
        )

    def mark_balanced(self):
        """
        Atomically validate and mark the journal as balanced.

        A journal can only become balanced when the actual ledger entries
        prove that it is balanced.
        """

        if self.pk is None:
            raise ValidationError(
                "Journal must be persisted before it can be balanced."
            )

        if self.is_balanced:
            return

        if not self.verify_balance():
            raise ValidationError(
                "Journal cannot be marked balanced because its "
                "ledger entries are not balanced."
            )

        self.is_balanced = True

        self.save(
            update_fields=[
                "is_balanced",
            ]
        )

    def clean(self):
        super().clean()

        if self.journal_type not in {
            choice[0]
            for choice in self.JOURNAL_TYPES
        }:
            raise ValidationError(
                {
                    "journal_type": "Invalid journal type."
                }
            )

        if self.total_amount is None:
            raise ValidationError(
                {
                    "total_amount": "Journal total amount is required."
                }
            )

        if self.total_amount <= MONEY_ZERO:
            raise ValidationError(
                {
                    "total_amount": (
                        "Journal total amount must be greater than zero."
                    )
                }
            )

    def save(self, *args, **kwargs):
        """
        Protect journal integrity.

        A balanced journal cannot be modified.

        The transition:

            False -> True

        is allowed only through mark_balanced(), which verifies the
        underlying entries first.
        """

        self.total_amount = quantize_money(self.total_amount)

        if self.pk is not None:
            existing = (
                type(self)
                .objects
                .filter(pk=self.pk)
                .values(
                    "is_balanced",
                    "journal_type",
                    "reference",
                    "total_amount",
                    "description",
                    "created_by_id",
                )
                .first()
            )

            if existing is not None:
                if existing["is_balanced"]:
                    if self.is_balanced is not True:
                        raise ValidationError(
                            "A balanced journal cannot be unbalanced."
                        )

                    immutable_fields = {
                        "journal_type": self.journal_type,
                        "reference": self.reference,
                        "total_amount": self.total_amount,
                        "description": self.description,
                        "created_by_id": self.created_by_id,
                    }

                    for field, value in immutable_fields.items():
                        if value != existing[field]:
                            raise ValidationError(
                                "Balanced journals are immutable."
                            )

                elif (
                    self.is_balanced
                    and not existing["is_balanced"]
                ):
                    if not self.verify_balance():
                        raise ValidationError(
                            "A journal cannot be marked balanced "
                            "without balanced ledger entries."
                        )

        self.full_clean()

        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        Journals are immutable financial records.

        Reversal journals must be used for corrections.
        """

        raise ValidationError(
            "Accounting journals cannot be deleted. "
            "Create a reversal journal instead."
        )


# ============================================================================
# EXTERNAL FLOAT / BANK ACCOUNT
# ============================================================================


class FloatAccount(models.Model):
    """
    External bank account used by Univa for operational settlement,
    collections, treasury, or safeguarding/reconciliation purposes.

    IMPORTANT
    ---------

    FloatAccount is NOT a customer ledger.

    It must never become a competing source of truth for customer
    Account balances.

    The external bank's statement is authoritative for the actual
    external-bank position.

    Internal customer balances remain authoritative only through:

        Account -> LedgerEntry

    The fields below therefore describe the external-bank relationship
    and reconciliation state rather than customer wallet balances.
    """

    BANK_CHOICES = [
        ("GTB", "Guaranty Trust Bank"),
        ("ZENITH", "Zenith Bank"),
        ("UBA", "United Bank for Africa"),
        ("FIRSTBANK", "First Bank of Nigeria"),
        ("ACCESS", "Access Bank"),
        ("FCMB", "First City Monument Bank"),
    ]

    bank_name = models.CharField(
        max_length=50,
        choices=BANK_CHOICES,
        db_index=True,
    )

    account_number = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
    )

    account_name = models.CharField(
        max_length=255,
    )

    statement_balance = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=(
            "Latest balance reported by the external bank. "
            "This is not a customer ledger balance."
        ),
    )

    last_reconciled_balance = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=(
            "External-bank balance captured at the last reconciliation."
        ),
    )

    last_reconciliation = models.DateTimeField(
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    max_daily_deposit = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("10000000.00"),
        validators=[
            MinValueValidator(MONEY_ZERO),
        ],
    )

    max_daily_withdrawal = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("10000000.00"),
        validators=[
            MinValueValidator(MONEY_ZERO),
        ],
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-created_at",
            "-id",
        ]

        indexes = [
            BTreeIndex(
                fields=[
                    "bank_name",
                    "is_active",
                ],
                name="bank_float_bank_active_idx",
            ),
            BTreeIndex(
                fields=[
                    "last_reconciliation",
                ],
                name="bank_float_reconciled_idx",
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(statement_balance__isnull=True)
                    | Q(statement_balance__gte=MONEY_ZERO)
                ),
                name="bank_float_statement_nonnegative",
            ),
            models.CheckConstraint(
                condition=(
                    Q(last_reconciled_balance__isnull=True)
                    | Q(last_reconciled_balance__gte=MONEY_ZERO)
                ),
                name="bank_float_reconciled_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(max_daily_deposit__gte=MONEY_ZERO),
                name="bank_float_daily_deposit_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(max_daily_withdrawal__gte=MONEY_ZERO),
                name="bank_float_daily_withdrawal_nonnegative",
            ),
        ]

    def discrepancy(self):
        """
        Return the difference between the latest external-bank statement
        balance and the last reconciled external-bank balance.

        This is a reconciliation metric only.

        It is NOT a customer-account balance.
        """

        if (
            self.statement_balance is None
            or self.last_reconciled_balance is None
        ):
            return None

        return quantize_money(
            self.statement_balance
            - self.last_reconciled_balance
        )

    def __str__(self):
        return (
            f"{self.bank_name} - "
            f"{self.account_number}"
        )


# ============================================================================
# KYC
# ============================================================================


class KYCDocument(models.Model):
    """
    KYC document belonging directly to the canonical user.

    Banking does not use UserProfile as an ownership intermediary.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="banking_kyc_documents",
    )

    document_type = models.CharField(
        max_length=50,
    )

    document_number = models.CharField(
        max_length=100,
        blank=True,
    )

    document_file = models.FileField(
        upload_to="kyc_documents/",
    )

    status = models.CharField(
        max_length=20,
        choices=[
            ("PENDING", "Pending"),
            ("VERIFIED", "Verified"),
            ("REJECTED", "Rejected"),
            ("MANUAL_REVIEW", "Manual Review"),
        ],
        default="PENDING",
        db_index=True,
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="verified_kyc_documents",
    )

    rejection_reason = models.TextField(
        blank=True,
    )

    country = models.CharField(
        max_length=2,
        default="NG",
    )

    issued_date = models.DateField(
        null=True,
        blank=True,
    )

    expiry_date = models.DateField(
        null=True,
        blank=True,
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "user",
                    "document_type",
                ],
                name="banking_kyc_user_document_type_unique",
            ),
        ]

        indexes = [
            BTreeIndex(
                fields=[
                    "user",
                    "document_type",
                ],
                name="banking_kyc_user_doc_type_idx",
            ),
            BTreeIndex(
                fields=[
                    "status",
                ],
                name="banking_kyc_status_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.user.email} - "
            f"{self.document_type}"
        )


class KYCDocumentVerification(models.Model):
    """
    Result of an automatic or manual KYC verification attempt.
    """

    document = models.OneToOneField(
        KYCDocument,
        on_delete=models.CASCADE,
        related_name="verification",
    )

    status = models.CharField(
        max_length=20,
    )

    verification_type = models.CharField(
        max_length=20,
    )

    verification_result = JSONField(
        default=dict,
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    requested_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        indexes = [
            BTreeIndex(
                fields=[
                    "status",
                ],
                name="banking_kyc_ver_status_idx",
            ),
            BTreeIndex(
                fields=[
                    "verification_type",
                ],
                name="banking_kyc_ver_type_idx",
            ),
        ]

    def __str__(self):
        return (
            f"Verification for "
            f"{self.document}"
        )


# ============================================================================
# FOREIGN EXCHANGE
# ============================================================================


class ForexLimit(models.Model):
    """
    Foreign-exchange limits assigned to a user.

    Limits are authorization/risk controls and are not balances.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="banking_forex_limits",
    )

    currency_pair = models.CharField(
        max_length=10,
    )

    daily_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(MONEY_ZERO),
        ],
    )

    monthly_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(MONEY_ZERO),
        ],
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "user",
                    "currency_pair",
                ],
                name="banking_forex_user_currency_pair_unique",
            ),
        ]

        indexes = [
            BTreeIndex(
                fields=[
                    "user",
                    "currency_pair",
                ],
                name="banking_forex_user_pair_idx",
            ),
            BTreeIndex(
                fields=[
                    "is_active",
                ],
                name="banking_forex_active_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.user.email} - "
            f"{self.currency_pair} Limit"
        )


# ============================================================================
# CURRENCY WALLET
# ============================================================================


class CurrencyWallet(models.Model):
    """
    Currency-account metadata.

    IMPORTANT
    ---------

    This model intentionally contains NO monetary balance fields.

    A currency position must eventually map to a canonical Account and
    corresponding ledger.

    Keeping available_balance or ledger_balance here would create a
    second financial source of truth and is therefore prohibited.

    The existing class name is preserved for API compatibility.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="banking_currency_wallets",
    )

    currency = models.CharField(
        max_length=3,
    )

    account_number = models.CharField(
        max_length=20,
        unique=True,
    )

    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="currency_wallets",
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "user",
                    "currency",
                ],
                name="banking_wallet_user_currency_unique",
            ),
        ]

        indexes = [
            BTreeIndex(
                fields=[
                    "user",
                    "currency",
                ],
                name="banking_wallet_user_currency_idx",
            ),
            BTreeIndex(
                fields=[
                    "is_active",
                ],
                name="banking_wallet_active_idx",
            ),
            BTreeIndex(
                fields=[
                    "account",
                ],
                name="banking_wallet_account_idx",
            ),
        ]

        ordering = [
            "-created_at",
        ]

    def clean(self):
        super().clean()

        if self.account_id is not None:
            if self.account.user_id != self.user_id:
                raise ValidationError(
                    {
                        "account": (
                            "Currency wallet account must belong "
                            "to the same user."
                        )
                    }
                )

            if self.account.status != Account.STATUS_ACTIVE:
                raise ValidationError(
                    {
                        "account": (
                            "Currency wallet account must be active."
                        )
                    }
                )

    @property
    def balance(self):
        """
        Return the balance from the canonical ledger.

        No balance is stored on CurrencyWallet.
        """

        if self.account_id is None:
            return MONEY_ZERO

        return AccountingManager.get_account_balance(
            self.account
        )

    def __str__(self):
        return (
            f"{self.user.email} - "
            f"{self.currency} Wallet"
        )


# ============================================================================
# FOREX TRANSACTION
# ============================================================================


class ForexTransaction(models.Model):
    """
    Forex conversions and cross-border payments.

    This model records the FX business event.

    Monetary account movements must still be posted through the
    accounting ledger.
    """

    TRANSACTION_TYPES = [
        ("CONVERSION", "Currency Conversion"),
        ("REMITTANCE", "International Transfer"),
        ("FX_PAYMENT", "Foreign Payment"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="banking_forex_transactions",
    )

    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES,
    )

    source_currency = models.CharField(
        max_length=3,
    )

    target_currency = models.CharField(
        max_length=3,
    )

    source_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
    )

    target_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
    )

    exchange_rate = models.DecimalField(
        max_digits=18,
        decimal_places=8,
    )

    fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=MONEY_ZERO,
    )

    status = models.CharField(
        max_length=20,
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        indexes = [
            BTreeIndex(
                fields=[
                    "user",
                    "transaction_type",
                ],
                name="banking_fx_user_type_idx",
            ),
            BTreeIndex(
                fields=[
                    "status",
                ],
                name="banking_fx_status_idx",
            ),
        ]

        ordering = [
            "-created_at",
            "-id",
        ]

    def __str__(self):
        return (
            f"{self.transaction_type} - "
            f"{self.source_currency} to "
            f"{self.target_currency}"
        )


# ============================================================================
# TRANSACTION DISPUTES
# ============================================================================


class TransactionDispute(models.Model):
    """
    Customer dispute associated with a banking transaction.

    A dispute does not directly mutate the ledger.

    Any approved refund/reversal must create an accounting journal.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="banking_transaction_disputes",
    )

    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name="disputes",
    )

    case_number = models.CharField(
        max_length=50,
        unique=True,
    )

    dispute_type = models.CharField(
        max_length=50,
    )

    reason = models.TextField()

    description = models.TextField()

    requested_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01")),
        ],
    )

    status = models.CharField(
        max_length=20,
        default="OPEN",
        db_index=True,
    )

    priority = models.CharField(
        max_length=10,
        default="NORMAL",
    )

    contact_preference = models.CharField(
        max_length=10,
        default="EMAIL",
    )

    estimated_resolution_date = models.DateField()

    resolution_date = models.DateField(
        null=True,
        blank=True,
    )

    resolution = models.TextField(
        blank=True,
    )

    refund_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(MONEY_ZERO),
        ],
    )

    created_by_user = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        indexes = [
            BTreeIndex(
                fields=[
                    "user",
                    "status",
                ],
                name="banking_dispute_user_status_idx",
            ),
            BTreeIndex(
                fields=[
                    "transaction",
                ],
                name="banking_dispute_transaction_idx",
            ),
        ]

        ordering = [
            "-created_at",
            "-id",
        ]

    def __str__(self):
        return (
            f"Dispute {self.case_number} - "
            f"{self.status}"
        )


class DisputeEvidence(models.Model):
    """
    Evidence attached to a transaction dispute.
    """

    dispute = models.ForeignKey(
        TransactionDispute,
        on_delete=models.CASCADE,
        related_name="evidences",
    )

    file = models.FileField(
        upload_to="dispute_evidences/",
    )

    evidence_type = models.CharField(
        max_length=20,
    )

    description = models.TextField(
        blank=True,
    )

    uploaded_by_user = models.BooleanField(
        default=True,
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        indexes = [
            BTreeIndex(
                fields=[
                    "dispute",
                ],
                name="banking_evidence_dispute_idx",
            ),
            BTreeIndex(
                fields=[
                    "evidence_type",
                ],
                name="banking_evidence_type_idx",
            ),
        ]

        ordering = [
            "-uploaded_at",
        ]

    def __str__(self):
        return (
            f"Evidence for Dispute "
            f"{self.dispute.case_number}"
        )


# ============================================================================
# SYSTEM ACCOUNT
# ============================================================================


class SystemAccount(models.Model):
    """
    Metadata describing a banking-owned internal Account.

    SystemAccount does NOT own money independently.

    The associated Account remains the canonical financial identity.

    LedgerEntry remains the sole financial source of truth.
    """

    FEE = "FEE"
    SETTLEMENT = "SETTLEMENT"
    SUSPENSE = "SUSPENSE"
    REVENUE = "REVENUE"

    PURPOSE_CHOICES = [
        (FEE, "Fee Account"),
        (SETTLEMENT, "Settlement Account"),
        (SUSPENSE, "Suspense Account"),
        (REVENUE, "Revenue Account"),
    ]

    account = models.OneToOneField(
        Account,
        on_delete=models.PROTECT,
        related_name="system_account",
    )

    purpose = models.CharField(
        max_length=20,
        choices=PURPOSE_CHOICES,
        unique=True,
        db_index=True,
    )

    description = models.TextField(
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "purpose",
        ]

        indexes = [
            BTreeIndex(
                fields=[
                    "purpose",
                    "is_active",
                ],
                name="bank_sysacct_purpose_active_idx",
            ),
        ]

    def clean(self):
        super().clean()

        if self.account_id is None:
            raise ValidationError(
                {
                    "account": (
                        "A system-account definition must reference "
                        "an Account."
                    )
                }
            )

        account = self.account

        if not account.is_system_account:
            raise ValidationError(
                {
                    "account": (
                        "SystemAccount can only reference an "
                        "Account marked as a system account."
                    )
                }
            )

        if account.user_id is not None:
            raise ValidationError(
                {
                    "account": (
                        "A system account cannot have a customer owner."
                    )
                }
            )

        if account.phone_number:
            raise ValidationError(
                {
                    "account": (
                        "A system account cannot have a customer "
                        "phone number."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.get_purpose_display()} - "
            f"{self.account.account_name}"
        )


# ============================================================================
# ACCOUNTING MANAGER
# ============================================================================


class AccountingManager:
    """
    Core accounting operations manager.

    Responsibilities
    ----------------

    - Validate financial amounts.
    - Validate account identities.
    - Validate system-account semantics.
    - Lock accounts before posting.
    - Create balanced double-entry journals.
    - Resolve system accounting accounts.
    - Calculate ledger-derived balances.
    - Generate account statements.

    Explicit non-responsibilities
    -----------------------------

    AccountingManager does NOT:

    - store balances;
    - update Account balances;
    - update CurrencyWallet balances;
    - update FloatAccount balances;
    - authorize KYC;
    - decide transaction limits;
    - silently create accounting adjustments.

    Financial balances are derived exclusively from LedgerEntry.
    """

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_amount(amount):
        """
        Validate and normalize a financial amount.
        """

        if amount is None:
            raise ValidationError(
                "Accounting transaction amount is required."
            )

        try:
            amount = Decimal(str(amount))
        except (
            TypeError,
            ValueError,
            ArithmeticError,
            InvalidOperation,
        ) as exc:
            raise ValidationError(
                "Accounting transaction amount is invalid."
            ) from exc

        if not amount.is_finite():
            raise ValidationError(
                "Accounting transaction amount must be finite."
            )

        if amount <= MONEY_ZERO:
            raise ValidationError(
                "Accounting transaction amount must be greater than zero."
            )

        return quantize_money(amount)

    @staticmethod
    def _validate_account_instance(account, label):
        """
        Validate that the supplied object is a persisted Account.
        """

        if account is None:
            raise ValidationError(
                f"{label} account is required."
            )

        if not isinstance(account, Account):
            raise ValidationError(
                f"{label} must be a banking Account."
            )

        if account.pk is None:
            raise ValidationError(
                f"{label} must be persisted before accounting operations."
            )

    @staticmethod
    def _validate_system_account_semantics(account):
        """
        Validate the system/customer classification of an Account.
        """

        if account.is_system_account:

            if account.user_id is not None:
                raise ValidationError(
                    f"System account {account.pk} cannot have a user owner."
                )

            if getattr(account, "phone_number", None):
                raise ValidationError(
                    (
                        f"System account {account.pk} cannot have "
                        "a customer phone number."
                    )
                )

            try:
                system_account = account.system_account
            except SystemAccount.DoesNotExist as exc:
                raise ValidationError(
                    (
                        f"Account {account.pk} is marked as a system "
                        "account but has no SystemAccount configuration."
                    )
                ) from exc

            if not system_account.is_active:
                raise ValidationError(
                    (
                        f"System account {account.pk} is configured "
                        "but its SystemAccount mapping is inactive."
                    )
                )

        else:
            if account.user_id is None:
                raise ValidationError(
                    (
                        f"Customer account {account.pk} must have "
                        "a customer owner."
                    )
                )

    @staticmethod
    def _validate_accounts(
        debit_account,
        credit_account,
    ):
        """
        Validate accounting accounts before database locking.

        State-sensitive validation is repeated after locking.
        """

        AccountingManager._validate_account_instance(
            debit_account,
            "Debit",
        )

        AccountingManager._validate_account_instance(
            credit_account,
            "Credit",
        )

        if debit_account.pk == credit_account.pk:
            raise ValidationError(
                "Debit and credit accounts must be different."
            )

        AccountingManager._validate_system_account_semantics(
            debit_account
        )

        AccountingManager._validate_system_account_semantics(
            credit_account
        )

        if debit_account.status != Account.STATUS_ACTIVE:
            raise ValidationError(
                "Debit account is not active."
            )

        if credit_account.status != Account.STATUS_ACTIVE:
            raise ValidationError(
                "Credit account is not active."
            )

    @staticmethod
    def _validate_locked_accounts(
        debit_account,
        credit_account,
    ):
        """
        Revalidate state after account rows have been locked.
        """

        if debit_account is None:
            raise ValidationError(
                "Debit account no longer exists."
            )

        if credit_account is None:
            raise ValidationError(
                "Credit account no longer exists."
            )

        if debit_account.pk == credit_account.pk:
            raise ValidationError(
                "Debit and credit accounts must be different."
            )

        if debit_account.status != Account.STATUS_ACTIVE:
            raise ValidationError(
                "Debit account is not active."
            )

        if credit_account.status != Account.STATUS_ACTIVE:
            raise ValidationError(
                "Credit account is not active."
            )

        if not debit_account.bank.is_active:
            raise ValidationError(
                "Debit account's bank is inactive."
            )

        if not credit_account.bank.is_active:
            raise ValidationError(
                "Credit account's bank is inactive."
            )

        AccountingManager._validate_system_account_semantics(
            debit_account
        )

        AccountingManager._validate_system_account_semantics(
            credit_account
        )

    @staticmethod
    def _valid_journal_type(journal_type):
        """
        Validate the requested journal type.
        """

        valid_types = {
            choice[0]
            for choice in AccountingJournal.JOURNAL_TYPES
        }

        if journal_type not in valid_types:
            raise ValidationError(
                f"Invalid journal type: {journal_type}"
            )

    # ------------------------------------------------------------------
    # References
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_journal_reference():
        """
        Generate a globally unique journal reference.
        """

        return (
            "JNL-"
            f"{timezone.now().strftime('%Y%m%d')}-"
            f"{uuid.uuid4().hex[:16].upper()}"
        )

    @staticmethod
    def _generate_entry_reference(
        journal_reference,
        entry_type,
    ):
        """
        Generate a unique ledger-entry reference.
        """

        suffix = (
            "DEBIT"
            if entry_type == LedgerEntry.DEBIT
            else "CREDIT"
        )

        return (
            f"{journal_reference}-"
            f"{suffix}-"
            f"{uuid.uuid4().hex[:12].upper()}"
        )

    # ------------------------------------------------------------------
    # Double-entry posting
    # ------------------------------------------------------------------

    @staticmethod
    @db_transaction.atomic
    def create_double_entry(
        transaction,
        debit_account,
        credit_account,
        amount,
        description="",
        journal_type=AccountingJournal.TRANSFER,
        created_by=None,
    ):
        """
        Create a balanced double-entry journal.

        The entire posting occurs in one database transaction.

        Sequence:

            1. Validate amount.
            2. Validate account identities.
            3. Validate journal type.
            4. Lock both Account rows deterministically.
            5. Revalidate locked account state.
            6. Calculate ledger-derived balances.
            7. Validate available debit funds (customer accounts only).
            8. Create journal.
            9. Create debit posting.
            10. Create credit posting.
            11. Verify journal integrity.
            12. Mark journal balanced.
            13. Return journal.

        No balance is written to Account.
        """

        amount = AccountingManager._validate_amount(
            amount
        )

        AccountingManager._validate_accounts(
            debit_account,
            credit_account,
        )

        AccountingManager._valid_journal_type(
            journal_type
        )

        if transaction is not None and transaction.pk is None:
            raise ValidationError(
                "Transaction must be persisted before ledger posting."
            )

        if created_by is not None and created_by.pk is None:
            raise ValidationError(
                "created_by must be a persisted user."
            )

        # --------------------------------------------------------------
        # Deterministic account locking.
        # --------------------------------------------------------------

        account_ids = sorted(
            {
                debit_account.pk,
                credit_account.pk,
            }
        )

        locked_accounts = (
            Account.objects
            .select_for_update()
            .select_related(
                "bank",
            )
            .in_bulk(
                account_ids
            )
        )

        locked_debit_account = locked_accounts.get(
            debit_account.pk
        )

        locked_credit_account = locked_accounts.get(
            credit_account.pk
        )

        AccountingManager._validate_locked_accounts(
            locked_debit_account,
            locked_credit_account,
        )

        debit_account = locked_debit_account
        credit_account = locked_credit_account

        # --------------------------------------------------------------
        # Authoritative balances.
        # --------------------------------------------------------------

        debit_balance = (
            AccountingManager.get_account_balance(
                debit_account
            )
        )

        credit_balance = (
            AccountingManager.get_account_balance(
                credit_account
            )
        )

        # --------------------------------------------------------------
        # Customer/system-account semantics.
        #
        # System accounts (SETTLEMENT, SUSPENSE, FEE, REVENUE) represent
        # the platform's accounting positions. They are permitted to go
        # negative, because they mirror the aggregate of customer
        # balances and legitimately swing both directions.
        #
        # Customer accounts are subject to the balance check.
        # --------------------------------------------------------------

        if (
            debit_balance < amount
            and not debit_account.is_system_account
        ):
            raise ValidationError(
                "Insufficient balance."
            )

        debit_new_balance = quantize_money(
            debit_balance - amount
        )

        credit_new_balance = quantize_money(
            credit_balance + amount
        )

        # --------------------------------------------------------------
        # Create journal header.
        # --------------------------------------------------------------

        journal = AccountingJournal.objects.create(
            journal_type=journal_type,
            reference=(
                AccountingManager
                ._generate_journal_reference()
            ),
            description=description or "",
            total_amount=amount,
            is_balanced=False,
            created_by=created_by,
        )

        # --------------------------------------------------------------
        # Debit posting.
        # --------------------------------------------------------------

        LedgerEntry.objects.create(
            journal=journal,
            account=debit_account,
            entry_type=LedgerEntry.DEBIT,
            amount=amount,
            balance_after=debit_new_balance,
            transaction=transaction,
            reference=(
                AccountingManager
                ._generate_entry_reference(
                    journal.reference,
                    LedgerEntry.DEBIT,
                )
            ),
            description=(
                f"Debit: {description}"
                if description
                else "Debit entry"
            ),
        )

        # --------------------------------------------------------------
        # Credit posting.
        # --------------------------------------------------------------

        LedgerEntry.objects.create(
            journal=journal,
            account=credit_account,
            entry_type=LedgerEntry.CREDIT,
            amount=amount,
            balance_after=credit_new_balance,
            transaction=transaction,
            reference=(
                AccountingManager
                ._generate_entry_reference(
                    journal.reference,
                    LedgerEntry.CREDIT,
                )
            ),
            description=(
                f"Credit: {description}"
                if description
                else "Credit entry"
            ),
        )

        # --------------------------------------------------------------
        # Verify actual ledger totals.
        # --------------------------------------------------------------

        debit_total, credit_total = (
            journal.calculate_totals()
        )

        if debit_total != credit_total:
            raise ValidationError(
                "Accounting journal is not balanced."
            )

        if debit_total != amount:
            raise ValidationError(
                (
                    "Accounting journal total does not match "
                    "the transaction amount."
                )
            )

        if journal.total_amount != amount:
            raise ValidationError(
                (
                    "Accounting journal total amount is "
                    "inconsistent."
                )
            )

        # --------------------------------------------------------------
        # Only now can the journal become posted/balanced.
        # --------------------------------------------------------------

        journal.mark_balanced()

        return journal

    # ------------------------------------------------------------------
    # System accounts
    # ------------------------------------------------------------------

    @staticmethod
    def get_system_account(purpose):
        """
        Resolve the active canonical Account assigned to a system purpose.

        SystemAccount is metadata only.

        The returned object is always banking.Account.
        """

        valid_purposes = {
            choice[0]
            for choice in SystemAccount.PURPOSE_CHOICES
        }

        if purpose not in valid_purposes:
            raise ValidationError(
                f"Invalid system-account purpose: {purpose}"
            )

        try:
            system_account = (
                SystemAccount.objects
                .select_related(
                    "account",
                    "account__bank",
                )
                .get(
                    purpose=purpose,
                    is_active=True,
                    account__is_system_account=True,
                    account__user__isnull=True,
                    account__status=Account.STATUS_ACTIVE,
                )
            )
        except SystemAccount.DoesNotExist as exc:
            raise ValidationError(
                (
                    "No active system account configured "
                    f"for purpose '{purpose}'."
                )
            ) from exc

        if not system_account.account.bank.is_active:
            raise ValidationError(
                (
                    f"System account for purpose '{purpose}' "
                    "belongs to an inactive bank."
                )
            )

        return system_account.account

    @staticmethod
    def get_fee_account():
        """
        Return the configured banking fee account.
        """

        return AccountingManager.get_system_account(
            SystemAccount.FEE
        )

    @staticmethod
    def get_settlement_account():
        """
        Return the configured settlement account.
        """

        return AccountingManager.get_system_account(
            SystemAccount.SETTLEMENT
        )

    @staticmethod
    def get_suspense_account():
        """
        Return the configured suspense account.
        """

        return AccountingManager.get_system_account(
            SystemAccount.SUSPENSE
        )

    @staticmethod
    def get_revenue_account():
        """
        Return the configured revenue account.
        """

        return AccountingManager.get_system_account(
            SystemAccount.REVENUE
        )

    # ------------------------------------------------------------------
    # Balance
    # ------------------------------------------------------------------

    @staticmethod
    def get_account_balance(
        account,
        as_of_date=None,
    ):
        """
        Calculate the authoritative balance directly from ledger postings.

        Formula:

            CREDIT total - DEBIT total

        `balance_after` is deliberately NOT used as the source of truth.

        If no entries exist, the balance is zero.

        `as_of_date` may be:

            - datetime
            - date

        When supplied, only entries created up to that point are included.
        """

        AccountingManager._validate_account_instance(
            account,
            "Account",
        )

        queryset = LedgerEntry.objects.filter(
            account_id=account.pk,
        )

        if as_of_date is not None:

            if hasattr(as_of_date, "tzinfo"):
                queryset = queryset.filter(
                    created_at__lte=as_of_date,
                )

            else:
                queryset = queryset.filter(
                    created_at__date__lte=as_of_date,
                )

        totals = (
            queryset
            .values("entry_type")
            .annotate(
                total=Sum("amount"),
            )
        )

        debit_total = MONEY_ZERO
        credit_total = MONEY_ZERO

        for row in totals:

            total = (
                Decimal(row["total"])
                if row["total"] is not None
                else MONEY_ZERO
            )

            total = quantize_money(total)

            if row["entry_type"] == LedgerEntry.DEBIT:
                debit_total = total

            elif row["entry_type"] == LedgerEntry.CREDIT:
                credit_total = total

        balance = (
            credit_total
            - debit_total
        )

        return quantize_money(balance)

    @staticmethod
    def get_account_debit_total(
        account,
        as_of_date=None,
    ):
        """
        Return total debits posted to an account.
        """

        AccountingManager._validate_account_instance(
            account,
            "Account",
        )

        queryset = LedgerEntry.objects.filter(
            account_id=account.pk,
            entry_type=LedgerEntry.DEBIT,
        )

        if as_of_date is not None:

            if hasattr(as_of_date, "tzinfo"):
                queryset = queryset.filter(
                    created_at__lte=as_of_date,
                )

            else:
                queryset = queryset.filter(
                    created_at__date__lte=as_of_date,
                )

        total = queryset.aggregate(
            total=Sum("amount")
        )["total"]

        return quantize_money(
            total if total is not None else MONEY_ZERO
        )

    @staticmethod
    def get_account_credit_total(
        account,
        as_of_date=None,
    ):
        """
        Return total credits posted to an account.
        """

        AccountingManager._validate_account_instance(
            account,
            "Account",
        )

        queryset = LedgerEntry.objects.filter(
            account_id=account.pk,
            entry_type=LedgerEntry.CREDIT,
        )

        if as_of_date is not None:

            if hasattr(as_of_date, "tzinfo"):
                queryset = queryset.filter(
                    created_at__lte=as_of_date,
                )

            else:
                queryset = queryset.filter(
                    created_at__date__lte=as_of_date,
                )

        total = queryset.aggregate(
            total=Sum("amount")
        )["total"]

        return quantize_money(
            total if total is not None else MONEY_ZERO
        )

    # ------------------------------------------------------------------
    # Statement
    # ------------------------------------------------------------------

    @staticmethod
    def get_account_statement(
        account,
        start_date,
        end_date,
    ):
        """
        Generate an account statement for a requested period.

        The returned queryset contains immutable ledger entries only.

        The statement operation does not mutate financial state.
        """

        AccountingManager._validate_account_instance(
            account,
            "Account",
        )

        if start_date is None:
            raise ValidationError(
                "Statement start date is required."
            )

        if end_date is None:
            raise ValidationError(
                "Statement end date is required."
            )

        if start_date > end_date:
            raise ValidationError(
                "Statement start date cannot be after end date."
            )

        return (
            LedgerEntry.objects
            .filter(
                account_id=account.pk,
                created_at__date__range=[
                    start_date,
                    end_date,
                ],
            )
            .select_related(
                "transaction",
                "journal",
            )
            .order_by(
                "created_at",
                "id",
            )
        )