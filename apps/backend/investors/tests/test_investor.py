from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.db.models.deletion import ProtectedError
from investors.models import Investor


User = get_user_model()


class InvestorModelTests(TestCase):

    def create_user(self, email="investor@example.com"):
        return User.objects.create_user(
            email=email,
            password="test-password",
        )

    def create_investor(self, **kwargs):
        user = kwargs.pop("user", None)

        if user is None:
            user = self.create_user()

        defaults = {
            "reference": "INV-000001",
            "status": Investor.Status.PENDING,
        }

        defaults.update(kwargs)

        investor = Investor(
            user=user,
            **defaults,
        )

        investor.full_clean()
        investor.save()

        return investor

    def test_investor_can_be_created(self):
        investor = self.create_investor()

        self.assertIsNotNone(investor.id)
        self.assertEqual(
            investor.reference,
            "INV-000001",
        )
        self.assertEqual(
            investor.status,
            Investor.Status.PENDING,
        )

    def test_investor_is_linked_to_user(self):
        user = self.create_user()

        investor = self.create_investor(
            user=user,
            reference="INV-000002",
        )

        self.assertEqual(
            investor.user,
            user,
        )

        self.assertEqual(
            user.investor_profile,
            investor,
        )

    def test_user_can_have_only_one_investor_profile(self):
        user = self.create_user()

        self.create_investor(
            user=user,
            reference="INV-000003",
        )

        with self.assertRaises(IntegrityError):
            Investor.objects.create(
                user=user,
                reference="INV-000004",
            )

    def test_reference_is_required(self):
        user = self.create_user()

        investor = Investor(
            user=user,
            reference="",
        )

        with self.assertRaises(ValidationError):
            investor.full_clean()

    def test_reference_must_be_unique(self):
        self.create_investor(
            reference="INV-UNIQUE-001",
        )

        user = self.create_user(
            email="second@example.com",
        )

        investor = Investor(
            user=user,
            reference="INV-UNIQUE-001",
        )

        with self.assertRaises(ValidationError):
            investor.full_clean()

    def test_default_status_is_pending(self):
        user = self.create_user()

        investor = Investor(
            user=user,
            reference="INV-000005",
        )

        self.assertEqual(
            investor.status,
            Investor.Status.PENDING,
        )

    def test_default_metadata_is_empty_dictionary(self):
        investor = self.create_investor(
            reference="INV-000006",
        )

        self.assertEqual(
            investor.metadata,
            {},
        )

    def test_metadata_must_be_dictionary(self):
        user = self.create_user()

        investor = Investor(
            user=user,
            reference="INV-000007",
            metadata=["invalid"],
        )

        with self.assertRaises(ValidationError):
            investor.full_clean()

    def test_metadata_can_store_structured_data(self):
        investor = self.create_investor(
            reference="INV-000008",
            metadata={
                "source": "onboarding",
                "risk_profile": "moderate",
            },
        )

        self.assertEqual(
            investor.metadata["source"],
            "onboarding",
        )

        self.assertEqual(
            investor.metadata["risk_profile"],
            "moderate",
        )

    def test_status_helpers(self):
        pending = self.create_investor(
            reference="INV-000009",
            status=Investor.Status.PENDING,
        )

        self.assertTrue(pending.is_pending)
        self.assertFalse(pending.is_active)
        self.assertFalse(pending.is_suspended)
        self.assertFalse(pending.is_closed)

        active = self.create_investor(
            user=self.create_user("active@example.com"),
            reference="INV-000010",
            status=Investor.Status.ACTIVE,
        )

        self.assertTrue(active.is_active)
        self.assertFalse(active.is_pending)

        suspended = self.create_investor(
            user=self.create_user("suspended@example.com"),
            reference="INV-000011",
            status=Investor.Status.SUSPENDED,
        )

        self.assertTrue(suspended.is_suspended)

        closed = self.create_investor(
            user=self.create_user("closed@example.com"),
            reference="INV-000012",
            status=Investor.Status.CLOSED,
        )

        self.assertTrue(closed.is_closed)

    def test_string_representation_uses_reference(self):
        investor = self.create_investor(
            reference="INV-STRING-001",
        )

        self.assertEqual(
            str(investor),
            "INV-STRING-001",
        )

    def test_user_is_protected_from_deletion(self):
        investor = self.create_investor(
            reference="INV-000013",
        )

        with self.assertRaises(ProtectedError):
            investor.user.delete()

        investor.refresh_from_db()

        self.assertEqual(
            investor.user_id,
            investor.user.id,
        )