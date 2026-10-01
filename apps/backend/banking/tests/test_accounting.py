"""
Tests for banking.models.accounting

This test suite covers:
- LedgerEntry model
- AccountingJournal model
- FloatAccount model
- KYCDocument & KYCDocumentVerification models
- ForexLimit model
- CurrencyWallet model
- ForexTransaction model
- TransactionDispute & DisputeEvidence models
- SystemAccount model
- AccountingManager class
"""

from decimal import Decimal
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model

from banking.models.core import Account, Bank
from banking.models.payments import Transaction
from banking.models.accounting import (
    MONEY_ZERO,
    MONEY_QUANTUM,
    quantize_money,
    LedgerEntry,
    AccountingJournal,
    FloatAccount,
    KYCDocument,
    KYCDocumentVerification,
    ForexLimit,
    CurrencyWallet,
    ForexTransaction,
    TransactionDispute,
    DisputeEvidence,
    SystemAccount,
    AccountingManager,
)

User = get_user_model()


class QuantizeMoneyTest(TestCase):
    """Test the quantize_money helper function."""

    def test_quantize_money_rounds_to_two_decimal_places(self):
        self.assertEqual(quantize_money(Decimal("10.555")), Decimal("10.56"))
        self.assertEqual(quantize_money(Decimal("10.554")), Decimal("10.55"))
        self.assertEqual(quantize_money(Decimal("10.5")), Decimal("10.50"))

    def test_quantize_money_accepts_strings(self):
        self.assertEqual(quantize_money("10.555"), Decimal("10.56"))

    def test_quantize_money_handles_integers(self):
        self.assertEqual(quantize_money(10), Decimal("10.00"))


