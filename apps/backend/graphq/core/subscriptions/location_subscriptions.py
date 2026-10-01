# ------------------------------------------------------------------------------
# apps/backend/core/graphql/subscriptions/location_subscriptions.py
# ------------------------------------------------------------------------------

"""
Reusable Location Subscriptions.

Shared by

• Accounts
• Banking
• Transport
• Logistics
• Marketplace
• Real Estate
• Warehouse
• Social

Every model inheriting LocationModel can broadcast location updates
through this subscription.
"""

import graphene

from channels_graphql_ws import Subscription
from graphq.core.types.location_types import LocationType


class LocationUpdatedSubscription(Subscription):
    """
    Generic live location subscription.
    """

    location = graphene.Field(LocationType)
    data = graphene.JSONString()

    class Arguments:
        app_label = graphene.String(required=True)
        model_name = graphene.String(required=True)
        object_id = graphene.ID(required=True)

    # ------------------------------------------------------------------
    # Subscribe
    # ------------------------------------------------------------------

    def subscribe(self, info, app_label, model_name, object_id):
        """
        Example groups

            accounts_User_15
            transport_Trip_21
            transport_Vehicle_9
            realestate_Property_3
            banking_BankBranch_8
        """
        return [
            f"{app_label}_{model_name}_{object_id}"
        ]

    # ------------------------------------------------------------------
    # Publish
    # ------------------------------------------------------------------

    def publish(self, info, app_label, model_name, object_id):
        return LocationUpdatedSubscription(
            location=self["location"],
            data=self["data"],
        )

    # ------------------------------------------------------------------
    # Trigger
    # ------------------------------------------------------------------

    @classmethod
    def trigger(cls, instance, payload=None):
        """
        Broadcast location updates.

        Usage:

            LocationUpdatedSubscription.trigger(vehicle)

            LocationUpdatedSubscription.trigger(
                property,
                {"verified": True}
            )
        """

        if payload is None:
            payload = {}

        payload.update(
            {
                "latitude": (
                    float(instance.latitude)
                    if instance.latitude is not None
                    else None
                ),
                "longitude": (
                    float(instance.longitude)
                    if instance.longitude is not None
                    else None
                ),
                "address": instance.location,
                "accuracy": instance.location_accuracy,
                "source": instance.location_source,
                "timestamp": instance.location_timestamp,
            }
        )

        cls.broadcast(
            group=(
                f"{instance._meta.app_label}_"
                f"{instance.__class__.__name__}_"
                f"{instance.pk}"
            ),
            payload={
                "location": instance,
                "data": payload,
            },
        )


class LocationSubscription(graphene.ObjectType):
    """
    Root Location subscriptions.
    """

    location_updated = LocationUpdatedSubscription.Field()