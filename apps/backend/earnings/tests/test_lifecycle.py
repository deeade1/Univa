# apps/backend/earnings/tests/test_lifecycle.py

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import User
from audit.constants import AuditAction
from audit.models import AuditLog
from earnings.models import Earning, EarningType
from earnings.services import EarningLifecycle


class EarningLifecycleTests(TestCase):

    def setUp(self):
        self.actor = User.objects.create_user(
            email="earning-actor@example.com",
            password="test-password",
        )

        self.beneficiary = User.objects.create_user(
            email="earning-beneficiary@example.com",
            password="test-password",
        )

        self.type = EarningType.objects.create(
            code="SERVICE",
            name="Service",
        )

    def make_earning(
        self,
        status=Earning.Status.CALCULATED,
    ):
        return Earning.objects.create(
            beneficiary=self.beneficiary,
            earning_type=self.type,
            source_type="transport",
            source_id="delivery-001",
            amount=Decimal("5000.00"),
            currency="NGN",
            status=status,
            earned_at="2026-09-27T10:00:00Z",
            calculated_at=(
                "2026-09-27T10:01:00Z"
                if status != Earning.Status.PENDING
                else None
            ),
        )

    def test_calculated_to_confirmed(self):
        earning = self.make_earning()

        EarningLifecycle.transition(
            earning=earning,
            target_status=Earning.Status.CONFIRMED,
            actor=self.actor,
        )

        earning.refresh_from_db()

        self.assertEqual(
            earning.status,
            Earning.Status.CONFIRMED,
        )

        self.assertIsNotNone(
            earning.confirmed_at,
        )

    def test_confirmed_to_payable(self):
        earning = self.make_earning(
            status=Earning.Status.CONFIRMED,
        )

        EarningLifecycle.transition(
            earning=earning,
            target_status=Earning.Status.PAYABLE,
            actor=self.actor,
        )

        earning.refresh_from_db()

        self.assertEqual(
            earning.status,
            Earning.Status.PAYABLE,
        )

        self.assertIsNotNone(
            earning.payable_at,
        )

    def test_payable_to_settled(self):
        earning = self.make_earning(
            status=Earning.Status.PAYABLE,
        )

        EarningLifecycle.transition(
            earning=earning,
            target_status=Earning.Status.SETTLED,
            actor=self.actor,
        )

        earning.refresh_from_db()

        self.assertEqual(
            earning.status,
            Earning.Status.SETTLED,
        )

        self.assertIsNotNone(
            earning.settled_at,
        )

    def test_invalid_transition_is_rejected(self):
        earning = self.make_earning(
            status=Earning.Status.CALCULATED,
        )

        with self.assertRaises(ValidationError):
            EarningLifecycle.transition(
                earning=earning,
                target_status=Earning.Status.SETTLED,
                actor=self.actor,
            )

    def test_same_state_is_rejected(self):
        earning = self.make_earning()

        with self.assertRaises(ValidationError):
            EarningLifecycle.transition(
                earning=earning,
                target_status=Earning.Status.CALCULATED,
                actor=self.actor,
            )

    def test_transition_creates_audit_record(self):
        earning = self.make_earning()

        EarningLifecycle.transition(
            earning=earning,
            target_status=Earning.Status.CONFIRMED,
            actor=self.actor,
        )

        audit = AuditLog.objects.get()

        self.assertEqual(
            audit.action,
            AuditAction.EARNING_CONFIRMED,
        )

        self.assertEqual(
            audit.actor,
            self.actor,
        )

        self.assertEqual(
            audit.target_user,
            self.beneficiary,
        )

        self.assertEqual(
            audit.data["from_status"],
            Earning.Status.CALCULATED,
        )

        self.assertEqual(
            audit.data["to_status"],
            Earning.Status.CONFIRMED,
        )