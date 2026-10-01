# apps/backend/banking/tests/test_investments.py

"""
Tests for banking investment models.

This module tests:
    - InvestmentProduct: Investment products offered
    - Investment: User's investment records
    - InvestmentEarnings: Earnings from investments
"""

from __future__ import annotations

from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from banking.models.investments import (
    InvestmentProduct,
    Investment,
    InvestmentEarnings,
)
from banking.models.core import Account, Bank
from banking.models.payments import Transaction, Wallet

User = get_user_model()


# ============================================================================
# INVESTMENT PRODUCT TESTS
# ============================================================================

class InvestmentProductTest(TestCase):
    """Test cases for InvestmentProduct model."""

    def setUp(self):
        self.product = InvestmentProduct.objects.create(
            name="Fixed Deposit Plus",
            slug="fixed-deposit-plus",
            product_type="FIXED_DEPOSIT",
            description="High-yield fixed deposit investment",
            risk_level="LOW",
            min_investment=Decimal("10000.00"),
            max_investment=Decimal("1000000.00"),
            min_tenure_days=30,
            max_tenure_days=365,
            default_tenure_days=90,
            interest_rate=Decimal("10.50"),
            interest_frequency="MONTHLY",
            compounding=True,
            compounding_frequency="MONTHLY",
            management_fee=Decimal("1.00"),
            early_withdrawal_fee=Decimal("2.50"),
            is_active=True,
            is_available=True,
            max_capacity=Decimal("50000000.00"),
            available_from=timezone.now() - timedelta(days=1),
            available_until=timezone.now() + timedelta(days=365),
        )

    def test_create_investment_product(self):
        """Test creating an InvestmentProduct instance."""
        self.assertIsNotNone(self.product.pk)
        self.assertEqual(self.product.name, "Fixed Deposit Plus")
        self.assertEqual(self.product.slug, "fixed-deposit-plus")
        self.assertEqual(self.product.product_type, "FIXED_DEPOSIT")
        self.assertEqual(self.product.risk_level, "LOW")
        self.assertEqual(self.product.min_investment, Decimal("10000.00"))
        self.assertEqual(self.product.max_investment, Decimal("1000000.00"))
        self.assertEqual(self.product.min_tenure_days, 30)
        self.assertEqual(self.product.max_tenure_days, 365)
        self.assertEqual(self.product.default_tenure_days, 90)
        self.assertEqual(self.product.interest_rate, Decimal("10.50"))
        self.assertEqual(self.product.interest_frequency, "MONTHLY")
        self.assertTrue(self.product.compounding)
        self.assertEqual(self.product.compounding_frequency, "MONTHLY")
        self.assertEqual(self.product.management_fee, Decimal("1.00"))
        self.assertEqual(self.product.early_withdrawal_fee, Decimal("2.50"))
        self.assertTrue(self.product.is_active)
        self.assertTrue(self.product.is_available)
        self.assertEqual(self.product.max_capacity, Decimal("50000000.00"))

    def test_str_representation(self):
        """Test string representation."""
        expected = "Fixed Deposit Plus (Fixed Deposit)"
        self.assertEqual(str(self.product), expected)

    def test_available_slots(self):
        """Test available_slots property."""
        self.assertEqual(self.product.available_slots, Decimal("50000000.00"))

        # Add some investments
        self.product.total_invested = Decimal("1000000.00")
        self.product.save()
        self.assertEqual(self.product.available_slots, Decimal("49000000.00"))

        # No max capacity
        self.product.max_capacity = None
        self.product.save()
        self.assertIsNone(self.product.available_slots)

    def test_meta_ordering(self):
        """Test meta ordering."""
        InvestmentProduct.objects.create(
            name="Another Product",
            slug="another-product",
            product_type="SAVINGS",
            description="Savings product",
            risk_level="VERY_LOW",
            min_investment=Decimal("1000.00"),
            min_tenure_days=1,
            max_tenure_days=30,
            default_tenure_days=7,
            interest_rate=Decimal("5.00"),
            available_from=timezone.now() - timedelta(days=1),
        )

        products = InvestmentProduct.objects.all()
        self.assertEqual(products[0].name, "Another Product")  # Most recent first

    def test_unique_slug(self):
        """Test that slug must be unique."""
        with self.assertRaises(IntegrityError):
            InvestmentProduct.objects.create(
                name="Duplicate Product",
                slug="fixed-deposit-plus",
                product_type="OTHER",
                description="Duplicate",
                risk_level="MEDIUM",
                min_investment=Decimal("1000.00"),
                min_tenure_days=1,
                max_tenure_days=30,
                default_tenure_days=7,
                interest_rate=Decimal("5.00"),
                available_from=timezone.now() - timedelta(days=1),
            )


