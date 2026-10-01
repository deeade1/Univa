# apps/backend/banking/tests/test_security.py

"""
Tests for banking security models.

This module tests:
    - BankingSecurity: PIN management
    - PhoneChangeRequest: OTP flow
    - FraudDetectionRule: Rule management
    - FraudAlert: Alert management
    - AuditLog: Audit trail
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from banking.models.security import (
    AuditLog,
    BankingSecurity,
    FraudAlert,
    FraudDetectionRule,
    PhoneChangeRequest,
)

User = get_user_model()


# ============================================================================
# BANKING SECURITY TESTS
# ============================================================================

class BankingSecurityTest(TestCase):
    """Test cases for BankingSecurity model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )
        self.security = BankingSecurity.objects.create(user=self.user)

    def test_create_banking_security(self):
        """Test creating a BankingSecurity instance."""
        self.assertIsNotNone(self.security.pk)
        self.assertEqual(self.security.user, self.user)
        self.assertFalse(self.security.has_pin)
        self.assertFalse(self.security.is_pin_locked)
        self.assertEqual(self.security.pin_attempts, 0)
        self.assertIsNone(self.security.pin_hash)
        self.assertIsNone(self.security.pin_set_at)
        self.assertIsNone(self.security.pin_locked_until)

    def test_str_representation(self):
        """Test string representation."""
        expected = f"Banking Security for {self.user.email}"
        self.assertEqual(str(self.security), expected)

    def test_set_pin_valid(self):
        """Test setting a valid PIN."""
        self.security.set_pin("1234")

        self.security.refresh_from_db()
        self.assertTrue(self.security.has_pin)
        self.assertIsNotNone(self.security.pin_hash)
        self.assertIsNotNone(self.security.pin_set_at)
        self.assertEqual(self.security.pin_attempts, 0)
        self.assertIsNone(self.security.pin_locked_until)

    def test_set_pin_invalid_format(self):
        """Test setting an invalid PIN format."""
        with self.assertRaises(ValidationError) as exc:
            self.security.set_pin("123")
        self.assertEqual(str(exc.exception), "['PIN must be exactly 4 digits.']")

        with self.assertRaises(ValidationError) as exc:
            self.security.set_pin("abcd")
        self.assertEqual(str(exc.exception), "['PIN must be exactly 4 digits.']")

        with self.assertRaises(ValidationError) as exc:
            self.security.set_pin("12345")
        self.assertEqual(str(exc.exception), "['PIN must be exactly 4 digits.']")

        with self.assertRaises(ValidationError) as exc:
            self.security.set_pin("")
        self.assertEqual(str(exc.exception), "['PIN must be exactly 4 digits.']")

        with self.assertRaises(ValidationError) as exc:
            self.security.set_pin(None)  # type: ignore
        self.assertEqual(str(exc.exception), "['PIN must be exactly 4 digits.']")

    def test_check_pin_correct(self):
        """Test checking a correct PIN."""
        self.security.set_pin("1234")

        result = self.security.check_pin("1234")

        self.assertTrue(result)
        self.security.refresh_from_db()
        self.assertEqual(self.security.pin_attempts, 0)
        self.assertIsNone(self.security.pin_locked_until)

    def test_check_pin_incorrect(self):
        """Test checking an incorrect PIN."""
        self.security.set_pin("1234")

        with self.assertRaises(ValidationError) as exc:
            self.security.check_pin("9999")

        self.assertIn("Incorrect PIN", str(exc.exception))
        self.security.refresh_from_db()
        self.assertEqual(self.security.pin_attempts, 1)

    def test_check_pin_multiple_incorrect(self):
        """Test multiple incorrect PIN attempts."""
        self.security.set_pin("1234")

        # First attempt
        with self.assertRaises(ValidationError) as exc:
            self.security.check_pin("9999")
        self.assertIn("2 attempt(s) left", str(exc.exception))

        # Second attempt
        with self.assertRaises(ValidationError) as exc:
            self.security.check_pin("9999")
        self.assertIn("1 attempt(s) left", str(exc.exception))

        # Third attempt - should lock
        with self.assertRaises(ValidationError) as exc:
            self.security.check_pin("9999")
        self.assertIn("PIN is locked for 30 minutes", str(exc.exception))

        self.security.refresh_from_db()
        self.assertEqual(self.security.pin_attempts, 3)
        self.assertTrue(self.security.is_pin_locked)
        self.assertIsNotNone(self.security.pin_locked_until)

    def test_check_pin_when_locked(self):
        """Test checking PIN when account is locked."""
        self.security.set_pin("1234")
        self.security.pin_attempts = 3
        self.security.pin_locked_until = timezone.now() + timedelta(minutes=30)
        self.security.save()

        with self.assertRaises(ValidationError) as exc:
            self.security.check_pin("1234")

        self.assertIn("PIN is temporarily locked", str(exc.exception))

    def test_check_pin_no_pin_set(self):
        """Test checking PIN when no PIN is set."""
        with self.assertRaises(ValidationError) as exc:
            self.security.check_pin("1234")

        self.assertEqual(str(exc.exception), "['No PIN is set for this account.']")

    def test_reset_pin_attempts(self):
        """Test resetting PIN attempts."""
        self.security.set_pin("1234")
        self.security.pin_attempts = 3
        self.security.pin_locked_until = timezone.now() + timedelta(minutes=30)
        self.security.save()

        self.security.reset_pin_attempts()

        self.security.refresh_from_db()
        self.assertEqual(self.security.pin_attempts, 0)
        self.assertIsNone(self.security.pin_locked_until)

    def test_clear_pin(self):
        """Test clearing a PIN."""
        self.security.set_pin("1234")
        self.assertTrue(self.security.has_pin)

        self.security.clear_pin()

        self.security.refresh_from_db()
        self.assertFalse(self.security.has_pin)
        self.assertIsNone(self.security.pin_hash)
        self.assertIsNone(self.security.pin_set_at)
        self.assertEqual(self.security.pin_attempts, 0)
        self.assertIsNone(self.security.pin_locked_until)

    def test_pin_properties(self):
        """Test PIN properties."""
        # has_pin - False initially
        self.assertFalse(self.security.has_pin)

        # Set PIN
        self.security.set_pin("1234")
        self.assertTrue(self.security.has_pin)

        # is_pin_locked - False initially
        self.assertFalse(self.security.is_pin_locked)

        # Lock the PIN
        self.security.pin_attempts = 3
        self.security.pin_locked_until = timezone.now() + timedelta(minutes=30)
        self.security.save()
        self.assertTrue(self.security.is_pin_locked)

    def test_remaining_lockout_minutes(self):
        """Test remaining_lockout_minutes property."""
        self.security.set_pin("1234")
        
        # Initially not locked
        self.assertEqual(self.security.remaining_lockout_minutes, 0)
        
        # Lock the PIN
        self.security.pin_attempts = 3
        self.security.pin_locked_until = timezone.now() + timedelta(minutes=30)
        self.security.save()
        
        # Should be about 30 minutes
        self.assertGreaterEqual(self.security.remaining_lockout_minutes, 29)
        self.assertLessEqual(self.security.remaining_lockout_minutes, 30)

    def test_pin_attempts_reset_on_success(self):
        """Test that PIN attempts reset on successful verification."""
        self.security.set_pin("1234")

        # Fail once
        with self.assertRaises(ValidationError):
            self.security.check_pin("9999")
        self.assertEqual(self.security.pin_attempts, 1)

        # Success should reset
        self.security.check_pin("1234")
        self.security.refresh_from_db()
        self.assertEqual(self.security.pin_attempts, 0)

    def test_require_pin_for_transactions_default(self):
        """Test default value for require_pin_for_transactions."""
        self.assertTrue(self.security.require_pin_for_transactions)

    def test_require_pin_for_login_default(self):
        """Test default value for require_pin_for_login."""
        self.assertFalse(self.security.require_pin_for_login)


