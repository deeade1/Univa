"""
Tests for InvestmentCommitment GraphQL mutations.

These tests exercise the GraphQL adapter contract:
- authentication is required;
- Relay opportunity and plan IDs are resolved;
- commitment creation delegates to the domain service;
- invalid IDs prevent commitment creation;
- domain service errors propagate to the caller;
- the mutation returns the commitment and client_mutation_id.

Run with:
    python manage.py test graphq.investors.tests.test_commitment_mutations
"""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from graphql import GraphQLError

from graphq.investors.mutations import CreateInvestmentCommitment


MUTATIONS_MODULE = "graphq.investors.mutations"


class InvestmentCommitmentMutationTests(SimpleTestCase):
    def setUp(self):
        self.user = SimpleNamespace(is_authenticated=True)
        self.info = SimpleNamespace(
            context=SimpleNamespace(user=self.user)
        )

        self.opportunity = SimpleNamespace(id=17)
        self.plan = SimpleNamespace(id=29)

        self.commitment = SimpleNamespace(
            id=41,
            reference="COMMIT-INVEST-001",
            amount=Decimal("500000.00"),
            currency="NGN",
        )

        self.opportunity_id = "SW52ZXN0bWVudE9wcG9ydHVuaXR5OjE3"
        self.plan_id = "SW52ZXN0bWVudFBsYW46Mjk="

    def test_create_commitment_rejects_anonymous_user(self):
        self.user.is_authenticated = False

        with (
            patch(
                f"{MUTATIONS_MODULE}.get_investment_opportunity_from_global_id"
            ) as resolve_opportunity,
            patch(
                f"{MUTATIONS_MODULE}.get_investment_plan_from_global_id"
            ) as resolve_plan,
            patch(
                f"{MUTATIONS_MODULE}.CommitmentService.create"
            ) as create_commitment,
        ):
            with self.assertRaisesMessage(
                GraphQLError,
                "Authentication required.",
            ):
                CreateInvestmentCommitment.mutate_and_get_payload(
                    None,
                    self.info,
                    opportunity_id=self.opportunity_id,
                    plan_id=self.plan_id,
                    reference="COMMIT-INVEST-001",
                    amount=Decimal("500000.00"),
                    currency="NGN",
                )

        resolve_opportunity.assert_not_called()
        resolve_plan.assert_not_called()
        create_commitment.assert_not_called()

    def test_create_commitment_resolves_ids_and_returns_payload(self):
        with (
            patch(
                f"{MUTATIONS_MODULE}.get_investment_opportunity_from_global_id",
                return_value=self.opportunity,
            ) as resolve_opportunity,
            patch(
                f"{MUTATIONS_MODULE}.get_investment_plan_from_global_id",
                return_value=self.plan,
            ) as resolve_plan,
            patch(
                f"{MUTATIONS_MODULE}.CommitmentService.create",
                return_value=self.commitment,
            ) as create_commitment,
        ):
            payload = CreateInvestmentCommitment.mutate_and_get_payload(
                None,
                self.info,
                opportunity_id=self.opportunity_id,
                plan_id=self.plan_id,
                reference="COMMIT-INVEST-001",
                amount=Decimal("500000.00"),
                currency="NGN",
                client_mutation_id="client-create-commitment-1",
            )

        resolve_opportunity.assert_called_once_with(self.opportunity_id)
        resolve_plan.assert_called_once_with(self.plan_id)

        create_commitment.assert_called_once_with(
            investor=self.user,
            opportunity=self.opportunity,
            plan=self.plan,
            reference="COMMIT-INVEST-001",
            amount=Decimal("500000.00"),
            currency="NGN",
        )

        self.assertIs(payload.investment_commitment, self.commitment)
        self.assertEqual(
            payload.client_mutation_id,
            "client-create-commitment-1",
        )

    def test_invalid_opportunity_id_prevents_creation(self):
        with (
            patch(
                f"{MUTATIONS_MODULE}.get_investment_opportunity_from_global_id",
                side_effect=GraphQLError(
                    "Invalid investment opportunity ID."
                ),
            ) as resolve_opportunity,
            patch(
                f"{MUTATIONS_MODULE}.get_investment_plan_from_global_id"
            ) as resolve_plan,
            patch(
                f"{MUTATIONS_MODULE}.CommitmentService.create"
            ) as create_commitment,
        ):
            with self.assertRaisesMessage(
                GraphQLError,
                "Invalid investment opportunity ID.",
            ):
                CreateInvestmentCommitment.mutate_and_get_payload(
                    None,
                    self.info,
                    opportunity_id="invalid-opportunity-id",
                    plan_id=self.plan_id,
                    reference="COMMIT-TEST-001",
                    amount=Decimal("500000.00"),
                    currency="NGN",
                )

        resolve_opportunity.assert_called_once_with(
            "invalid-opportunity-id"
        )
        resolve_plan.assert_not_called()
        create_commitment.assert_not_called()

    def test_invalid_plan_id_prevents_creation(self):
        with (
            patch(
                f"{MUTATIONS_MODULE}.get_investment_opportunity_from_global_id",
                return_value=self.opportunity,
            ) as resolve_opportunity,
            patch(
                f"{MUTATIONS_MODULE}.get_investment_plan_from_global_id",
                side_effect=GraphQLError(
                    "Invalid investment plan ID."
                ),
            ) as resolve_plan,
            patch(
                f"{MUTATIONS_MODULE}.CommitmentService.create"
            ) as create_commitment,
        ):
            with self.assertRaisesMessage(
                GraphQLError,
                "Invalid investment plan ID.",
            ):
                CreateInvestmentCommitment.mutate_and_get_payload(
                    None,
                    self.info,
                    opportunity_id=self.opportunity_id,
                    plan_id="invalid-plan-id",
                    reference="COMMIT-TEST-002",
                    amount=Decimal("500000.00"),
                    currency="NGN",
                )

        resolve_opportunity.assert_called_once_with(self.opportunity_id)
        resolve_plan.assert_called_once_with("invalid-plan-id")
        create_commitment.assert_not_called()

    def test_service_validation_error_propagates(self):
        validation_error = ValidationError(
            {"amount": "Amount is invalid."}
        )

        with (
            patch(
                f"{MUTATIONS_MODULE}.get_investment_opportunity_from_global_id",
                return_value=self.opportunity,
            ),
            patch(
                f"{MUTATIONS_MODULE}.get_investment_plan_from_global_id",
                return_value=self.plan,
            ),
            patch(
                f"{MUTATIONS_MODULE}.CommitmentService.create",
                side_effect=validation_error,
            ) as create_commitment,
        ):
            with self.assertRaises(ValidationError) as context:
                CreateInvestmentCommitment.mutate_and_get_payload(
                    None,
                    self.info,
                    opportunity_id=self.opportunity_id,
                    plan_id=self.plan_id,
                    reference="COMMIT-TEST-003",
                    amount=Decimal("500000.00"),
                    currency="NGN",
                )

        self.assertIs(context.exception, validation_error)
        create_commitment.assert_called_once_with(
            investor=self.user,
            opportunity=self.opportunity,
            plan=self.plan,
            reference="COMMIT-TEST-003",
            amount=Decimal("500000.00"),
            currency="NGN",
        )

    def test_client_mutation_id_is_optional(self):
        with (
            patch(
                f"{MUTATIONS_MODULE}.get_investment_opportunity_from_global_id",
                return_value=self.opportunity,
            ),
            patch(
                f"{MUTATIONS_MODULE}.get_investment_plan_from_global_id",
                return_value=self.plan,
            ),
            patch(
                f"{MUTATIONS_MODULE}.CommitmentService.create",
                return_value=self.commitment,
            ),
        ):
            payload = CreateInvestmentCommitment.mutate_and_get_payload(
                None,
                self.info,
                opportunity_id=self.opportunity_id,
                plan_id=self.plan_id,
                reference="COMMIT-TEST-004",
                amount=Decimal("250000.00"),
                currency="NGN",
            )

        self.assertIs(payload.investment_commitment, self.commitment)
        self.assertIsNone(payload.client_mutation_id)


class CommitmentMutationValidationTests(SimpleTestCase):
    @patch(
        f"{MUTATIONS_MODULE}.CommitmentService.create"
    )
    @patch(
        f"{MUTATIONS_MODULE}.get_investment_opportunity_from_global_id",
        side_effect=GraphQLError("Invalid investment opportunity ID."),
    )
    def test_invalid_opportunity_id_prevents_creation(
        self,
        mock_get_opportunity,
        mock_create,
    ):
        user = SimpleNamespace(is_authenticated=True)
        info = SimpleNamespace(
            context=SimpleNamespace(user=user)
        )

        with self.assertRaisesMessage(
            GraphQLError,
            "Invalid investment opportunity ID.",
        ):
            CreateInvestmentCommitment.mutate_and_get_payload(
                None,
                info,
                opportunity_id="invalid-opportunity-id",
                plan_id="plan-id",
                reference="COMMIT-TEST-001",
                amount=Decimal("500000.00"),
                currency="NGN",
            )

        mock_get_opportunity.assert_called_once_with(
            "invalid-opportunity-id"
        )
        mock_create.assert_not_called()