# ============================================================================
# INVESTMENT TESTS
# ============================================================================

class InvestmentTest(TestCase):
    """Test cases for Investment model."""

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
            balance=Decimal("100000.00"),
        )
        self.product = InvestmentProduct.objects.create(
            name="Fixed Deposit Plus",
            slug="fixed-deposit-plus",
            product_type="FIXED_DEPOSIT",
            description="High-yield fixed deposit investment",
            risk_level="LOW",
            min_investment=Decimal("10000.00"),
            max_investment=Decimal("1000000.00"),
            min_tenure_days=30,
            max_tenure_days=365,
            default_tenure_days=90,
            interest_rate=Decimal("10.50"),
            interest_frequency="AT_MATURITY",
            compounding=False,
            management_fee=Decimal("1.00"),
            early_withdrawal_fee=Decimal("2.50"),
            is_active=True,
            is_available=True,
            available_from=timezone.now() - timedelta(days=1),
        )
        self.investment = Investment.objects.create(
            user=self.user,
            product=self.product,
            wallet=self.wallet,
            amount=Decimal("50000.00"),
            tenure_days=90,
            interest_rate=Decimal("10.50"),
            start_date=timezone.now() - timedelta(days=30),
            maturity_date=timezone.now() + timedelta(days=60),
            interest_payment_date=timezone.now() + timedelta(days=60),
            expected_return=Decimal("1294.52"),
            status="ACTIVE",
            investment_reference="INV-20240101-ABC123",
        )

    def test_create_investment(self):
        """Test creating an Investment instance."""
        self.assertIsNotNone(self.investment.pk)
        self.assertEqual(self.investment.user, self.user)
        self.assertEqual(self.investment.product, self.product)
        self.assertEqual(self.investment.wallet, self.wallet)
        self.assertEqual(self.investment.amount, Decimal("50000.00"))
        self.assertEqual(self.investment.tenure_days, 90)
        self.assertEqual(self.investment.interest_rate, Decimal("10.50"))
        self.assertEqual(self.investment.expected_return, Decimal("1294.52"))
        self.assertEqual(self.investment.status, "ACTIVE")
        self.assertEqual(self.investment.investment_reference, "INV-20240101-ABC123")

    def test_str_representation(self):
        """Test string representation."""
        expected = f"{self.user.email} - Fixed Deposit Plus - ₦50000.00"
        self.assertEqual(str(self.investment), expected)

    def test_calculate_return(self):
        """Test calculate_return method."""
        # 30 days held at 10.5% on 50,000
        expected_return = Decimal("431.51")  # Approximate
        calculated_return = self.investment.calculate_return()
        self.assertAlmostEqual(calculated_return, Decimal("431.51"), places=2)

    def test_is_matured(self):
        """Test is_matured method."""
        self.assertFalse(self.investment.is_matured())

        # Matured investment - set maturity date in the past
        matured_investment = Investment.objects.create(
            user=self.user,
            product=self.product,
            wallet=self.wallet,
            amount=Decimal("10000.00"),
            tenure_days=30,
            interest_rate=Decimal("10.00"),
            start_date=timezone.now() - timedelta(days=60),
            maturity_date=timezone.now() - timedelta(days=1),  # Past date
            interest_payment_date=timezone.now() - timedelta(days=1),
            expected_return=Decimal("82.19"),
            status="ACTIVE",
            investment_reference="INV-20240101-DEF456",
        )
        self.assertTrue(matured_investment.is_matured())

    def test_meta_indexes(self):
        """Test meta indexes exist."""
        meta = Investment._meta
        index_fields = [idx.fields for idx in meta.indexes]
        self.assertIn(['user', 'status'], index_fields)
        self.assertIn(['product', 'status'], index_fields)
        self.assertIn(['maturity_date'], index_fields)
        self.assertIn(['investment_reference'], index_fields)


# ============================================================================
# INVESTMENT EARNINGS TESTS
# ============================================================================

