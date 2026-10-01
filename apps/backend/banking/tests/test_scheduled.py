# apps/backend/banking/tests/test_scheduled.py

"""
Tests for banking scheduled models.

This module tests:
    - ScheduledPayment: Standing orders, recurring transfers, bill payments
    - CreditProduct: Credit products like Quick Loans, Overdrafts
    - SupportTicket: Customer support ticketing system
    - APIKey: API keys for third-party integrations
    - RemittanceProvider: International money transfer providers
    - InternationalTransfer: International money transfer record
    - ExchangeRate: Real-time exchange rates for remittance
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

from banking.models.scheduled import (
    ScheduledPayment,
    CreditProduct,
    SupportTicket,
    APIKey,
    RemittanceProvider,
    InternationalTransfer,
    ExchangeRate,
)
from banking.models.core import Account, Bank
from banking.models.merchant import Merchant

User = get_user_model()


# ============================================================================
# SCHEDULED PAYMENT TESTS
# ============================================================================

class ScheduledPaymentTest(TestCase):
    """Test cases for ScheduledPayment model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
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
        self.scheduled_payment = ScheduledPayment.objects.create(
            user=self.user,
            source_account=self.account,
            beneficiary_name="John Doe",
            beneficiary_account="1234567890",
            beneficiary_bank_code="GTB",
            amount=Decimal("1000.00"),
            frequency="MONTHLY",
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=365),
            next_processing=timezone.now() + timedelta(days=30),
            is_active=True,
        )

    def test_create_scheduled_payment(self):
        """Test creating a ScheduledPayment instance."""
        self.assertIsNotNone(self.scheduled_payment.pk)
        self.assertEqual(self.scheduled_payment.user, self.user)
        self.assertEqual(self.scheduled_payment.source_account, self.account)
        self.assertEqual(self.scheduled_payment.beneficiary_name, "John Doe")
        self.assertEqual(self.scheduled_payment.beneficiary_account, "1234567890")
        self.assertEqual(self.scheduled_payment.beneficiary_bank_code, "GTB")
        self.assertEqual(self.scheduled_payment.amount, Decimal("1000.00"))
        self.assertEqual(self.scheduled_payment.frequency, "MONTHLY")
        self.assertTrue(self.scheduled_payment.is_active)

    def test_str_representation(self):
        """Test string representation."""
        expected = "ScheduledPayment(Test, 1000.00, MONTHLY)"
        self.assertEqual(str(self.scheduled_payment), expected)

    def test_meta_ordering(self):
        """Test meta ordering."""
        ScheduledPayment.objects.create(
            user=self.user,
            source_account=self.account,
            beneficiary_name="Jane Doe",
            beneficiary_account="0987654321",
            beneficiary_bank_code="UBA",
            amount=Decimal("500.00"),
            frequency="WEEKLY",
            start_date=timezone.now().date(),
            next_processing=timezone.now() + timedelta(days=7),
        )

        payments = ScheduledPayment.objects.all()
        self.assertEqual(payments[0].beneficiary_name, "Jane Doe")  # Earlier next_processing first


# ============================================================================
# CREDIT PRODUCT TESTS
# ============================================================================

class CreditProductTest(TestCase):
    """Test cases for CreditProduct model."""

    def setUp(self):
        self.credit_product = CreditProduct.objects.create(
            name="Quick Loan",
            product_type="QUICK_LOAN",
            min_amount=Decimal("1000.00"),
            max_amount=Decimal("100000.00"),
            interest_rate=Decimal("5.00"),
            tenor_days=30,
            eligibility_criteria={"min_age": 18, "min_income": 50000},
        )

    def test_create_credit_product(self):
        """Test creating a CreditProduct instance."""
        self.assertIsNotNone(self.credit_product.pk)
        self.assertEqual(self.credit_product.name, "Quick Loan")
        self.assertEqual(self.credit_product.product_type, "QUICK_LOAN")
        self.assertEqual(self.credit_product.min_amount, Decimal("1000.00"))
        self.assertEqual(self.credit_product.max_amount, Decimal("100000.00"))
        self.assertEqual(self.credit_product.interest_rate, Decimal("5.00"))
        self.assertEqual(self.credit_product.tenor_days, 30)
        self.assertEqual(self.credit_product.eligibility_criteria, {"min_age": 18, "min_income": 50000})

    def test_str_representation(self):
        """Test string representation."""
        expected = "CreditProduct(Quick Loan, QUICK_LOAN)"
        self.assertEqual(str(self.credit_product), expected)

    def test_meta_ordering(self):
        """Test meta ordering."""
        CreditProduct.objects.create(
            name="Payday Loan",
            product_type="PAYDAY_LOAN",
            min_amount=Decimal("500.00"),
            max_amount=Decimal("50000.00"),
            interest_rate=Decimal("10.00"),
            tenor_days=14,
        )

        products = CreditProduct.objects.all()
        self.assertEqual(products[0].name, "Payday Loan")  # Ordered by name


