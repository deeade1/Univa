# apps/backend/banking/tests/test_core.py

"""
Tests for banking core models.

This module tests:
    - Bank: Bank/financial institution model
    - Account: Core banking account model
"""

from __future__ import annotations

from decimal import Decimal
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from banking.models.core import Bank, Account
from banking.models.security import BankingSecurity

User = get_user_model()


# ============================================================================
# BANK TESTS
# ============================================================================

class BankTest(TestCase):
    """Test cases for Bank model."""

    def setUp(self):
        self.bank = Bank.objects.create(
            name="GTBANK",
            code="GTB",
            is_active=True,
            is_partner_bank=True,
            supports_transfers=True,
            supports_airtime=False,
            supports_bills=False,
            daily_capacity=100,
            health_score=100.0,
        )

    def test_create_bank(self):
        """Test creating a Bank instance."""
        self.assertIsNotNone(self.bank.pk)
        self.assertEqual(self.bank.name, "GTBANK")
        self.assertEqual(self.bank.code, "GTB")
        self.assertTrue(self.bank.is_active)
        self.assertTrue(self.bank.is_partner_bank)
        self.assertTrue(self.bank.supports_transfers)
        self.assertFalse(self.bank.supports_airtime)
        self.assertFalse(self.bank.supports_bills)
        self.assertEqual(self.bank.daily_capacity, 100)
        self.assertEqual(self.bank.health_score, 100.0)
        self.assertEqual(self.bank.consecutive_failures, 0)
        self.assertFalse(self.bank.is_temporarily_disabled)

    def test_str_representation(self):
        """Test string representation."""
        expected = "Guaranty Trust Bank (GTBank)"
        self.assertEqual(str(self.bank), expected)

    def test_clean_valid_bank(self):
        """Test clean() with valid data."""
        try:
            self.bank.full_clean()
        except ValidationError:
            self.fail("clean() raised ValidationError unexpectedly")

    def test_clean_invalid_health_score(self):
        """Test clean() with invalid health score."""
        self.bank.health_score = 150.0
        with self.assertRaises(ValidationError) as exc:
            self.bank.full_clean()
        self.assertIn("health_score", exc.exception.error_dict)

    def test_clean_virtual_provider_without_provider_type(self):
        """Test clean() with virtual provider but no provider type."""
        bank = Bank(
            name="PAYSTACK_WEMA",
            code="PAYSTACK",
            is_virtual_provider=True,
            is_partner_bank=True,
        )
        with self.assertRaises(ValidationError) as exc:
            bank.full_clean()
        self.assertIn("virtual_account_provider", exc.exception.error_dict)

    def test_clean_non_virtual_with_provider_type(self):
        """Test clean() with non-virtual but provider type set."""
        self.bank.is_virtual_provider = False
        self.bank.virtual_account_provider = "PAYSTACK"
        with self.assertRaises(ValidationError) as exc:
            self.bank.full_clean()
        self.assertIn("virtual_account_provider", exc.exception.error_dict)

    def test_clean_daily_usage_exceeds_capacity(self):
        """Test clean() with daily usage exceeding capacity."""
        self.bank.daily_capacity = 10
        self.bank.current_daily_usage = 15
        with self.assertRaises(ValidationError) as exc:
            self.bank.full_clean()
        self.assertIn("current_daily_usage", exc.exception.error_dict)

    def test_reset_daily_usage_if_needed(self):
        """Test resetting daily usage when day changes."""
        # Set usage to 50
        self.bank.current_daily_usage = 50
        self.bank.last_usage_reset = timezone.localdate() - timedelta(days=1)
        self.bank.save()

        # Reset should happen
        self.bank._reset_daily_usage_if_needed()
        self.bank.refresh_from_db()
        self.assertEqual(self.bank.current_daily_usage, 0)
        self.assertEqual(self.bank.last_usage_reset, timezone.localdate())

    def test_reset_daily_usage_no_change_same_day(self):
        """Test that daily usage doesn't reset on same day."""
        self.bank.current_daily_usage = 50
        self.bank.last_usage_reset = timezone.localdate()
        self.bank.save()

        self.bank._reset_daily_usage_if_needed()
        self.bank.refresh_from_db()
        self.assertEqual(self.bank.current_daily_usage, 50)

    def test_can_create_virtual_account(self):
        """Test can_create_virtual_account method."""
        self.assertTrue(self.bank.can_create_virtual_account())

        # Exceed capacity
        self.bank.current_daily_usage = 100
        self.bank.save()
        self.assertFalse(self.bank.can_create_virtual_account())

        # Not a partner bank
        self.bank.is_partner_bank = False
        self.bank.save()
        self.assertFalse(self.bank.can_create_virtual_account())

    def test_can_create_virtual_account_unlimited(self):
        """Test can_create_virtual_account with unlimited capacity."""
        self.bank.daily_capacity = 0
        self.bank.current_daily_usage = 1000
        self.bank.save()
        self.assertTrue(self.bank.can_create_virtual_account())

    def test_increment_virtual_account_usage(self):
        """Test incrementing virtual account usage."""
        self.bank.current_daily_usage = 50
        self.bank.save()

        self.bank.increment_virtual_account_usage()
        self.bank.refresh_from_db()
        self.assertEqual(self.bank.current_daily_usage, 51)

    def test_increment_virtual_account_usage_not_partner(self):
        """Test increment on non-partner bank does nothing."""
        self.bank.is_partner_bank = False
        self.bank.current_daily_usage = 50
        self.bank.save()

        self.bank.increment_virtual_account_usage()
        self.bank.refresh_from_db()
        self.assertEqual(self.bank.current_daily_usage, 50)

    def test_reset_daily_usage(self):
        """Test reset_daily_usage method."""
        self.bank.current_daily_usage = 75
        self.bank.save()

        self.bank.reset_daily_usage()
        self.bank.refresh_from_db()
        self.assertEqual(self.bank.current_daily_usage, 0)
        self.assertEqual(self.bank.last_usage_reset, timezone.localdate())

    def test_is_available_for_virtual_accounts(self):
        """Test is_available_for_virtual_accounts property."""
        self.assertTrue(self.bank.is_available_for_virtual_accounts)

        # Inactive
        self.bank.is_active = False
        self.bank.save()
        self.assertFalse(self.bank.is_available_for_virtual_accounts)

        # Not partner
        self.bank.is_active = True
        self.bank.is_partner_bank = False
        self.bank.save()
        self.assertFalse(self.bank.is_available_for_virtual_accounts)

        # Unhealthy
        self.bank.is_partner_bank = True
        self.bank.health_score = 30
        self.bank.save()
        self.assertFalse(self.bank.is_available_for_virtual_accounts)

    def test_get_bank_type(self):
        """Test get_bank_type method."""
        # Traditional bank
        self.assertEqual(self.bank.get_bank_type(), "Partner Bank")

        # Virtual provider
        self.bank.is_virtual_provider = True
        self.bank.save()
        self.assertEqual(self.bank.get_bank_type(), "Virtual Account Provider")

        # Neither
        self.bank.is_virtual_provider = False
        self.bank.is_partner_bank = False
        self.bank.save()
        self.assertEqual(self.bank.get_bank_type(), "Traditional Bank")

    def test_get_active_partner_banks(self):
        """Test get_active_partner_banks class method."""
        # Create another partner bank
        Bank.objects.create(
            name="ZENITH",
            code="ZEN",
            is_active=True,
            is_partner_bank=True,
        )

        # Create non-partner bank
        Bank.objects.create(
            name="UBA",
            code="UBA",
            is_active=True,
            is_partner_bank=False,
        )

        partner_banks = Bank.get_active_partner_banks()
        self.assertEqual(partner_banks.count(), 2)
        self.assertEqual(partner_banks[0].code, "GTB")  # Ordered by name
        self.assertEqual(partner_banks[1].code, "ZEN")

    def test_record_success(self):
        """Test record_success method."""
        self.bank.consecutive_failures = 3
        self.bank.health_score = 70
        self.bank.is_temporarily_disabled = True
        self.bank.save()

        self.bank.record_success()

        self.bank.refresh_from_db()
        self.assertEqual(self.bank.consecutive_failures, 0)
        # HEALTH_RECOVER = 5, so 70 + 5 = 75
        self.assertEqual(self.bank.health_score, 75)
        self.assertFalse(self.bank.is_temporarily_disabled)
        self.assertIsNone(self.bank.disabled_until)
        self.assertIsNotNone(self.bank.last_success_at)

    def test_record_failure(self):
        """Test record_failure method."""
        self.bank.health_score = 100
        self.bank.consecutive_failures = 0
        self.bank.save()

        self.bank.record_failure()

        self.bank.refresh_from_db()
        self.assertEqual(self.bank.consecutive_failures, 1)
        self.assertEqual(self.bank.health_score, 90)  # -10
        self.assertFalse(self.bank.is_temporarily_disabled)

    def test_record_failure_max_failures(self):
        """Test record_failure with max failures."""
        self.bank.health_score = 100
        self.bank.consecutive_failures = 2
        self.bank.save()

        self.bank.record_failure()

        self.bank.refresh_from_db()
        self.assertEqual(self.bank.consecutive_failures, 3)
        self.assertTrue(self.bank.is_temporarily_disabled)
        self.assertIsNotNone(self.bank.disabled_until)

    def test_is_healthy(self):
        """Test is_healthy method."""
        self.assertTrue(self.bank.is_healthy())

        # Unhealthy score
        self.bank.health_score = 30
        self.bank.save()
        self.assertFalse(self.bank.is_healthy())

        # Temporarily disabled
        self.bank.health_score = 100
        self.bank.is_temporarily_disabled = True
        self.bank.disabled_until = timezone.now() + timedelta(minutes=5)
        self.bank.save()
        self.assertFalse(self.bank.is_healthy())

        # Disabled expired
        self.bank.disabled_until = timezone.now() - timedelta(minutes=5)
        self.bank.save()
        self.assertTrue(self.bank.is_healthy())