class LedgerEntryTest(TestCase):
    """Test the LedgerEntry model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            phone_number="+2348012345678",
            password="testpass123"
        )
        self.bank = Bank.objects.create(
            name="Test Bank",
            code="001",
            is_active=True
        )
        self.account = Account.objects.create(
            user=self.user,
            bank=self.bank,
            account_name="Test Account",
            nuban_number="1234567890",
            phone_number=self.user.phone_number,
            status=Account.STATUS_ACTIVE
        )
        self.journal = AccountingJournal.objects.create(
            journal_type=AccountingJournal.TRANSFER,
            reference="JNL-20260101-TEST001",
            total_amount=Decimal("100.00"),
            is_balanced=False
        )

    def test_create_ledger_entry(self):
        """Test creating a basic LedgerEntry instance."""
        entry = LedgerEntry.objects.create(
            journal=self.journal,
            account=self.account,
            entry_type=LedgerEntry.DEBIT,
            amount=Decimal("100.00"),
            balance_after=Decimal("0.00"),
            reference="ENT-DEBIT-TEST001",
            description="Test debit entry"
        )

        self.assertEqual(entry.journal, self.journal)
        self.assertEqual(entry.account, self.account)
        self.assertEqual(entry.entry_type, LedgerEntry.DEBIT)
        self.assertEqual(entry.amount, Decimal("100.00"))
        self.assertEqual(entry.balance_after, Decimal("0.00"))
        self.assertEqual(entry.reference, "ENT-DEBIT-TEST001")
        self.assertEqual(entry.description, "Test debit entry")
        self.assertIsNotNone(entry.created_at)

    def test_ledger_entry_str(self):
        """Test the string representation."""
        entry = LedgerEntry.objects.create(
            journal=self.journal,
            account=self.account,
            entry_type=LedgerEntry.DEBIT,
            amount=Decimal("100.00"),
            balance_after=Decimal("0.00"),
            reference="ENT-DEBIT-TEST001",
        )
        expected = f"DEBIT 100.00 - {self.account}"
        self.assertEqual(str(entry), expected)

    def test_ledger_entry_amount_must_be_positive(self):
        """Test that amount must be greater than zero."""
        with self.assertRaises(ValidationError):
            LedgerEntry.objects.create(
                journal=self.journal,
                account=self.account,
                entry_type=LedgerEntry.DEBIT,
                amount=Decimal("0.00"),
                balance_after=Decimal("0.00"),
                reference="ENT-DEBIT-TEST001",
            )

    def test_ledger_entry_clean_validates_amount(self):
        """Test the clean method validates amount."""
        entry = LedgerEntry(
            journal=self.journal,
            account=self.account,
            entry_type=LedgerEntry.DEBIT,
            amount=Decimal("-10.00"),
            balance_after=Decimal("0.00"),
            reference="ENT-DEBIT-TEST001",
        )
        with self.assertRaises(ValidationError):
            entry.clean()

    def test_ledger_entry_clean_validates_entry_type(self):
        """Test the clean method validates entry_type."""
        entry = LedgerEntry(
            journal=self.journal,
            account=self.account,
            entry_type="INVALID",
            amount=Decimal("10.00"),
            balance_after=Decimal("0.00"),
            reference="ENT-DEBIT-TEST001",
        )
        with self.assertRaises(ValidationError):
            entry.clean()

    def test_ledger_entry_immutable_update(self):
        """Test that LedgerEntry cannot be updated after creation."""
        entry = LedgerEntry.objects.create(
            journal=self.journal,
            account=self.account,
            entry_type=LedgerEntry.DEBIT,
            amount=Decimal("100.00"),
            balance_after=Decimal("0.00"),
            reference="ENT-DEBIT-TEST001",
        )

        with self.assertRaises(ValidationError):
            entry.save()

    def test_ledger_entry_immutable_delete(self):
        """Test that LedgerEntry cannot be deleted."""
        entry = LedgerEntry.objects.create(
            journal=self.journal,
            account=self.account,
            entry_type=LedgerEntry.DEBIT,
            amount=Decimal("100.00"),
            balance_after=Decimal("0.00"),
            reference="ENT-DEBIT-TEST001",
        )

        with self.assertRaises(ValidationError):
            entry.delete()

    def test_ledger_entry_auto_quantize(self):
        """Test that amounts are automatically quantized on save."""
        entry = LedgerEntry.objects.create(
            journal=self.journal,
            account=self.account,
            entry_type=LedgerEntry.DEBIT,
            amount=Decimal("100.555"),
            balance_after=Decimal("0.555"),
            reference="ENT-DEBIT-TEST001",
        )
        self.assertEqual(entry.amount, Decimal("100.56"))
        self.assertEqual(entry.balance_after, Decimal("0.56"))

    def test_ledger_entry_with_transaction(self):
        """Test LedgerEntry with an associated Transaction."""
        # Create a transaction with an account
        transaction_obj = Transaction.objects.create(
            account=self.account,
            amount=Decimal("100.00"),
            status="PENDING"
        )
        entry = LedgerEntry.objects.create(
            journal=self.journal,
            account=self.account,
            entry_type=LedgerEntry.DEBIT,
            amount=Decimal("100.00"),
            balance_after=Decimal("0.00"),
            transaction=transaction_obj,
            reference="ENT-DEBIT-TEST001",
        )
        self.assertEqual(entry.transaction, transaction_obj)


class AccountingJournalTest(TestCase):
    """Test the AccountingJournal model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            phone_number="+2348012345678",
            password="testpass123"
        )
        self.bank = Bank.objects.create(
            name="Test Bank",
            code="001",
            is_active=True
        )
        self.account = Account.objects.create(
            user=self.user,
            bank=self.bank,
            account_name="Test Account",
            nuban_number="1234567890",
            phone_number=self.user.phone_number,
            status=Account.STATUS_ACTIVE
        )

    def test_create_accounting_journal(self):
        """Test creating a basic AccountingJournal instance."""
        journal = AccountingJournal.objects.create(
            journal_type=AccountingJournal.TRANSFER,
            reference="JNL-20260101-TEST001",
            total_amount=Decimal("100.00"),
            is_balanced=False,
            created_by=self.user,
            description="Test journal"
        )

        self.assertEqual(journal.journal_type, AccountingJournal.TRANSFER)
        self.assertEqual(journal.reference, "JNL-20260101-TEST001")
        self.assertEqual(journal.total_amount, Decimal("100.00"))
        self.assertFalse(journal.is_balanced)
        self.assertEqual(journal.created_by, self.user)
        self.assertEqual(journal.description, "Test journal")

    def test_accounting_journal_str(self):
        """Test the string representation."""
        journal = AccountingJournal.objects.create(
            journal_type=AccountingJournal.TRANSFER,
            reference="JNL-20260101-TEST001",
            total_amount=Decimal("100.00"),
        )
        expected = "TRANSFER - JNL-20260101-TEST001"
        self.assertEqual(str(journal), expected)

    def test_journal_total_positive_constraint(self):
        """Test that total_amount must be positive."""
        with self.assertRaises(ValidationError):
            AccountingJournal.objects.create(
                journal_type=AccountingJournal.TRANSFER,
                reference="JNL-20260101-TEST002",
                total_amount=Decimal("-10.00"),
            )

    def test_journal_clean_invalid_type(self):
        """Test clean method validates journal_type."""
        journal = AccountingJournal(
            journal_type="INVALID",
            reference="JNL-20260101-TEST003",
            total_amount=Decimal("100.00"),
        )
        with self.assertRaises(ValidationError):
            journal.clean()

    def test_journal_quantize_total(self):
        """Test that total_amount is quantized on save."""
        journal = AccountingJournal.objects.create(
            journal_type=AccountingJournal.TRANSFER,
            reference="JNL-20260101-TEST004",
            total_amount=Decimal("100.555"),
        )
        self.assertEqual(journal.total_amount, Decimal("100.56"))

    def test_journal_calculate_totals(self):
        """Test calculate_totals method."""
        journal = AccountingJournal.objects.create(
            journal_type=AccountingJournal.TRANSFER,
            reference="JNL-20260101-TEST005",
            total_amount=Decimal("100.00"),
            is_balanced=False,
        )

        LedgerEntry.objects.create(
            journal=journal,
            account=self.account,
            entry_type=LedgerEntry.DEBIT,
            amount=Decimal("100.00"),
            balance_after=Decimal("0.00"),
            reference="ENT-DEBIT-TEST001",
        )

        LedgerEntry.objects.create(
            journal=journal,
            account=self.account,
            entry_type=LedgerEntry.CREDIT,
            amount=Decimal("100.00"),
            balance_after=Decimal("100.00"),
            reference="ENT-CREDIT-TEST001",
        )

        debit_total, credit_total = journal.calculate_totals()
        self.assertEqual(debit_total, Decimal("100.00"))
        self.assertEqual(credit_total, Decimal("100.00"))

    def test_journal_verify_balance(self):
        """Test verify_balance method."""
        journal = AccountingJournal.objects.create(
            journal_type=AccountingJournal.TRANSFER,
            reference="JNL-20260101-TEST006",
            total_amount=Decimal("100.00"),
            is_balanced=False,
        )

        LedgerEntry.objects.create(
            journal=journal,
            account=self.account,
            entry_type=LedgerEntry.DEBIT,
            amount=Decimal("100.00"),
            balance_after=Decimal("0.00"),
            reference="ENT-DEBIT-TEST001",
        )

        LedgerEntry.objects.create(
            journal=journal,
            account=self.account,
            entry_type=LedgerEntry.CREDIT,
            amount=Decimal("100.00"),
            balance_after=Decimal("100.00"),
            reference="ENT-CREDIT-TEST001",
        )

        self.assertTrue(journal.verify_balance())

    def test_journal_mark_balanced(self):
        """Test mark_balanced method."""
        journal = AccountingJournal.objects.create(
            journal_type=AccountingJournal.TRANSFER,
            reference="JNL-20260101-TEST007",
            total_amount=Decimal("100.00"),
            is_balanced=False,
        )

        LedgerEntry.objects.create(
            journal=journal,
            account=self.account,
            entry_type=LedgerEntry.DEBIT,
            amount=Decimal("100.00"),
            balance_after=Decimal("0.00"),
            reference="ENT-DEBIT-TEST001",
        )

        LedgerEntry.objects.create(
            journal=journal,
            account=self.account,
            entry_type=LedgerEntry.CREDIT,
            amount=Decimal("100.00"),
            balance_after=Decimal("100.00"),
            reference="ENT-CREDIT-TEST001",
        )

        journal.mark_balanced()
        journal.refresh_from_db()
        self.assertTrue(journal.is_balanced)

    def test_journal_balanced_immutable(self):
        """Test that balanced journals cannot be modified."""
        journal = AccountingJournal.objects.create(
            journal_type=AccountingJournal.TRANSFER,
            reference="JNL-20260101-TEST008",
            total_amount=Decimal("100.00"),
            is_balanced=False,
        )

        LedgerEntry.objects.create(
            journal=journal,
            account=self.account,
            entry_type=LedgerEntry.DEBIT,
            amount=Decimal("100.00"),
            balance_after=Decimal("0.00"),
            reference="ENT-DEBIT-TEST001",
        )

        LedgerEntry.objects.create(
            journal=journal,
            account=self.account,
            entry_type=LedgerEntry.CREDIT,
            amount=Decimal("100.00"),
            balance_after=Decimal("100.00"),
            reference="ENT-CREDIT-TEST001",
        )

        journal.mark_balanced()
        journal.refresh_from_db()

        with self.assertRaises(ValidationError):
            journal.journal_type = AccountingJournal.DEPOSIT
            journal.save()

        with self.assertRaises(ValidationError):
            journal.total_amount = Decimal("200.00")
            journal.save()

    def test_journal_delete(self):
        """Test that journals cannot be deleted."""
        journal = AccountingJournal.objects.create(
            journal_type=AccountingJournal.TRANSFER,
            reference="JNL-20260101-TEST009",
            total_amount=Decimal("100.00"),
        )

        with self.assertRaises(ValidationError):
            journal.delete()


