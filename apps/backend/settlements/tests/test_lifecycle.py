"""
SettlementLifecycle tests.

These tests cover only Settlement state transitions.

They intentionally do not test:

    - Payment
    - Banking
    - external providers
    - SettlementAttempt
    - Audit
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch

from accounts.models import User
from settlements.models import Settlement
from settlements.services import (
    SettlementLifecycle,
    SettlementService,
)


class SettlementLifecycleTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="settlement-lifecycle@example.com",
            password="test-password",
        )

        cls.actor = User.objects.create_user(
            email="settlement-lifecycle-actor@example.com",
            password="test-password",
        )


    def create_settlement(self, **overrides):
        defaults = {
            "reference": "SET-LIFECYCLE-001",
            "beneficiary": self.user,
            "source_type": "earning",
            "source_id": "earning-001",
            "source_reference": "EARN-001",
            "amount": Decimal("50000.00"),
            "currency": "NGN",
            "idempotency_key": "settlement-lifecycle-key-001",
        }

        defaults.update(overrides)

        return SettlementService.create_settlement(
            **defaults
        )

    def test_pending_to_eligible(self):
        settlement = self.create_settlement()

        result = SettlementLifecycle.mark_eligible(
            settlement,
        )

        result.refresh_from_db()

        self.assertEqual(
            result.status,
            Settlement.Status.ELIGIBLE,
        )
        self.assertIsNotNone(
            result.eligible_at,
        )

    def test_eligible_to_processing(self):
        settlement = self.create_settlement()

        SettlementLifecycle.mark_eligible(
            settlement,
        )

        result = SettlementLifecycle.mark_processing(
            settlement,
        )

        result.refresh_from_db()

        self.assertEqual(
            result.status,
            Settlement.Status.PROCESSING,
        )
        self.assertIsNotNone(
            result.processing_at,
        )

    def test_processing_to_settled(self):
        settlement = self.create_settlement()

        SettlementLifecycle.mark_eligible(
            settlement,
        )
        SettlementLifecycle.mark_processing(
            settlement,
        )

        result = SettlementLifecycle.mark_settled(
            settlement,
        )

        result.refresh_from_db()

        self.assertEqual(
            result.status,
            Settlement.Status.SETTLED,
        )
        self.assertIsNotNone(
            result.settled_at,
        )

    def test_processing_to_failed(self):
        settlement = self.create_settlement()

        SettlementLifecycle.mark_eligible(
            settlement,
        )
        SettlementLifecycle.mark_processing(
            settlement,
        )

        result = SettlementLifecycle.mark_failed(
            settlement,
            failure_code="PROVIDER_REJECTED",
            failure_reason="Provider rejected settlement.",
        )

        result.refresh_from_db()

        self.assertEqual(
            result.status,
            Settlement.Status.FAILED,
        )
        self.assertIsNotNone(
            result.failed_at,
        )
        self.assertEqual(
            result.failure_code,
            "PROVIDER_REJECTED",
        )
        self.assertEqual(
            result.failure_reason,
            "Provider rejected settlement.",
        )

    def test_failed_to_processing_clears_failure_information(self):
        settlement = self.create_settlement()

        SettlementLifecycle.mark_eligible(
            settlement,
        )
        SettlementLifecycle.mark_processing(
            settlement,
        )
        SettlementLifecycle.mark_failed(
            settlement,
            failure_code="PROVIDER_ERROR",
            failure_reason="Provider unavailable.",
        )

        result = SettlementLifecycle.mark_processing(
            settlement,
        )

        result.refresh_from_db()

        self.assertEqual(
            result.status,
            Settlement.Status.PROCESSING,
        )
        self.assertIsNotNone(
            result.processing_at,
        )
        self.assertEqual(
            result.failure_code,
            "",
        )
        self.assertEqual(
            result.failure_reason,
            "",
        )
        self.assertIsNone(
            result.failed_at,
        )

    def test_pending_to_cancelled(self):
        settlement = self.create_settlement()

        result = SettlementLifecycle.cancel(
            settlement,
        )

        result.refresh_from_db()

        self.assertEqual(
            result.status,
            Settlement.Status.CANCELLED,
        )
        self.assertIsNotNone(
            result.cancelled_at,
        )

    def test_eligible_to_cancelled(self):
        settlement = self.create_settlement()

        SettlementLifecycle.mark_eligible(
            settlement,
        )

        result = SettlementLifecycle.cancel(
            settlement,
        )

        result.refresh_from_db()

        self.assertEqual(
            result.status,
            Settlement.Status.CANCELLED,
        )
        self.assertIsNotNone(
            result.cancelled_at,
        )

    def test_failed_to_cancelled(self):
        settlement = self.create_settlement()

        SettlementLifecycle.mark_eligible(
            settlement,
        )
        SettlementLifecycle.mark_processing(
            settlement,
        )
        SettlementLifecycle.mark_failed(
            settlement,
            failure_reason="Provider unavailable.",
        )

        result = SettlementLifecycle.cancel(
            settlement,
        )

        result.refresh_from_db()

        self.assertEqual(
            result.status,
            Settlement.Status.CANCELLED,
        )
        self.assertIsNotNone(
            result.cancelled_at,
        )

    def test_settled_to_reversed(self):
        settlement = self.create_settlement()

        SettlementLifecycle.mark_eligible(
            settlement,
        )
        SettlementLifecycle.mark_processing(
            settlement,
        )
        SettlementLifecycle.mark_settled(
            settlement,
        )

        result = SettlementLifecycle.reverse(
            settlement,
        )

        result.refresh_from_db()

        self.assertEqual(
            result.status,
            Settlement.Status.REVERSED,
        )
        self.assertIsNotNone(
            result.reversed_at,
        )

    def test_pending_cannot_go_directly_to_processing(self):
        settlement = self.create_settlement()

        with self.assertRaises(ValidationError):
            SettlementLifecycle.mark_processing(
                settlement,
            )

    def test_pending_cannot_be_settled(self):
        settlement = self.create_settlement()

        with self.assertRaises(ValidationError):
            SettlementLifecycle.mark_settled(
                settlement,
            )

    def test_pending_cannot_be_reversed(self):
        settlement = self.create_settlement()

        with self.assertRaises(ValidationError):
            SettlementLifecycle.reverse(
                settlement,
            )

    def test_eligible_cannot_be_settled(self):
        settlement = self.create_settlement()

        SettlementLifecycle.mark_eligible(
            settlement,
        )

        with self.assertRaises(ValidationError):
            SettlementLifecycle.mark_settled(
                settlement,
            )

    def test_processing_cannot_be_cancelled(self):
        settlement = self.create_settlement()

        SettlementLifecycle.mark_eligible(
            settlement,
        )
        SettlementLifecycle.mark_processing(
            settlement,
        )

        with self.assertRaises(ValidationError):
            SettlementLifecycle.cancel(
                settlement,
            )

    def test_processing_cannot_be_reversed(self):
        settlement = self.create_settlement()

        SettlementLifecycle.mark_eligible(
            settlement,
        )
        SettlementLifecycle.mark_processing(
            settlement,
        )

        with self.assertRaises(ValidationError):
            SettlementLifecycle.reverse(
                settlement,
            )

    def test_settled_cannot_be_processed_again(self):
        settlement = self.create_settlement()

        SettlementLifecycle.mark_eligible(
            settlement,
        )
        SettlementLifecycle.mark_processing(
            settlement,
        )
        SettlementLifecycle.mark_settled(
            settlement,
        )

        with self.assertRaises(ValidationError):
            SettlementLifecycle.mark_processing(
                settlement,
            )

    def test_settled_cannot_be_cancelled(self):
        settlement = self.create_settlement()

        SettlementLifecycle.mark_eligible(
            settlement,
        )
        SettlementLifecycle.mark_processing(
            settlement,
        )
        SettlementLifecycle.mark_settled(
            settlement,
        )

        with self.assertRaises(ValidationError):
            SettlementLifecycle.cancel(
                settlement,
            )

    def test_cancelled_is_terminal(self):
        settlement = self.create_settlement()

        SettlementLifecycle.cancel(
            settlement,
        )

        with self.assertRaises(ValidationError):
            SettlementLifecycle.mark_eligible(
                settlement,
            )

    def test_reversed_is_terminal(self):
        settlement = self.create_settlement()

        SettlementLifecycle.mark_eligible(
            settlement,
        )
        SettlementLifecycle.mark_processing(
            settlement,
        )
        SettlementLifecycle.mark_settled(
            settlement,
        )
        SettlementLifecycle.reverse(
            settlement,
        )

        with self.assertRaises(ValidationError):
            SettlementLifecycle.mark_processing(
                settlement,
            )

    def test_mark_failed_requires_reason(self):
        settlement = self.create_settlement()

        SettlementLifecycle.mark_eligible(
            settlement,
        )
        SettlementLifecycle.mark_processing(
            settlement,
        )

        with self.assertRaises(ValidationError):
            SettlementLifecycle.mark_failed(
                settlement,
                failure_reason="",
            )

    def test_mark_failed_accepts_failure_code(self):
        settlement = self.create_settlement()

        SettlementLifecycle.mark_eligible(
            settlement,
        )
        SettlementLifecycle.mark_processing(
            settlement,
        )

        result = SettlementLifecycle.mark_failed(
            settlement,
            failure_code="TIMEOUT",
            failure_reason="Provider request timed out.",
        )

        self.assertEqual(
            result.failure_code,
            "TIMEOUT",
        )

    def test_transition_preserves_financial_identity(self):
        settlement = self.create_settlement()

        original_amount = settlement.amount
        original_currency = settlement.currency
        original_source_type = settlement.source_type
        original_source_id = settlement.source_id
        original_beneficiary_id = settlement.beneficiary_id

        SettlementLifecycle.mark_eligible(
            settlement,
        )
        SettlementLifecycle.mark_processing(
            settlement,
        )
        SettlementLifecycle.mark_settled(
            settlement,
        )

        settlement.refresh_from_db()

        self.assertEqual(
            settlement.amount,
            original_amount,
        )
        self.assertEqual(
            settlement.currency,
            original_currency,
        )
        self.assertEqual(
            settlement.source_type,
            original_source_type,
        )
        self.assertEqual(
            settlement.source_id,
            original_source_id,
        )
        self.assertEqual(
            settlement.beneficiary_id,
            original_beneficiary_id,
        )
        
    

    @patch(
        "settlements.services.lifecycle.SettlementAuditService.record_transition"
    )
    def test_mark_eligible_records_audit(self, mock_audit):
        settlement = self.create_settlement()

        SettlementLifecycle.mark_eligible(
            settlement,
            actor=self.actor,
        )

        mock_audit.assert_called_once_with(
            settlement,
            previous_status=Settlement.Status.PENDING,
            new_status=Settlement.Status.ELIGIBLE,
            actor=self.actor,
        )

    @patch(
        "settlements.services.lifecycle.SettlementAuditService.record_transition"
    )
    def test_mark_processing_records_audit(self, mock_audit):
        settlement = self.create_settlement()

        SettlementLifecycle.mark_eligible(
            settlement,
        )

        mock_audit.reset_mock()

        SettlementLifecycle.mark_processing(
            settlement,
            actor=self.actor,
        )

        mock_audit.assert_called_once_with(
            settlement,
            previous_status=Settlement.Status.ELIGIBLE,
            new_status=Settlement.Status.PROCESSING,
            actor=self.actor,
        )

    @patch(
        "settlements.services.lifecycle.SettlementAuditService.record_transition"
    )
    def test_mark_settled_records_audit(self, mock_audit):
        settlement = self.create_settlement()

        SettlementLifecycle.mark_eligible(
            settlement,
        )

        SettlementLifecycle.mark_processing(
            settlement,
        )

        mock_audit.reset_mock()

        SettlementLifecycle.mark_settled(
            settlement,
            actor=self.actor,
        )

        mock_audit.assert_called_once_with(
            settlement,
            previous_status=Settlement.Status.PROCESSING,
            new_status=Settlement.Status.SETTLED,
            actor=self.actor,
        )

    @patch(
        "settlements.services.lifecycle.SettlementAuditService.record_transition"
    )
    def test_mark_failed_records_audit(self, mock_audit):
        settlement = self.create_settlement()

        SettlementLifecycle.mark_eligible(
            settlement,
        )

        SettlementLifecycle.mark_processing(
            settlement,
        )

        mock_audit.reset_mock()

        SettlementLifecycle.mark_failed(
            settlement,
            failure_reason="Provider timeout.",
            failure_code="TIMEOUT",
            actor=self.actor,
        )

        mock_audit.assert_called_once_with(
            settlement,
            previous_status=Settlement.Status.PROCESSING,
            new_status=Settlement.Status.FAILED,
            actor=self.actor,
        )

    @patch(
        "settlements.services.lifecycle.SettlementAuditService.record_transition"
    )
    def test_cancel_records_audit(self, mock_audit):
        settlement = self.create_settlement()

        SettlementLifecycle.cancel(
            settlement,
            actor=self.actor,
        )

        mock_audit.assert_called_once_with(
            settlement,
            previous_status=Settlement.Status.PENDING,
            new_status=Settlement.Status.CANCELLED,
            actor=self.actor,
        )

    @patch(
        "settlements.services.lifecycle.SettlementAuditService.record_transition"
    )
    def test_reverse_records_audit(self, mock_audit):
        settlement = self.create_settlement()

        SettlementLifecycle.mark_eligible(
            settlement,
        )

        SettlementLifecycle.mark_processing(
            settlement,
        )

        SettlementLifecycle.mark_settled(
            settlement,
        )

        mock_audit.reset_mock()

        SettlementLifecycle.reverse(
            settlement,
            actor=self.actor,
        )

        mock_audit.assert_called_once_with(
            settlement,
            previous_status=Settlement.Status.SETTLED,
            new_status=Settlement.Status.REVERSED,
            actor=self.actor,
        )

    @patch(
        "settlements.services.lifecycle.SettlementAuditService.record_transition"
    )
    def test_failed_to_processing_records_audit(self, mock_audit):
        settlement = self.create_settlement()

        SettlementLifecycle.mark_eligible(
            settlement,
        )

        SettlementLifecycle.mark_processing(
            settlement,
        )

        SettlementLifecycle.mark_failed(
            settlement,
            failure_code="TIMEOUT",
            failure_reason="Provider timeout.",
        )

        mock_audit.reset_mock()

        SettlementLifecycle.mark_processing(
            settlement,
            actor=self.actor,
        )

        mock_audit.assert_called_once_with(
            settlement,
            previous_status=Settlement.Status.FAILED,
            new_status=Settlement.Status.PROCESSING,
            actor=self.actor,
        )

    @patch(
        "settlements.services.lifecycle.SettlementAuditService.record_transition"
    )
    def test_failed_to_cancelled_records_audit(self, mock_audit):
        settlement = self.create_settlement()

        SettlementLifecycle.mark_eligible(
            settlement,
        )

        SettlementLifecycle.mark_processing(
            settlement,
        )

        SettlementLifecycle.mark_failed(
            settlement,
            failure_code="TIMEOUT",
            failure_reason="Provider timeout.",
        )

        mock_audit.reset_mock()

        SettlementLifecycle.cancel(
            settlement,
            actor=self.actor,
        )

        mock_audit.assert_called_once_with(
            settlement,
            previous_status=Settlement.Status.FAILED,
            new_status=Settlement.Status.CANCELLED,
            actor=self.actor,
        )