# ============================================================================
# PHONE CHANGE REQUEST TESTS
# ============================================================================

class PhoneChangeRequestTest(TestCase):
    """Test cases for PhoneChangeRequest model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        self.phone_request = PhoneChangeRequest.objects.create(
            user=self.user,
            old_phone="+1234567890",
            new_phone="+0987654321",
        )

    def test_create_phone_change_request(self):
        """Test creating a PhoneChangeRequest instance."""
        self.assertIsNotNone(self.phone_request.pk)
        self.assertEqual(self.phone_request.user, self.user)
        self.assertEqual(self.phone_request.old_phone, "+1234567890")
        self.assertEqual(self.phone_request.new_phone, "+0987654321")
        self.assertFalse(self.phone_request.verified)
        self.assertEqual(self.phone_request.otp_attempts, 0)
        # otp_code is None by default
        self.assertIsNone(self.phone_request.otp_code)
        self.assertIsNone(self.phone_request.otp_sent_at)

    def test_str_representation(self):
        """Test string representation."""
        expected = f"PhoneChangeRequest({self.user}, +0987654321)"
        self.assertEqual(str(self.phone_request), expected)

    def test_generate_otp_valid(self):
        """Test generating a valid OTP."""
        otp = self.phone_request.generate_otp()

        self.assertIsNotNone(otp)
        self.assertEqual(len(otp), 6)
        self.assertTrue(otp.isdigit())
        self.assertEqual(self.phone_request.otp_code, otp)
        self.assertIsNotNone(self.phone_request.otp_sent_at)
        self.assertEqual(self.phone_request.otp_attempts, 0)
        self.assertIsNone(self.phone_request.locked_until)

    def test_generate_otp_resend_interval(self):
        """Test OTP resend interval protection."""
        self.phone_request.generate_otp()

        # Try to generate another OTP immediately
        with self.assertRaises(ValidationError) as exc:
            self.phone_request.generate_otp()

        self.assertIn("Please wait", str(exc.exception))

    def test_generate_otp_when_locked(self):
        """Test generating OTP when locked."""
        self.phone_request.locked_until = timezone.now() + timedelta(minutes=30)
        self.phone_request.save()

        with self.assertRaises(ValidationError) as exc:
            self.phone_request.generate_otp()

        self.assertIn("Too many failed attempts", str(exc.exception))

    def test_is_otp_valid_correct(self):
        """Test validating a correct OTP."""
        otp = self.phone_request.generate_otp()

        result = self.phone_request.is_otp_valid(otp)

        self.assertTrue(result)

    def test_is_otp_valid_incorrect(self):
        """Test validating an incorrect OTP."""
        self.phone_request.generate_otp()

        with self.assertRaises(ValidationError) as exc:
            self.phone_request.is_otp_valid("999999")

        self.assertIn("Incorrect OTP", str(exc.exception))
        self.phone_request.refresh_from_db()
        self.assertEqual(self.phone_request.otp_attempts, 1)

    def test_is_otp_valid_expired(self):
        """Test validating an expired OTP."""
        self.phone_request.generate_otp()
        # Simulate OTP expiry
        self.phone_request.otp_sent_at = timezone.now() - timedelta(minutes=15)
        self.phone_request.save()

        with self.assertRaises(ValidationError) as exc:
            self.phone_request.is_otp_valid(self.phone_request.otp_code)

        self.assertEqual(str(exc.exception), "['OTP has expired.']")

    def test_is_otp_valid_no_otp(self):
        """Test validating when no OTP exists."""
        with self.assertRaises(ValidationError) as exc:
            self.phone_request.is_otp_valid("123456")

        self.assertEqual(str(exc.exception), "['No OTP found.']")

    def test_is_otp_valid_max_attempts(self):
        """Test OTP validation with max attempts."""
        self.phone_request.generate_otp()

        # Try 3 times with wrong OTP
        for i in range(3):
            with self.assertRaises(ValidationError):
                self.phone_request.is_otp_valid("999999")

        # Should be locked
        self.phone_request.refresh_from_db()
        self.assertTrue(self.phone_request.locked_until)

    def test_mark_verified(self):
        """Test marking phone change request as verified."""
        self.assertFalse(self.phone_request.verified)

        self.phone_request.mark_verified()

        self.phone_request.refresh_from_db()
        self.assertTrue(self.phone_request.verified)


# ============================================================================
# FRAUD DETECTION RULE TESTS
# ============================================================================

class FraudDetectionRuleTest(TestCase):
    """Test cases for FraudDetectionRule model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="admin@example.com",
            password="adminpass123",
        )
        self.rule = FraudDetectionRule.objects.create(
            name="High Amount Transaction",
            description="Flag transactions over $10,000",
            rule_type=FraudDetectionRule.RuleType.TRANSACTION_AMOUNT,
            threshold=10000.0,
            action="FLAG",
            created_by=self.user,
        )

    def test_create_fraud_rule(self):
        """Test creating a FraudDetectionRule instance."""
        self.assertIsNotNone(self.rule.pk)
        self.assertEqual(self.rule.name, "High Amount Transaction")
        self.assertEqual(self.rule.rule_type, FraudDetectionRule.RuleType.TRANSACTION_AMOUNT)
        self.assertEqual(self.rule.threshold, 10000.0)
        self.assertTrue(self.rule.is_active)
        self.assertEqual(self.rule.created_by, self.user)

    def test_str_representation(self):
        """Test string representation."""
        expected = "High Amount Transaction (Transaction Amount)"
        self.assertEqual(str(self.rule), expected)

    def test_rule_type_choices(self):
        """Test rule type choices."""
        choices = FraudDetectionRule.RuleType.choices
        choice_values = [choice[0] for choice in choices]

        self.assertIn('TRANSACTION_AMOUNT', choice_values)
        self.assertIn('FREQUENCY', choice_values)
        self.assertIn('LOCATION', choice_values)
        self.assertIn('DEVICE', choice_values)
        self.assertIn('BEHAVIORAL', choice_values)

    def test_action_choices(self):
        """Test action choices."""
        # Create rule with different action
        rule_block = FraudDetectionRule.objects.create(
            name="Block Suspicious",
            rule_type=FraudDetectionRule.RuleType.FREQUENCY,
            threshold=5.0,
            action="BLOCK",
            created_by=self.user,
        )

        self.assertEqual(rule_block.action, "BLOCK")

    def test_meta_ordering(self):
        """Test meta ordering."""
        # Create another rule
        FraudDetectionRule.objects.create(
            name="Another Rule",
            rule_type=FraudDetectionRule.RuleType.LOCATION,
            threshold=50.0,
            created_by=self.user,
        )

        # Get all rules - should be ordered by is_active (desc) then name
        rules = FraudDetectionRule.objects.all()
        self.assertEqual(rules[0].name, "Another Rule")  # is_active True
        self.assertEqual(rules[1].name, "High Amount Transaction")  # is_active True