class FloatAccountTest(TestCase):
    """Test the FloatAccount model."""

    def test_create_float_account(self):
        """Test creating a FloatAccount instance."""
        float_account = FloatAccount.objects.create(
            bank_name="GTB",
            account_number="0123456789",
            account_name="Test Float Account",
            statement_balance=Decimal("1000000.00"),
            last_reconciled_balance=Decimal("950000.00"),
            is_active=True,
        )

        self.assertEqual(float_account.bank_name, "GTB")
        self.assertEqual(float_account.account_number, "0123456789")
        self.assertEqual(float_account.account_name, "Test Float Account")
        self.assertEqual(float_account.statement_balance, Decimal("1000000.00"))
        self.assertEqual(float_account.last_reconciled_balance, Decimal("950000.00"))
        self.assertTrue(float_account.is_active)

    def test_float_account_str(self):
        """Test the string representation."""
        float_account = FloatAccount.objects.create(
            bank_name="ZENITH",
            account_number="9876543210",
            account_name="Test Float",
        )
        expected = "ZENITH - 9876543210"
        self.assertEqual(str(float_account), expected)

    def test_float_account_discrepancy(self):
        """Test the discrepancy method."""
        float_account = FloatAccount.objects.create(
            bank_name="UBA",
            account_number="1234567890",
            account_name="Test Float",
            statement_balance=Decimal("1000000.00"),
            last_reconciled_balance=Decimal("950000.00"),
        )

        discrepancy = float_account.discrepancy()
        self.assertEqual(discrepancy, Decimal("50000.00"))

    def test_float_account_discrepancy_none(self):
        """Test discrepancy returns None when balances are missing."""
        float_account = FloatAccount.objects.create(
            bank_name="UBA",
            account_number="1234567890",
            account_name="Test Float",
        )
        self.assertIsNone(float_account.discrepancy())


class KYCDocumentTest(TestCase):
    """Test the KYCDocument model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            phone_number="+2348012345678",
            password="testpass123"
        )

    def test_create_kyc_document(self):
        """Test creating a KYCDocument instance."""
        kyc_doc = KYCDocument.objects.create(
            user=self.user,
            document_type="PASSPORT",
            document_number="A12345678",
            status="PENDING",
            country="NG",
        )

        self.assertEqual(kyc_doc.user, self.user)
        self.assertEqual(kyc_doc.document_type, "PASSPORT")
        self.assertEqual(kyc_doc.document_number, "A12345678")
        self.assertEqual(kyc_doc.status, "PENDING")
        self.assertEqual(kyc_doc.country, "NG")

    def test_kyc_document_str(self):
        """Test the string representation."""
        kyc_doc = KYCDocument.objects.create(
            user=self.user,
            document_type="PASSPORT",
        )
        expected = f"{self.user.email} - PASSPORT"
        self.assertEqual(str(kyc_doc), expected)

    def test_kyc_document_unique_constraint(self):
        """Test the unique constraint for user and document_type."""
        KYCDocument.objects.create(
            user=self.user,
            document_type="PASSPORT",
            document_number="A12345678",
        )

        with self.assertRaises(Exception):
            KYCDocument.objects.create(
                user=self.user,
                document_type="PASSPORT",
                document_number="B98765432",
            )


class KYCDocumentVerificationTest(TestCase):
    """Test the KYCDocumentVerification model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            phone_number="+2348012345678",
            password="testpass123"
        )
        self.kyc_doc = KYCDocument.objects.create(
            user=self.user,
            document_type="PASSPORT",
            document_number="A12345678",
        )

    def test_create_kyc_verification(self):
        """Test creating a KYCDocumentVerification instance."""
        verification = KYCDocumentVerification.objects.create(
            document=self.kyc_doc,
            status="VERIFIED",
            verification_type="AUTO",
            verification_result={"score": 95, "status": "passed"},
        )

        self.assertEqual(verification.document, self.kyc_doc)
        self.assertEqual(verification.status, "VERIFIED")
        self.assertEqual(verification.verification_type, "AUTO")
        self.assertEqual(verification.verification_result, {"score": 95, "status": "passed"})

    def test_kyc_verification_str(self):
        """Test the string representation."""
        verification = KYCDocumentVerification.objects.create(
            document=self.kyc_doc,
            status="VERIFIED",
            verification_type="AUTO",
        )
        expected = f"Verification for {self.kyc_doc}"
        self.assertEqual(str(verification), expected)


