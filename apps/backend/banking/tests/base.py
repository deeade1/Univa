# apps/backend/banking/tests/base.py

"""
Shared test scaffolding for banking service-level tests.

Provides:
    - fresh customer and staff users
    - a funded customer account
    - a settlement-adjacent account (for SUSPENSE-dependent flows)
    - helpers to assert the ledger is balanced globally

Every test that exercises money movement should:
    1. snapshot balances before
    2. run the service
    3. assert the specific journal is balanced
    4. assert the ledger sum is still zero
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from banking.models.accounting import AccountingJournal, AccountingManager
from banking.models.core import Account, Bank


User = get_user_model()


class BankingServiceTestBase(TestCase):
    """Base class for all banking service tests."""

    @classmethod
    def setUpTestData(cls):
        # --------------------------------------------------------------
        # Bank
        # --------------------------------------------------------------
        cls.bank = Bank.objects.create(
            name="PAYSTACK_WEMA",
            code="PAYSTACK_WEMA",
            is_active=True,
            is_partner_bank=True,
            is_virtual_provider=False,
            virtual_account_provider="PAYSTACK",
        )

        # --------------------------------------------------------------
        # Users
        # --------------------------------------------------------------
        cls.customer = User.objects.create_user(
            email="customer@test.univa",
            password="testpass",
            phone_number="08011112222",
            first_name="Test",
            last_name="Customer",
        )

        cls.staff = User.objects.create_user(
            email="staff@test.univa",
            password="testpass",
            phone_number="08099998888",
            is_staff=True,
        )

        cls.other_customer = User.objects.create_user(
            email="other@test.univa",
            password="testpass",
            phone_number="08033334444",
            first_name="Other",
            last_name="Customer",
        )

        # --------------------------------------------------------------
        # System accounts (SETTLEMENT, FEE, SUSPENSE, REVENUE)
        # --------------------------------------------------------------
        cls.system_accounts = cls._ensure_system_accounts()

        # --------------------------------------------------------------
        # Customer accounts
        # --------------------------------------------------------------
        cls.customer_account = Account.objects.create(
            user=cls.customer,
            bank=cls.bank,
            phone_number="08011112222",
            nuban_number="8011112222",
            account_name="Test Customer",
            status=Account.STATUS_ACTIVE,
            is_system_account=False,
            daily_limit=Decimal("10000000.00"),
            single_transaction_limit=Decimal("10000000.00"),
        )

        cls.other_customer_account = Account.objects.create(
            user=cls.other_customer,
            bank=cls.bank,
            phone_number="08033334444",
            nuban_number="8033334444",
            account_name="Other Customer",
            status=Account.STATUS_ACTIVE,
            is_system_account=False,
            daily_limit=Decimal("10000000.00"),
            single_transaction_limit=Decimal("10000000.00"),
        )

    # ==================================================================
    # System account bootstrap
    # ==================================================================

    @classmethod
    def _ensure_system_accounts(cls):
        """
        Create the four platform system accounts plus their
        SystemAccount metadata rows, idempotently.
        """
        from banking.models.accounting import SystemAccount

        system_specs = [
            ("9000000001", "Univa Settlement", SystemAccount.SETTLEMENT),
            ("9000000002", "Univa Fee", SystemAccount.FEE),
            ("9000000003", "Univa Suspense", SystemAccount.SUSPENSE),
            ("9000000004", "Univa Revenue", SystemAccount.REVENUE),
        ]

        result = {}
        for nuban, name, purpose in system_specs:
            account, _ = Account.objects.get_or_create(
                nuban_number=nuban,
                defaults={
                    "bank": cls.bank,
                    "phone_number": None,
                    "account_name": name,
                    "status": Account.STATUS_ACTIVE,
                    "is_system_account": True,
                    "user": None,
                },
            )
            SystemAccount.objects.get_or_create(
                account=account,
                defaults={"purpose": purpose, "is_active": True},
            )
            result[purpose] = account

        return result

    # ==================================================================
    # Fund an account via SUSPENSE (test setup only)
    # ==================================================================

    def fund_account(self, account, amount):
        """
        Credit `account` with `amount` by debiting the SUSPENSE system
        account. Only for test setup — never used by production code.

        Creates a real journal so the ledger stays balanced.
        """
        amount = Decimal(str(amount))
        suspense = self.system_accounts["SUSPENSE"]

        from banking.models.payments import Transaction

        txn = Transaction.objects.create(
            account=suspense,
            amount=amount,
            type=Transaction.DEPOSIT,
            narration=f"Test top-up to {account.nuban_number}",
            status=Transaction.SUCCESS,
        )

        journal = AccountingManager.create_double_entry(
            transaction=txn,
            debit_account=suspense,
            credit_account=account,
            amount=amount,
            description="Test top-up",
            journal_type=AccountingJournal.DEPOSIT,
            created_by=self.staff,
        )
        return journal

    # ==================================================================
    # Assertions
    # ==================================================================

    def assert_journal_balanced(self, journal):
        self.assertIsNotNone(journal, "Journal is None.")
        self.assertTrue(
            journal.is_balanced,
            f"Journal {journal.pk} is not balanced.",
        )
        debit_total, credit_total = journal.calculate_totals()
        self.assertEqual(debit_total, credit_total)
        self.assertEqual(debit_total, journal.total_amount)

    def assert_ledger_sums_to_zero(self):
        """
        Global double-entry integrity check.
        """
        total = sum(
            a.get_balance() for a in Account.objects.all()
        )
        self.assertEqual(
            total, Decimal("0.00"),
            f"Ledger sum is {total}, expected 0.00.",
        )

    def assert_account_moved_by(self, account, delta):
        """
        Assert the account's ledger-derived balance is now exactly
        `account._baseline_balance + delta`.
        """
        expected = account._baseline_balance + Decimal(str(delta))
        self.assertEqual(account.get_balance(), expected)

    def snapshot(self, *accounts):
        """
        Store each account's current balance as _baseline_balance.
        """
        for account in accounts:
            account._baseline_balance = account.get_balance()