class InvestmentEarningsTest(TestCase):
    """Test cases for InvestmentEarnings model."""

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
            balance=Decimal("100000.00"),
        )
        self.product = InvestmentProduct.objects.create(
            name="Fixed Deposit Plus",
            slug="fixed-deposit-plus",
            product_type="FIXED_DEPOSIT",
            description="High-yield fixed deposit investment",
            risk_level="LOW",
            min_investment=Decimal("10000.00"),
            max_investment=Decimal("1000000.00"),
            min_tenure_days=30,
            max_tenure_days=365,
            default_tenure_days=90,
            interest_rate=Decimal("10.50"),
            interest_frequency="AT_MATURITY",
            compounding=False,
            management_fee=Decimal("1.00"),
            early_withdrawal_fee=Decimal("2.50"),
            is_active=True,
            is_available=True,
            available_from=timezone.now() - timedelta(days=1),
        )
        self.investment = Investment.objects.create(
            user=self.user,
            product=self.product,
            wallet=self.wallet,
            amount=Decimal("50000.00"),
            tenure_days=90,
            interest_rate=Decimal("10.50"),
            start_date=timezone.now() - timedelta(days=30),
            maturity_date=timezone.now() + timedelta(days=60),
            interest_payment_date=timezone.now() + timedelta(days=60),
            expected_return=Decimal("1294.52"),
            status="ACTIVE",
            investment_reference="INV-20240101-ABC123",
        )
        self.transaction = Transaction.objects.create(
            account=self.account,
            amount=Decimal("431.51"),
            type=Transaction.TRANSFER,
        )
        self.earnings = InvestmentEarnings.objects.create(
            investment=self.investment,
            user=self.user,
            transaction=self.transaction,
            earning_type="INTEREST",
            amount=Decimal("431.51"),
            description="Monthly interest payment",
            period_start=timezone.now() - timedelta(days=30),
            period_end=timezone.now(),
        )

    def test_create_investment_earnings(self):
        """Test creating an InvestmentEarnings instance."""
        self.assertIsNotNone(self.earnings.pk)
        self.assertEqual(self.earnings.investment, self.investment)
        self.assertEqual(self.earnings.user, self.user)
        self.assertEqual(self.earnings.transaction, self.transaction)
        self.assertEqual(self.earnings.earning_type, "INTEREST")
        self.assertEqual(self.earnings.amount, Decimal("431.51"))
        self.assertEqual(self.earnings.description, "Monthly interest payment")

    def test_str_representation(self):
        """Test string representation."""
        # InvestmentEarnings doesn't have a custom __str__, check the model
        self.assertIsNotNone(str(self.earnings))

    def test_earning_types(self):
        """Test earning type choices."""
        choices = InvestmentEarnings.EARNING_TYPES
        choice_values = [choice[0] for choice in choices]
        self.assertIn('INTEREST', choice_values)
        self.assertIn('BONUS', choice_values)
        self.assertIn('REFERRAL', choice_values)
        self.assertIn('OTHER', choice_values)

    def test_meta_indexes(self):
        """Test meta indexes exist."""
        meta = InvestmentEarnings._meta
        index_fields = [idx.fields for idx in meta.indexes]
        self.assertIn(['investment', 'earning_type'], index_fields)
        self.assertIn(['user', 'paid_at'], index_fields)


# ============================================================================
# INTEGRATION TESTS - FIXED
# ============================================================================