class ForexLimitTest(TestCase):
    """Test the ForexLimit model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            phone_number="+2348012345678",
            password="testpass123"
        )

    def test_create_forex_limit(self):
        """Test creating a ForexLimit instance."""
        forex_limit = ForexLimit.objects.create(
            user=self.user,
            currency_pair="NGN/USD",
            daily_limit=Decimal("5000.00"),
            monthly_limit=Decimal("100000.00"),
            is_active=True,
        )

        self.assertEqual(forex_limit.user, self.user)
        self.assertEqual(forex_limit.currency_pair, "NGN/USD")
        self.assertEqual(forex_limit.daily_limit, Decimal("5000.00"))
        self.assertEqual(forex_limit.monthly_limit, Decimal("100000.00"))
        self.assertTrue(forex_limit.is_active)

    def test_forex_limit_str(self):
        """Test the string representation."""
        forex_limit = ForexLimit.objects.create(
            user=self.user,
            currency_pair="NGN/USD",
            daily_limit=Decimal("5000.00"),
            monthly_limit=Decimal("100000.00"),
        )
        expected = f"{self.user.email} - NGN/USD Limit"
        self.assertEqual(str(forex_limit), expected)

    def test_forex_limit_unique_constraint(self):
        """Test the unique constraint for user and currency_pair."""
        ForexLimit.objects.create(
            user=self.user,
            currency_pair="NGN/USD",
            daily_limit=Decimal("5000.00"),
            monthly_limit=Decimal("100000.00"),
        )

        with self.assertRaises(Exception):
            ForexLimit.objects.create(
                user=self.user,
                currency_pair="NGN/USD",
                daily_limit=Decimal("10000.00"),
                monthly_limit=Decimal("200000.00"),
            )


class CurrencyWalletTest(TestCase):
    """Test the CurrencyWallet model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            phone_number="+2348012345678",
            password="testpass123"
        )
        self.bank = Bank.objects.create(
            name="Test Bank",
            code="001",
            is_active=True
        )
        self.account = Account.objects.create(
            user=self.user,
            bank=self.bank,
            account_name="Test Account",
            nuban_number="1234567890",
            phone_number=self.user.phone_number,
            status=Account.STATUS_ACTIVE
        )

    def test_create_currency_wallet(self):
        """Test creating a CurrencyWallet instance."""
        wallet = CurrencyWallet.objects.create(
            user=self.user,
            currency="NGN",
            account_number="9876543210",
            account=self.account,
            is_active=True,
        )

        self.assertEqual(wallet.user, self.user)
        self.assertEqual(wallet.currency, "NGN")
        self.assertEqual(wallet.account_number, "9876543210")
        self.assertEqual(wallet.account, self.account)
        self.assertTrue(wallet.is_active)

    def test_currency_wallet_str(self):
        """Test the string representation."""
        wallet = CurrencyWallet.objects.create(
            user=self.user,
            currency="NGN",
            account_number="9876543210",
        )
        expected = f"{self.user.email} - NGN Wallet"
        self.assertEqual(str(wallet), expected)

    def test_currency_wallet_balance_property(self):
        """Test the balance property."""
        wallet = CurrencyWallet.objects.create(
            user=self.user,
            currency="NGN",
            account_number="9876543210",
            account=self.account,
        )
        self.assertEqual(wallet.balance, Decimal("0.00"))

    def test_currency_wallet_unique_constraint(self):
        """Test the unique constraint for user and currency."""
        CurrencyWallet.objects.create(
            user=self.user,
            currency="NGN",
            account_number="9876543210",
        )

        with self.assertRaises(Exception):
            CurrencyWallet.objects.create(
                user=self.user,
                currency="NGN",
                account_number="1234567890",
            )

    def test_currency_wallet_account_must_belong_to_user(self):
        """Test that account must belong to the same user."""
        other_user = User.objects.create_user(
            email="other@example.com",
            phone_number="+2348098765432",
            password="testpass123"
        )
        other_account = Account.objects.create(
            user=other_user,
            bank=self.bank,
            account_name="Other Account",
            nuban_number="9999999999",
            phone_number=other_user.phone_number,
            status=Account.STATUS_ACTIVE
        )

        wallet = CurrencyWallet(
            user=self.user,
            currency="NGN",
            account_number="9876543210",
            account=other_account,
        )
        with self.assertRaises(ValidationError):
            wallet.full_clean()


