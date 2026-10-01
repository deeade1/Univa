"""
------------------------------------------------------------------------------
Location Nodes
------------------------------------------------------------------------------

Graphene-Django nodes backed by Django models.

These types expose database models through Relay.

Used by

    • Accounts
    • Banking
    • Transport
    • Logistics
    • Marketplace
    • Real Estate
    • Warehouse
    • Social
------------------------------------------------------------------------------
"""

'''from graphene import relay
from graphene_django import DjangoObjectType
from core.models.location import LocationModel



# ------------------------------------------------------------------------------
# Abstract Location
# ------------------------------------------------------------------------------


class LocationNode(DjangoObjectType):
    """
    Base location node.

    This node exposes the common fields inherited
    from LocationModel.
    """

    class Meta:
        model = LocationModel
        abstract = True
        fields = (
            "location",
            "latitude",
            "longitude",
            "location_accuracy",
            "location_timestamp",
            "location_source",
            "location_point",
        )
        interfaces = (relay.Node,)'''