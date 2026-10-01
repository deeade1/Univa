from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase

from audit.constants import AuditAction
from settlements.models import Settlement
from settlements.services.audit import (
SETTLEMENT_AUDIT_ACTIONS,
SettlementAuditService,
)

class SettlementAuditServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.beneficiary = cls._create_user(
        email="[beneficiary@example.com](mailto:beneficiary@example.com)",
        )
        cls.actor = cls._create_user(
        email="[actor@example.com](mailto:actor@example.com)",
        )

    @staticmethod
    def _create_user(*, email):
        from django.contrib.auth import get_user_model

        User = get_user_model()

        return User.objects.create_user(
            email=email,
            password="test-password",
        )

    def create_settlement(
        self,
        *,
        status=Settlement.Status.PENDING,
        source_reference="SOURCE-001",
        failure_code="",
        failure_reason="",
    ):
        settlement = Settlement.objects.create(
            reference="SET-001",
            beneficiary=self.beneficiary,
            source_type="earning",
            source_id="earning-001",
            source_reference=source_reference,
            amount=Decimal("10000.00"),
            currency="NGN",
            status=status,
            idempotency_key="idem-001",
            failure_code=failure_code,
            failure_reason=failure_reason,
        )

        return settlement

    def test_audit_action_mapping_contains_all_auditable_statuses(self):
        expected = {
            Settlement.Status.ELIGIBLE: AuditAction.SETTLEMENT_ELIGIBLE,
            Settlement.Status.PROCESSING: AuditAction.SETTLEMENT_PROCESSING,
            Settlement.Status.SETTLED: AuditAction.SETTLEMENT_SETTLED,
            Settlement.Status.FAILED: AuditAction.SETTLEMENT_FAILED,
            Settlement.Status.CANCELLED: AuditAction.SETTLEMENT_CANCELLED,
            Settlement.Status.REVERSED: AuditAction.SETTLEMENT_REVERSED,
        }

        self.assertEqual(
            SETTLEMENT_AUDIT_ACTIONS,
            expected,
        )

    @patch("settlements.services.audit.record_audit")
    def test_record_transition_eligible(self, mock_record_audit):
        settlement = self.create_settlement(
            status=Settlement.Status.ELIGIBLE,
        )

        expected_result = object()
        mock_record_audit.return_value = expected_result

        result = SettlementAuditService.record_transition(
            settlement,
            previous_status=Settlement.Status.PENDING,
            new_status=Settlement.Status.ELIGIBLE,
            actor=self.actor,
        )

        self.assertIs(result, expected_result)

        mock_record_audit.assert_called_once_with(
            action=AuditAction.SETTLEMENT_ELIGIBLE,
            actor=self.actor,
            target_user=self.beneficiary,
            data={
                "settlement_id": str(settlement.id),
                "reference": settlement.reference,
                "previous_status": Settlement.Status.PENDING,
                "new_status": Settlement.Status.ELIGIBLE,
                "amount": "10000.00",
                "currency": "NGN",
                "source_type": "earning",
                "source_id": "earning-001",
                "source_reference": "SOURCE-001",
            },
        )

    @patch("settlements.services.audit.record_audit")
    def test_record_transition_processing(self, mock_record_audit):
        settlement = self.create_settlement(
            status=Settlement.Status.PROCESSING,
        )

        SettlementAuditService.record_transition(
            settlement,
            previous_status=Settlement.Status.ELIGIBLE,
            new_status=Settlement.Status.PROCESSING,
            actor=self.actor,
        )

        mock_record_audit.assert_called_once_with(
            action=AuditAction.SETTLEMENT_PROCESSING,
            actor=self.actor,
            target_user=self.beneficiary,
            data={
                "settlement_id": str(settlement.id),
                "reference": settlement.reference,
                "previous_status": Settlement.Status.ELIGIBLE,
                "new_status": Settlement.Status.PROCESSING,
                "amount": "10000.00",
                "currency": "NGN",
                "source_type": "earning",
                "source_id": "earning-001",
                "source_reference": "SOURCE-001",
            },
        )

    @patch("settlements.services.audit.record_audit")
    def test_record_transition_settled(self, mock_record_audit):
        settlement = self.create_settlement(
            status=Settlement.Status.SETTLED,
        )

        SettlementAuditService.record_transition(
            settlement,
            previous_status=Settlement.Status.PROCESSING,
            new_status=Settlement.Status.SETTLED,
            actor=self.actor,
        )

        mock_record_audit.assert_called_once_with(
            action=AuditAction.SETTLEMENT_SETTLED,
            actor=self.actor,
            target_user=self.beneficiary,
            data={
                "settlement_id": str(settlement.id),
                "reference": settlement.reference,
                "previous_status": Settlement.Status.PROCESSING,
                "new_status": Settlement.Status.SETTLED,
                "amount": "10000.00",
                "currency": "NGN",
                "source_type": "earning",
                "source_id": "earning-001",
                "source_reference": "SOURCE-001",
            },
        )

    @patch("settlements.services.audit.record_audit")
    def test_record_transition_failed_includes_failure_information(
        self,
        mock_record_audit,
    ):
        settlement = self.create_settlement(
            status=Settlement.Status.FAILED,
            failure_code="PROVIDER_TIMEOUT",
            failure_reason="Settlement provider timed out.",
        )

        SettlementAuditService.record_transition(
            settlement,
            previous_status=Settlement.Status.PROCESSING,
            new_status=Settlement.Status.FAILED,
            actor=self.actor,
        )

        mock_record_audit.assert_called_once_with(
            action=AuditAction.SETTLEMENT_FAILED,
            actor=self.actor,
            target_user=self.beneficiary,
            data={
                "settlement_id": str(settlement.id),
                "reference": settlement.reference,
                "previous_status": Settlement.Status.PROCESSING,
                "new_status": Settlement.Status.FAILED,
                "amount": "10000.00",
                "currency": "NGN",
                "source_type": "earning",
                "source_id": "earning-001",
                "source_reference": "SOURCE-001",
                "failure_code": "PROVIDER_TIMEOUT",
                "failure_reason": "Settlement provider timed out.",
            },
        )

    @patch("settlements.services.audit.record_audit")
    def test_record_transition_cancelled(self, mock_record_audit):
        settlement = self.create_settlement(
            status=Settlement.Status.CANCELLED,
        )

        SettlementAuditService.record_transition(
            settlement,
            previous_status=Settlement.Status.PENDING,
            new_status=Settlement.Status.CANCELLED,
            actor=self.actor,
        )

        mock_record_audit.assert_called_once_with(
            action=AuditAction.SETTLEMENT_CANCELLED,
            actor=self.actor,
            target_user=self.beneficiary,
            data={
                "settlement_id": str(settlement.id),
                "reference": settlement.reference,
                "previous_status": Settlement.Status.PENDING,
                "new_status": Settlement.Status.CANCELLED,
                "amount": "10000.00",
                "currency": "NGN",
                "source_type": "earning",
                "source_id": "earning-001",
                "source_reference": "SOURCE-001",
            },
        )

    @patch("settlements.services.audit.record_audit")
    def test_record_transition_reversed(self, mock_record_audit):
        settlement = self.create_settlement(
            status=Settlement.Status.REVERSED,
        )

        SettlementAuditService.record_transition(
            settlement,
            previous_status=Settlement.Status.SETTLED,
            new_status=Settlement.Status.REVERSED,
            actor=self.actor,
        )

        mock_record_audit.assert_called_once_with(
            action=AuditAction.SETTLEMENT_REVERSED,
            actor=self.actor,
            target_user=self.beneficiary,
            data={
                "settlement_id": str(settlement.id),
                "reference": settlement.reference,
                "previous_status": Settlement.Status.SETTLED,
                "new_status": Settlement.Status.REVERSED,
                "amount": "10000.00",
                "currency": "NGN",
                "source_type": "earning",
                "source_id": "earning-001",
                "source_reference": "SOURCE-001",
            },
        )

    @patch("settlements.services.audit.record_audit")
    def test_actor_is_optional(self, mock_record_audit):
        settlement = self.create_settlement(
            status=Settlement.Status.ELIGIBLE,
        )

        SettlementAuditService.record_transition(
            settlement,
            previous_status=Settlement.Status.PENDING,
            new_status=Settlement.Status.ELIGIBLE,
        )

        self.assertEqual(
            mock_record_audit.call_args.kwargs["actor"],
            None,
        )

    @patch("settlements.services.audit.record_audit")
    def test_source_reference_is_omitted_when_empty(
        self,
        mock_record_audit,
    ):
        settlement = self.create_settlement(
            status=Settlement.Status.ELIGIBLE,
            source_reference="",
        )

        SettlementAuditService.record_transition(
            settlement,
            previous_status=Settlement.Status.PENDING,
            new_status=Settlement.Status.ELIGIBLE,
            actor=self.actor,
        )

        data = mock_record_audit.call_args.kwargs["data"]

        self.assertNotIn(
            "source_reference",
            data,
        )

    @patch("settlements.services.audit.record_audit")
    def test_target_user_is_set_to_beneficiary(
        self,
        mock_record_audit,
    ):
        settlement = self.create_settlement(
            status=Settlement.Status.SETTLED,
        )

        SettlementAuditService.record_transition(
            settlement,
            previous_status=Settlement.Status.PROCESSING,
            new_status=Settlement.Status.SETTLED,
            actor=self.actor,
        )

        self.assertEqual(
            mock_record_audit.call_args.kwargs["target_user"],
            settlement.beneficiary,
        )

    @patch("settlements.services.audit.record_audit")
    def test_record_audit_called_exactly_once(
        self,
        mock_record_audit,
    ):
        settlement = self.create_settlement(
            status=Settlement.Status.ELIGIBLE,
        )

        SettlementAuditService.record_transition(
            settlement,
            previous_status=Settlement.Status.PENDING,
            new_status=Settlement.Status.ELIGIBLE,
            actor=self.actor,
        )

        mock_record_audit.assert_called_once()

    def test_unknown_status_raises_value_error(self):
        settlement = self.create_settlement()

        with self.assertRaises(ValueError):
            SettlementAuditService.record_transition(
                settlement,
                previous_status=Settlement.Status.PENDING,
                new_status="unknown-status",
                actor=self.actor,
            )