class ForexTransactionTest(TestCase):
    """Test the ForexTransaction model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            phone_number="+2348012345678",
            password="testpass123"
        )

    def test_create_forex_transaction(self):
        """Test creating a ForexTransaction instance."""
        forex_tx = ForexTransaction.objects.create(
            user=self.user,
            transaction_type="CONVERSION",
            source_currency="NGN",
            target_currency="USD",
            source_amount=Decimal("1500.00"),
            target_amount=Decimal("1.00"),
            exchange_rate=Decimal("1500.00000000"),
            fee=Decimal("15.00"),
            status="COMPLETED",
        )

        self.assertEqual(forex_tx.user, self.user)
        self.assertEqual(forex_tx.transaction_type, "CONVERSION")
        self.assertEqual(forex_tx.source_currency, "NGN")
        self.assertEqual(forex_tx.target_currency, "USD")
        self.assertEqual(forex_tx.source_amount, Decimal("1500.00"))
        self.assertEqual(forex_tx.target_amount, Decimal("1.00"))
        self.assertEqual(forex_tx.exchange_rate, Decimal("1500.00000000"))
        self.assertEqual(forex_tx.fee, Decimal("15.00"))
        self.assertEqual(forex_tx.status, "COMPLETED")

    def test_forex_transaction_str(self):
        """Test the string representation."""
        forex_tx = ForexTransaction.objects.create(
            user=self.user,
            transaction_type="CONVERSION",
            source_currency="NGN",
            target_currency="USD",
            source_amount=Decimal("1500.00"),
            target_amount=Decimal("1.00"),
            exchange_rate=Decimal("1500.00000000"),
            status="PENDING",
        )
        expected = "CONVERSION - NGN to USD"
        self.assertEqual(str(forex_tx), expected)


class TransactionDisputeTest(TestCase):
    """Test the TransactionDispute model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            phone_number="+2348012345678",
            password="testpass123"
        )
        self.bank = Bank.objects.create(
            name="Test Bank",
            code="001",
            is_active=True
        )
        self.account = Account.objects.create(
            user=self.user,
            bank=self.bank,
            account_name="Test Account",
            nuban_number="1234567890",
            phone_number=self.user.phone_number,
            status=Account.STATUS_ACTIVE
        )
        # Transaction requires an account
        self.transaction = Transaction.objects.create(
            account=self.account,
            amount=Decimal("100.00"),
            status="COMPLETED"
        )

    def test_create_transaction_dispute(self):
        """Test creating a TransactionDispute instance."""
        dispute = TransactionDispute.objects.create(
            user=self.user,
            transaction=self.transaction,
            case_number="DS-20260101-001",
            dispute_type="FRAUD",
            reason="Unauthorized transaction",
            description="Customer reported unauthorized transfer",
            requested_amount=Decimal("100.00"),
            status="OPEN",
            priority="HIGH",
            contact_preference="PHONE",
            estimated_resolution_date=date.today() + timedelta(days=5),
        )

        self.assertEqual(dispute.user, self.user)
        self.assertEqual(dispute.transaction, self.transaction)
        self.assertEqual(dispute.case_number, "DS-20260101-001")
        self.assertEqual(dispute.dispute_type, "FRAUD")
        self.assertEqual(dispute.reason, "Unauthorized transaction")
        self.assertEqual(dispute.description, "Customer reported unauthorized transfer")
        self.assertEqual(dispute.requested_amount, Decimal("100.00"))
        self.assertEqual(dispute.status, "OPEN")
        self.assertEqual(dispute.priority, "HIGH")
        self.assertEqual(dispute.contact_preference, "PHONE")
        self.assertEqual(dispute.estimated_resolution_date, date.today() + timedelta(days=5))

    def test_transaction_dispute_str(self):
        """Test the string representation."""
        dispute = TransactionDispute.objects.create(
            user=self.user,
            transaction=self.transaction,
            case_number="DS-20260101-001",
            dispute_type="FRAUD",
            reason="Unauthorized",
            description="Test",
            requested_amount=Decimal("100.00"),
            status="OPEN",
            estimated_resolution_date=date.today() + timedelta(days=5),
        )
        expected = "Dispute DS-20260101-001 - OPEN"
        self.assertEqual(str(dispute), expected)


