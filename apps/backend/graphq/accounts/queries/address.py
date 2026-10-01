"""
GraphQL queries for account-owned addresses.

Graphene:
    3.2.3

Relay:
    Global Relay Node IDs

Architecture
------------

    GraphQL
        │
        ▼
    AddressQuery
        │
        ├── AddressNode
        ├── AddressFilter
        │
        └── Address resolvers
                │
                ▼
          Address queryset

Responsibilities:
    - expose Address through Relay
    - connect AddressFilter to the Relay connection
    - enforce authenticated-user visibility
    - resolve individual addresses through Relay global IDs
    - delegate queryset construction to resolvers

This module does NOT:
    - create or update addresses
    - perform mutations
    - handle authentication
    - contain address business logic
    - implement authorization rules directly

Authorization and queryset construction belong to:
    graphq.accounts.resolvers.address
"""

from __future__ import annotations

import graphene
from graphene import relay
from graphene_django.filter import DjangoFilterConnectionField

from graphq.accounts.filters.address import AddressFilter
from graphq.accounts.resolvers.address import (
    optimize_address_queryset,
    resolve_address,
    resolve_addresses,
)
from graphq.accounts.types.address import AddressNode


class AddressQuery(graphene.ObjectType):
    """
    Relay queries for account-owned addresses.
    """

    # ==================================================================
    # Single Address
    # ==================================================================

    address = graphene.Field(AddressNode)

    # ==================================================================
    # Address Connection
    # ==================================================================

    all_address = DjangoFilterConnectionField(
        AddressNode,
        filterset_class=AddressFilter,
        description=(
            "Relay connection containing addresses visible to the "
            "authenticated user."
        ),
    )

    # ==================================================================
    # Resolvers
    # ==================================================================

    @staticmethod
    def resolve_address(
        root,
        info,
        id,
    ):
        """
        Resolve one Address from a Relay global ID.

        Graphene decodes the Relay global ID first. The resulting
        database primary key is passed to the address resolver.

        Visibility is enforced by resolve_address().
        """

        address = relay.Node.get_node_from_global_id(
            info,
            id,
            only_type=AddressNode,
        )

        if address is None:
            return None

        user = getattr(
            info.context,
            "user",
            None,
        )

        return resolve_address(
            user,
            address.pk,
        )

    @staticmethod
    def resolve_addresses(
        root,
        info,
        **kwargs,
    ):
        """
        Resolve the base Address queryset.

        The resolver establishes the authorization boundary.

        Address filtering is handled by AddressFilter and Relay
        pagination is handled by DjangoFilterConnectionField.
        """

        user = getattr(
            info.context,
            "user",
            None,
        )

        queryset = resolve_addresses(user)

        return optimize_address_queryset(
            queryset,
        )


__all__ = [
    "AddressQuery",
]