from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from investors.models import InvestmentOpportunity


class InvestmentOpportunityModelTests(TestCase):

    def create_opportunity(self, **kwargs):
        defaults = {
            "reference": "OPP-000001",
            "name": "Univa Property Fund",
            "description": "A test investment opportunity.",
            "status": InvestmentOpportunity.Status.DRAFT,
            "currency": "NGN",
            "minimum_amount": Decimal("100000.00"),
            "maximum_amount": Decimal("10000000.00"),
        }

        defaults.update(kwargs)

        opportunity = InvestmentOpportunity(**defaults)
        opportunity.full_clean()
        opportunity.save()

        return opportunity

    def test_opportunity_can_be_created(self):
        opportunity = self.create_opportunity()

        self.assertIsNotNone(opportunity.id)
        self.assertEqual(
            opportunity.reference,
            "OPP-000001",
        )

        self.assertEqual(
            opportunity.name,
            "Univa Property Fund",
        )

    def test_default_status_is_draft(self):
        opportunity = self.create_opportunity()

        self.assertEqual(
            opportunity.status,
            InvestmentOpportunity.Status.DRAFT,
        )

    def test_reference_must_be_unique(self):
        self.create_opportunity(
            reference="OPP-UNIQUE-001",
        )

        duplicate = InvestmentOpportunity(
            reference="OPP-UNIQUE-001",
            name="Another Opportunity",
            currency="NGN",
            minimum_amount=Decimal("100000.00"),
        )

        with self.assertRaises(ValidationError):
            duplicate.full_clean()

    def test_name_is_required(self):
        opportunity = InvestmentOpportunity(
            reference="OPP-000002",
            name="",
            currency="NGN",
            minimum_amount=Decimal("100000.00"),
        )

        with self.assertRaises(ValidationError):
            opportunity.full_clean()

    def test_currency_is_normalized_to_uppercase(self):
        opportunity = self.create_opportunity(
            reference="OPP-000003",
            currency="ngn",
        )

        self.assertEqual(
            opportunity.currency,
            "NGN",
        )

    def test_currency_must_be_three_characters(self):
        opportunity = InvestmentOpportunity(
            reference="OPP-000004",
            name="Invalid Currency Opportunity",
            currency="NG",
            minimum_amount=Decimal("100000.00"),
        )

        with self.assertRaises(ValidationError):
            opportunity.full_clean()

    def test_minimum_amount_must_be_positive(self):
        opportunity = InvestmentOpportunity(
            reference="OPP-000005",
            name="Invalid Minimum",
            currency="NGN",
            minimum_amount=Decimal("0.00"),
        )

        with self.assertRaises(ValidationError):
            opportunity.full_clean()

    def test_maximum_amount_is_optional(self):
        opportunity = self.create_opportunity(
            reference="OPP-000006",
            maximum_amount=None,
        )

        self.assertIsNone(
            opportunity.maximum_amount,
        )

    def test_maximum_amount_cannot_be_less_than_minimum(self):
        opportunity = InvestmentOpportunity(
            reference="OPP-000007",
            name="Invalid Range",
            currency="NGN",
            minimum_amount=Decimal("1000000.00"),
            maximum_amount=Decimal("500000.00"),
        )

        with self.assertRaises(ValidationError):
            opportunity.full_clean()

    def test_metadata_defaults_to_empty_dictionary(self):
        opportunity = self.create_opportunity(
            reference="OPP-000008",
        )

        self.assertEqual(
            opportunity.metadata,
            {},
        )

    def test_metadata_can_store_structured_data(self):
        opportunity = self.create_opportunity(
            reference="OPP-000009",
            metadata={
                "category": "real_estate",
                "risk_level": "moderate",
            },
        )

        self.assertEqual(
            opportunity.metadata["category"],
            "real_estate",
        )

        self.assertEqual(
            opportunity.metadata["risk_level"],
            "moderate",
        )

    def test_metadata_must_be_dictionary(self):
        opportunity = InvestmentOpportunity(
            reference="OPP-000010",
            name="Invalid Metadata",
            currency="NGN",
            minimum_amount=Decimal("100000.00"),
            metadata=["invalid"],
        )

        with self.assertRaises(ValidationError):
            opportunity.full_clean()

    def test_status_helpers(self):
        draft = self.create_opportunity(
            reference="OPP-000011",
            status=InvestmentOpportunity.Status.DRAFT,
        )

        self.assertTrue(draft.is_draft)
        self.assertFalse(draft.is_open)

        open_opportunity = self.create_opportunity(
            reference="OPP-000012",
            status=InvestmentOpportunity.Status.OPEN,
        )

        self.assertTrue(open_opportunity.is_open)
        self.assertFalse(open_opportunity.is_draft)

        paused = self.create_opportunity(
            reference="OPP-000013",
            status=InvestmentOpportunity.Status.PAUSED,
        )

        self.assertTrue(paused.is_paused)

        closed = self.create_opportunity(
            reference="OPP-000014",
            status=InvestmentOpportunity.Status.CLOSED,
        )

        self.assertTrue(closed.is_closed)

        cancelled = self.create_opportunity(
            reference="OPP-000015",
            status=InvestmentOpportunity.Status.CANCELLED,
        )

        self.assertTrue(cancelled.is_cancelled)

    def test_string_representation_uses_reference(self):
        opportunity = self.create_opportunity(
            reference="OPP-STRING-001",
        )

        self.assertEqual(
            str(opportunity),
            "OPP-STRING-001",
        )