class DisputeEvidenceTest(TestCase):
    """Test the DisputeEvidence model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            phone_number="+2348012345678",
            password="testpass123"
        )
        self.bank = Bank.objects.create(
            name="Test Bank",
            code="001",
            is_active=True
        )
        self.account = Account.objects.create(
            user=self.user,
            bank=self.bank,
            account_name="Test Account",
            nuban_number="1234567890",
            phone_number=self.user.phone_number,
            status=Account.STATUS_ACTIVE
        )
        self.transaction = Transaction.objects.create(
            account=self.account,
            amount=Decimal("100.00"),
            status="COMPLETED"
        )
        self.dispute = TransactionDispute.objects.create(
            user=self.user,
            transaction=self.transaction,
            case_number="DS-20260101-001",
            dispute_type="FRAUD",
            reason="Unauthorized",
            description="Test",
            requested_amount=Decimal("100.00"),
            status="OPEN",
            estimated_resolution_date=date.today() + timedelta(days=5),
        )

    def test_create_dispute_evidence(self):
        """Test creating a DisputeEvidence instance."""
        evidence = DisputeEvidence.objects.create(
            dispute=self.dispute,
            evidence_type="SCREENSHOT",
            description="Transaction screenshot",
            uploaded_by_user=True,
        )

        self.assertEqual(evidence.dispute, self.dispute)
        self.assertEqual(evidence.evidence_type, "SCREENSHOT")
        self.assertEqual(evidence.description, "Transaction screenshot")
        self.assertTrue(evidence.uploaded_by_user)

    def test_dispute_evidence_str(self):
        """Test the string representation."""
        evidence = DisputeEvidence.objects.create(
            dispute=self.dispute,
            evidence_type="SCREENSHOT",
        )
        expected = f"Evidence for Dispute {self.dispute.case_number}"
        self.assertEqual(str(evidence), expected)


class SystemAccountTest(TestCase):
    """Test the SystemAccount model."""

    def setUp(self):
        self.bank = Bank.objects.create(
            name="Test Bank",
            code="001",
            is_active=True
        )

    def test_create_system_account(self):
        """Test creating a SystemAccount instance."""
        account = Account.objects.create(
            bank=self.bank,
            account_name="System Fee Account",
            nuban_number="9999999999",
            is_system_account=True,
            status=Account.STATUS_ACTIVE,
        )

        system_account = SystemAccount.objects.create(
            account=account,
            purpose=SystemAccount.FEE,
            description="Fee collection account",
            is_active=True,
        )

        self.assertEqual(system_account.account, account)
        self.assertEqual(system_account.purpose, SystemAccount.FEE)
        self.assertEqual(system_account.description, "Fee collection account")
        self.assertTrue(system_account.is_active)

    def test_system_account_str(self):
        """Test the string representation."""
        account = Account.objects.create(
            bank=self.bank,
            account_name="System Fee Account",
            nuban_number="9999999998",
            is_system_account=True,
            status=Account.STATUS_ACTIVE,
        )

        system_account = SystemAccount.objects.create(
            account=account,
            purpose=SystemAccount.FEE,
        )

        expected = f"Fee Account - {account.account_name}"
        self.assertEqual(str(system_account), expected)

    def test_system_account_unique_purpose(self):
        """Test that purpose must be unique."""
        account1 = Account.objects.create(
            bank=self.bank,
            account_name="System Fee Account",
            nuban_number="9999999997",
            is_system_account=True,
            status=Account.STATUS_ACTIVE,
        )

        account2 = Account.objects.create(
            bank=self.bank,
            account_name="Another System Fee Account",
            nuban_number="9999999996",
            is_system_account=True,
            status=Account.STATUS_ACTIVE,
        )

        SystemAccount.objects.create(
            account=account1,
            purpose=SystemAccount.FEE,
        )

        with self.assertRaises(Exception):
            SystemAccount.objects.create(
                account=account2,
                purpose=SystemAccount.FEE,
            )


class AccountingManagerTest(TestCase):
    """Test the AccountingManager class."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            phone_number="+2348012345678",
            password="testpass123"
        )
        self.bank = Bank.objects.create(
            name="Test Bank",
            code="001",
            is_active=True
        )

        # Create source account with unique phone number
        self.source_account = Account.objects.create(
            user=self.user,
            bank=self.bank,
            account_name="Source Account",
            nuban_number="1111111111",
            phone_number=self.user.phone_number,
            status=Account.STATUS_ACTIVE,
        )

        # Create destination account with unique phone number
        self.dest_user = User.objects.create_user(
            email="dest@example.com",
            phone_number="+2348098765432",
            password="testpass123"
        )
        self.dest_account = Account.objects.create(
            user=self.dest_user,
            bank=self.bank,
            account_name="Destination Account",
            nuban_number="2222222222",
            phone_number=self.dest_user.phone_number,
            status=Account.STATUS_ACTIVE,
        )

        # Create system accounts
        self.fee_account = Account.objects.create(
            bank=self.bank,
            account_name="System Fee Account",
            nuban_number="9999999995",
            is_system_account=True,
            status=Account.STATUS_ACTIVE,
        )
        SystemAccount.objects.create(
            account=self.fee_account,
            purpose=SystemAccount.FEE,
            is_active=True,
        )

        self.settlement_account = Account.objects.create(
            bank=self.bank,
            account_name="System Settlement Account",
            nuban_number="9999999994",
            is_system_account=True,
            status=Account.STATUS_ACTIVE,
        )
        SystemAccount.objects.create(
            account=self.settlement_account,
            purpose=SystemAccount.SETTLEMENT,
            is_active=True,
        )

        # Fund the source account with an initial credit
        # Need both DEBIT and CREDIT entries for the journal to be balanced
        self.journal = AccountingJournal.objects.create(
            journal_type=AccountingJournal.DEPOSIT,
            reference="JNL-INIT-001",
            total_amount=Decimal("1000.00"),
            is_balanced=False,
        )

        # Create a temporary system account for the DEBIT side (funding source)
        temp_account = Account.objects.create(
            bank=self.bank,
            account_name="Temp Funding Account",
            nuban_number="3333333333",
            is_system_account=True,
            status=Account.STATUS_ACTIVE,
        )

        LedgerEntry.objects.create(
            journal=self.journal,
            account=temp_account,
            entry_type=LedgerEntry.DEBIT,
            amount=Decimal("1000.00"),
            balance_after=Decimal("0.00"),
            reference="ENT-INIT-DEBIT",
            description="Initial funding debit",
        )

        LedgerEntry.objects.create(
            journal=self.journal,
            account=self.source_account,
            entry_type=LedgerEntry.CREDIT,
            amount=Decimal("1000.00"),
            balance_after=Decimal("1000.00"),
            reference="ENT-INIT-CREDIT",
            description="Initial funding credit",
        )

        self.journal.mark_balanced()

    def test_validate_amount(self):
        """Test the _validate_amount method."""
        result = AccountingManager._validate_amount(Decimal("10.00"))
        self.assertEqual(result, Decimal("10.00"))

        result = AccountingManager._validate_amount("10.50")
        self.assertEqual(result, Decimal("10.50"))

        result = AccountingManager._validate_amount(10)
        self.assertEqual(result, Decimal("10.00"))

        with self.assertRaises(ValidationError):
            AccountingManager._validate_amount(None)

        with self.assertRaises(ValidationError):
            AccountingManager._validate_amount(Decimal("0.00"))

        with self.assertRaises(ValidationError):
            AccountingManager._validate_amount(Decimal("-10.00"))

        with self.assertRaises(ValidationError):
            AccountingManager._validate_amount("invalid")

    def test_create_double_entry(self):
        """Test creating a balanced double-entry journal."""
        transaction_obj = Transaction.objects.create(
            account=self.source_account,
            amount=Decimal("100.00"),
            status="PENDING"
        )

        journal = AccountingManager.create_double_entry(
            transaction=transaction_obj,
            debit_account=self.source_account,
            credit_account=self.dest_account,
            amount=Decimal("100.00"),
            description="Test transfer",
            journal_type=AccountingJournal.TRANSFER,
            created_by=self.user,
        )

        self.assertIsNotNone(journal)
        self.assertTrue(journal.is_balanced)
        self.assertEqual(journal.total_amount, Decimal("100.00"))

        entries = journal.entries.all()
        self.assertEqual(entries.count(), 2)

        debit_entry = entries.get(entry_type=LedgerEntry.DEBIT)
        credit_entry = entries.get(entry_type=LedgerEntry.CREDIT)

        self.assertEqual(debit_entry.amount, Decimal("100.00"))
        self.assertEqual(credit_entry.amount, Decimal("100.00"))
        self.assertEqual(debit_entry.account, self.source_account)
        self.assertEqual(credit_entry.account, self.dest_account)

        source_balance = AccountingManager.get_account_balance(self.source_account)
        dest_balance = AccountingManager.get_account_balance(self.dest_account)
        self.assertEqual(source_balance, Decimal("900.00"))
        self.assertEqual(dest_balance, Decimal("100.00"))

    def test_create_double_entry_insufficient_balance(self):
        """Test that insufficient balance raises ValidationError."""
        transaction_obj = Transaction.objects.create(
            account=self.source_account,
            amount=Decimal("2000.00"),
            status="PENDING"
        )

        with self.assertRaises(ValidationError) as context:
            AccountingManager.create_double_entry(
                transaction=transaction_obj,
                debit_account=self.source_account,
                credit_account=self.dest_account,
                amount=Decimal("2000.00"),
                description="Test transfer",
            )

        self.assertIn("Insufficient balance", str(context.exception))

    def test_create_double_entry_same_account(self):
        """Test that debit and credit accounts must be different."""
        transaction_obj = Transaction.objects.create(
            account=self.source_account,
            amount=Decimal("100.00"),
            status="PENDING"
        )

        with self.assertRaises(ValidationError):
            AccountingManager.create_double_entry(
                transaction=transaction_obj,
                debit_account=self.source_account,
                credit_account=self.source_account,
                amount=Decimal("100.00"),
                description="Test transfer",
            )

    def test_create_double_entry_inactive_account(self):
        """Test that inactive accounts cannot be used."""
        # Set account status to a non-active status
        self.source_account.status = "INACTIVE"
        self.source_account.save()

        transaction_obj = Transaction.objects.create(
            account=self.source_account,
            amount=Decimal("100.00"),
            status="PENDING"
        )

        with self.assertRaises(ValidationError):
            AccountingManager.create_double_entry(
                transaction=transaction_obj,
                debit_account=self.source_account,
                credit_account=self.dest_account,
                amount=Decimal("100.00"),
                description="Test transfer",
            )

    def test_get_account_balance(self):
        """Test get_account_balance method."""
        balance = AccountingManager.get_account_balance(self.source_account)
        self.assertEqual(balance, Decimal("1000.00"))

        balance = AccountingManager.get_account_balance(self.dest_account)
        self.assertEqual(balance, Decimal("0.00"))

    def test_get_account_balance_as_of_date(self):
        """Test get_account_balance with as_of_date."""
        future_date = timezone.now() + timedelta(days=1)

        journal = AccountingJournal.objects.create(
            journal_type=AccountingJournal.TRANSFER,
            reference="JNL-ASOF-001",
            total_amount=Decimal("100.00"),
            is_balanced=False,
        )

        LedgerEntry.objects.create(
            journal=journal,
            account=self.source_account,
            entry_type=LedgerEntry.DEBIT,
            amount=Decimal("100.00"),
            balance_after=Decimal("900.00"),
            reference="ENT-ASOF-DEBIT",
            description="Future debit",
        )

        LedgerEntry.objects.filter(reference="ENT-ASOF-DEBIT").update(
            created_at=future_date
        )

        balance = AccountingManager.get_account_balance(
            self.source_account,
            as_of_date=timezone.now()
        )
        self.assertEqual(balance, Decimal("1000.00"))

    def test_get_account_debit_total(self):
        """Test get_account_debit_total method."""
        journal = AccountingJournal.objects.create(
            journal_type=AccountingJournal.TRANSFER,
            reference="JNL-DEBIT-001",
            total_amount=Decimal("100.00"),
            is_balanced=False,
        )

        LedgerEntry.objects.create(
            journal=journal,
            account=self.source_account,
            entry_type=LedgerEntry.DEBIT,
            amount=Decimal("100.00"),
            balance_after=Decimal("900.00"),
            reference="ENT-DEBIT-TEST",
        )

        total = AccountingManager.get_account_debit_total(self.source_account)
        self.assertEqual(total, Decimal("100.00"))

    def test_get_account_credit_total(self):
        """Test get_account_credit_total method."""
        total = AccountingManager.get_account_credit_total(self.source_account)
        self.assertEqual(total, Decimal("1000.00"))

    def test_get_account_statement(self):
        """Test get_account_statement method."""
        start_date = date.today() - timedelta(days=1)
        end_date = date.today() + timedelta(days=1)

        statement = AccountingManager.get_account_statement(
            self.source_account,
            start_date,
            end_date,
        )

        self.assertGreaterEqual(statement.count(), 1)

    def test_get_account_statement_invalid_dates(self):
        """Test get_account_statement with invalid dates."""
        start_date = date.today() + timedelta(days=1)
        end_date = date.today() - timedelta(days=1)

        with self.assertRaises(ValidationError):
            AccountingManager.get_account_statement(
                self.source_account,
                start_date,
                end_date,
            )

    def test_get_system_account(self):
        """Test get_system_account method."""
        fee_account = AccountingManager.get_system_account(SystemAccount.FEE)
        self.assertEqual(fee_account, self.fee_account)

        settlement_account = AccountingManager.get_system_account(SystemAccount.SETTLEMENT)
        self.assertEqual(settlement_account, self.settlement_account)

    def test_get_system_account_invalid_purpose(self):
        """Test get_system_account with invalid purpose."""
        with self.assertRaises(ValidationError):
            AccountingManager.get_system_account("INVALID")

    def test_get_system_account_not_configured(self):
        """Test get_system_account when purpose is not configured."""
        with self.assertRaises(ValidationError):
            AccountingManager.get_system_account(SystemAccount.REVENUE)

    def test_get_fee_account(self):
        """Test get_fee_account method."""
        account = AccountingManager.get_fee_account()
        self.assertEqual(account, self.fee_account)

    def test_get_settlement_account(self):
        """Test get_settlement_account method."""
        account = AccountingManager.get_settlement_account()
        self.assertEqual(account, self.settlement_account)

    def test_get_suspense_account(self):
        """Test get_suspense_account when not configured."""
        with self.assertRaises(ValidationError):
            AccountingManager.get_suspense_account()


