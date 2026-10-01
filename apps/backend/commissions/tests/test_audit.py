from decimal import Decimal

from django.test import TestCase

from accounts.models import User
from audit.constants import AuditAction
from audit.models import AuditLog
from commissions.models import Commission, CommissionPlan
from commissions.services import CommissionAuditService


class CommissionAuditServiceTests(TestCase):
    def setUp(self):
        self.actor = User.objects.create_user(
            email="audit-actor@example.com",
            password="test-password",
        )

        self.beneficiary = User.objects.create_user(
            email="audit-beneficiary@example.com",
            password="test-password",
        )

        self.plan = CommissionPlan.objects.create(
            name="Audit Test Plan",
            code="AUDIT_TEST_PLAN",
            plan_type=CommissionPlan.PlanType.PERCENTAGE,
            percentage=Decimal("10.0000"),
        )

        self.commission = Commission.objects.create(
            plan=self.plan,
            beneficiary=self.beneficiary,
            source_type=Commission.SourceType.TRANSPORT,
            source_id="trip-audit-001",
            calculation_basis=Decimal("100000.00"),
            rate=Decimal("10.0000"),
            calculated_amount=Decimal("10000.00"),
            currency="NGN",
            status=Commission.Status.CALCULATED,
        )

    def test_record_transition_creates_audit_log(self):
        audit = CommissionAuditService.record_transition(
            commission=self.commission,
            action=AuditAction.COMMISSION_APPROVED,
            actor=self.actor,
            from_status=Commission.Status.CALCULATED,
            to_status=Commission.Status.APPROVED,
        )

        self.assertIsInstance(
            audit,
            AuditLog,
        )

        self.assertEqual(
            AuditLog.objects.count(),
            1,
        )

    def test_record_transition_records_actor(self):
        audit = CommissionAuditService.record_transition(
            commission=self.commission,
            action=AuditAction.COMMISSION_APPROVED,
            actor=self.actor,
            from_status=Commission.Status.CALCULATED,
            to_status=Commission.Status.APPROVED,
        )

        self.assertEqual(
            audit.actor,
            self.actor,
        )

    def test_record_transition_records_beneficiary_as_target_user(self):
        audit = CommissionAuditService.record_transition(
            commission=self.commission,
            action=AuditAction.COMMISSION_APPROVED,
            actor=self.actor,
            from_status=Commission.Status.CALCULATED,
            to_status=Commission.Status.APPROVED,
        )

        self.assertEqual(
            audit.target_user,
            self.beneficiary,
        )

    def test_record_transition_records_action(self):
        audit = CommissionAuditService.record_transition(
            commission=self.commission,
            action=AuditAction.COMMISSION_APPROVED,
            actor=self.actor,
            from_status=Commission.Status.CALCULATED,
            to_status=Commission.Status.APPROVED,
        )

        self.assertEqual(
            audit.action,
            AuditAction.COMMISSION_APPROVED,
        )

    def test_record_transition_records_commission_identity(self):
        audit = CommissionAuditService.record_transition(
            commission=self.commission,
            action=AuditAction.COMMISSION_APPROVED,
            actor=self.actor,
            from_status=Commission.Status.CALCULATED,
            to_status=Commission.Status.APPROVED,
        )

        self.assertEqual(
            audit.data["object_type"],
            "commission",
        )

        self.assertEqual(
            audit.data["object_id"],
            str(self.commission.id),
        )

    def test_record_transition_records_status_change(self):
        audit = CommissionAuditService.record_transition(
            commission=self.commission,
            action=AuditAction.COMMISSION_APPROVED,
            actor=self.actor,
            from_status=Commission.Status.CALCULATED,
            to_status=Commission.Status.APPROVED,
        )

        self.assertEqual(
            audit.data["from_status"],
            Commission.Status.CALCULATED,
        )

        self.assertEqual(
            audit.data["to_status"],
            Commission.Status.APPROVED,
        )

    def test_record_transition_records_financial_context(self):
        audit = CommissionAuditService.record_transition(
            commission=self.commission,
            action=AuditAction.COMMISSION_APPROVED,
            actor=self.actor,
            from_status=Commission.Status.CALCULATED,
            to_status=Commission.Status.APPROVED,
        )

        self.assertEqual(
            audit.data["calculated_amount"],
            "10000.00",
        )

        self.assertEqual(
            audit.data["currency"],
            "NGN",
        )

        self.assertEqual(
            audit.data["plan_id"],
            str(self.plan.id),
        )

    def test_record_transition_records_source_context(self):
        audit = CommissionAuditService.record_transition(
            commission=self.commission,
            action=AuditAction.COMMISSION_APPROVED,
            actor=self.actor,
            from_status=Commission.Status.CALCULATED,
            to_status=Commission.Status.APPROVED,
        )

        self.assertEqual(
            audit.data["source_type"],
            Commission.SourceType.TRANSPORT,
        )

        self.assertEqual(
            audit.data["source_id"],
            "trip-audit-001",
        )

    def test_record_transition_supports_extra_data(self):
        audit = CommissionAuditService.record_transition(
            commission=self.commission,
            action=AuditAction.COMMISSION_APPROVED,
            actor=self.actor,
            from_status=Commission.Status.CALCULATED,
            to_status=Commission.Status.APPROVED,
            approval_reference="APPROVAL-001",
            reason="Manual approval",
        )

        self.assertEqual(
            audit.data["approval_reference"],
            "APPROVAL-001",
        )

        self.assertEqual(
            audit.data["reason"],
            "Manual approval",
        )

    def test_record_transition_without_actor_creates_system_audit(self):
        audit = CommissionAuditService.record_transition(
            commission=self.commission,
            action=AuditAction.COMMISSION_CALCULATED,
            from_status=Commission.Status.PENDING,
            to_status=Commission.Status.CALCULATED,
        )

        self.assertIsNone(
            audit.actor,
        )

        self.assertEqual(
            audit.target_user,
            self.beneficiary,
        )

    def test_invalid_audit_action_is_rejected_by_canonical_audit_service(self):
        with self.assertRaises(ValueError):
            CommissionAuditService.record_transition(
                commission=self.commission,
                action="COMMISSION.INVALID_ACTION",
                actor=self.actor,
                from_status=Commission.Status.CALCULATED,
                to_status=Commission.Status.APPROVED,
            )

        self.assertEqual(
            AuditLog.objects.count(),
            0,
        )