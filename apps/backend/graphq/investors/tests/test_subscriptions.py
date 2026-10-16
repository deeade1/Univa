from unittest.mock import patch

from django.test import TestCase

from accounts.models import User
from investors.models import Investor

from graphq.investors.subscriptions import (
    InvestorStatusChangedSubscription,
)


class InvestorStatusChangedSubscriptionTestCase(TestCase):
    def create_investor(self):
        user = User.objects.create_user(
            email="investor@example.com",
            password="test-password",
        )

        return Investor.objects.create(
            user=user,
            reference="INV-0001",
            status=Investor.Status.PENDING,
            display_name="Test Investor",
            metadata={},
        )

    def test_subscribe_returns_investor_status_group(self):
        investor = self.create_investor()

        from graphql_relay import to_global_id

        global_id = to_global_id(
            "InvestorNode",
            investor.pk,
        )

        groups = (
            InvestorStatusChangedSubscription.subscribe(
                None,
                None,
                global_id,
            )
        )

        self.assertEqual(
            groups,
            [f"investor_status_{investor.pk}"],
        )

    def test_publish_maps_payload(self):
        investor = self.create_investor()

        payload = {
            "investor": investor,
            "old_status": Investor.Status.PENDING,
            "new_status": Investor.Status.ACTIVE,
            "changed_by": str(investor.user.pk),
        }

        result = (
            InvestorStatusChangedSubscription.publish(
                payload,
                None,
                "investor-global-id",
            )
        )

        self.assertIs(
            result.investor,
            investor,
        )

        self.assertEqual(
            result.old_status,
            Investor.Status.PENDING,
        )

        self.assertEqual(
            result.new_status,
            Investor.Status.ACTIVE,
        )

        self.assertEqual(
            result.changed_by,
            str(investor.user.pk),
        )

    @patch.object(
        InvestorStatusChangedSubscription,
        "broadcast",
    )
    def test_trigger_broadcasts_status_change(
        self,
        broadcast,
    ):
        investor = self.create_investor()

        InvestorStatusChangedSubscription.trigger(
            investor=investor,
            old_status=Investor.Status.PENDING,
            new_status=Investor.Status.ACTIVE,
            changed_by=investor.user.pk,
        )

        broadcast.assert_called_once_with(
            group=f"investor_status_{investor.pk}",
            payload={
                "investor": investor,
                "old_status": Investor.Status.PENDING,
                "new_status": Investor.Status.ACTIVE,
                "changed_by": investor.user.pk,
            },
        )

    @patch.object(
        InvestorStatusChangedSubscription,
        "broadcast",
    )
    def test_trigger_supports_system_change_without_actor(
        self,
        broadcast,
    ):
        investor = self.create_investor()

        InvestorStatusChangedSubscription.trigger(
            investor=investor,
            old_status=Investor.Status.ACTIVE,
            new_status=Investor.Status.SUSPENDED,
        )

        broadcast.assert_called_once_with(
            group=f"investor_status_{investor.pk}",
            payload={
                "investor": investor,
                "old_status": Investor.Status.ACTIVE,
                "new_status": Investor.Status.SUSPENDED,
                "changed_by": None,
            },
        )

    def test_subscription_returns_expected_field_values(self):
        investor = self.create_investor()

        subscription = (
            InvestorStatusChangedSubscription(
                investor=investor,
                old_status=Investor.Status.PENDING,
                new_status=Investor.Status.ACTIVE,
                changed_by=str(investor.user.pk),
            )
        )

        self.assertIs(
            subscription.investor,
            investor,
        )

        self.assertEqual(
            subscription.old_status,
            Investor.Status.PENDING,
        )

        self.assertEqual(
            subscription.new_status,
            Investor.Status.ACTIVE,
        )

        self.assertEqual(
            subscription.changed_by,
            str(investor.user.pk),
        )