class IntegrationAccountingTest(TestCase):
    """Integration tests for the accounting system."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            phone_number="+2348012345678",
            password="testpass123"
        )
        self.bank = Bank.objects.create(
            name="Test Bank",
            code="001",
            is_active=True
        )

        # Create account1 with user's phone number
        self.account1 = Account.objects.create(
            user=self.user,
            bank=self.bank,
            account_name="Account 1",
            nuban_number="1111111111",
            phone_number=self.user.phone_number,
            status=Account.STATUS_ACTIVE,
        )

        # Create account2 with a different user and phone number
        self.user2 = User.objects.create_user(
            email="user2@example.com",
            phone_number="+2348098765432",
            password="testpass123"
        )
        self.account2 = Account.objects.create(
            user=self.user2,
            bank=self.bank,
            account_name="Account 2",
            nuban_number="2222222222",
            phone_number=self.user2.phone_number,
            status=Account.STATUS_ACTIVE,
        )

        # Fund account1 - need both DEBIT and CREDIT
        journal = AccountingJournal.objects.create(
            journal_type=AccountingJournal.DEPOSIT,
            reference="JNL-INIT-001",
            total_amount=Decimal("1000.00"),
            is_balanced=False,
        )

        temp_account = Account.objects.create(
            bank=self.bank,
            account_name="Temp Funding Account",
            nuban_number="3333333333",
            is_system_account=True,
            status=Account.STATUS_ACTIVE,
        )

        LedgerEntry.objects.create(
            journal=journal,
            account=temp_account,
            entry_type=LedgerEntry.DEBIT,
            amount=Decimal("1000.00"),
            balance_after=Decimal("0.00"),
            reference="ENT-INIT-DEBIT",
        )

        LedgerEntry.objects.create(
            journal=journal,
            account=self.account1,
            entry_type=LedgerEntry.CREDIT,
            amount=Decimal("1000.00"),
            balance_after=Decimal("1000.00"),
            reference="ENT-INIT-CREDIT",
        )
        journal.mark_balanced()

    def test_full_transfer_workflow(self):
        """Test a complete transfer workflow with accounting."""
        transaction_obj = Transaction.objects.create(
            account=self.account1,
            amount=Decimal("250.00"),
            status="PENDING"
        )

        journal = AccountingManager.create_double_entry(
            transaction=transaction_obj,
            debit_account=self.account1,
            credit_account=self.account2,
            amount=Decimal("250.00"),
            description="Test transfer",
        )

        self.assertTrue(journal.is_balanced)

        balance1 = AccountingManager.get_account_balance(self.account1)
        balance2 = AccountingManager.get_account_balance(self.account2)

        self.assertEqual(balance1, Decimal("750.00"))
        self.assertEqual(balance2, Decimal("250.00"))

        entries = journal.entries.filter(transaction=transaction_obj)
        self.assertEqual(entries.count(), 2)



    def test_multiple_transactions(self):
        """Test multiple transactions and balance consistency."""
        amounts = [100.00, 200.00, 50.00, 75.00]

        for i, amount in enumerate(amounts):
            transaction_obj = Transaction.objects.create(
                account=self.account1,
                amount=Decimal(str(amount)),
                status="COMPLETED"
            )

            AccountingManager.create_double_entry(
                transaction=transaction_obj,
                debit_account=self.account1,
                credit_account=self.account2,
                amount=Decimal(str(amount)),
                description=f"Transfer {i+1}",
            )

        # Convert sum to Decimal
        total_amounts = Decimal(str(sum(amounts)))
        expected_balance = Decimal("1000.00") - total_amounts
        actual_balance = AccountingManager.get_account_balance(self.account1)

        self.assertEqual(actual_balance, expected_balance)

        account2_balance = AccountingManager.get_account_balance(self.account2)
        self.assertEqual(account2_balance, total_amounts)

    def test_account_statement_consistency(self):
        """Test that account statement matches balances."""
        for i in range(5):
            transaction_obj = Transaction.objects.create(
                account=self.account1,
                amount=Decimal("50.00"),
                status="COMPLETED"
            )

            AccountingManager.create_double_entry(
                transaction=transaction_obj,
                debit_account=self.account1,
                credit_account=self.account2,
                amount=Decimal("50.00"),
                description=f"Transfer {i+1}",
            )

        start_date = date.today() - timedelta(days=1)
        end_date = date.today() + timedelta(days=1)

        statement = AccountingManager.get_account_statement(
            self.account1,
            start_date,
            end_date,
        )

        total_debits = sum(
            entry.amount
            for entry in statement
            if entry.entry_type == LedgerEntry.DEBIT
        )

        expected_debits = Decimal("250.00")
        self.assertEqual(total_debits, expected_debits)

        final_balance = AccountingManager.get_account_balance(self.account1)
        self.assertEqual(final_balance, Decimal("750.00"))