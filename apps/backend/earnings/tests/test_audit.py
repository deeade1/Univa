# apps/backend/earnings/tests/test_audit.py

from decimal import Decimal

from django.test import TestCase

from accounts.models import User
from audit.constants import AuditAction
from audit.models import AuditLog
from earnings.models import Earning, EarningType
from earnings.services import EarningAuditService


class EarningAuditServiceTests(TestCase):

    def setUp(self):
        self.actor = User.objects.create_user(
            email="earning-audit-actor@example.com",
            password="test-password",
        )

        self.beneficiary = User.objects.create_user(
            email="earning-audit-beneficiary@example.com",
            password="test-password",
        )

        self.type = EarningType.objects.create(
            code="SERVICE",
            name="Service",
        )

        self.earning = Earning.objects.create(
            beneficiary=self.beneficiary,
            earning_type=self.type,
            source_type="transport",
            source_id="delivery-audit-001",
            source_reference="DEL-AUDIT-001",
            amount=Decimal("5000.00"),
            currency="NGN",
            status=Earning.Status.CALCULATED,
            earned_at="2026-09-27T10:00:00Z",
            calculated_at="2026-09-27T10:01:00Z",
        )

    def test_record_transition_creates_audit(self):
        audit = EarningAuditService.record_transition(
            earning=self.earning,
            action=AuditAction.EARNING_CONFIRMED,
            actor=self.actor,
            from_status=Earning.Status.CALCULATED,
            to_status=Earning.Status.CONFIRMED,
        )

        self.assertIsInstance(
            audit,
            AuditLog,
        )

        self.assertEqual(
            AuditLog.objects.count(),
            1,
        )

    def test_records_actor(self):
        audit = EarningAuditService.record_transition(
            earning=self.earning,
            action=AuditAction.EARNING_CONFIRMED,
            actor=self.actor,
        )

        self.assertEqual(
            audit.actor,
            self.actor,
        )

    def test_records_beneficiary(self):
        audit = EarningAuditService.record_transition(
            earning=self.earning,
            action=AuditAction.EARNING_CONFIRMED,
            actor=self.actor,
        )

        self.assertEqual(
            audit.target_user,
            self.beneficiary,
        )

    def test_records_identity(self):
        audit = EarningAuditService.record_transition(
            earning=self.earning,
            action=AuditAction.EARNING_CONFIRMED,
            actor=self.actor,
        )

        self.assertEqual(
            audit.data["object_type"],
            "earning",
        )

        self.assertEqual(
            audit.data["object_id"],
            str(self.earning.id),
        )

    def test_records_financial_context(self):
        audit = EarningAuditService.record_transition(
            earning=self.earning,
            action=AuditAction.EARNING_CONFIRMED,
            actor=self.actor,
        )

        self.assertEqual(
            audit.data["amount"],
            "5000.00",
        )

        self.assertEqual(
            audit.data["currency"],
            "NGN",
        )

        self.assertEqual(
            audit.data["earning_type"],
            "SERVICE",
        )

    def test_records_source_context(self):
        audit = EarningAuditService.record_transition(
            earning=self.earning,
            action=AuditAction.EARNING_CONFIRMED,
            actor=self.actor,
        )

        self.assertEqual(
            audit.data["source_type"],
            "transport",
        )

        self.assertEqual(
            audit.data["source_id"],
            "delivery-audit-001",
        )

        self.assertEqual(
            audit.data["source_reference"],
            "DEL-AUDIT-001",
        )

    def test_system_audit_has_no_actor(self):
        audit = EarningAuditService.record_transition(
            earning=self.earning,
            action=AuditAction.EARNING_CALCULATED,
        )

        self.assertIsNone(
            audit.actor,
        )

        self.assertEqual(
            audit.target_user,
            self.beneficiary,
        )

    def test_invalid_action_is_rejected(self):
        with self.assertRaises(ValueError):
            EarningAuditService.record_transition(
                earning=self.earning,
                action="EARNING.INVALID",
                actor=self.actor,
            )

        self.assertEqual(
            AuditLog.objects.count(),
            0,
        )