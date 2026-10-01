# apps/backend/banking/tests/test_payments.py

"""
Tests for banking payment models.

This module tests:
    - Transaction: Unified transaction model
    - Wallet: User wallet for storing funds
    - PaymentStat: Payment statistics
    - MoneyTransfer: Money transfer records
"""

from __future__ import annotations

from decimal import Decimal
from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from banking.models.core import Bank, Account
from banking.models.payments import Transaction, Wallet, PaymentStat, MoneyTransfer

User = get_user_model()


# ============================================================================
# TRANSACTION TESTS
# ============================================================================

class TransactionTest(TestCase):
    """Test cases for Transaction model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        self.user.phone_number = "+1234567890"
        self.user.save()

        self.bank = Bank.objects.create(
            name="GTBANK",
            code="GTB",
            is_active=True,
        )
        self.account = Account.objects.create(
            user=self.user,
            bank=self.bank,
            phone_number="+1234567890",
            nuban_number="1234567890",
            account_name="Test User",
        )
        self.transaction = Transaction.objects.create(
            account=self.account,
            amount=Decimal("100.00"),
            type=Transaction.TRANSFER,
            narration="Test transfer",
            status=Transaction.PENDING,
        )

    def test_create_transaction(self):
        """Test creating a Transaction instance."""
        self.assertIsNotNone(self.transaction.pk)
        self.assertEqual(self.transaction.account, self.account)
        self.assertEqual(self.transaction.amount, Decimal("100.00"))
        self.assertEqual(self.transaction.type, "TRANSFER")
        self.assertEqual(self.transaction.narration, "Test transfer")
        self.assertEqual(self.transaction.status, Transaction.PENDING)
        self.assertIsNotNone(self.transaction.reference)

    def test_str_representation(self):
        """Test string representation."""
        expected = f"{self.transaction.reference}: ₦100.00 (PENDING)"
        self.assertEqual(str(self.transaction), expected)

    def test_save_generates_reference(self):
        """Test that reference is auto-generated on save."""
        tx = Transaction.objects.create(
            account=self.account,
            amount=Decimal("50.00"),
            type=Transaction.DEPOSIT,
        )
        self.assertIsNotNone(tx.reference)
        self.assertTrue(tx.reference.startswith("TX"))

    def test_save_does_not_overwrite_existing_reference(self):
        """Test that existing reference is not overwritten."""
        custom_ref = "CUSTOM-REF-001"
        tx = Transaction.objects.create(
            account=self.account,
            amount=Decimal("50.00"),
            type=Transaction.DEPOSIT,
            reference=custom_ref,
        )
        self.assertEqual(tx.reference, custom_ref)

    def test_transaction_status_choices(self):
        """Test transaction status choices."""
        statuses = [choice[0] for choice in Transaction.STATUS_CHOICES]
        self.assertIn('PENDING', statuses)
        self.assertIn('SUCCESS', statuses)
        self.assertIn('FAILED', statuses)
        self.assertIn('REVERSED', statuses)

    def test_transaction_types(self):
        """Test transaction types."""
        types = [choice[0] for choice in Transaction.TRANSACTION_TYPES]
        self.assertIn('TRANSFER', types)
        self.assertIn('DEPOSIT', types)
        self.assertIn('WITHDRAWAL', types)
        self.assertIn('BILL_PAYMENT', types)
        self.assertIn('AIRTIME', types)
        self.assertIn('FEE', types)

    def test_meta_indexes(self):
        """Test meta indexes exist."""
        meta = Transaction._meta
        index_fields = [idx.fields for idx in meta.indexes]
        self.assertIn(['account', 'created_at'], index_fields)
        self.assertIn(['reference', 'status'], index_fields)
        self.assertIn(['type', 'created_at'], index_fields)

    def test_transaction_with_fee(self):
        """Test transaction with fee."""
        tx = Transaction.objects.create(
            account=self.account,
            amount=Decimal("100.00"),
            type=Transaction.TRANSFER,
            fee=Decimal("5.00"),
        )
        self.assertEqual(tx.fee, Decimal("5.00"))

    def test_transaction_with_balance_after(self):
        """Test transaction with balance_after."""
        tx = Transaction.objects.create(
            account=self.account,
            amount=Decimal("100.00"),
            type=Transaction.DEPOSIT,
            balance_after=Decimal("150.00"),
        )
        self.assertEqual(tx.balance_after, Decimal("150.00"))

    def test_transaction_with_provider_reference(self):
        """Test transaction with provider_reference."""
        tx = Transaction.objects.create(
            account=self.account,
            amount=Decimal("100.00"),
            type=Transaction.TRANSFER,
            provider_reference="PROV-123456",
        )
        self.assertEqual(tx.provider_reference, "PROV-123456")


# ============================================================================
# WALLET TESTS
# ============================================================================

class WalletTest(TestCase):
    """Test cases for Wallet model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        self.user.phone_number = "+1234567890"
        self.user.save()

        self.bank = Bank.objects.create(
            name="GTBANK",
            code="GTB",
            is_active=True,
        )
        self.account = Account.objects.create(
            user=self.user,
            bank=self.bank,
            phone_number="+1234567890",
            nuban_number="1234567890",
            account_name="Test User",
        )
        self.wallet = Wallet.objects.create(
            user=self.user,
            account=self.account,
            wallet_reference="WALLET-001",
            balance=Decimal("1000.00"),
        )

    def test_create_wallet(self):
        """Test creating a wallet."""
        self.assertIsNotNone(self.wallet.pk)
        self.assertEqual(self.wallet.user, self.user)
        self.assertEqual(self.wallet.account, self.account)
        self.assertEqual(self.wallet.wallet_reference, "WALLET-001")
        self.assertEqual(self.wallet.balance, Decimal("1000.00"))
        self.assertEqual(self.wallet.status, "ACTIVE")
        self.assertFalse(self.wallet.is_verified)

    def test_str_representation(self):
        """Test string representation."""
        expected = f"Wallet WALLET-001 - {self.user.email}"
        self.assertEqual(str(self.wallet), expected)

    def test_clean_valid_wallet(self):
        """Test clean() with valid data."""
        try:
            self.wallet.full_clean()
        except ValidationError:
            self.fail("clean() raised ValidationError unexpectedly")

    def test_clean_negative_balance(self):
        """Test clean() with negative balance."""
        self.wallet.balance = Decimal("-100.00")
        with self.assertRaises(ValidationError) as exc:
            self.wallet.full_clean()
        self.assertIn("balance", exc.exception.error_dict)

    def test_clean_negative_daily_limit(self):
        """Test clean() with negative daily limit."""
        self.wallet.daily_transaction_limit = Decimal("-100.00")
        with self.assertRaises(ValidationError) as exc:
            self.wallet.full_clean()
        self.assertIn("daily_transaction_limit", exc.exception.error_dict)

    def test_clean_single_limit_exceeds_daily(self):
        """Test clean() with single limit exceeding daily limit."""
        self.wallet.daily_transaction_limit = Decimal("1000.00")
        self.wallet.single_transaction_limit = Decimal("2000.00")
        with self.assertRaises(ValidationError) as exc:
            self.wallet.full_clean()
        self.assertIn("single_transaction_limit", exc.exception.error_dict)

    def test_debit(self):
        """Test debiting wallet."""
        self.wallet.debit(Decimal("100.00"))
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("900.00"))

    def test_debit_insufficient_balance(self):
        """Test debiting more than balance."""
        with self.assertRaises(ValidationError) as exc:
            self.wallet.debit(Decimal("2000.00"))
        self.assertEqual(str(exc.exception), "['Insufficient wallet balance.']")

    def test_debit_inactive_wallet(self):
        """Test debiting inactive wallet."""
        self.wallet.status = "SUSPENDED"
        self.wallet.save()
        with self.assertRaises(ValidationError) as exc:
            self.wallet.debit(Decimal("100.00"))
        self.assertEqual(str(exc.exception), "['Cannot debit inactive wallet.']")

    def test_debit_zero_amount(self):
        """Test debiting zero amount."""
        with self.assertRaises(ValidationError) as exc:
            self.wallet.debit(Decimal("0.00"))
        self.assertEqual(str(exc.exception), "['Debit amount must be greater than zero.']")

    def test_credit(self):
        """Test crediting wallet."""
        self.wallet.credit(Decimal("200.00"))
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("1200.00"))

    def test_credit_inactive_wallet(self):
        """Test crediting inactive wallet."""
        self.wallet.status = "SUSPENDED"
        self.wallet.save()
        with self.assertRaises(ValidationError) as exc:
            self.wallet.credit(Decimal("100.00"))
        self.assertEqual(str(exc.exception), "['Cannot credit inactive wallet.']")

    def test_credit_zero_amount(self):
        """Test crediting zero amount."""
        with self.assertRaises(ValidationError) as exc:
            self.wallet.credit(Decimal("0.00"))
        self.assertEqual(str(exc.exception), "['Credit amount must be greater than zero.']")

    def test_can_transact(self):
        """Test can_transact method."""
        self.assertTrue(self.wallet.can_transact(Decimal("100.00")))

    def test_can_transact_insufficient_balance(self):
        """Test can_transact with insufficient balance."""
        with self.assertRaises(ValidationError) as exc:
            self.wallet.can_transact(Decimal("2000.00"))
        self.assertEqual(str(exc.exception), "['Insufficient wallet balance.']")

    def test_can_transact_exceeds_single_limit(self):
        """Test can_transact exceeding single transaction limit."""
        self.wallet.single_transaction_limit = Decimal("500.00")
        self.wallet.save()
        with self.assertRaises(ValidationError) as exc:
            self.wallet.can_transact(Decimal("1000.00"))
        self.assertIn("exceeds single transaction limit", str(exc.exception))

    def test_can_transact_exceeds_daily_limit(self):
        """Test can_transact exceeding daily limit."""
        self.wallet.daily_transaction_limit = Decimal("1000.00")
        self.wallet.daily_transaction_amount = Decimal("900.00")
        self.wallet.save()
        with self.assertRaises(ValidationError) as exc:
            self.wallet.can_transact(Decimal("200.00"))
        self.assertIn("exceed daily limit", str(exc.exception))

    def test_can_transact_inactive_wallet(self):
        """Test can_transact with inactive wallet."""
        self.wallet.status = "SUSPENDED"
        self.wallet.save()
        with self.assertRaises(ValidationError) as exc:
            self.wallet.can_transact(Decimal("100.00"))
        self.assertEqual(str(exc.exception), "['Wallet is not active.']")

    def test_record_transaction(self):
        """Test recording a transaction."""
        self.wallet.record_transaction(Decimal("100.00"))
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("1100.00"))
        self.assertEqual(self.wallet.daily_transaction_count, 1)
        self.assertEqual(self.wallet.daily_transaction_amount, Decimal("100.00"))

    def test_record_transaction_inactive_wallet(self):
        """Test recording transaction on inactive wallet."""
        self.wallet.status = "SUSPENDED"
        self.wallet.save()
        with self.assertRaises(ValidationError) as exc:
            self.wallet.record_transaction(Decimal("100.00"))
        self.assertEqual(str(exc.exception), "['Cannot record transaction on inactive wallet.']")

    def test_activate(self):
        """Test activating wallet."""
        self.wallet.status = "SUSPENDED"
        self.wallet.save()
        self.wallet.activate()
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.status, "ACTIVE")

    def test_suspend(self):
        """Test suspending wallet."""
        self.wallet.suspend()
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.status, "SUSPENDED")

    def test_close_with_balance(self):
        """Test closing wallet with balance."""
        with self.assertRaises(ValidationError) as exc:
            self.wallet.close()
        self.assertEqual(str(exc.exception), "['Cannot close wallet with positive balance.']")

    def test_close_with_zero_balance(self):
        """Test closing wallet with zero balance."""
        self.wallet.balance = Decimal("0.00")
        self.wallet.save()
        self.wallet.close()
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.status, "CLOSED")

    def test_properties(self):
        """Test wallet properties."""
        self.assertTrue(self.wallet.is_active)
        self.assertTrue(self.wallet.has_balance)
        self.assertEqual(self.wallet.remaining_daily_limit, Decimal("500000.00"))
        self.assertEqual(self.wallet.remaining_daily_transactions, 100)

    def test_reset_daily_limits(self):
        """Test daily limits reset."""
        self.wallet.daily_transaction_amount = Decimal("100.00")
        self.wallet.daily_transaction_count = 5
        self.wallet.last_reset_date = timezone.localdate() - timedelta(days=1)
        self.wallet.save()

        self.wallet._reset_daily_limits_if_needed()
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.daily_transaction_amount, Decimal("0.00"))
        self.assertEqual(self.wallet.daily_transaction_count, 0)
        self.assertEqual(self.wallet.last_reset_date, timezone.localdate())

    def test_remaining_daily_limit_calls_reset(self):
        """Test that remaining_daily_limit calls reset."""
        self.wallet.daily_transaction_amount = Decimal("100.00")
        self.wallet.daily_transaction_count = 5
        self.wallet.last_reset_date = timezone.localdate() - timedelta(days=1)
        self.wallet.save()

        limit = self.wallet.remaining_daily_limit
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.daily_transaction_amount, Decimal("0.00"))


