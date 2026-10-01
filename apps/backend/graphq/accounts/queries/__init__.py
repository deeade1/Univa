"""
Accounts GraphQL query composition.

Graphene:
    3.2.3

Relay:
    Global Relay Node IDs.

This package exposes the query composition objects for the
centralized Accounts domain.

Query boundaries
----------------

    UserQuery
        └── user / users / me

    ProfileQuery
        └── profile / profiles / my_profile

    AddressQuery
        └── address / addresses

    RoleQuery
        └── role / roles / role assignments

Each query class owns its GraphQL fields and delegates actual
queryset/object resolution to the corresponding resolver layer.

This package initializer is responsible only for query exports.

No business logic belongs here.
"""

from .address import AddressQuery
from .profile import ProfileQuery
from .role import RoleQuery
from .user import UserQuery


__all__ = [
    "AddressQuery",
    "ProfileQuery",
    "RoleQuery",
    "UserQuery",
]