# ============================================================================
# SUPPORT TICKET TESTS
# ============================================================================

class SupportTicketTest(TestCase):
    """Test cases for SupportTicket model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="adminpass123",
            is_staff=True,
        )
        self.support_ticket = SupportTicket.objects.create(
            user=self.user,
            ticket_id="TKT-20240101-ABC123",
            subject="Login Issue",
            description="Unable to log in to my account",
            category="TECHNICAL",
            priority="HIGH",
            status="OPEN",
            assigned_to=self.admin,
        )

    def test_create_support_ticket(self):
        """Test creating a SupportTicket instance."""
        self.assertIsNotNone(self.support_ticket.pk)
        self.assertEqual(self.support_ticket.user, self.user)
        self.assertEqual(self.support_ticket.ticket_id, "TKT-20240101-ABC123")
        self.assertEqual(self.support_ticket.subject, "Login Issue")
        self.assertEqual(self.support_ticket.description, "Unable to log in to my account")
        self.assertEqual(self.support_ticket.category, "TECHNICAL")
        self.assertEqual(self.support_ticket.priority, "HIGH")
        self.assertEqual(self.support_ticket.status, "OPEN")
        self.assertEqual(self.support_ticket.assigned_to, self.admin)

    def test_str_representation(self):
        """Test string representation."""
        expected = "SupportTicket(TKT-20240101-ABC123, Login Issue, OPEN)"
        self.assertEqual(str(self.support_ticket), expected)

    def test_meta_ordering(self):
        """Test meta ordering."""
        SupportTicket.objects.create(
            user=self.user,
            ticket_id="TKT-20240101-DEF456",
            subject="Payment Issue",
            description="Payment not processed",
            category="PAYMENT",
            priority="CRITICAL",
        )

        tickets = SupportTicket.objects.all()
        self.assertEqual(tickets[0].subject, "Payment Issue")  # Most recent first


# ============================================================================
# API KEY TESTS
# ============================================================================

class APIKeyTest(TestCase):
    """Test cases for APIKey model."""

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
        self.merchant = Merchant.objects.create(
            user=self.user,
            business_name="Test Merchant",
            business_type="INDIVIDUAL",
            business_email="merchant@example.com",
            business_phone="+1234567890",
            business_address="123 Test Street",
            business_state="Lagos",
            business_city="Ikeja",
            settlement_account=self.account,
            settlement_bank=self.bank,
        )
        self.api_key = APIKey.objects.create(
            merchant=self.merchant,
            key="ak_testkey123456789",
            secret="sk_secretkey123456789",
            is_active=True,
            permissions=["read", "write"],
            rate_limit=200,
            webhook_url="https://example.com/webhook",
        )

    def test_create_api_key(self):
        """Test creating an APIKey instance."""
        self.assertIsNotNone(self.api_key.pk)
        self.assertEqual(self.api_key.merchant, self.merchant)
        self.assertEqual(self.api_key.key, "ak_testkey123456789")
        self.assertEqual(self.api_key.secret, "sk_secretkey123456789")
        self.assertTrue(self.api_key.is_active)
        self.assertEqual(self.api_key.permissions, ["read", "write"])
        self.assertEqual(self.api_key.rate_limit, 200)
        self.assertEqual(self.api_key.webhook_url, "https://example.com/webhook")

    def test_unique_key(self):
        """Test that key must be unique."""
        with self.assertRaises(IntegrityError):
            APIKey.objects.create(
                merchant=self.merchant,
                key="ak_testkey123456789",
                secret="sk_anothersecret",
            )


# ============================================================================
# REMITTANCE PROVIDER TESTS
# ============================================================================

class RemittanceProviderTest(TestCase):
    """Test cases for RemittanceProvider model."""

    def setUp(self):
        self.provider = RemittanceProvider.objects.create(
            name="Western Union",
            provider_code="WESTERN_UNION",
            supported_countries=["US", "UK", "NG"],
            supported_currencies=["USD", "GBP", "NGN"],
            transfer_methods=["BANK_DEPOSIT", "CASH_PICKUP"],
            fee_structure={"type": "percentage", "value": 1.5},
            exchange_margin=Decimal("1.00"),
            min_amount=Decimal("10.00"),
            max_amount=Decimal("10000.00"),
            daily_limit=Decimal("50000.00"),
            api_endpoint="https://api.westernunion.com",
            api_key="wu_test_key",
            api_secret="wu_test_secret",
            is_active=True,
        )

    def test_create_remittance_provider(self):
        """Test creating a RemittanceProvider instance."""
        self.assertIsNotNone(self.provider.pk)
        self.assertEqual(self.provider.name, "Western Union")
        self.assertEqual(self.provider.provider_code, "WESTERN_UNION")
        self.assertEqual(self.provider.supported_countries, ["US", "UK", "NG"])
        self.assertEqual(self.provider.supported_currencies, ["USD", "GBP", "NGN"])
        self.assertEqual(self.provider.transfer_methods, ["BANK_DEPOSIT", "CASH_PICKUP"])
        self.assertEqual(self.provider.exchange_margin, Decimal("1.00"))
        self.assertEqual(self.provider.min_amount, Decimal("10.00"))
        self.assertEqual(self.provider.max_amount, Decimal("10000.00"))
        self.assertEqual(self.provider.daily_limit, Decimal("50000.00"))
        self.assertTrue(self.provider.is_active)

    def test_str_representation(self):
        """Test string representation."""
        expected = "Western Union"
        self.assertEqual(str(self.provider), expected)

    def test_unique_provider_code(self):
        """Test that provider_code must be unique."""
        with self.assertRaises(IntegrityError):
            RemittanceProvider.objects.create(
                name="MoneyGram",
                provider_code="WESTERN_UNION",
            )


# ============================================================================
# INTERNATIONAL TRANSFER TESTS
# ============================================================================

class InternationalTransferTest(TestCase):
    """Test cases for InternationalTransfer model."""

    def setUp(self):
        self.sender = User.objects.create_user(
            email="sender@example.com",
            password="testpass123",
        )
        self.recipient = User.objects.create_user(
            email="recipient@example.com",
            password="testpass123",
        )
        self.provider = RemittanceProvider.objects.create(
            name="Western Union",
            provider_code="WESTERN_UNION",
            is_active=True,
        )
        self.transfer = InternationalTransfer.objects.create(
            sender=self.sender,
            recipient=self.recipient,
            provider=self.provider,
            transfer_type="SEND",
            source_amount=Decimal("1000.00"),
            source_currency="NGN",
            target_amount=Decimal("2.50"),
            target_currency="USD",
            exchange_rate=Decimal("0.0025"),
            provider_fee=Decimal("10.00"),
            platform_fee=Decimal("5.00"),
            payout_method="BANK_DEPOSIT",
            recipient_name="John Doe",
            recipient_phone="+1234567890",
            recipient_country="US",
            recipient_bank="Chase",
            recipient_account="1234567890",
            purpose_of_remittance="Family Support",
            source_of_funds="Salary",
            status="PENDING",
        )

    def test_create_international_transfer(self):
        """Test creating an InternationalTransfer instance."""
        self.assertIsNotNone(self.transfer.pk)
        self.assertEqual(self.transfer.sender, self.sender)
        self.assertEqual(self.transfer.recipient, self.recipient)
        self.assertEqual(self.transfer.provider, self.provider)
        self.assertEqual(self.transfer.transfer_type, "SEND")
        self.assertEqual(self.transfer.source_amount, Decimal("1000.00"))
        self.assertEqual(self.transfer.source_currency, "NGN")
        self.assertEqual(self.transfer.target_amount, Decimal("2.50"))
        self.assertEqual(self.transfer.target_currency, "USD")
        self.assertEqual(self.transfer.exchange_rate, Decimal("0.0025"))
        self.assertEqual(self.transfer.provider_fee, Decimal("10.00"))
        self.assertEqual(self.transfer.platform_fee, Decimal("5.00"))
        self.assertEqual(self.transfer.total_fee, Decimal("15.00"))
        self.assertEqual(self.transfer.status, "PENDING")
        self.assertIsNotNone(self.transfer.reference)

    def test_str_representation(self):
        """Test string representation."""
        expected = f"International Transfer {self.transfer.reference}"
        self.assertEqual(str(self.transfer), expected)

    def test_save_generates_reference(self):
        """Test that reference is auto-generated on save."""
        transfer = InternationalTransfer.objects.create(
            sender=self.sender,
            provider=self.provider,
            transfer_type="SEND",
            source_amount=Decimal("100.00"),
            source_currency="NGN",
            target_amount=Decimal("0.25"),
            target_currency="USD",
            exchange_rate=Decimal("0.0025"),
            payout_method="BANK_DEPOSIT",
            recipient_name="Jane Doe",
            recipient_phone="+1987654321",
            recipient_country="UK",
        )
        self.assertIsNotNone(transfer.reference)
        self.assertTrue(transfer.reference.startswith("INTL-"))

    def test_save_calculates_total_fee(self):
        """Test that total_fee is calculated on save."""
        self.assertEqual(self.transfer.total_fee, Decimal("15.00"))


# ============================================================================
# EXCHANGE RATE TESTS
# ============================================================================

class ExchangeRateTest(TestCase):
    """Test cases for ExchangeRate model."""

    def setUp(self):
        self.provider = RemittanceProvider.objects.create(
            name="Western Union",
            provider_code="WESTERN_UNION",
            is_active=True,
        )
        self.exchange_rate = ExchangeRate.objects.create(
            base_currency="NGN",
            target_currency="USD",
            buy_rate=Decimal("0.0025"),
            sell_rate=Decimal("0.0028"),
            mid_rate=Decimal("0.00265"),
            provider_buy_rate=Decimal("0.0024"),
            provider_sell_rate=Decimal("0.0029"),
            provider=self.provider,
            next_update=timezone.now() + timedelta(hours=1),
            is_active=True,
        )

    def test_create_exchange_rate(self):
        """Test creating an ExchangeRate instance."""
        self.assertIsNotNone(self.exchange_rate.pk)
        self.assertEqual(self.exchange_rate.base_currency, "NGN")
        self.assertEqual(self.exchange_rate.target_currency, "USD")
        self.assertEqual(self.exchange_rate.buy_rate, Decimal("0.0025"))
        self.assertEqual(self.exchange_rate.sell_rate, Decimal("0.0028"))
        self.assertEqual(self.exchange_rate.mid_rate, Decimal("0.00265"))
        self.assertEqual(self.exchange_rate.provider_buy_rate, Decimal("0.0024"))
        self.assertEqual(self.exchange_rate.provider_sell_rate, Decimal("0.0029"))
        self.assertEqual(self.exchange_rate.provider, self.provider)
        self.assertTrue(self.exchange_rate.is_active)

    def test_str_representation(self):
        """Test string representation."""
        expected = "NGN/USD: 0.0028"
        self.assertEqual(str(self.exchange_rate), expected)

    def test_unique_together(self):
        """Test unique_together constraint."""
        with self.assertRaises(IntegrityError):
            ExchangeRate.objects.create(
                base_currency="NGN",
                target_currency="USD",
                buy_rate=Decimal("0.0025"),
                sell_rate=Decimal("0.0028"),
                mid_rate=Decimal("0.00265"),
                provider=self.provider,
                next_update=timezone.now() + timedelta(hours=1),
            )

    def test_meta_ordering(self):
        """Test meta ordering."""
        ExchangeRate.objects.create(
            base_currency="NGN",
            target_currency="EUR",
            buy_rate=Decimal("0.0015"),
            sell_rate=Decimal("0.0018"),
            mid_rate=Decimal("0.00165"),
            provider=self.provider,
            next_update=timezone.now() + timedelta(hours=1),
        )

        rates = ExchangeRate.objects.all()
        self.assertEqual(rates[0].target_currency, "EUR")  # Ordered by base_currency then target_currency


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class ScheduledIntegrationTest(TestCase):
    """Integration tests for scheduled models."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
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

    def test_scheduled_payment_workflow(self):
        """Test complete scheduled payment workflow."""
        # Create scheduled payment
        payment = ScheduledPayment.objects.create(
            user=self.user,
            source_account=self.account,
            beneficiary_name="John Doe",
            beneficiary_account="1234567890",
            beneficiary_bank_code="GTB",
            amount=Decimal("1000.00"),
            frequency="MONTHLY",
            start_date=timezone.now().date(),
            next_processing=timezone.now() + timedelta(days=30),
            is_active=True,
        )

        self.assertTrue(payment.is_active)
        self.assertEqual(payment.frequency, "MONTHLY")

        # Process payment (simulated)
        payment.last_processed = timezone.now()
        payment.next_processing = timezone.now() + timedelta(days=30)
        payment.save()

        self.assertIsNotNone(payment.last_processed)

        # Deactivate payment
        payment.is_active = False
        payment.save()
        self.assertFalse(payment.is_active)

    def test_international_transfer_workflow(self):
        """Test complete international transfer workflow."""
        provider = RemittanceProvider.objects.create(
            name="Western Union",
            provider_code="WESTERN_UNION",
            is_active=True,
        )

        # Create transfer
        transfer = InternationalTransfer.objects.create(
            sender=self.user,
            provider=provider,
            transfer_type="SEND",
            source_amount=Decimal("500.00"),
            source_currency="NGN",
            target_amount=Decimal("1.25"),
            target_currency="USD",
            exchange_rate=Decimal("0.0025"),
            provider_fee=Decimal("5.00"),
            platform_fee=Decimal("2.00"),
            payout_method="BANK_DEPOSIT",
            recipient_name="Jane Doe",
            recipient_phone="+1987654321",
            recipient_country="US",
            purpose_of_remittance="Family Support",
            source_of_funds="Salary",
            status="PENDING",
        )

        self.assertEqual(transfer.status, "PENDING")
        self.assertEqual(transfer.total_fee, Decimal("7.00"))

        # Process transfer
        transfer.status = "PROCESSING"
        transfer.initiated_at = timezone.now()
        transfer.save()

        self.assertEqual(transfer.status, "PROCESSING")
        self.assertIsNotNone(transfer.initiated_at)

        # Complete transfer
        transfer.status = "COMPLETED"
        transfer.completed_at = timezone.now()
        transfer.external_reference = "WU-123456789"
        transfer.save()

        self.assertEqual(transfer.status, "COMPLETED")
        self.assertIsNotNone(transfer.completed_at)
        self.assertEqual(transfer.external_reference, "WU-123456789")

    def test_support_ticket_workflow(self):
        """Test complete support ticket workflow."""
        admin = User.objects.create_user(
            email="admin@example.com",
            password="adminpass123",
            is_staff=True,
        )

        # Create ticket
        ticket = SupportTicket.objects.create(
            user=self.user,
            ticket_id="TKT-20240101-INT001",
            subject="Payment Issue",
            description="Payment not processed",
            category="PAYMENT",
            priority="HIGH",
            status="OPEN",
        )

        self.assertEqual(ticket.status, "OPEN")
        self.assertEqual(ticket.priority, "HIGH")

        # Assign ticket
        ticket.assigned_to = admin
        ticket.status = "IN_PROGRESS"
        ticket.save()

        self.assertEqual(ticket.assigned_to, admin)
        self.assertEqual(ticket.status, "IN_PROGRESS")

        # Resolve ticket
        ticket.resolution = "Payment was processed successfully"
        ticket.status = "RESOLVED"
        ticket.save()

        self.assertEqual(ticket.status, "RESOLVED")
        self.assertEqual(ticket.resolution, "Payment was processed successfully")


# ============================================================================
# RUNNER
# ============================================================================

if __name__ == "__main__":
    import django
    django.setup()
    from django.test import runner
    runner.DiscoverRunner().run_tests([
        "banking.tests.test_scheduled"
    ])