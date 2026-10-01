# ===========================================================================
# ACCOUNT
# ===========================================================================

# apps/backend/banking/models/core.py

"""
Core banking models.

Architecture
------------

    accounts.User
        │
        └── banking.Account

The banking domain owns the Account model and references the canonical
Django user model directly.

Ownership semantics
-------------------

Customer account:

    accounts.User
        │
        └── banking.Account
                is_system_account = False
                user != NULL

System account:

    banking.Account
        is_system_account = True
        user = NULL

System accounts are internal banking accounts and are NOT owned by
ordinary application users.

Balances are NOT stored on Account.

The authoritative balance is derived from LedgerEntry through:

    banking.models.accounting.AccountingManager

This prevents multiple competing sources of truth for financial
balances.

PIN Management
--------------

PINs are NOT stored on Account.

BankingSecurity is the SINGLE SOURCE OF TRUTH for banking PINs.

Use BankingSecurity for all PIN operations:
    
    security = BankingSecurity.objects.get(user=user)
    security.set_pin("1234")
    security.check_pin("1234")
"""

import logging
import re
from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from django.db.models import Q


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Provider health configuration
# ---------------------------------------------------------------------------

HEALTH_DEGRADE = 10
HEALTH_RECOVER = 5
MAX_FAILURES = 3
DISABLE_MINUTES = 15


# ===========================================================================
# BANK
# ===========================================================================


