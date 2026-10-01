# apps/backend/banking/tests/test_bill_payments.py

"""
Tests for banking bill payment models.

This module tests:
    - BillCategory: Bill categories/types
    - Biller: Biller/provider information
    - BillProvider: Utility bill providers
    - BillAccount: Customer's bill accounts
    - Bill: Individual bill instance
    - BillPayment: Record of bill payment transactions
    - AirtimePurchase: Airtime top-up transactions
    - DataBundlePurchase: Data bundle purchases
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

from banking.models.bill_payments import (
    Bill,
    BillAccount,
    BillCategory,
    Biller,
    BillPayment,
    BillProvider,
    AirtimePurchase,
    DataBundlePurchase,
)
from banking.models.core import Account, Bank
from banking.models.payments import Transaction

User = get_user_model()


# ============================================================================
# BILL CATEGORY TESTS
# ============================================================================

class BillCategoryTest(TestCase):
    """Test cases for BillCategory model."""

    def setUp(self):
        self.category = BillCategory.objects.create(
            name="Electricity",
            slug="electricity",
            description="Electricity bills",
            icon="⚡",
            is_active=True,
        )

    def test_create_bill_category(self):
        """Test creating a BillCategory instance."""
        self.assertIsNotNone(self.category.pk)
        self.assertEqual(self.category.name, "Electricity")
        self.assertEqual(self.category.slug, "electricity")
        self.assertEqual(self.category.description, "Electricity bills")
        self.assertEqual(self.category.icon, "⚡")
        self.assertTrue(self.category.is_active)

    def test_str_representation(self):
        """Test string representation."""
        self.assertEqual(str(self.category), "Electricity")

    def test_unique_name(self):
        """Test that name must be unique."""
        with self.assertRaises(IntegrityError):
            BillCategory.objects.create(
                name="Electricity",
                slug="electricity-2",
            )

    def test_unique_slug(self):
        """Test that slug must be unique."""
        with self.assertRaises(IntegrityError):
            BillCategory.objects.create(
                name="Electricity 2",
                slug="electricity",
            )

    def test_meta_ordering(self):
        """Test meta ordering."""
        BillCategory.objects.create(
            name="Water",
            slug="water",
        )
        BillCategory.objects.create(
            name="Internet",
            slug="internet",
        )

        categories = BillCategory.objects.all()
        self.assertEqual(categories[0].name, "Electricity")
        self.assertEqual(categories[1].name, "Internet")
        self.assertEqual(categories[2].name, "Water")


# ============================================================================
# BILLER TESTS
# ============================================================================

class BillerTest(TestCase):
    """Test cases for Biller model."""

    def setUp(self):
        self.category = BillCategory.objects.create(
            name="Electricity",
            slug="electricity",
        )
        self.biller = Biller.objects.create(
            name="IKEDC",
            slug="ikedc",
            category=self.category,
            code="IKEDC001",
            description="Ikeja Electric",
            fee_percentage=Decimal("1.50"),
            fee_fixed=Decimal("50.00"),
            min_amount=Decimal("100.00"),
            max_amount=Decimal("500000.00"),
            is_active=True,
        )

    def test_create_biller(self):
        """Test creating a Biller instance."""
        self.assertIsNotNone(self.biller.pk)
        self.assertEqual(self.biller.name, "IKEDC")
        self.assertEqual(self.biller.slug, "ikedc")
        self.assertEqual(self.biller.category, self.category)
        self.assertEqual(self.biller.code, "IKEDC001")
        self.assertEqual(self.biller.fee_percentage, Decimal("1.50"))
        self.assertEqual(self.biller.fee_fixed, Decimal("50.00"))
        self.assertEqual(self.biller.min_amount, Decimal("100.00"))
        self.assertEqual(self.biller.max_amount, Decimal("500000.00"))
        self.assertTrue(self.biller.is_active)

    def test_str_representation(self):
        """Test string representation."""
        expected = "IKEDC (Electricity)"
        self.assertEqual(str(self.biller), expected)

    def test_calculate_fee(self):
        """Test fee calculation."""
        # Amount with percentage fee only
        amount = Decimal("1000.00")
        fee = self.biller.calculate_fee(amount)
        expected_fee = Decimal("15.00") + Decimal("50.00")  # 1.5% + 50
        self.assertEqual(fee, expected_fee)

        # Amount with no percentage fee
        self.biller.fee_percentage = Decimal("0.00")
        self.biller.save()
        fee = self.biller.calculate_fee(amount)
        self.assertEqual(fee, Decimal("50.00"))

        # Amount with no fees
        self.biller.fee_fixed = Decimal("0.00")
        self.biller.save()
        fee = self.biller.calculate_fee(amount)
        self.assertEqual(fee, Decimal("0.00"))

    def test_validate_amount_valid(self):
        """Test validate_amount with valid amount."""
        try:
            self.biller.validate_amount(Decimal("1000.00"))
        except ValidationError:
            self.fail("validate_amount raised ValidationError unexpectedly")

    def test_validate_amount_below_min(self):
        """Test validate_amount with amount below minimum."""
        with self.assertRaises(ValidationError) as exc:
            self.biller.validate_amount(Decimal("50.00"))
        self.assertIn("Amount must be at least ₦100.00", str(exc.exception))

    def test_validate_amount_above_max(self):
        """Test validate_amount with amount above maximum."""
        with self.assertRaises(ValidationError) as exc:
            self.biller.validate_amount(Decimal("600000.00"))
        self.assertIn("Amount cannot exceed ₦500,000.00", str(exc.exception))

    def test_validate_amount_no_max(self):
        """Test validate_amount with no maximum amount."""
        self.biller.max_amount = None
        self.biller.save()
        try:
            self.biller.validate_amount(Decimal("1000000.00"))
        except ValidationError:
            self.fail("validate_amount raised ValidationError unexpectedly")


# ============================================================================
# BILL PROVIDER TESTS
# ============================================================================

class BillProviderTest(TestCase):
    """Test cases for BillProvider model."""

    def setUp(self):
        self.provider = BillProvider.objects.create(
            name="IKEDC",
            provider_type="ELECTRICITY",
            provider_code="IKEDC001",
            is_active=True,
            api_endpoint="https://api.ikedc.com",
            validation_required=True,
            supports_auto_debit=True,
            supports_one_time_payment=True,
            service_states=["Lagos", "Ogun"],
            service_cities=["Ikeja", "Lagos Island"],
        )

    def test_create_bill_provider(self):
        """Test creating a BillProvider instance."""
        self.assertIsNotNone(self.provider.pk)
        self.assertEqual(self.provider.name, "IKEDC")
        self.assertEqual(self.provider.provider_type, "ELECTRICITY")
        self.assertEqual(self.provider.provider_code, "IKEDC001")
        self.assertTrue(self.provider.is_active)
        self.assertEqual(self.provider.api_endpoint, "https://api.ikedc.com")
        self.assertTrue(self.provider.validation_required)
        self.assertTrue(self.provider.supports_auto_debit)
        self.assertTrue(self.provider.supports_one_time_payment)
        self.assertEqual(self.provider.service_states, ["Lagos", "Ogun"])
        self.assertEqual(self.provider.service_cities, ["Ikeja", "Lagos Island"])

    def test_str_representation(self):
        """Test string representation."""
        expected = "IKEDC (Electricity)"
        self.assertEqual(str(self.provider), expected)

    def test_unique_provider_code(self):
        """Test that provider_code must be unique."""
        with self.assertRaises(IntegrityError):
            BillProvider.objects.create(
                name="Other Provider",
                provider_type="WATER",
                provider_code="IKEDC001",
            )


# ============================================================================
# BILL ACCOUNT TESTS
# ============================================================================

class BillAccountTest(TestCase):
    """Test cases for BillAccount model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        self.provider = BillProvider.objects.create(
            name="IKEDC",
            provider_type="ELECTRICITY",
            provider_code="IKEDC001",
        )
        self.bill_account = BillAccount.objects.create(
            user=self.user,
            provider=self.provider,
            account_number="1234567890",
            account_name="Test Account",
            customer_name="Test Customer",
            address="123 Test Street",
            state="Lagos",
            city="Ikeja",
            auto_pay_enabled=True,
            auto_pay_threshold=Decimal("1000.00"),
            is_validated=True,
        )

    def test_create_bill_account(self):
        """Test creating a BillAccount instance."""
        self.assertIsNotNone(self.bill_account.pk)
        self.assertEqual(self.bill_account.user, self.user)
        self.assertEqual(self.bill_account.provider, self.provider)
        self.assertEqual(self.bill_account.account_number, "1234567890")
        self.assertEqual(self.bill_account.account_name, "Test Account")
        self.assertEqual(self.bill_account.customer_name, "Test Customer")
        self.assertEqual(self.bill_account.address, "123 Test Street")
        self.assertEqual(self.bill_account.state, "Lagos")
        self.assertEqual(self.bill_account.city, "Ikeja")
        self.assertTrue(self.bill_account.auto_pay_enabled)
        self.assertEqual(self.bill_account.auto_pay_threshold, Decimal("1000.00"))
        self.assertTrue(self.bill_account.is_validated)

    def test_str_representation(self):
        """Test string representation."""
        expected = "1234567890 - IKEDC"
        self.assertEqual(str(self.bill_account), expected)

    def test_unique_together(self):
        """Test unique_together constraint."""
        with self.assertRaises(IntegrityError):
            BillAccount.objects.create(
                user=self.user,
                provider=self.provider,
                account_number="1234567890",
                account_name="Another Account",
            )


