from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from investors.models import Investor
from investors.lifecycle.investor import InvestorLifecycle


User = get_user_model()


class InvestorLifecycleTests(TestCase):

    def create_user(self, email=None):
        if email is None:
            index = User.objects.count() + 1

            while User.objects.filter(
                email=f"investor-lifecycle-{index}@example.com"
            ).exists():
                index += 1

            email = f"investor-lifecycle-{index}@example.com"

        return User.objects.create_user(
            email=email,
            password="test-password",
        )

    def create_investor(
        self,
        status=Investor.Status.PENDING,
        reference=None,
    ):
        user = self.create_user()

        if reference is None:
            index = Investor.objects.count() + 1

            while Investor.objects.filter(
                reference=f"INVESTOR-LIFECYCLE-{index:03d}"
            ).exists():
                index += 1

            reference = f"INVESTOR-LIFECYCLE-{index:03d}"

        investor = Investor(
            user=user,
            reference=reference,
            status=status,
            display_name="Lifecycle Investor",
            metadata={},
        )

        investor.full_clean()
        investor.save()

        return investor

    # ------------------------------------------------------------------
    # activate
    # ------------------------------------------------------------------

    def test_activate_pending_investor(self):
        investor = self.create_investor(
            status=Investor.Status.PENDING,
        )

        result = InvestorLifecycle.activate(investor)

        investor.refresh_from_db()

        self.assertEqual(
            result.pk,
            investor.pk,
        )
        self.assertEqual(
            investor.status,
            Investor.Status.ACTIVE,
        )

    def test_activate_suspended_investor(self):
        investor = self.create_investor(
            status=Investor.Status.SUSPENDED,
        )

        result = InvestorLifecycle.activate(investor)

        investor.refresh_from_db()

        self.assertEqual(
            result.pk,
            investor.pk,
        )
        self.assertEqual(
            investor.status,
            Investor.Status.ACTIVE,
        )

    def test_activate_rejects_active_investor(self):
        investor = self.create_investor(
            status=Investor.Status.ACTIVE,
        )

        with self.assertRaises(ValidationError) as context:
            InvestorLifecycle.activate(investor)

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    def test_activate_rejects_closed_investor(self):
        investor = self.create_investor(
            status=Investor.Status.CLOSED,
        )

        with self.assertRaises(ValidationError) as context:
            InvestorLifecycle.activate(investor)

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    # ------------------------------------------------------------------
    # suspend
    # ------------------------------------------------------------------

    def test_suspend_active_investor(self):
        investor = self.create_investor(
            status=Investor.Status.ACTIVE,
        )

        result = InvestorLifecycle.suspend(investor)

        investor.refresh_from_db()

        self.assertEqual(
            result.pk,
            investor.pk,
        )
        self.assertEqual(
            investor.status,
            Investor.Status.SUSPENDED,
        )

    def test_suspend_rejects_pending_investor(self):
        investor = self.create_investor(
            status=Investor.Status.PENDING,
        )

        with self.assertRaises(ValidationError) as context:
            InvestorLifecycle.suspend(investor)

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    def test_suspend_rejects_suspended_investor(self):
        investor = self.create_investor(
            status=Investor.Status.SUSPENDED,
        )

        with self.assertRaises(ValidationError) as context:
            InvestorLifecycle.suspend(investor)

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    def test_suspend_rejects_closed_investor(self):
        investor = self.create_investor(
            status=Investor.Status.CLOSED,
        )

        with self.assertRaises(ValidationError) as context:
            InvestorLifecycle.suspend(investor)

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    # ------------------------------------------------------------------
    # close
    # ------------------------------------------------------------------

    def test_close_active_investor(self):
        investor = self.create_investor(
            status=Investor.Status.ACTIVE,
        )

        result = InvestorLifecycle.close(investor)

        investor.refresh_from_db()

        self.assertEqual(
            result.pk,
            investor.pk,
        )
        self.assertEqual(
            investor.status,
            Investor.Status.CLOSED,
        )

    def test_close_suspended_investor(self):
        investor = self.create_investor(
            status=Investor.Status.SUSPENDED,
        )

        result = InvestorLifecycle.close(investor)

        investor.refresh_from_db()

        self.assertEqual(
            result.pk,
            investor.pk,
        )
        self.assertEqual(
            investor.status,
            Investor.Status.CLOSED,
        )

    def test_close_rejects_pending_investor(self):
        investor = self.create_investor(
            status=Investor.Status.PENDING,
        )

        with self.assertRaises(ValidationError) as context:
            InvestorLifecycle.close(investor)

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    def test_close_rejects_closed_investor(self):
        investor = self.create_investor(
            status=Investor.Status.CLOSED,
        )

        with self.assertRaises(ValidationError) as context:
            InvestorLifecycle.close(investor)

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

    # ------------------------------------------------------------------
    # validation
    # ------------------------------------------------------------------

    def test_activate_requires_investor(self):
        with self.assertRaises(ValidationError) as context:
            InvestorLifecycle.activate(None)

        self.assertIn(
            "investor",
            context.exception.message_dict,
        )

    def test_suspend_requires_investor(self):
        with self.assertRaises(ValidationError) as context:
            InvestorLifecycle.suspend(None)

        self.assertIn(
            "investor",
            context.exception.message_dict,
        )

    def test_close_requires_investor(self):
        with self.assertRaises(ValidationError) as context:
            InvestorLifecycle.close(None)

        self.assertIn(
            "investor",
            context.exception.message_dict,
        )

    def test_activate_rejects_invalid_investor(self):
        with self.assertRaises(ValidationError) as context:
            InvestorLifecycle.activate("invalid")

        self.assertIn(
            "investor",
            context.exception.message_dict,
        )

    def test_suspend_rejects_invalid_investor(self):
        with self.assertRaises(ValidationError) as context:
            InvestorLifecycle.suspend("invalid")

        self.assertIn(
            "investor",
            context.exception.message_dict,
        )

    def test_close_rejects_invalid_investor(self):
        with self.assertRaises(ValidationError) as context:
            InvestorLifecycle.close("invalid")

        self.assertIn(
            "investor",
            context.exception.message_dict,
        )