class Bank(models.Model):
    """
    Bank / financial institution / virtual-account provider.

    A Bank record may represent:

    - a traditional Nigerian bank
    - a microfinance/digital bank
    - a payment service bank
    - a virtual-account provider
    - an external banking partner
    """

    NIGERIAN_BANK_CHOICES = [
        # ------------------------------------------------------------------
        # Traditional Banks
        # ------------------------------------------------------------------

        ("ACCESS", "Access Bank"),
        ("ACCESS_D", "Access Bank (Diamond)"),
        ("CITIBANK", "Citibank Nigeria"),
        ("ECOBANK", "Ecobank Nigeria"),
        ("FIDELITY", "Fidelity Bank"),
        ("FIRSTBANK", "First Bank of Nigeria"),
        ("FCMB", "First City Monument Bank (FCMB)"),
        ("GTBANK", "Guaranty Trust Bank (GTBank)"),
        ("HERITAGE", "Heritage Bank"),
        ("KEYSTONE", "Keystone Bank"),
        ("POLARIS", "Polaris Bank"),
        ("PROVIDUS", "Providus Bank"),
        ("STANBIC", "Stanbic IBTC Bank"),
        ("STANDARD", "Standard Chartered Bank"),
        ("STERLING", "Sterling Bank"),
        ("SUNTRUST", "Suntrust Bank"),
        ("UBA", "United Bank for Africa (UBA)"),
        ("UNION", "Union Bank"),
        ("UNITY", "Unity Bank"),
        ("WEMA", "Wema Bank"),
        ("ZENITH", "Zenith Bank"),

        # ------------------------------------------------------------------
        # Fintech / Digital / MFB
        # ------------------------------------------------------------------

        ("KUDA", "Kuda Bank"),
        ("OPAY", "OPay Digital Services"),
        ("PALMPAY", "PalmPay"),
        ("MONIEPOINT", "Moniepoint MFB"),
        ("FAIRMONEY", "FairMoney MFB"),
        ("CARBON", "Carbon (One Finance)"),
        ("RUBIES", "Rubies Bank"),
        ("VFD", "VFD Microfinance Bank"),
        ("TITAN", "Titan Trust Bank"),
        ("EYOWO", "Eyowo MFB"),
        ("GOMONEY", "GoMoney MFB"),
        ("LOTUS", "Lotus Bank"),
        ("PARALLEX", "Parallex Bank"),
        ("BOWEN", "Bowen Microfinance Bank"),
        ("ACCELEREX", "Accelerex MFB"),

        # ------------------------------------------------------------------
        # Payment Service Banks
        # ------------------------------------------------------------------

        ("MTN_MOMO", "MTN MoMo PSB"),
        ("9PSB", "9 Payment Service Bank (9PSB)"),
        ("SMARTCASH", "SmartCash PSB"),

        # ------------------------------------------------------------------
        # Banking technology / providers
        # ------------------------------------------------------------------

        ("TEAMAPT", "TeamApt (Moniepoint Tech)"),

        # ------------------------------------------------------------------
        # Virtual Account Providers
        # ------------------------------------------------------------------

        ("PAYSTACK_WEMA", "Paystack (Wema Bank)"),
        ("MONNIFY_PROVIDUS", "Monnify (Providus Bank)"),
        ("FLUTTERWAVE_ACCESS", "Flutterwave (Access Bank)"),
        ("PROVIDUS_VIRTUAL", "Providus Virtual Accounts"),
        ("UNITY_VIRTUAL", "Unity Virtual Accounts"),
    ]

    VIRTUAL_ACCOUNT_PROVIDER_CHOICES = [
        ("PAYSTACK", "Paystack"),
        ("MONNIFY", "Monnify"),
        ("FLUTTERWAVE", "Flutterwave"),
        ("DIRECT", "Direct Bank API"),
    ]

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    name = models.CharField(
        max_length=100,
        choices=NIGERIAN_BANK_CHOICES,
        db_index=True,
    )

    code = models.CharField(
        max_length=32,
        unique=True,
        db_index=True,
    )

    logo = models.ImageField(
        upload_to="bank_logos/",
        blank=True,
        null=True,
    )

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    is_virtual_provider = models.BooleanField(
        default=False,
        db_index=True,
    )

    is_partner_bank = models.BooleanField(
        default=False,
        db_index=True,
    )

    # ------------------------------------------------------------------
    # Capabilities
    # ------------------------------------------------------------------

    supports_transfers = models.BooleanField(
        default=True,
    )

    supports_airtime = models.BooleanField(
        default=False,
    )

    supports_bills = models.BooleanField(
        default=False,
    )

    # ------------------------------------------------------------------
    # Virtual-account capacity
    # ------------------------------------------------------------------

    virtual_account_provider = models.CharField(
        max_length=50,
        blank=True,
        choices=VIRTUAL_ACCOUNT_PROVIDER_CHOICES,
    )

    daily_capacity = models.PositiveIntegerField(
        default=0,
        help_text=(
            "Maximum virtual accounts created per day. "
            "0 means unlimited."
        ),
    )

    current_daily_usage = models.PositiveIntegerField(
        default=0,
    )

    last_usage_reset = models.DateField(
        default=timezone.localdate,
    )

    # ------------------------------------------------------------------
    # External provider configuration
    # ------------------------------------------------------------------

    api_key_encrypted = models.BinaryField(
        null=True,
        blank=True,
    )

    api_secret_encrypted = models.BinaryField(
        null=True,
        blank=True,
    )

    webhook_url = models.URLField(
        blank=True,
    )

    contact_email = models.EmailField(
        blank=True,
    )

    # ------------------------------------------------------------------
    # Provider health
    # ------------------------------------------------------------------

    health_score = models.FloatField(
        default=100.0,
    )

    consecutive_failures = models.PositiveIntegerField(
        default=0,
    )

    last_failure_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    last_success_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    is_temporarily_disabled = models.BooleanField(
        default=False,
    )

    disabled_until = models.DateTimeField(
        null=True,
        blank=True,
    )

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["name"]

        indexes = [
            models.Index(
                fields=["name", "is_active"],
                name="bank_name_active_idx",
            ),
            models.Index(
                fields=["is_virtual_provider"],
                name="bank_virtual_provider_idx",
            ),
            models.Index(
                fields=["is_partner_bank"],
                name="bank_partner_idx",
            ),
            models.Index(
                fields=["virtual_account_provider"],
                name="bank_virtual_provider_type_idx",
            ),
            models.Index(
                fields=["is_active", "is_partner_bank"],
                name="bank_active_partner_idx",
            ),
        ]

    def __str__(self):
        return dict(self.NIGERIAN_BANK_CHOICES).get(
            self.name,
            self.name,
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def clean(self):
        super().clean()

        if not 0 <= self.health_score <= 100:
            raise ValidationError(
                {
                    "health_score": (
                        "Health score must be between 0 and 100."
                    )
                }
            )

        if (
            self.is_virtual_provider
            and not self.virtual_account_provider
        ):
            raise ValidationError(
                {
                    "virtual_account_provider": (
                        "A virtual-account provider must specify "
                        "virtual_account_provider."
                    )
                }
            )

        if (
            not self.is_virtual_provider
            and self.virtual_account_provider
        ):
            raise ValidationError(
                {
                    "virtual_account_provider": (
                        "A non-virtual bank cannot specify a "
                        "virtual-account provider."
                    )
                }
            )

        if (
            self.current_daily_usage > self.daily_capacity
            and self.daily_capacity
        ):
            raise ValidationError(
                {
                    "current_daily_usage": (
                        "Current daily usage cannot exceed "
                        "daily capacity."
                    )
                }
            )

    # ------------------------------------------------------------------
    # Virtual-account capacity
    # ------------------------------------------------------------------

    def _reset_daily_usage_if_needed(self):
        """
        Reset daily virtual-account usage when the calendar day changes.

        Uses a targeted database update rather than saving the complete
        model instance.
        """

        if not self.pk:
            return

        today = timezone.localdate()

        if self.last_usage_reset >= today:
            return

        self.current_daily_usage = 0
        self.last_usage_reset = today

        type(self).objects.filter(pk=self.pk).update(
            current_daily_usage=0,
            last_usage_reset=today,
            updated_at=timezone.now(),
        )

    def can_create_virtual_account(self):
        """
        Return whether this bank can currently create a virtual account.
        """

        if not self.is_partner_bank:
            return False

        self._reset_daily_usage_if_needed()

        return (
            self.daily_capacity == 0
            or self.current_daily_usage < self.daily_capacity
        )

    def increment_virtual_account_usage(self):
        """
        Increment virtual-account creation usage.

        This should only be called after a virtual-account creation
        has actually succeeded.

        Capacity enforcement for concurrent callers should ultimately
        be performed by the provider/service layer inside a transaction.
        """

        if not self.is_partner_bank or not self.pk:
            return

        self._reset_daily_usage_if_needed()

        type(self).objects.filter(pk=self.pk).update(
            current_daily_usage=models.F(
                "current_daily_usage"
            ) + 1,
            updated_at=timezone.now(),
        )

        self.refresh_from_db(
            fields=[
                "current_daily_usage",
                "last_usage_reset",
                "updated_at",
            ]
        )

    def reset_daily_usage(self):
        """Reset the daily virtual-account creation counter."""

        if not self.is_partner_bank or not self.pk:
            return

        today = timezone.localdate()

        type(self).objects.filter(pk=self.pk).update(
            current_daily_usage=0,
            last_usage_reset=today,
            updated_at=timezone.now(),
        )

        self.current_daily_usage = 0
        self.last_usage_reset = today

    @property
    def is_available_for_virtual_accounts(self):
        """
        Return whether this provider is currently available for
        virtual-account creation.
        """

        return (
            self.is_active
            and self.is_partner_bank
            and self.is_healthy()
            and self.can_create_virtual_account()
        )

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    def get_bank_type(self):
        """Return a human-readable bank/provider type."""

        if self.is_virtual_provider:
            return "Virtual Account Provider"

        if self.is_partner_bank:
            return "Partner Bank"

        return "Traditional Bank"

    @classmethod
    def get_active_partner_banks(cls):
        """Return active partner banks ordered by name."""

        return cls.objects.filter(
            is_active=True,
            is_partner_bank=True,
        ).order_by("name")

    # ------------------------------------------------------------------
    # Provider health
    # ------------------------------------------------------------------

    def record_success(self):
        """
        Record a successful provider operation.

        A successful operation resets the consecutive failure counter
        and gradually restores provider health.
        """

        self.consecutive_failures = 0
        self.health_score = min(
            100.0,
            self.health_score + HEALTH_RECOVER,
        )
        self.last_success_at = timezone.now()
        self.is_temporarily_disabled = False
        self.disabled_until = None

        self.save(
            update_fields=[
                "consecutive_failures",
                "health_score",
                "last_success_at",
                "is_temporarily_disabled",
                "disabled_until",
                "updated_at",
            ]
        )

    def record_failure(self):
        """
        Record a failed provider operation.

        After MAX_FAILURES consecutive failures, the provider is
        temporarily disabled.
        """

        now = timezone.now()

        self.consecutive_failures += 1
        self.health_score = max(
            0.0,
            self.health_score - HEALTH_DEGRADE,
        )
        self.last_failure_at = now

        if self.consecutive_failures >= MAX_FAILURES:
            self.is_temporarily_disabled = True
            self.disabled_until = (
                now + timedelta(minutes=DISABLE_MINUTES)
            )

        self.save(
            update_fields=[
                "consecutive_failures",
                "health_score",
                "last_failure_at",
                "is_temporarily_disabled",
                "disabled_until",
                "updated_at",
            ]
        )

    def is_healthy(self):
        """
        Return whether this provider is currently healthy.

        A temporary disable expires automatically when its disable
        period has elapsed.
        """

        if not self.is_active:
            return False

        if not self.is_temporarily_disabled:
            return self.health_score >= 50

        now = timezone.now()

        if self.disabled_until and now >= self.disabled_until:
            self.is_temporarily_disabled = False
            self.consecutive_failures = 0
            self.disabled_until = None

            self.save(
                update_fields=[
                    "is_temporarily_disabled",
                    "consecutive_failures",
                    "disabled_until",
                    "updated_at",
                ]
            )

            return self.health_score >= 50

        return False


# ===========================================================================
# ACCOUNT
# ===========================================================================

class Account(models.Model):
    """
    Core Univa banking account.

    Account is the canonical financial-account identity in the banking
    domain.

    Customer account
        - is_system_account=False
        - user is not NULL
        - phone_number is required

    System account
        - is_system_account=True
        - user is NULL
        - phone_number is NULL

    IMPORTANT
    ---------
    Account does NOT store a financial balance.

    LedgerEntry is the authoritative financial source of truth.

    SystemAccount is metadata describing the purpose of a banking-owned
    Account. It is NOT a second account system and MUST NOT maintain an
    independent financial balance.

    PIN Management
    --------------
    PINs are NOT stored on Account.
    
    BankingSecurity is the SINGLE SOURCE OF TRUTH for banking PINs.
    
    Use BankingSecurity for all PIN operations:
        security = BankingSecurity.objects.get(user=user)
        security.set_pin("1234")
        security.check_pin("1234")
    """

    STATUS_ACTIVE = "ACTIVE"
    STATUS_SUSPENDED = "SUSPENDED"
    STATUS_CLOSED = "CLOSED"

    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_SUSPENDED, "Suspended"),
        (STATUS_CLOSED, "Closed"),
    ]

    # ------------------------------------------------------------------
    # Public/customer identifier
    # ------------------------------------------------------------------

    phone_number = models.CharField(
        max_length=15,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text=(
            "Customer phone number. Must be NULL for system accounts."
        ),
    )

    # ------------------------------------------------------------------
    # Banking identifiers
    # ------------------------------------------------------------------

    nuban_number = models.CharField(
        max_length=10,
        unique=True,
        db_index=True,
    )

    bank = models.ForeignKey(
        Bank,
        on_delete=models.PROTECT,
        related_name="accounts",
    )

    provider_reference = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
    )

    # ------------------------------------------------------------------
    # Ownership
    # ------------------------------------------------------------------

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="banking_account",
        help_text=(
            "Canonical customer owner. Must be NULL for system accounts."
        ),
    )

    account_name = models.CharField(
        max_length=200,
    )

    # ------------------------------------------------------------------
    # External transfer permissions
    # ------------------------------------------------------------------

    can_send_external = models.BooleanField(
        default=False,
    )

    can_receive_external = models.BooleanField(
        default=True,
    )

    # ------------------------------------------------------------------
    # Security
    # ------------------------------------------------------------------
    #
    # NOTE: PINs are NOT stored here anymore.
    #
    # BankingSecurity is the single source of truth for banking PINs.
    #
    # BVN is stored here because it's an identity verification number,
    # not a PIN. BVNs are hashed and never stored in plaintext.
    #
    # ------------------------------------------------------------------

    bvn_hash = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        help_text="Hashed BVN (Bank Verification Number).",
    )

    # ------------------------------------------------------------------
    # Account status
    # ------------------------------------------------------------------

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        db_index=True,
    )

    # ------------------------------------------------------------------
    # Transaction limits
    # ------------------------------------------------------------------

    daily_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("50000.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )

    single_transaction_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("50000.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )

    # ------------------------------------------------------------------
    # System ownership
    # ------------------------------------------------------------------

    is_system_account = models.BooleanField(
        default=False,
        db_index=True,
    )

    # ------------------------------------------------------------------
    # External float linkage
    # ------------------------------------------------------------------

    linked_float_account = models.OneToOneField(
        "banking.FloatAccount",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="linked_account",
    )

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["bank", "status"],
                name="bank_account_bank_status_idx",
            ),
            models.Index(
                fields=["status", "created_at"],
                name="bank_acct_status_created_idx",
            ),
            models.Index(
                fields=["is_system_account"],
                name="bank_account_system_idx",
            ),
        ]

        constraints = [
            # ----------------------------------------------------------
            # Ownership invariant
            #
            # System account:
            #     is_system_account=True
            #     user IS NULL
            #
            # Customer account:
            #     is_system_account=False
            #     user IS NOT NULL
            # ----------------------------------------------------------

            models.CheckConstraint(
                condition=(
                    models.Q(
                        is_system_account=True,
                        user__isnull=True,
                    )
                    |
                    models.Q(
                        is_system_account=False,
                        user__isnull=False,
                    )
                ),
                name="bank_account_ownership_consistent",
            ),

            # ----------------------------------------------------------
            # Phone-number invariant
            #
            # System account:
            #     phone_number IS NULL
            #
            # Customer account:
            #     phone_number IS NOT NULL
            # ----------------------------------------------------------

            models.CheckConstraint(
                condition=(
                    models.Q(
                        is_system_account=True,
                        phone_number__isnull=True,
                    )
                    |
                    models.Q(
                        is_system_account=False,
                        phone_number__isnull=False,
                    )
                ),
                name="bank_account_phone_ownership_consistent",
            ),
        ]

    def __str__(self):
        return (
            f"{self.phone_number or self.nuban_number} - "
            f"{self.account_name}"
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def clean(self):
        super().clean()

        errors = {}

        # --------------------------------------------------------------
        # Ownership
        # --------------------------------------------------------------

        if self.is_system_account:
            if self.user_id is not None:
                errors["user"] = (
                    "System accounts must not be owned by a customer user."
                )

            if self.phone_number:
                errors["phone_number"] = (
                    "System accounts must not have a customer phone number."
                )

            if self.can_send_external:
                errors["can_send_external"] = (
                    "System accounts cannot send external transfers."
                )

            if self.can_receive_external:
                errors["can_receive_external"] = (
                    "System accounts cannot receive external transfers."
                )

            if self.bvn_hash:
                errors["bvn_hash"] = (
                    "System accounts must not have a BVN."
                )

        else:
            if self.user_id is None:
                errors["user"] = (
                    "Customer accounts must have an owner."
                )

            if not self.phone_number:
                errors["phone_number"] = (
                    "Customer accounts must have a phone number."
                )

        # --------------------------------------------------------------
        # Transaction limits
        # --------------------------------------------------------------

        if self.daily_limit < Decimal("0.00"):
            errors["daily_limit"] = (
                "Daily limit cannot be negative."
            )

        if self.single_transaction_limit < Decimal("0.00"):
            errors["single_transaction_limit"] = (
                "Single transaction limit cannot be negative."
            )

        if (
            self.single_transaction_limit
            > self.daily_limit
        ):
            errors["single_transaction_limit"] = (
                "Single transaction limit cannot exceed "
                "the daily limit."
            )

        # --------------------------------------------------------------
        # System-account lifecycle
        # --------------------------------------------------------------

        if (
            self.is_system_account
            and self.status == self.STATUS_CLOSED
        ):
            logger.warning(
                "System account %s is being marked CLOSED.",
                self.pk,
            )

        if errors:
            raise ValidationError(errors)

    # ------------------------------------------------------------------
    # Account classification
    # ------------------------------------------------------------------

    @property
    def is_customer_account(self):
        """
        True when this is a customer-owned banking account.
        """

        return (
            not self.is_system_account
            and self.user_id is not None
        )

    @property
    def is_internal_account(self):
        """
        True when this is a banking-platform-owned account.
        """

        return (
            self.is_system_account
            and self.user_id is None
        )

    # ------------------------------------------------------------------
    # BVN Management (Identity Verification)
    # ------------------------------------------------------------------

    def set_bvn(self, raw_bvn):
        """
        Hash and store a customer BVN.

        BVNs are never persisted in plaintext.
        """

        if self.is_system_account:
            raise ValidationError(
                "System accounts do not have BVNs."
            )

        if not isinstance(raw_bvn, str):
            raise ValidationError(
                "BVN must be provided as text."
            )

        if not re.fullmatch(r"\d{11}", raw_bvn):
            raise ValidationError(
                "BVN must be exactly 11 digits."
            )

        self.bvn_hash = make_password(raw_bvn)
        self.save(update_fields=["bvn_hash", "updated_at"])

    def check_bvn(self, raw_bvn):
        """
        Verify a customer BVN.
        """

        if self.is_system_account:
            return False

        if not self.bvn_hash:
            return False

        if not isinstance(raw_bvn, str):
            return False

        return check_password(
            raw_bvn,
            self.bvn_hash,
        )

    # ------------------------------------------------------------------
    # Account state
    # ------------------------------------------------------------------

    @property
    def is_active_account(self):
        return self.status == self.STATUS_ACTIVE

    def can_transact(self):
        """
        Return whether this account can participate in accounting
        transactions.
        """

        return (
            self.status == self.STATUS_ACTIVE
            and self.bank.is_active
            and self.bank.is_healthy()
        )

    # ------------------------------------------------------------------
    # Authoritative ledger balance
    # ------------------------------------------------------------------

    def get_balance(self, as_of_date=None):
        """
        Return the authoritative ledger-derived balance.

        Account never stores a financial balance.
        """

        from .accounting import AccountingManager

        return AccountingManager.get_account_balance(
            self,
            as_of_date=as_of_date,
        )

    @property
    def balance(self):
        """
        Backward-compatible read-only balance property.

        This is computed from LedgerEntry and is NOT stored on Account.
        """

        return self.get_balance()

    # ------------------------------------------------------------------
    # Transaction limits
    # ------------------------------------------------------------------

    def validate_transaction_amount(self, amount):
        """
        Validate a transaction amount against the account's
        single-transaction limit.
        """

        try:
            amount = Decimal(str(amount))
        except (
            TypeError,
            ValueError,
            ArithmeticError,
        ) as exc:
            raise ValidationError(
                "Invalid transaction amount."
            ) from exc

        if not amount.is_finite():
            raise ValidationError(
                "Transaction amount must be finite."
            )

        amount = amount.quantize(
            Decimal("0.01")
        )

        if amount <= Decimal("0.00"):
            raise ValidationError(
                "Transaction amount must be greater than zero."
            )

        if amount > self.single_transaction_limit:
            raise ValidationError(
                "Transaction amount exceeds the account's "
                "single-transaction limit."
            )

        return amount


# ===========================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "Bank",
    "Account",
    "HEALTH_DEGRADE",
    "HEALTH_RECOVER",
    "MAX_FAILURES",
    "DISABLE_MINUTES",
]