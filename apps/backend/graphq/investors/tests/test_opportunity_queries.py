from types import SimpleNamespace

from django.test import TestCase
from graphql_relay import to_global_id

from accounts.models import User
from investors.models import InvestmentOpportunity
from graphq.investors.queries import InvestorQueries
from graphq.investors.types import InvestmentOpportunityNode


class InvestmentOpportunityQueriesTestCase(TestCase):
    def create_user(self):
        return User.objects.create_user(
            email="opportunity-query@example.com",
            password="test-password",
        )

    def create_opportunity(
        self,
        reference="OPP-0001",
        name="Test Opportunity",
        status=InvestmentOpportunity.Status.DRAFT,
    ):
        return InvestmentOpportunity.objects.create(
            reference=reference,
            name=name,
            description="Test investment opportunity",
            currency="NGN",
            minimum_amount="1000.00",
            maximum_amount="100000.00",
            status=status,
            metadata={"source": "test"},
        )

    def create_info(self, user):
        return SimpleNamespace(
            context=SimpleNamespace(user=user),
        )

    def test_node_uses_relay_node_interface(self):
        self.assertIn(
            "Node",
            [
                interface._meta.name
                for interface in InvestmentOpportunityNode._meta.interfaces
            ],
        )

    def test_node_global_id_can_be_constructed(self):
        opportunity = self.create_opportunity()

        global_id = to_global_id(
            InvestmentOpportunityNode._meta.name,
            opportunity.pk,
        )

        self.assertTrue(global_id)
        self.assertIsInstance(global_id, str)

    def test_query_requires_authentication(self):
        anonymous_user = SimpleNamespace(
            is_authenticated=False,
        )
        info = self.create_info(anonymous_user)

        with self.assertRaises(Exception) as raised:
            InvestorQueries.resolve_all_investment_opportunities(
                None,
                info,
            )

        self.assertEqual(
            str(raised.exception),
            "Authentication required.",
        )

    def test_query_returns_authenticated_queryset(self):
        user = self.create_user()
        opportunity = self.create_opportunity()

        queryset = InvestorQueries.resolve_all_investment_opportunities(
            None,
            self.create_info(user),
        )

        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first(), opportunity)

    def test_query_returns_multiple_opportunities(self):
        user = self.create_user()

        first = self.create_opportunity(
            reference="OPP-0001",
            name="First Opportunity",
        )
        second = self.create_opportunity(
            reference="OPP-0002",
            name="Second Opportunity",
        )

        queryset = InvestorQueries.resolve_all_investment_opportunities(
            None,
            self.create_info(user),
        )

        self.assertEqual(queryset.count(), 2)
        self.assertSetEqual(
            set(queryset),
            {first, second},
        )

    def test_filter_fields_are_declared(self):
        filter_fields = InvestmentOpportunityNode._meta.filter_fields

        self.assertIn("reference", filter_fields)
        self.assertIn("name", filter_fields)
        self.assertIn("status", filter_fields)
        self.assertIn("currency", filter_fields)

        self.assertEqual(
            filter_fields["reference"],
            ["exact", "icontains", "istartswith"],
        )
        self.assertEqual(
            filter_fields["name"],
            ["exact", "icontains", "istartswith"],
        )
        self.assertEqual(
            filter_fields["status"],
            ["exact"],
        )
        self.assertEqual(
            filter_fields["currency"],
            ["exact"],
        )
