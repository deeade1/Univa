"""
Tests for InvestmentCommitment GraphQL queries.

Run:
    python manage.py test graphq.investors.tests.test_commitment_queries
"""

from decimal import Decimal
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase
from graphql_relay import to_global_id

from backend.schema import schema
from investors.models import (
    InvestmentCommitment,
    InvestmentOpportunity,
    InvestmentPlan,
)

User = get_user_model()


class InvestmentCommitmentQueryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="commitment-query-user@example.com",
            password="test-password",
        )
        self.context = SimpleNamespace(user=self.user)

        self.opportunity = InvestmentOpportunity(
            reference="COMMITMENT-QUERY-OPP-001",
            name="Commitment Query Opportunity",
            status=InvestmentOpportunity.Status.OPEN,
            currency="NGN",
            minimum_amount=Decimal("100000.00"),
            maximum_amount=Decimal("10000000.00"),
        )
        self.opportunity.full_clean()
        self.opportunity.save()

        self.plan = InvestmentPlan(
            opportunity=self.opportunity,
            reference="COMMITMENT-QUERY-PLAN-001",
            name="Commitment Query Plan",
            status=InvestmentPlan.Status.ACTIVE,
            minimum_amount=Decimal("100000.00"),
            maximum_amount=Decimal("5000000.00"),
            duration_days=365,
            expected_return_rate=Decimal("15.0000"),
        )
        self.plan.full_clean()
        self.plan.save()

        self.commitment = InvestmentCommitment(
            investor=self.user,
            opportunity=self.opportunity,
            plan=self.plan,
            reference="COMMITMENT-QUERY-001",
            amount=Decimal("500000.00"),
            currency="NGN",
            status=InvestmentCommitment.Status.PENDING,
        )
        self.commitment.full_clean()
        self.commitment.save()

    def execute(self, query, context=None, variables=None):
        return schema.execute(
            query,
            context_value=context if context is not None else self.context,
            variable_values=variables,
        )

    def test_single_commitment_can_be_resolved_by_relay_id(self):
        commitment_id = to_global_id(
            "InvestmentCommitmentNode",
            self.commitment.pk,
        )
        query = """
            query GetInvestmentCommitment($id: ID!) {
                investmentCommitment(id: $id) {
                    id
                    reference
                    status
                    currency
                    amount
                }
            }
        """

        result = self.execute(query, variables={"id": commitment_id})

        self.assertIsNone(result.errors, result.errors)
        commitment_data = result.data["investmentCommitment"]
        self.assertEqual(
            commitment_data["id"],
            commitment_id,
        )
        self.assertEqual(
            commitment_data["reference"],
            self.commitment.reference,
        )
        self.assertEqual(commitment_data["currency"], "NGN")
        self.assertEqual(
            Decimal(commitment_data["amount"]),
            Decimal("500000.00"),
        )

    def test_all_commitments_returns_connection_and_related_objects(self):
        query = """
            query {
                allInvestmentCommitments(first: 10) {
                    edges {
                        node {
                            id
                            reference
                            status
                            currency
                            investor { id }
                            opportunity { id }
                            plan { id }
                        }
                    }
                    pageInfo {
                        hasNextPage
                    }
                }
            }
        """

        result = self.execute(query)

        self.assertIsNone(result.errors, result.errors)
        connection = result.data["allInvestmentCommitments"]
        self.assertEqual(len(connection["edges"]), 1)

        node = connection["edges"][0]["node"]
        self.assertEqual(node["reference"], self.commitment.reference)
        self.assertEqual(node["currency"], self.commitment.currency)
        self.assertEqual(
            node["opportunity"]["id"],
            to_global_id(
                "InvestmentOpportunityNode",
                self.opportunity.pk,
            ),
        )
        self.assertEqual(
            node["plan"]["id"],
            to_global_id("InvestmentPlanNode", self.plan.pk),
        )
        self.assertIsNotNone(node["investor"]["id"])
        self.assertFalse(connection["pageInfo"]["hasNextPage"])

    def test_all_commitments_requires_authentication(self):
        anonymous_context = SimpleNamespace(
            user=SimpleNamespace(is_authenticated=False),
        )
        query = """
            query {
                allInvestmentCommitments(first: 10) {
                    edges {
                        node { id reference }
                    }
                }
            }
        """

        result = self.execute(query, context=anonymous_context)

        self.assertIsNotNone(result.errors)
        self.assertIn(
            "Authentication required.",
            str(result.errors[0]),
        )

    def test_all_commitments_returns_empty_connection_when_none_exist(self):
        self.commitment.delete()

        query = """
            query {
                allInvestmentCommitments(first: 10) {
                    edges {
                        node { id reference }
                    }
                    pageInfo {
                        hasNextPage
                    }
                }
            }
        """

        result = self.execute(query)

        self.assertIsNone(result.errors, result.errors)
        connection = result.data["allInvestmentCommitments"]
        self.assertEqual(connection["edges"], [])
        self.assertFalse(connection["pageInfo"]["hasNextPage"])
