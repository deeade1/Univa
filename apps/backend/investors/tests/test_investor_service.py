from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from investors.models import Investor
from investors.services.investor import InvestorService


User = get_user_model()


class InvestorServiceTests(TestCase):

    def create_user(self, email=None):
        if email is None:
            index = User.objects.count() + 1

            while User.objects.filter(
                email=f"investor-service-{index}@example.com"
            ).exists():
                index += 1

            email = f"investor-service-{index}@example.com"

        return User.objects.create_user(
            email=email,
            password="test-password",
        )

    def create_investor(
        self,
        user=None,
        reference=None,
        display_name="Test Investor",
        metadata=None,
        status=Investor.Status.PENDING,
    ):
        if user is None:
            user = self.create_user()

        if reference is None:
            index = Investor.objects.count() + 1

            while Investor.objects.filter(
                reference=f"INVESTOR-SERVICE-{index:03d}"
            ).exists():
                index += 1

            reference = f"INVESTOR-SERVICE-{index:03d}"

        investor = Investor(
            user=user,
            reference=reference,
            display_name=display_name,
            metadata={} if metadata is None else metadata,
            status=status,
        )
        investor.full_clean()
        investor.save()

        return investor

    # ------------------------------------------------------------------
    # create
    # ------------------------------------------------------------------

    def test_create_investor(self):
        user = self.create_user()

        investor = InvestorService.create(
            user=user,
            reference="INVESTOR-SERVICE-001",
            display_name="Dayo Investor",
        )

        self.assertIsNotNone(investor.pk)
        self.assertEqual(investor.user, user)
        self.assertEqual(investor.reference, "INVESTOR-SERVICE-001")
        self.assertEqual(investor.display_name, "Dayo Investor")
        self.assertEqual(investor.status, Investor.Status.PENDING)
        self.assertEqual(investor.metadata, {})

    def test_create_investor_with_metadata(self):
        user = self.create_user()

        metadata = {
            "source": "onboarding",
            "tier": "premium",
        }

        investor = InvestorService.create(
            user=user,
            reference="INVESTOR-SERVICE-002",
            metadata=metadata,
        )

        self.assertEqual(investor.metadata, metadata)

    def test_create_investor_with_status(self):
        user = self.create_user()

        investor = InvestorService.create(
            user=user,
            reference="INVESTOR-SERVICE-003",
            status=Investor.Status.ACTIVE,
        )

        self.assertEqual(investor.status, Investor.Status.ACTIVE)

    def test_create_requires_user(self):
        with self.assertRaises(ValidationError) as context:
            InvestorService.create(
                user=None,
                reference="INVESTOR-SERVICE-004",
            )

        self.assertIn("user", context.exception.message_dict)

    def test_create_requires_reference(self):
        user = self.create_user()

        with self.assertRaises(ValidationError) as context:
            InvestorService.create(
                user=user,
                reference="",
            )

        self.assertIn("reference", context.exception.message_dict)

    def test_create_rejects_duplicate_user(self):
        user = self.create_user()

        self.create_investor(
            user=user,
            reference="INVESTOR-SERVICE-005",
        )

        with self.assertRaises(ValidationError) as context:
            InvestorService.create(
                user=user,
                reference="INVESTOR-SERVICE-006",
            )

        self.assertIn("user", context.exception.message_dict)

    def test_create_rejects_invalid_metadata(self):
        user = self.create_user()

        with self.assertRaises(ValidationError) as context:
            InvestorService.create(
                user=user,
                reference="INVESTOR-SERVICE-007",
                metadata=["invalid"],
            )

        self.assertIn("metadata", context.exception.message_dict)

    # ------------------------------------------------------------------
    # update
    # ------------------------------------------------------------------

    def test_update_display_name(self):
        investor = self.create_investor()

        updated = InvestorService.update(
            investor,
            display_name="Updated Investor",
        )

        updated.refresh_from_db()

        self.assertEqual(updated.display_name, "Updated Investor")

    def test_update_reference(self):
        investor = self.create_investor(
            reference="INVESTOR-SERVICE-008",
        )

        updated = InvestorService.update(
            investor,
            reference="INVESTOR-SERVICE-009",
        )

        updated.refresh_from_db()

        self.assertEqual(updated.reference, "INVESTOR-SERVICE-009")

    def test_update_metadata(self):
        investor = self.create_investor(
            metadata={"tier": "standard"},
        )

        updated = InvestorService.update(
            investor,
            metadata={
                "tier": "premium",
                "source": "upgrade",
            },
        )

        updated.refresh_from_db()

        self.assertEqual(
            updated.metadata,
            {
                "tier": "premium",
                "source": "upgrade",
            },
        )

    def test_update_preserves_unspecified_fields(self):
        investor = self.create_investor(
            reference="INVESTOR-SERVICE-010",
            display_name="Original Name",
            metadata={"tier": "standard"},
        )

        InvestorService.update(
            investor,
            display_name="New Name",
        )

        investor.refresh_from_db()

        self.assertEqual(
            investor.reference,
            "INVESTOR-SERVICE-010",
        )
        self.assertEqual(
            investor.display_name,
            "New Name",
        )
        self.assertEqual(
            investor.metadata,
            {"tier": "standard"},
        )

    def test_update_requires_investor(self):
        with self.assertRaises(ValidationError) as context:
            InvestorService.update(
                None,
                display_name="Invalid",
            )

        self.assertIn("investor", context.exception.message_dict)

    def test_update_rejects_invalid_metadata(self):
        investor = self.create_investor()

        with self.assertRaises(ValidationError) as context:
            InvestorService.update(
                investor,
                metadata=["invalid"],
            )

        self.assertIn("metadata", context.exception.message_dict)

    # ------------------------------------------------------------------
    # activate
    # ------------------------------------------------------------------

    def test_activate(self):
        investor = self.create_investor(
            status=Investor.Status.PENDING,
        )

        result = InvestorService.activate(investor)

        investor.refresh_from_db()

        self.assertEqual(result.pk, investor.pk)
        self.assertEqual(
            investor.status,
            Investor.Status.ACTIVE,
        )

    def test_suspend(self):
        investor = self.create_investor(
            status=Investor.Status.ACTIVE,
        )

        result = InvestorService.suspend(investor)

        investor.refresh_from_db()

        self.assertEqual(result.pk, investor.pk)
        self.assertEqual(
            investor.status,
            Investor.Status.SUSPENDED,
        )

    def test_close(self):
        investor = self.create_investor(
            status=Investor.Status.ACTIVE,
        )

        result = InvestorService.close(investor)

        investor.refresh_from_db()

        self.assertEqual(result.pk, investor.pk)
        self.assertEqual(
            investor.status,
            Investor.Status.CLOSED,
        )

    def test_activate_requires_investor(self):
        with self.assertRaises(ValidationError) as context:
            InvestorService.activate(None)

        self.assertIn("investor", context.exception.message_dict)

    def test_suspend_requires_investor(self):
        with self.assertRaises(ValidationError) as context:
            InvestorService.suspend(None)

        self.assertIn("investor", context.exception.message_dict)

    def test_close_requires_investor(self):
        with self.assertRaises(ValidationError) as context:
            InvestorService.close(None)

        self.assertIn("investor", context.exception.message_dict)