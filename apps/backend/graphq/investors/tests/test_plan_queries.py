from types import SimpleNamespace

from django.test import TestCase
from graphql_relay import to_global_id

from accounts.models import User
from investors.models import InvestmentOpportunity, InvestmentPlan
from graphq.investors.queries import InvestorQueries
from graphq.investors.types import InvestmentPlanNode


class InvestmentPlanQueriesTestCase(TestCase):
    def create_user(self):
        return User.objects.create_user(
            email="plan-query@example.com",
            password="test-password",
        )

    def create_opportunity(self):
        return InvestmentOpportunity.objects.create(
            reference="OPP-PLAN-001",
            name="Plan Test Opportunity",
            description="Opportunity for plan tests",
            currency="NGN",
            minimum_amount="1000.00",
            maximum_amount="1000000.00",
            status=InvestmentOpportunity.Status.OPEN,
            metadata={},
        )

    def create_plan(
        self,
        reference="PLAN-0001",
        name="Test Investment Plan",
    ):
        opportunity = self.create_opportunity()

        return InvestmentPlan.objects.create(
            opportunity=opportunity,
            reference=reference,
            name=name,
            description="Plan for query tests",
            status=InvestmentPlan.Status.DRAFT,
            minimum_amount="1000.00",
            maximum_amount="100000.00",
            duration_days=90,
            expected_return_rate="5.00",
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
                for interface in InvestmentPlanNode._meta.interfaces
            ],
        )

    def test_node_global_id_can_be_constructed(self):
        plan = self.create_plan()

        global_id = to_global_id(
            InvestmentPlanNode._meta.name,
            plan.pk,
        )

        self.assertTrue(global_id)
        self.assertIsInstance(global_id, str)

    def test_query_requires_authentication(self):
        anonymous_user = SimpleNamespace(
            is_authenticated=False,
        )

        with self.assertRaises(Exception) as raised:
            InvestorQueries.resolve_all_investment_plans(
                None,
                self.create_info(anonymous_user),
            )

        self.assertEqual(
            str(raised.exception),
            "Authentication required.",
        )

    def test_query_returns_authenticated_queryset(self):
        user = self.create_user()
        plan = self.create_plan()

        queryset = InvestorQueries.resolve_all_investment_plans(
            None,
            self.create_info(user),
        )

        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first(), plan)

    
    def test_query_returns_multiple_plans(self):
        user = self.create_user()
        opportunity = self.create_opportunity()

        first = InvestmentPlan.objects.create(
            opportunity=opportunity,
            reference="PLAN-0001",
            name="First Plan",
            description="First plan for query tests",
            status=InvestmentPlan.Status.DRAFT,
            minimum_amount="1000.00",
            maximum_amount="100000.00",
            duration_days=90,
            expected_return_rate="5.00",
            metadata={"source": "test"},
        )

        second = InvestmentPlan.objects.create(
            opportunity=opportunity,
            reference="PLAN-0002",
            name="Second Plan",
            description="Second plan for query tests",
            status=InvestmentPlan.Status.DRAFT,
            minimum_amount="2000.00",
            maximum_amount="200000.00",
            duration_days=180,
            expected_return_rate="6.00",
            metadata={"source": "test"},
        )

        queryset = InvestorQueries.resolve_all_investment_plans(
            None,
            self.create_info(user),
        )

        self.assertEqual(queryset.count(), 2)
        self.assertSetEqual(set(queryset), {first, second})


    def test_filter_fields_are_declared(self):
        filter_fields = InvestmentPlanNode._meta.filter_fields

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
