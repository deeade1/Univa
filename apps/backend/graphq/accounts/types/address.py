"""
GraphQL Address Types.

Graphene 3.2.3 + Relay.

This module contains only GraphQL representations of account addresses.

Domain/business logic belongs in:
    accounts.models.address
    accounts.services.address

Filtering belongs in:
    graphq.accounts.filters.address

Query optimization belongs in:
    graphq.accounts.resolvers.address
    queryset/service layer

GraphQL node for accounts.Address.

Address is country-neutral: `state` is free-form text (state / province /
region / territory / county / prefecture), and `country` is an ISO-2
country code. Neither is enum-validated at the DB level, so the filters
below use text lookups on `state` and exact/in lookups on `country`.

Important: filter keys use forward field names only. `user` is the FK;
`addresses` is the reverse accessor from User and does NOT belong here.
"""

from __future__ import annotations

import graphene
from graphene import ID, Boolean, Field, String
from graphene.relay import Node
from graphene_django import DjangoObjectType

from accounts.models.address import Address


class AddressNode(DjangoObjectType):
    """
    Account-owned postal/contact address.
    """

    # ------------------------------------------------------------------
    # Derived properties (declared so Graphene exposes them)
    # ------------------------------------------------------------------

    full_name = graphene.String(
        description="Concatenation of first_name and last_name."
    )
    country_name = graphene.String(
        description="Human-readable country name for the stored ISO code."
    )
    state_name = graphene.String(
        description=(
            "The stored administrative division (country-neutral: state, "
            "province, region, territory, county, or equivalent)."
        )
    )
    address_type_display = graphene.String(
        description="Human-readable label for address_type."
    )

    class Meta:
        model = Address
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # ---- Ownership (FK; forward name only) ---------------------
            "user": ["exact"],
            "user__email": ["exact", "icontains"],
            "user__username": ["exact", "icontains"],

            # ---- Classification ----------------------------------------
            "address_type": ["exact", "in"],
            "is_default": ["exact"],

            # ---- Role visibility (forward M2M) -------------------------
            "role_visibility": ["exact"],

            # ---- Recipient ---------------------------------------------
            "first_name": ["exact", "icontains", "istartswith"],
            "last_name": ["exact", "icontains", "istartswith"],
            "company_name": ["exact", "icontains"],

            # ---- Address lines -----------------------------------------
            "street_address_1": ["exact", "icontains", "istartswith"],
            "street_address_2": ["exact", "icontains"],
            "city": ["exact", "icontains"],
            "city_area": ["exact", "icontains"],
            "postal_code": ["exact", "icontains", "istartswith"],

            # ---- Country-neutral administrative division ----------------
            # `state` is free text; only text lookups apply.
            "state": ["exact", "icontains", "istartswith"],
            "country": ["exact", "in"],
            "country_area": ["exact", "icontains"],

            # ---- Contact -----------------------------------------------
            "phone": ["exact", "icontains"],

            # ---- Validation state --------------------------------------
            "validation_skipped": ["exact"],

            # ---- Timestamps --------------------------------------------
            "created_at": ["exact", "gte", "lte", "lt", "gt"],
            "updated_at": ["exact", "gte", "lte", "lt", "gt"],
        }

    # ------------------------------------------------------------------
    # Resolvers for declared properties
    # ------------------------------------------------------------------

    def resolve_full_name(self, info):
        return self.full_name

    def resolve_country_name(self, info):
        return self.country_name

    def resolve_state_name(self, info):
        return self.state_name

    def resolve_address_type_display(self, info):
        return self.address_type_display