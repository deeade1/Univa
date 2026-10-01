"""
Tests for Univa Wallet Gateway API.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from banking.models.core import Account, Bank
from banking.models.payments import Wallet
from payment.gateways.univa.api import UnivaWalletAPI

User = get_user_model()


class UnivaWalletAPITest(TestCase):
    """Test cases for Univa Wallet API."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
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
            balance=Decimal("50000.00"),
            status="ACTIVE",
        )

    def test_get_wallet_balance(self):
        """Test getting wallet balance."""
        result = UnivaWalletAPI.get_wallet_balance(self.user)

        self.assertTrue(result["success"])
        self.assertEqual(result["balance"], Decimal("50000.00"))
        self.assertEqual(result["currency"], "NGN")
        self.assertTrue(result["is_active"])

    def test_initiate_payment_success(self):
        """Test successful wallet payment."""
        result = UnivaWalletAPI.initiate_payment(
            user=self.user,
            amount=Decimal("1000.00"),
            payment_reference="PAY-123",
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["amount"], Decimal("1000.00"))
        self.assertIsNotNone(result.get("reference"))

        # Verify wallet balance was debited
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("49000.00"))

    def test_initiate_payment_insufficient_balance(self):
        """Test payment with insufficient balance."""
        result = UnivaWalletAPI.initiate_payment(
            user=self.user,
            amount=Decimal("100000.00"),
            payment_reference="PAY-123",
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "INSUFFICIENT_BALANCE")

    def test_initiate_payment_invalid_amount(self):
        """Test payment with invalid amount."""
        result = UnivaWalletAPI.initiate_payment(
            user=self.user,
            amount=Decimal("0.00"),
            payment_reference="PAY-123",
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "AMOUNT_INVALID")

    def test_process_refund_success(self):
        """Test successful wallet refund."""
        result = UnivaWalletAPI.process_refund(
            user=self.user,
            amount=Decimal("500.00"),
            payment_reference="REF-123",
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["amount"], Decimal("500.00"))

        # Verify wallet balance was credited
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("50500.00"))


__all__ = [
    "UnivaWalletAPITest",
]