import graphene
from channels_graphql_ws import Subscription
from graphql_relay import from_global_id

from .types import InvestorNode


class InvestorStatusChangedSubscription(Subscription):
    """
    Real-time Investor status updates.

    Examples:

        PENDING   → ACTIVE
        ACTIVE    → SUSPENDED
        SUSPENDED → ACTIVE
        ACTIVE    → CLOSED
    """

    investor = graphene.Field(InvestorNode)
    old_status = graphene.String()
    new_status = graphene.String()
    changed_by = graphene.ID()

    class Arguments:
        investor_id = graphene.ID(required=True)

    @staticmethod
    def subscribe(root, info, investor_id):
        """
        Subscribe to status changes for one Investor.
        """
        _, pk = from_global_id(investor_id)

        return [f"investor_status_{pk}"]

    @staticmethod
    def publish(payload, info, investor_id):
        """
        Convert the broadcast payload into the GraphQL
        subscription payload.
        """
        return InvestorStatusChangedSubscription(
            investor=payload.get("investor"),
            old_status=payload.get("old_status"),
            new_status=payload.get("new_status"),
            changed_by=payload.get("changed_by"),
        )

    @classmethod
    def trigger(
        cls,
        investor,
        old_status,
        new_status,
        changed_by=None,
    ):
        """
        Broadcast an Investor status transition.
        """
        cls.broadcast(
            group=f"investor_status_{investor.id}",
            payload={
                "investor": investor,
                "old_status": old_status,
                "new_status": new_status,
                "changed_by": changed_by,
            },
        )


class InvestorSubscriptions(graphene.ObjectType):
    """
    Investor GraphQL subscriptions.
    """

    investor_status_changed = (
        InvestorStatusChangedSubscription.Field()
    )