class InvestmentIntegrationTest(TestCase):
    """Integration tests for investment models."""

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
            balance=Decimal("100000.00"),
        )
        self.product = InvestmentProduct.objects.create(
            name="Fixed Deposit Plus",
            slug="fixed-deposit-plus",
            product_type="FIXED_DEPOSIT",
            description="High-yield fixed deposit investment",
            risk_level="LOW",
            min_investment=Decimal("10000.00"),
            max_investment=Decimal("1000000.00"),
            min_tenure_days=30,
            max_tenure_days=365,
            default_tenure_days=90,
            interest_rate=Decimal("10.50"),
            interest_frequency="MONTHLY",
            is_active=True,
            is_available=True,
            available_from=timezone.now() - timedelta(days=1),
            early_withdrawal_fee=Decimal("2.50"),  # Make sure this is set
        )

    def test_investment_workflow(self):
        """Test complete investment workflow from creation to maturity."""
        # Create investment
        investment = Investment.objects.create(
            user=self.user,
            product=self.product,
            wallet=self.wallet,
            amount=Decimal("50000.00"),
            tenure_days=90,
            interest_rate=self.product.interest_rate,
            start_date=timezone.now(),
            maturity_date=timezone.now() + timedelta(days=90),
            interest_payment_date=timezone.now() + timedelta(days=90),
            expected_return=Decimal("1294.52"),
            status="ACTIVE",
            investment_reference="INV-20240101-INT001",
        )

        self.assertEqual(investment.status, "ACTIVE")
        self.assertFalse(investment.is_matured())

        # Update wallet balance
        self.wallet.balance = Decimal("50000.00")
        self.wallet.save()

        # Calculate return
        return_amount = investment.calculate_return()
        self.assertIsNotNone(return_amount)

        # Mark as matured - set maturity date to past and mark status
        investment.maturity_date = timezone.now() - timedelta(days=1)  # Past date
        investment.status = "MATURED"
        investment.actual_return = return_amount
        investment.total_return = investment.amount + return_amount
        investment.save()

        self.assertEqual(investment.status, "MATURED")
        self.assertTrue(investment.is_matured())

    def test_investment_earnings_workflow(self):
        """Test investment earnings workflow."""
        # Create investment
        investment = Investment.objects.create(
            user=self.user,
            product=self.product,
            wallet=self.wallet,
            amount=Decimal("50000.00"),
            tenure_days=90,
            interest_rate=self.product.interest_rate,
            start_date=timezone.now() - timedelta(days=30),
            maturity_date=timezone.now() + timedelta(days=60),
            interest_payment_date=timezone.now(),
            expected_return=Decimal("1294.52"),
            status="ACTIVE",
            investment_reference="INV-20240101-INT002",
        )

        # Create transaction for earnings
        transaction = Transaction.objects.create(
            account=self.account,
            amount=Decimal("431.51"),
            type=Transaction.TRANSFER,
        )

        # Record earnings
        earnings = InvestmentEarnings.objects.create(
            investment=investment,
            user=self.user,
            transaction=transaction,
            earning_type="INTEREST",
            amount=Decimal("431.51"),
            description="Monthly interest payment",
            period_start=timezone.now() - timedelta(days=30),
            period_end=timezone.now(),
        )

        self.assertEqual(earnings.earning_type, "INTEREST")
        self.assertEqual(earnings.amount, Decimal("431.51"))

        # Update investment interest paid
        investment.interest_paid += earnings.amount
        investment.save()
        self.assertEqual(investment.interest_paid, Decimal("431.51"))

    def test_investment_early_withdrawal(self):
        """Test early withdrawal of investment."""
        investment = Investment.objects.create(
            user=self.user,
            product=self.product,
            wallet=self.wallet,
            amount=Decimal("50000.00"),
            tenure_days=90,
            interest_rate=self.product.interest_rate,
            start_date=timezone.now() - timedelta(days=30),
            maturity_date=timezone.now() + timedelta(days=60),
            interest_payment_date=timezone.now() + timedelta(days=60),
            expected_return=Decimal("1294.52"),
            status="ACTIVE",
            investment_reference="INV-20240101-INT003",
        )

        # Calculate return with early withdrawal fee
        # Use Decimal for division to avoid float issues
        early_fee = investment.amount * (Decimal(str(self.product.early_withdrawal_fee)) / Decimal(100))
        return_amount = investment.calculate_return()
        net_return = return_amount - early_fee

        # Mark as withdrawn - SET THE FEE ON THE INVESTMENT OBJECT BEFORE SAVING
        investment.status = "WITHDRAWN"
        investment.early_withdrawal = True
        investment.early_withdrawal_fee = early_fee  # IMPORTANT: Set before save
        investment.actual_return = net_return if net_return > 0 else Decimal("0.00")
        investment.total_return = investment.amount + investment.actual_return
        investment.withdrawal_date = timezone.now()
        investment.save()

        # Refresh from database to ensure it was saved
        investment.refresh_from_db()

        self.assertEqual(investment.status, "WITHDRAWN")
        self.assertTrue(investment.early_withdrawal)
        self.assertEqual(investment.early_withdrawal_fee, Decimal("1250.00"))
        self.assertIsNotNone(investment.withdrawal_date)

    def test_investment_cancellation(self):
        """Test cancellation of pending investment."""
        investment = Investment.objects.create(
            user=self.user,
            product=self.product,
            wallet=self.wallet,
            amount=Decimal("50000.00"),
            tenure_days=90,
            interest_rate=self.product.interest_rate,
            start_date=timezone.now(),
            maturity_date=timezone.now() + timedelta(days=90),
            interest_payment_date=timezone.now() + timedelta(days=90),
            expected_return=Decimal("1294.52"),
            status="PENDING",
            investment_reference="INV-20240101-INT004",
        )

        # Cancel investment
        investment.status = "CANCELLED"
        investment.status_reason = "User cancelled"
        investment.save()

        self.assertEqual(investment.status, "CANCELLED")
        self.assertEqual(investment.status_reason, "User cancelled")

# ============================================================================
# RUNNER
# ============================================================================

if __name__ == "__main__":
    import django
    django.setup()
    from django.test import runner
    runner.DiscoverRunner().run_tests([
        "banking.tests.test_investments"
    ])