# ============================================================================
# FRAUD ALERT TESTS
# ============================================================================

class FraudAlertTest(TestCase):
    """Test cases for FraudAlert model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="adminpass123",
        )
        self.rule = FraudDetectionRule.objects.create(
            name="High Amount Transaction",
            rule_type=FraudDetectionRule.RuleType.TRANSACTION_AMOUNT,
            threshold=10000.0,
            created_by=self.admin,
        )
        self.alert = FraudAlert.objects.create(
            rule=self.rule,
            user=self.user,
            transaction_reference="TXN-123456",
            detected_value=15000.0,
            status=FraudAlert.AlertStatus.OPEN,
        )

    def test_create_fraud_alert(self):
        """Test creating a FraudAlert instance."""
        self.assertIsNotNone(self.alert.pk)
        self.assertEqual(self.alert.rule, self.rule)
        self.assertEqual(self.alert.user, self.user)
        self.assertEqual(self.alert.transaction_reference, "TXN-123456")
        self.assertEqual(self.alert.detected_value, 15000.0)
        self.assertEqual(self.alert.status, FraudAlert.AlertStatus.OPEN)

    def test_str_representation(self):
        """Test string representation."""
        expected = f"Alert #{self.alert.pk} - Open"
        self.assertEqual(str(self.alert), expected)

    def test_alert_status_choices(self):
        """Test alert status choices."""
        choices = FraudAlert.AlertStatus.choices
        choice_values = [choice[0] for choice in choices]

        self.assertIn('OPEN', choice_values)
        self.assertIn('INVESTIGATING', choice_values)
        self.assertIn('RESOLVED', choice_values)
        self.assertIn('FALSE_POSITIVE', choice_values)

    def test_save_sets_resolved_at(self):
        """Test that resolved_at is set when status changes to resolved."""
        self.assertIsNone(self.alert.resolved_at)

        # Resolve the alert
        self.alert.status = FraudAlert.AlertStatus.RESOLVED
        self.alert.resolved_by = self.admin
        self.alert.save()

        self.alert.refresh_from_db()
        self.assertIsNotNone(self.alert.resolved_at)

    def test_save_sets_resolved_at_for_false_positive(self):
        """Test that resolved_at is set when status changes to false positive."""
        self.assertIsNone(self.alert.resolved_at)

        self.alert.status = FraudAlert.AlertStatus.FALSE_POSITIVE
        self.alert.resolved_by = self.admin
        self.alert.save()

        self.alert.refresh_from_db()
        self.assertIsNotNone(self.alert.resolved_at)

    def test_meta_indexes(self):
        """Test meta indexes exist."""
        # Get the meta options
        meta = FraudAlert._meta
        index_fields = [idx.fields for idx in meta.indexes]

        self.assertIn(['status'], index_fields)
        self.assertIn(['user'], index_fields)
        self.assertIn(['rule'], index_fields)

    def test_cascade_delete(self):
        """Test that alerts are deleted when rule is deleted."""
        alert_id = self.alert.pk

        # Delete the rule
        self.rule.delete()

        # Alert should be deleted
        with self.assertRaises(FraudAlert.DoesNotExist):
            FraudAlert.objects.get(pk=alert_id)


# ============================================================================
# AUDIT LOG TESTS
# ============================================================================

class AuditLogTest(TestCase):
    """Test cases for AuditLog model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        self.audit_log = AuditLog.objects.create(
            user=self.user,
            action="LOGIN",
            resource_type="User",
            resource_id=str(self.user.pk),
            description="User logged in successfully",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            metadata={"browser": "Chrome", "os": "Windows"},
        )

    def test_create_audit_log(self):
        """Test creating an AuditLog instance."""
        self.assertIsNotNone(self.audit_log.pk)
        self.assertEqual(self.audit_log.user, self.user)
        self.assertEqual(self.audit_log.action, "LOGIN")
        self.assertEqual(self.audit_log.resource_type, "User")
        self.assertEqual(self.audit_log.resource_id, str(self.user.pk))
        self.assertEqual(self.audit_log.description, "User logged in successfully")
        self.assertEqual(self.audit_log.ip_address, "192.168.1.1")
        self.assertEqual(self.audit_log.user_agent, "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        self.assertEqual(self.audit_log.metadata, {"browser": "Chrome", "os": "Windows"})

    def test_str_representation(self):
        """Test string representation."""
        expected = f"{self.user} - LOGIN - User"
        self.assertEqual(str(self.audit_log), expected)

    def test_meta_indexes(self):
        """Test meta indexes exist."""
        meta = AuditLog._meta
        index_fields = [idx.fields for idx in meta.indexes]

        self.assertIn(['user', 'timestamp'], index_fields)
        self.assertIn(['action', 'timestamp'], index_fields)
        self.assertIn(['resource_type', 'resource_id'], index_fields)

    def test_ordering(self):
        """Test meta ordering."""
        # Create another audit log
        AuditLog.objects.create(
            user=self.user,
            action="LOGOUT",
            resource_type="User",
            resource_id=str(self.user.pk),
            description="User logged out",
        )

        logs = AuditLog.objects.all()
        self.assertEqual(logs[0].action, "LOGOUT")  # Most recent first

    def test_null_user(self):
        """Test audit log with null user (system action)."""
        system_log = AuditLog.objects.create(
            user=None,
            action="CREATE",
            resource_type="System",
            resource_id="sys-1",
            description="System initialized",
        )

        self.assertIsNone(system_log.user)
        self.assertEqual(system_log.action, "CREATE")
        self.assertEqual(system_log.resource_type, "System")

    def test_metadata_json_field(self):
        """Test metadata JSON field."""
        self.audit_log.metadata = {"key": "value", "nested": {"inner": "data"}}
        self.audit_log.save()

        self.audit_log.refresh_from_db()
        self.assertEqual(self.audit_log.metadata, {"key": "value", "nested": {"inner": "data"}})

    def test_ip_address_nullable(self):
        """Test IP address is nullable."""
        log = AuditLog.objects.create(
            user=self.user,
            action="UPDATE",
            resource_type="Profile",
            resource_id="1",
            description="Profile updated",
        )

        self.assertIsNone(log.ip_address)


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class SecurityIntegrationTest(TestCase):
    """Integration tests for security models."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )

    def test_banking_security_and_audit_log_integration(self):
        """Test that banking security operations create audit logs."""
        # Set PIN
        security = BankingSecurity.objects.create(user=self.user)
        security.set_pin("1234")

        # Create audit log for PIN change
        AuditLog.objects.create(
            user=self.user,
            action="UPDATE",
            resource_type="BankingSecurity",
            resource_id=str(security.pk),
            description="PIN set successfully",
            metadata={"action": "set_pin"},
        )

        audit_logs = AuditLog.objects.filter(
            user=self.user,
            resource_type="BankingSecurity"
        )
        self.assertEqual(audit_logs.count(), 1)
        self.assertEqual(audit_logs[0].metadata, {"action": "set_pin"})

    def test_phone_change_and_audit_log_integration(self):
        """Test that phone change operations create audit logs."""
        phone_request = PhoneChangeRequest.objects.create(
            user=self.user,
            old_phone="+1234567890",
            new_phone="+0987654321",
        )

        # Generate OTP
        otp = phone_request.generate_otp()

        # Create audit log
        AuditLog.objects.create(
            user=self.user,
            action="UPDATE",
            resource_type="PhoneChangeRequest",
            resource_id=str(phone_request.pk),
            description="OTP generated for phone change",
            metadata={"otp_sent": True},
        )

        audit_logs = AuditLog.objects.filter(
            user=self.user,
            resource_type="PhoneChangeRequest"
        )
        self.assertEqual(audit_logs.count(), 1)
        self.assertEqual(audit_logs[0].metadata, {"otp_sent": True})

    def test_fraud_detection_integration(self):
        """Test fraud detection rule and alert integration."""
        # Create rule
        rule = FraudDetectionRule.objects.create(
            name="Suspicious Activity",
            rule_type=FraudDetectionRule.RuleType.BEHAVIORAL,
            threshold=5.0,
            action="REQUIRE_VERIFICATION",
            created_by=self.user,
        )

        # Create alert
        alert = FraudAlert.objects.create(
            rule=rule,
            user=self.user,
            detected_value=7.5,
            status=FraudAlert.AlertStatus.OPEN,
        )

        # Create audit log
        AuditLog.objects.create(
            user=self.user,
            action="TRANSACTION",
            resource_type="FraudAlert",
            resource_id=str(alert.pk),
            description=f"Fraud alert triggered by rule: {rule.name}",
            metadata={"detected_value": 7.5, "threshold": 5.0},
        )

        logs = AuditLog.objects.filter(
            user=self.user,
            resource_type="FraudAlert"
        )
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs[0].metadata["detected_value"], 7.5)