# ============================================================================
# ACCOUNT TESTS
# ============================================================================

class AccountTest(TestCase):
    """Test cases for Account model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        # Set phone number directly since User model may not have phone_number field
        self.user.phone_number = "+1234567890"
        self.user.save()
        
        self.bank = Bank.objects.create(
            name="GTBANK",
            code="GTB",
            is_active=True,
            is_partner_bank=True,
        )
        self.account = Account.objects.create(
            user=self.user,
            bank=self.bank,
            phone_number="+1234567890",
            nuban_number="1234567890",
            account_name="Test User",
            daily_limit=Decimal("50000.00"),
            single_transaction_limit=Decimal("50000.00"),
            status=Account.STATUS_ACTIVE,
        )

    def test_create_customer_account(self):
        """Test creating a customer account."""
        self.assertIsNotNone(self.account.pk)
        self.assertEqual(self.account.user, self.user)
        self.assertEqual(self.account.bank, self.bank)
        self.assertEqual(self.account.phone_number, "+1234567890")
        self.assertEqual(self.account.nuban_number, "1234567890")
        self.assertEqual(self.account.account_name, "Test User")
        self.assertFalse(self.account.is_system_account)
        self.assertEqual(self.account.status, Account.STATUS_ACTIVE)
        self.assertEqual(self.account.daily_limit, Decimal("50000.00"))
        self.assertEqual(self.account.single_transaction_limit, Decimal("50000.00"))

    def test_str_representation(self):
        """Test string representation."""
        expected = "+1234567890 - Test User"
        self.assertEqual(str(self.account), expected)

    def test_is_customer_account(self):
        """Test is_customer_account property."""
        self.assertTrue(self.account.is_customer_account)
        self.assertFalse(self.account.is_internal_account)

    def test_is_internal_account(self):
        """Test is_internal_account property."""
        # Create system account
        system_account = Account.objects.create(
            bank=self.bank,
            nuban_number="0987654321",
            account_name="System Account",
            is_system_account=True,
            can_receive_external=False,
            status=Account.STATUS_ACTIVE,
        )
        self.assertTrue(system_account.is_internal_account)
        self.assertFalse(system_account.is_customer_account)

    def test_clean_customer_account_valid(self):
        """Test clean() with valid customer account."""
        try:
            self.account.full_clean()
        except ValidationError:
            self.fail("clean() raised ValidationError unexpectedly")

    def test_clean_customer_account_missing_user(self):
        """Test clean() with customer account missing user."""
        self.account.user = None
        with self.assertRaises(ValidationError) as exc:
            self.account.full_clean()
        self.assertIn("user", exc.exception.error_dict)

    def test_clean_customer_account_missing_phone(self):
        """Test clean() with customer account missing phone."""
        self.account.phone_number = None
        with self.assertRaises(ValidationError) as exc:
            self.account.full_clean()
        self.assertIn("phone_number", exc.exception.error_dict)

    def test_clean_system_account_valid(self):
        """Test clean() with valid system account."""
        # System account must have can_receive_external=False
        system_account = Account(
            bank=self.bank,
            nuban_number="0987654321",
            account_name="System Account",
            is_system_account=True,
            can_receive_external=False,
            status=Account.STATUS_ACTIVE,
        )
        try:
            system_account.full_clean()
        except ValidationError:
            self.fail("clean() raised ValidationError unexpectedly")

    def test_clean_system_account_with_user(self):
        """Test clean() with system account having user."""
        system_account = Account(
            user=self.user,
            bank=self.bank,
            nuban_number="0987654321",
            account_name="System Account",
            is_system_account=True,
            can_receive_external=False,
            status=Account.STATUS_ACTIVE,
        )
        with self.assertRaises(ValidationError) as exc:
            system_account.full_clean()
        self.assertIn("user", exc.exception.error_dict)

    def test_clean_system_account_with_phone(self):
        """Test clean() with system account having phone."""
        system_account = Account(
            bank=self.bank,
            nuban_number="0987654321",
            account_name="System Account",
            phone_number="+1234567890",
            is_system_account=True,
            can_receive_external=False,
            status=Account.STATUS_ACTIVE,
        )
        with self.assertRaises(ValidationError) as exc:
            system_account.full_clean()
        self.assertIn("phone_number", exc.exception.error_dict)

    def test_clean_system_account_with_bvn(self):
        """Test clean() with system account having BVN."""
        system_account = Account(
            bank=self.bank,
            nuban_number="0987654321",
            account_name="System Account",
            is_system_account=True,
            bvn_hash="hashed_bvn",
            can_receive_external=False,
            status=Account.STATUS_ACTIVE,
        )
        with self.assertRaises(ValidationError) as exc:
            system_account.full_clean()
        self.assertIn("bvn_hash", exc.exception.error_dict)

    def test_clean_system_account_with_external_transfers(self):
        """Test clean() with system account having external transfers."""
        system_account = Account(
            bank=self.bank,
            nuban_number="0987654321",
            account_name="System Account",
            is_system_account=True,
            can_send_external=True,
            can_receive_external=True,
            status=Account.STATUS_ACTIVE,
        )
        with self.assertRaises(ValidationError) as exc:
            system_account.full_clean()
        self.assertIn("can_send_external", exc.exception.error_dict)
        self.assertIn("can_receive_external", exc.exception.error_dict)

    def test_clean_invalid_limits(self):
        """Test clean() with invalid transaction limits."""
        # Negative daily limit
        self.account.daily_limit = Decimal("-100.00")
        with self.assertRaises(ValidationError) as exc:
            self.account.full_clean()
        self.assertIn("daily_limit", exc.exception.error_dict)

        # Single limit > daily limit
        self.account.daily_limit = Decimal("50000.00")
        self.account.single_transaction_limit = Decimal("100000.00")
        with self.assertRaises(ValidationError) as exc:
            self.account.full_clean()
        self.assertIn("single_transaction_limit", exc.exception.error_dict)

    # =============================================================
    # REMOVED PIN TESTS - PINs are now in BankingSecurity
    # =============================================================
    #
    # The following tests have been removed because PIN functionality
    # has been moved to BankingSecurity:
    #   - test_set_pin_valid
    #   - test_set_pin_invalid
    #   - test_set_pin_on_system_account
    #   - test_check_pin_no_pin
    #
    # Use BankingSecurityTest for PIN-related tests.
    # =============================================================

    def test_set_bvn_valid(self):
        """Test set_bvn with valid BVN."""
        self.account.set_bvn("12345678901")
        self.assertIsNotNone(self.account.bvn_hash)
        self.assertTrue(self.account.check_bvn("12345678901"))
        self.assertFalse(self.account.check_bvn("99999999999"))

    def test_set_bvn_invalid(self):
        """Test set_bvn with invalid BVN."""
        with self.assertRaises(ValidationError) as exc:
            self.account.set_bvn("1234567890")  # 10 digits
        self.assertEqual(str(exc.exception), "['BVN must be exactly 11 digits.']")

        with self.assertRaises(ValidationError) as exc:
            self.account.set_bvn("abcdefghijk")
        self.assertEqual(str(exc.exception), "['BVN must be exactly 11 digits.']")

    def test_set_bvn_on_system_account(self):
        """Test set_bvn on system account."""
        system_account = Account.objects.create(
            bank=self.bank,
            nuban_number="0987654321",
            account_name="System Account",
            is_system_account=True,
            can_receive_external=False,
            status=Account.STATUS_ACTIVE,
        )
        with self.assertRaises(ValidationError) as exc:
            system_account.set_bvn("12345678901")
        self.assertEqual(
            str(exc.exception),
            "['System accounts do not have BVNs.']"
        )

    def test_is_active_account(self):
        """Test is_active_account property."""
        self.assertTrue(self.account.is_active_account)

        self.account.status = Account.STATUS_SUSPENDED
        self.account.save()
        self.assertFalse(self.account.is_active_account)

        self.account.status = Account.STATUS_CLOSED
        self.account.save()
        self.assertFalse(self.account.is_active_account)

    def test_can_transact(self):
        """Test can_transact method."""
        self.assertTrue(self.account.can_transact())

        # Account suspended
        self.account.status = Account.STATUS_SUSPENDED
        self.account.save()
        self.assertFalse(self.account.can_transact())

        # Bank inactive - health_score 30 should make bank unhealthy
        self.account.status = Account.STATUS_ACTIVE
        self.account.save()
        self.bank.health_score = 30
        self.bank.save()
        # Force bank to be unhealthy - health_score 30 < 50
        self.assertFalse(self.bank.is_healthy())
        self.assertFalse(self.account.can_transact())

    def test_get_balance(self):
        """Test get_balance method."""
        # Initially balance should be 0
        balance = self.account.get_balance()
        self.assertEqual(balance, Decimal("0.00"))

    def test_balance_property(self):
        """Test balance property."""
        self.assertEqual(self.account.balance, Decimal("0.00"))

    def test_validate_transaction_amount_valid(self):
        """Test validate_transaction_amount with valid amount."""
        result = self.account.validate_transaction_amount("100.00")
        self.assertEqual(result, Decimal("100.00"))

        result = self.account.validate_transaction_amount(Decimal("50.50"))
        self.assertEqual(result, Decimal("50.50"))

    def test_validate_transaction_amount_invalid(self):
        """Test validate_transaction_amount with invalid amount."""
        with self.assertRaises(ValidationError) as exc:
            self.account.validate_transaction_amount("invalid")
        self.assertEqual(str(exc.exception), "['Invalid transaction amount.']")

        with self.assertRaises(ValidationError) as exc:
            self.account.validate_transaction_amount("-100.00")
        self.assertEqual(
            str(exc.exception),
            "['Transaction amount must be greater than zero.']"
        )

        with self.assertRaises(ValidationError) as exc:
            self.account.validate_transaction_amount("0.00")
        self.assertEqual(
            str(exc.exception),
            "['Transaction amount must be greater than zero.']"
        )

    def test_validate_transaction_amount_exceeds_limit(self):
        """Test validate_transaction_amount exceeding limit."""
        self.account.single_transaction_limit = Decimal("1000.00")
        self.account.save()

        with self.assertRaises(ValidationError) as exc:
            self.account.validate_transaction_amount("2000.00")
        self.assertEqual(
            str(exc.exception),
            '["Transaction amount exceeds the account\'s single-transaction limit."]'
        )

    def test_validate_transaction_amount_rounding(self):
        """Test validate_transaction_amount rounds to 2 decimals."""
        result = self.account.validate_transaction_amount("100.456")
        self.assertEqual(result, Decimal("100.46"))

    def test_meta_constraints(self):
        """Test model constraints."""
        # Test unique nuban_number - use a separate user
        user2 = User.objects.create_user(
            email="test2@example.com",
            password="testpass123",
        )
        user2.phone_number = "+1987654321"
        user2.save()
        
        with self.assertRaises(IntegrityError):
            Account.objects.create(
                user=user2,
                bank=self.bank,
                phone_number="+1987654321",
                nuban_number="1234567890",  # Duplicate
                account_name="Another User",
            )


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class BankingCoreIntegrationTest(TestCase):
    """Integration tests for banking core models."""

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
            is_partner_bank=True,
            daily_capacity=10,
            health_score=100.0,
        )
        self.account = Account.objects.create(
            user=self.user,
            bank=self.bank,
            phone_number="+1234567890",
            nuban_number="1234567890",
            account_name="Test User",
        )

    def test_bank_and_account_integration(self):
        """Test bank and account integration."""
        # Account should be linked to bank
        self.assertEqual(self.account.bank, self.bank)
        self.assertIn(self.account, self.bank.accounts.all())

        # Bank should have account
        self.assertEqual(self.bank.accounts.count(), 1)

    def test_account_limits_integration(self):
        """Test account limits integration."""
        # Set limits
        self.account.daily_limit = Decimal("50000.00")
        self.account.single_transaction_limit = Decimal("10000.00")
        self.account.save()

        # Validate transaction
        result = self.account.validate_transaction_amount("5000.00")
        self.assertEqual(result, Decimal("5000.00"))

        # Should fail
        with self.assertRaises(ValidationError):
            self.account.validate_transaction_amount("15000.00")

    def test_bank_health_and_account_integration(self):
        """Test bank health affecting account."""
        self.assertTrue(self.account.can_transact())

        # Bank becomes unhealthy (health_score < 50)
        self.bank.health_score = 30
        self.bank.save()
        # Force bank to be unhealthy
        self.assertFalse(self.bank.is_healthy())
        self.assertFalse(self.account.can_transact())

        # Bank recovers (health_score >= 50)
        self.bank.health_score = 60
        self.bank.save()
        self.assertTrue(self.bank.is_healthy())
        self.assertTrue(self.account.can_transact())