from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from investors.models import InvestmentOpportunity
from investors.services.opportunity import OpportunityService


class OpportunityServiceTests(TestCase):

    def create_opportunity(
        self,
        reference=None,
        name="Service Test Opportunity",
        description="Test investment opportunity",
        currency="NGN",
        minimum_amount=Decimal("100000.00"),
        maximum_amount=Decimal("10000000.00"),
        metadata=None,
        status=InvestmentOpportunity.Status.DRAFT,
    ):
        if reference is None:
            index = InvestmentOpportunity.objects.count() + 1

            while InvestmentOpportunity.objects.filter(
                reference=f"OPPORTUNITY-SERVICE-{index:03d}"
            ).exists():
                index += 1

            reference = f"OPPORTUNITY-SERVICE-{index:03d}"

        opportunity = InvestmentOpportunity(
            reference=reference,
            name=name,
            description=description,
            currency=currency,
            minimum_amount=minimum_amount,
            maximum_amount=maximum_amount,
            metadata={} if metadata is None else metadata,
            status=status,
        )

        opportunity.full_clean()
        opportunity.save()

        return opportunity

    # ------------------------------------------------------------------
    # create
    # ------------------------------------------------------------------

    def test_create_opportunity(self):
        opportunity = OpportunityService.create(
            reference="OPPORTUNITY-SERVICE-001",
            name="New Investment Opportunity",
        )

        self.assertIsNotNone(opportunity.pk)
        self.assertEqual(
            opportunity.reference,
            "OPPORTUNITY-SERVICE-001",
        )
        self.assertEqual(
            opportunity.name,
            "New Investment Opportunity",
        )
        self.assertEqual(
            opportunity.status,
            InvestmentOpportunity.Status.DRAFT,
        )
        self.assertEqual(
            opportunity.currency,
            "NGN",
        )

    def test_create_with_all_fields(self):
        metadata = {
            "sector": "real-estate",
            "risk": "medium",
        }

        opportunity = OpportunityService.create(
            reference="OPPORTUNITY-SERVICE-002",
            name="Real Estate Opportunity",
            description="Residential development opportunity",
            currency="USD",
            minimum_amount=Decimal("5000.00"),
            maximum_amount=Decimal("500000.00"),
            metadata=metadata,
            status=InvestmentOpportunity.Status.OPEN,
        )

        self.assertEqual(
            opportunity.description,
            "Residential development opportunity",
        )
        self.assertEqual(opportunity.currency, "USD")
        self.assertEqual(
            opportunity.minimum_amount,
            Decimal("5000.00"),
        )
        self.assertEqual(
            opportunity.maximum_amount,
            Decimal("500000.00"),
        )
        self.assertEqual(opportunity.metadata, metadata)
        self.assertEqual(
            opportunity.status,
            InvestmentOpportunity.Status.OPEN,
        )

    def test_create_defaults_metadata(self):
        opportunity = OpportunityService.create(
            reference="OPPORTUNITY-SERVICE-003",
            name="Metadata Test Opportunity",
        )

        self.assertEqual(opportunity.metadata, {})

    def test_create_requires_reference(self):
        with self.assertRaises(ValidationError) as context:
            OpportunityService.create(
                reference="",
                name="Invalid Opportunity",
            )

        self.assertIn(
            "reference",
            context.exception.message_dict,
        )

    def test_create_rejects_invalid_metadata(self):
        with self.assertRaises(ValidationError) as context:
            OpportunityService.create(
                reference="OPPORTUNITY-SERVICE-004",
                name="Invalid Metadata Opportunity",
                metadata=["invalid"],
            )

        self.assertIn(
            "metadata",
            context.exception.message_dict,
        )

    def test_create_rejects_invalid_minimum_amount(self):
        with self.assertRaises(ValidationError) as context:
            OpportunityService.create(
                reference="OPPORTUNITY-SERVICE-005",
                name="Invalid Amount Opportunity",
                minimum_amount=Decimal("0.00"),
            )

        self.assertIn(
            "minimum_amount",
            context.exception.message_dict,
        )

    # ------------------------------------------------------------------
    # update
    # ------------------------------------------------------------------

    def test_update_name(self):
        opportunity = self.create_opportunity()

        result = OpportunityService.update(
            opportunity,
            name="Updated Opportunity",
        )

        opportunity.refresh_from_db()

        self.assertEqual(result.pk, opportunity.pk)
        self.assertEqual(
            opportunity.name,
            "Updated Opportunity",
        )

    def test_update_description(self):
        opportunity = self.create_opportunity()

        OpportunityService.update(
            opportunity,
            description="Updated description",
        )

        opportunity.refresh_from_db()

        self.assertEqual(
            opportunity.description,
            "Updated description",
        )

    def test_update_reference(self):
        opportunity = self.create_opportunity(
            reference="OPPORTUNITY-SERVICE-006",
        )

        OpportunityService.update(
            opportunity,
            reference="OPPORTUNITY-SERVICE-007",
        )

        opportunity.refresh_from_db()

        self.assertEqual(
            opportunity.reference,
            "OPPORTUNITY-SERVICE-007",
        )

    def test_update_financial_fields(self):
        opportunity = self.create_opportunity()

        OpportunityService.update(
            opportunity,
            currency="USD",
            minimum_amount=Decimal("5000.00"),
            maximum_amount=Decimal("500000.00"),
        )

        opportunity.refresh_from_db()

        self.assertEqual(opportunity.currency, "USD")
        self.assertEqual(
            opportunity.minimum_amount,
            Decimal("5000.00"),
        )
        self.assertEqual(
            opportunity.maximum_amount,
            Decimal("500000.00"),
        )

    def test_update_metadata(self):
        opportunity = self.create_opportunity(
            metadata={"risk": "low"},
        )

        metadata = {
            "risk": "medium",
            "sector": "technology",
        }

        OpportunityService.update(
            opportunity,
            metadata=metadata,
        )

        opportunity.refresh_from_db()

        self.assertEqual(
            opportunity.metadata,
            metadata,
        )

    def test_update_preserves_unspecified_fields(self):
        opportunity = self.create_opportunity(
            reference="OPPORTUNITY-SERVICE-008",
            name="Original Name",
            description="Original description",
            metadata={"risk": "low"},
        )

        OpportunityService.update(
            opportunity,
            name="Updated Name",
        )

        opportunity.refresh_from_db()

        self.assertEqual(
            opportunity.reference,
            "OPPORTUNITY-SERVICE-008",
        )
        self.assertEqual(
            opportunity.name,
            "Updated Name",
        )
        self.assertEqual(
            opportunity.description,
            "Original description",
        )
        self.assertEqual(
            opportunity.metadata,
            {"risk": "low"},
        )

    def test_update_requires_opportunity(self):
        with self.assertRaises(ValidationError) as context:
            OpportunityService.update(
                None,
                name="Invalid",
            )

        self.assertIn(
            "opportunity",
            context.exception.message_dict,
        )

    def test_update_rejects_invalid_metadata(self):
        opportunity = self.create_opportunity()

        with self.assertRaises(ValidationError) as context:
            OpportunityService.update(
                opportunity,
                metadata=["invalid"],
            )

        self.assertIn(
            "metadata",
            context.exception.message_dict,
        )

    def test_update_rejects_invalid_amount_range(self):
        opportunity = self.create_opportunity()

        with self.assertRaises(ValidationError) as context:
            OpportunityService.update(
                opportunity,
                minimum_amount=Decimal("9000000.00"),
                maximum_amount=Decimal("1000000.00"),
            )

        self.assertIn(
            "maximum_amount",
            context.exception.message_dict,
        )

    # ------------------------------------------------------------------
    # status operations
    # ------------------------------------------------------------------

    def test_open(self):
        opportunity = self.create_opportunity(
            status=InvestmentOpportunity.Status.DRAFT,
        )

        result = OpportunityService.open(opportunity)

        opportunity.refresh_from_db()

        self.assertEqual(result.pk, opportunity.pk)
        self.assertEqual(
            opportunity.status,
            InvestmentOpportunity.Status.OPEN,
        )

    def test_pause(self):
        opportunity = self.create_opportunity(
            status=InvestmentOpportunity.Status.OPEN,
        )

        result = OpportunityService.pause(opportunity)

        opportunity.refresh_from_db()

        self.assertEqual(result.pk, opportunity.pk)
        self.assertEqual(
            opportunity.status,
            InvestmentOpportunity.Status.PAUSED,
        )

    def test_close(self):
        opportunity = self.create_opportunity(
            status=InvestmentOpportunity.Status.OPEN,
        )

        result = OpportunityService.close(opportunity)

        opportunity.refresh_from_db()

        self.assertEqual(result.pk, opportunity.pk)
        self.assertEqual(
            opportunity.status,
            InvestmentOpportunity.Status.CLOSED,
        )

    def test_cancel(self):
        opportunity = self.create_opportunity(
            status=InvestmentOpportunity.Status.DRAFT,
        )

        result = OpportunityService.cancel(opportunity)

        opportunity.refresh_from_db()

        self.assertEqual(result.pk, opportunity.pk)
        self.assertEqual(
            opportunity.status,
            InvestmentOpportunity.Status.CANCELLED,
        )

    def test_open_requires_opportunity(self):
        with self.assertRaises(ValidationError) as context:
            OpportunityService.open(None)

        self.assertIn(
            "opportunity",
            context.exception.message_dict,
        )

    def test_pause_requires_opportunity(self):
        with self.assertRaises(ValidationError) as context:
            OpportunityService.pause(None)

        self.assertIn(
            "opportunity",
            context.exception.message_dict,
        )

    def test_close_requires_opportunity(self):
        with self.assertRaises(ValidationError) as context:
            OpportunityService.close(None)

        self.assertIn(
            "opportunity",
            context.exception.message_dict,
        )

    def test_cancel_requires_opportunity(self):
        with self.assertRaises(ValidationError) as context:
            OpportunityService.cancel(None)

        self.assertIn(
            "opportunity",
            context.exception.message_dict,
        )