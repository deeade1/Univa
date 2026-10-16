from types import SimpleNamespace

from django.test import TestCase
from graphql_relay import to_global_id

from accounts.models import User
from investors.models import Investor
from graphq.investors.queries import InvestorQueries
from graphq.investors.types import InvestorNode


class InvestorQueriesTestCase(TestCase):
    def create_user(self, email="investor@example.com"):
        return User.objects.create_user(
            email=email,
            password="test-password",
        )

    def create_investor(
        self,
        email="investor@example.com",
        reference="INV-0001",
        status=Investor.Status.ACTIVE,
        display_name="Test Investor",
    ):
        user = self.create_user(email=email)

        return Investor.objects.create(
            user=user,
            reference=reference,
            status=status,
            display_name=display_name,
            metadata={
                "source": "test",
            },
        )

    def test_investor_node_uses_relay_node_interface(self):
        self.assertIn(
            "Node",
            [
                interface._meta.name
                for interface in InvestorNode._meta.interfaces
            ],
        )

    def test_investor_query_resolver_requires_authentication(self):
        anonymous_user = SimpleNamespace(
            is_authenticated=False,
        )
        info = SimpleNamespace(
            context=SimpleNamespace(user=anonymous_user),
        )

        with self.assertRaises(Exception) as raised:
            InvestorQueries.resolve_all_investors(
                None,
                info,
            )

        self.assertEqual(
            str(raised.exception),
            "Authentication required.",
        )

    def test_all_investors_returns_authenticated_queryset(self):
        user = self.create_user()

        investor = Investor.objects.create(
            user=user,
            reference="INV-0001",
            status=Investor.Status.ACTIVE,
            display_name="Test Investor",
            metadata={},
        )

        info = SimpleNamespace(
            context=SimpleNamespace(user=user),
        )

        queryset = InvestorQueries.resolve_all_investors(
            None,
            info,
        )

        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first(), investor)

    def test_all_investors_returns_multiple_investors(self):
        self.create_investor(
            email="one@example.com",
            reference="INV-0001",
        )

        self.create_investor(
            email="two@example.com",
            reference="INV-0002",
        )

        authenticated_user = User.objects.first()

        info = SimpleNamespace(
            context=SimpleNamespace(user=authenticated_user),
        )

        queryset = InvestorQueries.resolve_all_investors(
            None,
            info,
        )

        self.assertEqual(queryset.count(), 2)

    def test_investor_node_global_id_can_be_constructed(self):
        investor = self.create_investor()

        global_id = to_global_id(
            InvestorNode._meta.name,
            investor.pk,
        )

        self.assertTrue(global_id)
        self.assertIsInstance(global_id, str)

    def test_investor_filter_fields_are_declared(self):
        filter_fields = InvestorNode._meta.filter_fields

        self.assertIn("reference", filter_fields)
        self.assertIn("status", filter_fields)
        self.assertIn("display_name", filter_fields)

        self.assertEqual(
            filter_fields["reference"],
            ["exact", "icontains", "istartswith"],
        )

        self.assertEqual(
            filter_fields["status"],
            ["exact"],
        )

        self.assertEqual(
            filter_fields["display_name"],
            ["exact", "icontains", "istartswith"],
        )

    def test_queryset_uses_related_user(self):
        investor = self.create_investor()

        queryset = InvestorNode.get_queryset(
            Investor.objects.all(),
            None,
        )

        result = queryset.get(pk=investor.pk)

        self.assertEqual(
            result.user.pk,
            investor.user.pk,
        )