# ============================================================================
# BILL TESTS
# ============================================================================

class BillTest(TestCase):
    """Test cases for Bill model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        self.provider = BillProvider.objects.create(
            name="IKEDC",
            provider_type="ELECTRICITY",
            provider_code="IKEDC001",
        )
        self.bill_account = BillAccount.objects.create(
            user=self.user,
            provider=self.provider,
            account_number="1234567890",
            account_name="Test Account",
            state="Lagos",
            city="Ikeja",
        )
        self.bill = Bill.objects.create(
            bill_account=self.bill_account,
            billing_period_start=timezone.now().date() - timedelta(days=30),
            billing_period_end=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=14),
            total_amount=Decimal("5000.00"),
            breakdown={"energy_charge": 4500, "tax": 500},
        )

    def test_create_bill(self):
        """Test creating a Bill instance."""
        self.assertIsNotNone(self.bill.pk)
        self.assertEqual(self.bill.bill_account, self.bill_account)
        self.assertIsNotNone(self.bill.bill_reference)
        self.assertEqual(self.bill.total_amount, Decimal("5000.00"))
        self.assertEqual(self.bill.amount_paid, Decimal("0.00"))
        self.assertEqual(self.bill.outstanding_amount, Decimal("5000.00"))
        self.assertEqual(self.bill.status, "PENDING")
        self.assertFalse(self.bill.is_auto_paid)

    def test_str_representation(self):
        """Test string representation."""
        expected = f"Bill {self.bill.bill_reference} - ₦5000.00"
        self.assertEqual(str(self.bill), expected)

    def test_save_generates_reference(self):
        """Test that reference is auto-generated on save."""
        bill = Bill.objects.create(
            bill_account=self.bill_account,
            billing_period_start=timezone.now().date() - timedelta(days=30),
            billing_period_end=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=14),
            total_amount=Decimal("1000.00"),
        )
        self.assertIsNotNone(bill.bill_reference)
        self.assertTrue(bill.bill_reference.startswith("BILL-"))

    def test_save_updates_outstanding_amount(self):
        """Test that outstanding_amount is updated on save."""
        self.bill.amount_paid = Decimal("2000.00")
        self.bill.save()
        self.bill.refresh_from_db()
        self.assertEqual(self.bill.outstanding_amount, Decimal("3000.00"))

    def test_save_updates_status_to_paid(self):
        """Test that status updates to PAID when fully paid."""
        self.bill.amount_paid = Decimal("5000.00")
        self.bill.save()
        self.bill.refresh_from_db()
        self.assertEqual(self.bill.status, "PAID")

    def test_save_updates_status_to_overdue(self):
        """Test that status updates to OVERDUE when past due date."""
        self.bill.due_date = timezone.now().date() - timedelta(days=1)
        self.bill.save()
        self.bill.refresh_from_db()
        self.assertEqual(self.bill.status, "OVERDUE")



# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class BillPaymentIntegrationTest(TestCase):
    """Integration tests for bill payment models."""

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
        self.category = BillCategory.objects.create(
            name="Electricity",
            slug="electricity",
        )
        self.biller = Biller.objects.create(
            name="IKEDC",
            slug="ikedc",
            category=self.category,
            code="IKEDC001",
            fee_percentage=Decimal("1.50"),
            fee_fixed=Decimal("50.00"),
        )
        self.transaction = Transaction.objects.create(
            account=self.account,
            amount=Decimal("1000.00"),
            type=Transaction.TRANSFER,
        )

    def test_bill_payment_workflow(self):
        """Test complete bill payment workflow."""
        # Create bill payment
        payment = BillPayment.objects.create(
            user=self.user,
            account=self.account,
            transaction=self.transaction,
            biller=self.biller,
            bill_type=BillPayment.ELECTRICITY,
            provider="IKEDC",
            customer_id="1234567890",
            amount=Decimal("1000.00"),
            reference="BP-20240101-INT001",
            status=BillPayment.PENDING,
        )

        # Validate
        payment.mark_validating()
        self.assertEqual(payment.status, BillPayment.VALIDATING)

        # Process
        payment.mark_processing()
        self.assertEqual(payment.status, BillPayment.PROCESSING)

        # Success
        payment.mark_success()
        self.assertEqual(payment.status, BillPayment.SUCCESS)
        self.assertIsNotNone(payment.completed_at)

    def test_bill_payment_retry_workflow(self):
        """Test bill payment retry workflow."""
        payment = BillPayment.objects.create(
            user=self.user,
            account=self.account,
            transaction=self.transaction,
            biller=self.biller,
            bill_type=BillPayment.ELECTRICITY,
            provider="IKEDC",
            customer_id="1234567890",
            amount=Decimal("1000.00"),
            reference="BP-20240101-INT002",
            status=BillPayment.FAILED,
            retry_count=1,
        )

        self.assertTrue(payment.can_retry)
        payment.increment_retry()
        self.assertEqual(payment.retry_count, 2)

        payment.status = BillPayment.PENDING
        payment.save()
        self.assertTrue(payment.is_pending)

    def test_airtime_purchase_workflow(self):
        """Test complete airtime purchase workflow."""
        # Create airtime purchase
        airtime = AirtimePurchase.objects.create(
            user=self.user,
            account=self.account,
            transaction=self.transaction,
            phone_number="08012345678",
            operator=AirtimePurchase.MTN,
            amount=Decimal("100.00"),
            reference="AT-20240101-INT001",
            status=AirtimePurchase.PENDING,
        )

        # Process
        airtime.mark_processing()
        self.assertEqual(airtime.status, AirtimePurchase.PROCESSING)

        # Success
        airtime.mark_success("PROV-123")
        self.assertEqual(airtime.status, AirtimePurchase.SUCCESS)
        self.assertIsNotNone(airtime.completed_at)
        self.assertEqual(airtime.provider_reference, "PROV-123")

    def test_bill_category_biller_integration(self):
        """Test BillCategory and Biller integration."""
        # Category should have billers
        billers = self.category.billers.all()
        self.assertEqual(billers.count(), 1)
        self.assertEqual(billers.first(), self.biller)

        # Biller should have category
        self.assertEqual(self.biller.category, self.category)



# ============================================================================
# DATA BUNDLE PURCHASE TESTS - FIXED
# ============================================================================

class DataBundlePurchaseTest(TestCase):
    """Test cases for DataBundlePurchase model."""

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
        self.transaction = Transaction.objects.create(
            account=self.account,
            amount=Decimal("500.00"),
            type=Transaction.TRANSFER,
        )
        self.data_bundle = DataBundlePurchase.objects.create(
            user=self.user,
            transaction=self.transaction,
            phone_number="08012345678",
            operator=AirtimePurchase.MTN,
            bundle_name="Data Plus",
            data_amount="2GB",
            data_type="MONTHLY",
            price=Decimal("500.00"),
            validity_days=30,
            status='PENDING',  # FIXED: Use string literal instead of DataBundlePurchase.PENDING
        )

    def test_create_data_bundle_purchase(self):
        """Test creating a DataBundlePurchase instance."""
        self.assertIsNotNone(self.data_bundle.pk)
        self.assertEqual(self.data_bundle.user, self.user)
        self.assertEqual(self.data_bundle.transaction, self.transaction)
        self.assertEqual(self.data_bundle.phone_number, "08012345678")
        self.assertEqual(self.data_bundle.operator, AirtimePurchase.MTN)
        self.assertEqual(self.data_bundle.bundle_name, "Data Plus")
        self.assertEqual(self.data_bundle.data_amount, "2GB")
        self.assertEqual(self.data_bundle.data_type, "MONTHLY")
        self.assertEqual(self.data_bundle.price, Decimal("500.00"))
        self.assertEqual(self.data_bundle.validity_days, 30)
        self.assertEqual(self.data_bundle.status, "PENDING")

    def test_str_representation(self):
        """Test string representation."""
        expected = "MTN - Data Plus - ₦500.00"
        self.assertEqual(str(self.data_bundle), expected)


# ============================================================================
# BILL PAYMENT TESTS - FIXED
# ============================================================================


class BillPaymentTest(TestCase):
    """Test cases for BillPayment model."""

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
        self.category = BillCategory.objects.create(
            name="Electricity",
            slug="electricity",
        )
        self.biller = Biller.objects.create(
            name="IKEDC",
            slug="ikedc",
            category=self.category,
            code="IKEDC001",
            fee_percentage=Decimal("1.50"),
            fee_fixed=Decimal("15.00"),
        )
        self.transaction = Transaction.objects.create(
            account=self.account,
            amount=Decimal("1000.00"),
            type=Transaction.TRANSFER,
        )
        self.bill_payment = BillPayment.objects.create(
            user=self.user,
            account=self.account,
            transaction=self.transaction,
            biller=self.biller,
            bill_type=BillPayment.ELECTRICITY,
            provider="IKEDC",
            customer_id="1234567890",
            customer_name="Test Customer",
            amount=Decimal("1000.00"),
            fee=Decimal("15.00"),
            reference="BP-20240101-ABC123",
            status=BillPayment.PENDING,
            metadata={},  # Add this to provide a default value
        )

    def test_clean_valid(self):
        """Test clean() with valid data."""
        try:
            self.bill_payment.full_clean()
        except ValidationError as exc:
            self.fail(f"clean() raised ValidationError unexpectedly: {exc}")
# ============================================================================
# AIRTIME PURCHASE TESTS - FIXED
# ============================================================================

class AirtimePurchaseTest(TestCase):
    """Test cases for AirtimePurchase model."""

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
        self.transaction = Transaction.objects.create(
            account=self.account,
            amount=Decimal("50.00"),
            type=Transaction.TRANSFER,
        )
        self.airtime = AirtimePurchase.objects.create(
            user=self.user,
            account=self.account,
            transaction=self.transaction,
            phone_number="08012345678",
            operator=AirtimePurchase.MTN,
            amount=Decimal("50.00"),
            fee=Decimal("5.00"),
            reference="AT-20240101-ABC123",
            status=AirtimePurchase.PENDING,
        )

    def test_calculate_fee(self):
        """Test calculate_fee method."""
        # Amount = 50, should be 5.00
        fee = self.airtime.calculate_fee()
        self.assertEqual(fee, Decimal("5.00"))

        # Amount between 51 and 100
        self.airtime.amount = Decimal("75.00")
        self.airtime.save()
        fee = self.airtime.calculate_fee()
        self.assertEqual(fee, Decimal("7.00"))

        # Amount between 101 and 500
        self.airtime.amount = Decimal("200.00")
        self.airtime.save()
        fee = self.airtime.calculate_fee()
        self.assertEqual(fee, Decimal("10.00"))

        # Amount between 501 and 1000
        self.airtime.amount = Decimal("750.00")
        self.airtime.save()
        fee = self.airtime.calculate_fee()
        self.assertEqual(fee, Decimal("15.00"))

        # Amount > 1000
        self.airtime.amount = Decimal("1500.00")
        self.airtime.save()
        fee = self.airtime.calculate_fee()
        self.assertEqual(fee, Decimal("20.00"))
     
# ============================================================================
# RUNNER
# ============================================================================

if __name__ == "__main__":
    import django
    django.setup()
    from django.test import runner
    runner.DiscoverRunner().run_tests([
        "banking.tests.test_bill_payments"
    ])