# ============================================================================
# PAYMENT STAT TESTS
# ============================================================================

class PaymentStatTest(TestCase):
    """Test cases for PaymentStat model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        self.payment_stat = PaymentStat.objects.create(
            user=self.user,
            number_of_payments=5,
            total_payments_amount=Decimal("1000.00"),
            last_transaction_amount=Decimal("200.00"),
            last_transaction_date=timezone.now(),
            daily_limit=Decimal("500.00"),
            monthly_limit=Decimal("5000.00"),
        )

    def test_create_payment_stat(self):
        """Test creating a PaymentStat instance."""
        self.assertIsNotNone(self.payment_stat.pk)
        self.assertEqual(self.payment_stat.user, self.user)
        self.assertEqual(self.payment_stat.number_of_payments, 5)
        self.assertEqual(self.payment_stat.total_payments_amount, Decimal("1000.00"))
        self.assertEqual(self.payment_stat.last_transaction_amount, Decimal("200.00"))
        self.assertEqual(self.payment_stat.daily_limit, Decimal("500.00"))
        self.assertEqual(self.payment_stat.monthly_limit, Decimal("5000.00"))

    def test_str_representation(self):
        """Test string representation."""
        expected = f"{self.user.first_name or 'Unknown'} Payments"
        self.assertEqual(str(self.payment_stat), expected)

    def test_can_make_transaction_within_limits(self):
        """Test can_make_transaction within limits."""
        self.assertTrue(self.payment_stat.can_make_transaction(Decimal("100.00")))

    def test_can_make_transaction_exceeds_daily_limit(self):
        """Test can_make_transaction exceeding daily limit."""
        self.assertFalse(self.payment_stat.can_make_transaction(Decimal("600.00")))

    def test_can_make_transaction_exceeds_monthly_limit(self):
        """Test can_make_transaction exceeding monthly limit."""
        self.assertFalse(self.payment_stat.can_make_transaction(Decimal("6000.00")))

    def test_meta_indexes(self):
        """Test meta indexes exist."""
        meta = PaymentStat._meta
        index_fields = [idx.fields for idx in meta.indexes]
        self.assertIn(['total_payments_amount'], index_fields)
        self.assertIn(['last_transaction_date'], index_fields)


# ============================================================================
# MONEY TRANSFER TESTS
# ============================================================================

class MoneyTransferTest(TestCase):
    """Test cases for MoneyTransfer model."""

    def setUp(self):
        self.sender = User.objects.create_user(
            email="sender@example.com",
            password="testpass123",
        )
        self.sender.phone_number = "+1234567890"
        self.sender.save()

        self.receiver = User.objects.create_user(
            email="receiver@example.com",
            password="testpass123",
        )
        self.receiver.phone_number = "+0987654321"
        self.receiver.save()

        self.bank = Bank.objects.create(
            name="GTBANK",
            code="GTB",
            is_active=True,
        )

        self.sender_account = Account.objects.create(
            user=self.sender,
            bank=self.bank,
            phone_number="+1234567890",
            nuban_number="1234567890",
            account_name="Sender User",
        )

        self.receiver_account = Account.objects.create(
            user=self.receiver,
            bank=self.bank,
            phone_number="+0987654321",
            nuban_number="0987654321",
            account_name="Receiver User",
        )

        self.transfer = MoneyTransfer.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            sender_account=self.sender_account,
            receiver_account=self.receiver_account,
            amount=Decimal("100.00"),
            fee=Decimal("5.00"),
            narration="Test transfer",
            status=Transaction.PENDING,
        )

    def test_create_money_transfer(self):
        """Test creating a MoneyTransfer instance."""
        self.assertIsNotNone(self.transfer.pk)
        self.assertEqual(self.transfer.sender, self.sender)
        self.assertEqual(self.transfer.receiver, self.receiver)
        self.assertEqual(self.transfer.sender_account, self.sender_account)
        self.assertEqual(self.transfer.receiver_account, self.receiver_account)
        self.assertEqual(self.transfer.amount, Decimal("100.00"))
        self.assertEqual(self.transfer.fee, Decimal("5.00"))
        self.assertEqual(self.transfer.narration, "Test transfer")
        self.assertEqual(self.transfer.status, Transaction.PENDING)
        self.assertIsNotNone(self.transfer.reference)

    def test_str_representation(self):
        """Test string representation."""
        sender_name = self.sender.first_name or "Unknown"
        receiver_name = self.receiver.first_name or "Unknown"
        expected = f"{sender_name} to {receiver_name} - $100.00"
        self.assertEqual(str(self.transfer), expected)

    def test_save_generates_reference(self):
        """Test that reference is auto-generated on save."""
        transfer = MoneyTransfer.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            sender_account=self.sender_account,
            receiver_account=self.receiver_account,
            amount=Decimal("50.00"),
        )
        self.assertIsNotNone(transfer.reference)
        self.assertTrue(transfer.reference.startswith("TF-"))

    def test_save_does_not_overwrite_reference(self):
        """Test that existing reference is not overwritten."""
        custom_ref = "CUSTOM-TF-001"
        transfer = MoneyTransfer.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            sender_account=self.sender_account,
            receiver_account=self.receiver_account,
            amount=Decimal("50.00"),
            reference=custom_ref,
        )
        self.assertEqual(transfer.reference, custom_ref)

    def test_money_transfer_status_choices(self):
        """Test money transfer status choices."""
        statuses = [choice[0] for choice in Transaction.STATUS_CHOICES]
        self.assertIn('PENDING', statuses)
        self.assertIn('SUCCESS', statuses)
        self.assertIn('FAILED', statuses)
        self.assertIn('REVERSED', statuses)

    def test_meta_indexes(self):
        """Test meta indexes exist."""
        meta = MoneyTransfer._meta
        index_fields = [idx.fields for idx in meta.indexes]
        self.assertIn(['sender', 'receiver'], index_fields)
        self.assertIn(['amount', 'status'], index_fields)
        self.assertIn(['created_at', 'status'], index_fields)

    def test_transfer_with_bank_reference(self):
        """Test money transfer with bank reference."""
        transfer = MoneyTransfer.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            sender_account=self.sender_account,
            receiver_account=self.receiver_account,
            amount=Decimal("100.00"),
            bank_reference="BANK-REF-123",
        )
        self.assertEqual(transfer.bank_reference, "BANK-REF-123")


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class PaymentIntegrationTest(TestCase):
    """Integration tests for payment models."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        self.user.phone_number = "+1234567890"
        self.user.save()

        self.bank = Bank.objects.create(
            name="GTBANK",
            code="GTB",
            is_active=True,
        )
        self.account = Account.objects.create(
            user=self.user,
            bank=self.bank,
            phone_number="+1234567890",
            nuban_number="1234567890",
            account_name="Test User",
        )
        self.wallet = Wallet.objects.create(
            user=self.user,
            account=self.account,
            wallet_reference="WALLET-001",
            balance=Decimal("1000.00"),
        )

    def test_wallet_and_transaction_integration(self):
        """Test wallet and transaction integration."""
        # Create transaction
        tx = Transaction.objects.create(
            account=self.account,
            amount=Decimal("100.00"),
            type=Transaction.TRANSFER,
            status=Transaction.SUCCESS,
        )

        # Record transaction in wallet
        self.wallet.record_transaction(Decimal("100.00"))
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("1100.00"))
        self.assertEqual(self.wallet.daily_transaction_count, 1)

    def test_wallet_debit_and_transaction_integration(self):
        """Test wallet debit and transaction integration."""
        # Create transaction
        tx = Transaction.objects.create(
            account=self.account,
            amount=Decimal("100.00"),
            type=Transaction.WITHDRAWAL,
            status=Transaction.SUCCESS,
        )

        # Debit wallet
        self.wallet.debit(Decimal("100.00"))
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("900.00"))

    def test_wallet_credit_and_transaction_integration(self):
        """Test wallet credit and transaction integration."""
        # Create transaction
        tx = Transaction.objects.create(
            account=self.account,
            amount=Decimal("200.00"),
            type=Transaction.DEPOSIT,
            status=Transaction.SUCCESS,
        )

        # Credit wallet
        self.wallet.credit(Decimal("200.00"))
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("1200.00"))

    def test_payment_stat_and_transaction_integration(self):
        """Test payment stat and transaction integration."""
        payment_stat = PaymentStat.objects.create(
            user=self.user,
            number_of_payments=0,
            total_payments_amount=Decimal("0.00"),
        )

        # Create transaction
        tx = Transaction.objects.create(
            account=self.account,
            amount=Decimal("100.00"),
            type=Transaction.TRANSFER,
            status=Transaction.SUCCESS,
        )

        # Update payment stat
        payment_stat.number_of_payments += 1
        payment_stat.total_payments_amount += tx.amount
        payment_stat.last_transaction_amount = tx.amount
        payment_stat.last_transaction_date = timezone.now()
        payment_stat.save()

        payment_stat.refresh_from_db()
        self.assertEqual(payment_stat.number_of_payments, 1)
        self.assertEqual(payment_stat.total_payments_amount, Decimal("100.00"))
        self.assertEqual(payment_stat.last_transaction_amount, Decimal("100.00"))


# ============================================================================
# RUNNER
# ============================================================================

if __name__ == "__main__":
    import django
    django.setup()
    from django.test import runner
    runner.DiscoverRunner().run_tests([
        "banking.tests.test_payments"
    ])