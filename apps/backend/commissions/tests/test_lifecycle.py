from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import User
from commissions.models import Commission, CommissionPlan
from commissions.services import CommissionLifecycle


class CommissionLifecycleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="lifecycle@example.com",
            password="test-password",
        )

        self.plan = CommissionPlan.objects.create(
            name="Lifecycle Test Plan",
            code="LIFECYCLE_TEST",
            plan_type=CommissionPlan.PlanType.PERCENTAGE,
            percentage=Decimal("10.0000"),
        )

    def create_commission(
        self,
        *,
        status=Commission.Status.PENDING,
    ):
        return Commission.objects.create(
            plan=self.plan,
            beneficiary=self.user,
            source_type=Commission.SourceType.TRANSPORT,
            source_id="trip-lifecycle-001",
            calculation_basis=Decimal("100000.00"),
            rate=Decimal("10.0000"),
            calculated_amount=Decimal("10000.00"),
            currency="NGN",
            status=status,
        )

    def test_pending_can_transition_to_calculated(self):
        commission = self.create_commission()

        CommissionLifecycle.transition(
            commission=commission,
            target_status=Commission.Status.CALCULATED,
        )

        commission.refresh_from_db()

        self.assertEqual(
            commission.status,
            Commission.Status.CALCULATED,
        )
        self.assertIsNotNone(commission.calculated_at)

    def test_pending_can_transition_to_cancelled(self):
        commission = self.create_commission()

        CommissionLifecycle.transition(
            commission=commission,
            target_status=Commission.Status.CANCELLED,
        )

        commission.refresh_from_db()

        self.assertEqual(
            commission.status,
            Commission.Status.CANCELLED,
        )

    def test_calculated_can_transition_to_approved(self):
        commission = self.create_commission(
            status=Commission.Status.CALCULATED,
        )

        CommissionLifecycle.transition(
            commission=commission,
            target_status=Commission.Status.APPROVED,
        )

        commission.refresh_from_db()

        self.assertEqual(
            commission.status,
            Commission.Status.APPROVED,
        )
        self.assertIsNotNone(commission.approved_at)

    def test_calculated_can_transition_to_cancelled(self):
        commission = self.create_commission(
            status=Commission.Status.CALCULATED,
        )

        CommissionLifecycle.transition(
            commission=commission,
            target_status=Commission.Status.CANCELLED,
        )

        commission.refresh_from_db()

        self.assertEqual(
            commission.status,
            Commission.Status.CANCELLED,
        )

    def test_calculated_can_transition_to_reversed(self):
        commission = self.create_commission(
            status=Commission.Status.CALCULATED,
        )

        CommissionLifecycle.transition(
            commission=commission,
            target_status=Commission.Status.REVERSED,
        )

        commission.refresh_from_db()

        self.assertEqual(
            commission.status,
            Commission.Status.REVERSED,
        )
        self.assertIsNotNone(commission.reversed_at)

    def test_approved_can_transition_to_payable(self):
        commission = self.create_commission(
            status=Commission.Status.APPROVED,
        )

        CommissionLifecycle.transition(
            commission=commission,
            target_status=Commission.Status.PAYABLE,
        )

        commission.refresh_from_db()

        self.assertEqual(
            commission.status,
            Commission.Status.PAYABLE,
        )
        self.assertIsNotNone(commission.payable_at)

    def test_approved_can_transition_to_cancelled(self):
        commission = self.create_commission(
            status=Commission.Status.APPROVED,
        )

        CommissionLifecycle.transition(
            commission=commission,
            target_status=Commission.Status.CANCELLED,
        )

        commission.refresh_from_db()

        self.assertEqual(
            commission.status,
            Commission.Status.CANCELLED,
        )

    def test_approved_can_transition_to_reversed(self):
        commission = self.create_commission(
            status=Commission.Status.APPROVED,
        )

        CommissionLifecycle.transition(
            commission=commission,
            target_status=Commission.Status.REVERSED,
        )

        commission.refresh_from_db()

        self.assertEqual(
            commission.status,
            Commission.Status.REVERSED,
        )
        self.assertIsNotNone(commission.reversed_at)

    def test_payable_can_transition_to_settled(self):
        commission = self.create_commission(
            status=Commission.Status.PAYABLE,
        )

        CommissionLifecycle.transition(
            commission=commission,
            target_status=Commission.Status.SETTLED,
        )

        commission.refresh_from_db()

        self.assertEqual(
            commission.status,
            Commission.Status.SETTLED,
        )
        self.assertIsNotNone(commission.settled_at)

    def test_payable_can_transition_to_cancelled(self):
        commission = self.create_commission(
            status=Commission.Status.PAYABLE,
        )

        CommissionLifecycle.transition(
            commission=commission,
            target_status=Commission.Status.CANCELLED,
        )

        commission.refresh_from_db()

        self.assertEqual(
            commission.status,
            Commission.Status.CANCELLED,
        )

    def test_payable_can_transition_to_reversed(self):
        commission = self.create_commission(
            status=Commission.Status.PAYABLE,
        )

        CommissionLifecycle.transition(
            commission=commission,
            target_status=Commission.Status.REVERSED,
        )

        commission.refresh_from_db()

        self.assertEqual(
            commission.status,
            Commission.Status.REVERSED,
        )
        self.assertIsNotNone(commission.reversed_at)

    def test_settled_can_transition_to_reversed(self):
        commission = self.create_commission(
            status=Commission.Status.SETTLED,
        )

        CommissionLifecycle.transition(
            commission=commission,
            target_status=Commission.Status.REVERSED,
        )

        commission.refresh_from_db()

        self.assertEqual(
            commission.status,
            Commission.Status.REVERSED,
        )
        self.assertIsNotNone(commission.reversed_at)

    def test_cancelled_is_terminal(self):
        commission = self.create_commission(
            status=Commission.Status.CANCELLED,
        )

        with self.assertRaises(ValidationError):
            CommissionLifecycle.transition(
                commission=commission,
                target_status=Commission.Status.CALCULATED,
            )

    def test_reversed_is_terminal(self):
        commission = self.create_commission(
            status=Commission.Status.REVERSED,
        )

        with self.assertRaises(ValidationError):
            CommissionLifecycle.transition(
                commission=commission,
                target_status=Commission.Status.APPROVED,
            )

    def test_same_state_transition_is_rejected(self):
        commission = self.create_commission(
            status=Commission.Status.CALCULATED,
        )

        with self.assertRaises(ValidationError):
            CommissionLifecycle.transition(
                commission=commission,
                target_status=Commission.Status.CALCULATED,
            )

    def test_invalid_transition_is_rejected(self):
        commission = self.create_commission(
            status=Commission.Status.PENDING,
        )

        with self.assertRaises(ValidationError):
            CommissionLifecycle.transition(
                commission=commission,
                target_status=Commission.Status.APPROVED,
            )

    def test_pending_cannot_be_settled_directly(self):
        commission = self.create_commission(
            status=Commission.Status.PENDING,
        )

        with self.assertRaises(ValidationError):
            CommissionLifecycle.transition(
                commission=commission,
                target_status=Commission.Status.SETTLED,
            )

    def test_calculated_cannot_be_settled_directly(self):
        commission = self.create_commission(
            status=Commission.Status.CALCULATED,
        )

        with self.assertRaises(ValidationError):
            CommissionLifecycle.transition(
                commission=commission,
                target_status=Commission.Status.SETTLED,
            )

    def test_can_transition_reports_valid_transition(self):
        self.assertTrue(
            CommissionLifecycle.can_transition(
                current_status=Commission.Status.PENDING,
                target_status=Commission.Status.CALCULATED,
            )
        )

    def test_can_transition_reports_invalid_transition(self):
        self.assertFalse(
            CommissionLifecycle.can_transition(
                current_status=Commission.Status.PENDING,
                target_status=Commission.Status.SETTLED,
            )
        )

    def test_lifecycle_does_not_change_calculation_amount(self):
        commission = self.create_commission(
            status=Commission.Status.CALCULATED,
        )

        original_amount = commission.calculated_amount

        CommissionLifecycle.transition(
            commission=commission,
            target_status=Commission.Status.APPROVED,
        )

        commission.refresh_from_db()

        self.assertEqual(
            commission.calculated_amount,
            original_amount,
        )