from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from investors.lifecycle.commitment import InvestmentCommitmentLifecycle
from investors.models import (
    InvestmentCommitment,
    InvestmentOpportunity,
    InvestmentPlan,
)


User = get_user_model()


class InvestmentCommitmentLifecycleTests(TestCase):

    def create_user(self, email=None):
        if email is None:
            index = User.objects.count() + 1

            while User.objects.filter(
                email=f"commitment-lifecycle-{index}@example.com"
            ).exists():
                index += 1

            email = f"commitment-lifecycle-{index}@example.com"

        return User.objects.create_user(
            email=email,
            password="test-password",
        )

    def create_opportunity(self, reference=None):
        if reference is None:
            index = InvestmentOpportunity.objects.count() + 1

            while InvestmentOpportunity.objects.filter(
                reference=f"COMMITMENT-LIFECYCLE-OPP-{index:03d}"
            ).exists():
                index += 1

            reference = f"COMMITMENT-LIFECYCLE-OPP-{index:03d}"

        opportunity = InvestmentOpportunity(
            reference=reference,
            name="Commitment Lifecycle Opportunity",
            status=InvestmentOpportunity.Status.OPEN,
            currency="NGN",
            minimum_amount=Decimal("100000.00"),
            maximum_amount=Decimal("10000000.00"),
            metadata={},
        )

        opportunity.full_clean()
        opportunity.save()

        return opportunity

    def create_plan(self, opportunity=None, reference=None):
        if opportunity is None:
            opportunity = self.create_opportunity()

        if reference is None:
            index = InvestmentPlan.objects.count() + 1

            while InvestmentPlan.objects.filter(
                reference=f"COMMITMENT-LIFECYCLE-PLAN-{index:03d}"
            ).exists():
                index += 1

            reference = f"COMMITMENT-LIFECYCLE-PLAN-{index:03d}"

        plan = InvestmentPlan(
            opportunity=opportunity,
            reference=reference,
            name="Commitment Lifecycle Plan",
            status=InvestmentPlan.Status.ACTIVE,
            minimum_amount=Decimal("100000.00"),
            maximum_amount=Decimal("5000000.00"),
            duration_days=365,
            expected_return_rate=Decimal("15.0000"),
            metadata={},
        )

        plan.full_clean()
        plan.save()

        return plan

    def create_commitment(
        self,
        status=InvestmentCommitment.Status.PENDING,
        reference=None,
        investor=None,
        opportunity=None,
        plan=None,
        expires_at=None,
    ):
        if investor is None:
            investor = self.create_user()

        if opportunity is None:
            opportunity = self.create_opportunity()

        if plan is None:
            plan = self.create_plan(
                opportunity=opportunity,
            )

        if reference is None:
            index = InvestmentCommitment.objects.count() + 1

            while InvestmentCommitment.objects.filter(
                reference=f"COMMITMENT-LIFECYCLE-{index:03d}"
            ).exists():
                index += 1

            reference = f"COMMITMENT-LIFECYCLE-{index:03d}"

        if expires_at is None:
            expires_at = timezone.now() + timedelta(days=7)

        commitment = InvestmentCommitment(
            investor=investor,
            opportunity=opportunity,
            plan=plan,
            reference=reference,
            amount=Decimal("500000.00"),
            currency="NGN",
            status=status,
            expires_at=expires_at,
        )

        commitment.full_clean()
        commitment.save()

        return commitment

    # ------------------------------------------------------------------
    # confirm
    # ------------------------------------------------------------------

    def test_confirm_pending_commitment(self):
        commitment = self.create_commitment(
            status=InvestmentCommitment.Status.PENDING,
        )

        before = timezone.now()

        result = InvestmentCommitmentLifecycle.confirm(
            commitment,
        )

        after = timezone.now()

        commitment.refresh_from_db()

        self.assertEqual(
            result.pk,
            commitment.pk,
        )
        self.assertEqual(
            commitment.status,
            InvestmentCommitment.Status.CONFIRMED,
        )
        self.assertIsNotNone(commitment.confirmed_at)
        self.assertGreaterEqual(
            commitment.confirmed_at,
            before,
        )
        self.assertLessEqual(
            commitment.confirmed_at,
            after,
        )

    def test_confirm_rejects_confirmed_commitment(self):
        commitment = self.create_commitment(
            status=InvestmentCommitment.Status.CONFIRMED,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentCommitmentLifecycle.confirm(
                commitment,
            )

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    def test_confirm_rejects_funded_commitment(self):
        commitment = self.create_commitment(
            status=InvestmentCommitment.Status.FUNDED,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentCommitmentLifecycle.confirm(
                commitment,
            )

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    def test_confirm_rejects_cancelled_commitment(self):
        commitment = self.create_commitment(
            status=InvestmentCommitment.Status.CANCELLED,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentCommitmentLifecycle.confirm(
                commitment,
            )

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    def test_confirm_rejects_expired_commitment(self):
        commitment = self.create_commitment(
            status=InvestmentCommitment.Status.EXPIRED,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentCommitmentLifecycle.confirm(
                commitment,
            )

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    # ------------------------------------------------------------------
    # fund
    # ------------------------------------------------------------------

    def test_fund_confirmed_commitment(self):
        commitment = self.create_commitment(
            status=InvestmentCommitment.Status.CONFIRMED,
        )

        before = timezone.now()

        result = InvestmentCommitmentLifecycle.fund(
            commitment,
        )

        after = timezone.now()

        commitment.refresh_from_db()

        self.assertEqual(
            result.pk,
            commitment.pk,
        )
        self.assertEqual(
            commitment.status,
            InvestmentCommitment.Status.FUNDED,
        )
        self.assertIsNotNone(commitment.funded_at)
        self.assertGreaterEqual(
            commitment.funded_at,
            before,
        )
        self.assertLessEqual(
            commitment.funded_at,
            after,
        )

    def test_fund_rejects_pending_commitment(self):
        commitment = self.create_commitment(
            status=InvestmentCommitment.Status.PENDING,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentCommitmentLifecycle.fund(
                commitment,
            )

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    def test_fund_rejects_funded_commitment(self):
        commitment = self.create_commitment(
            status=InvestmentCommitment.Status.FUNDED,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentCommitmentLifecycle.fund(
                commitment,
            )

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    def test_fund_rejects_cancelled_commitment(self):
        commitment = self.create_commitment(
            status=InvestmentCommitment.Status.CANCELLED,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentCommitmentLifecycle.fund(
                commitment,
            )

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    def test_fund_rejects_expired_commitment(self):
        commitment = self.create_commitment(
            status=InvestmentCommitment.Status.EXPIRED,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentCommitmentLifecycle.fund(
                commitment,
            )

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    # ------------------------------------------------------------------
    # cancel
    # ------------------------------------------------------------------

    def test_cancel_pending_commitment(self):
        commitment = self.create_commitment(
            status=InvestmentCommitment.Status.PENDING,
        )

        before = timezone.now()

        result = InvestmentCommitmentLifecycle.cancel(
            commitment,
        )

        after = timezone.now()

        commitment.refresh_from_db()

        self.assertEqual(
            result.pk,
            commitment.pk,
        )
        self.assertEqual(
            commitment.status,
            InvestmentCommitment.Status.CANCELLED,
        )
        self.assertIsNotNone(commitment.cancelled_at)
        self.assertGreaterEqual(
            commitment.cancelled_at,
            before,
        )
        self.assertLessEqual(
            commitment.cancelled_at,
            after,
        )

    def test_cancel_confirmed_commitment(self):
        commitment = self.create_commitment(
            status=InvestmentCommitment.Status.CONFIRMED,
        )

        result = InvestmentCommitmentLifecycle.cancel(
            commitment,
        )

        commitment.refresh_from_db()

        self.assertEqual(
            result.pk,
            commitment.pk,
        )
        self.assertEqual(
            commitment.status,
            InvestmentCommitment.Status.CANCELLED,
        )
        self.assertIsNotNone(commitment.cancelled_at)

    def test_cancel_rejects_funded_commitment(self):
        commitment = self.create_commitment(
            status=InvestmentCommitment.Status.FUNDED,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentCommitmentLifecycle.cancel(
                commitment,
            )

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    def test_cancel_rejects_expired_commitment(self):
        commitment = self.create_commitment(
            status=InvestmentCommitment.Status.EXPIRED,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentCommitmentLifecycle.cancel(
                commitment,
            )

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    def test_cancel_rejects_cancelled_commitment(self):
        commitment = self.create_commitment(
            status=InvestmentCommitment.Status.CANCELLED,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentCommitmentLifecycle.cancel(
                commitment,
            )

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    # ------------------------------------------------------------------
    # expire
    # ------------------------------------------------------------------

    def test_expire_pending_commitment(self):
        commitment = self.create_commitment(
            status=InvestmentCommitment.Status.PENDING,
        )

        result = InvestmentCommitmentLifecycle.expire(
            commitment,
        )

        commitment.refresh_from_db()

        self.assertEqual(
            result.pk,
            commitment.pk,
        )
        self.assertEqual(
            commitment.status,
            InvestmentCommitment.Status.EXPIRED,
        )

    def test_expire_rejects_confirmed_commitment(self):
        commitment = self.create_commitment(
            status=InvestmentCommitment.Status.CONFIRMED,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentCommitmentLifecycle.expire(
                commitment,
            )

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    def test_expire_rejects_funded_commitment(self):
        commitment = self.create_commitment(
            status=InvestmentCommitment.Status.FUNDED,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentCommitmentLifecycle.expire(
                commitment,
            )

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    def test_expire_rejects_cancelled_commitment(self):
        commitment = self.create_commitment(
            status=InvestmentCommitment.Status.CANCELLED,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentCommitmentLifecycle.expire(
                commitment,
            )

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    def test_expire_rejects_expired_commitment(self):
        commitment = self.create_commitment(
            status=InvestmentCommitment.Status.EXPIRED,
        )

        with self.assertRaises(ValidationError) as context:
            InvestmentCommitmentLifecycle.expire(
                commitment,
            )

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    # ------------------------------------------------------------------
    # validation
    # ------------------------------------------------------------------

    def test_confirm_requires_commitment(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentCommitmentLifecycle.confirm(None)

        self.assertIn(
            "commitment",
            context.exception.message_dict,
        )

    def test_fund_requires_commitment(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentCommitmentLifecycle.fund(None)

        self.assertIn(
            "commitment",
            context.exception.message_dict,
        )

    def test_cancel_requires_commitment(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentCommitmentLifecycle.cancel(None)

        self.assertIn(
            "commitment",
            context.exception.message_dict,
        )

    def test_expire_requires_commitment(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentCommitmentLifecycle.expire(None)

        self.assertIn(
            "commitment",
            context.exception.message_dict,
        )

    def test_confirm_rejects_invalid_commitment(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentCommitmentLifecycle.confirm("invalid")

        self.assertIn(
            "commitment",
            context.exception.message_dict,
        )

    def test_fund_rejects_invalid_commitment(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentCommitmentLifecycle.fund("invalid")

        self.assertIn(
            "commitment",
            context.exception.message_dict,
        )

    def test_cancel_rejects_invalid_commitment(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentCommitmentLifecycle.cancel("invalid")

        self.assertIn(
            "commitment",
            context.exception.message_dict,
        )

    def test_expire_rejects_invalid_commitment(self):
        with self.assertRaises(ValidationError) as context:
            InvestmentCommitmentLifecycle.expire("invalid")

        self.assertIn(
            "commitment",
            context.exception.message_dict,
        )