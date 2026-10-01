"""
Accounts GraphQL schema composition.

Graphene:
    3.2.3

Relay:
    Global Relay Node IDs

Architecture
------------

The Accounts GraphQL layer is intentionally divided into small,
domain-focused components:

    types/
        Relay GraphQL node definitions

    filters/
        GraphQL filtering definitions

    resolvers/
        Queryset construction and authorization-aware resolution

    queries/
        Query field definitions and composition

    mutations/
        State-changing operations

This module is the Accounts query composition boundary.

It must NOT contain:

    - Django ORM queries
    - filtering logic
    - authorization logic
    - business logic
    - mutation logic
    - feature-specific queries

Query flow:

    Root Query
        │
        ▼
    AccountsQuery
        │
        ├── UserQuery
        ├── ProfileQuery
        ├── AddressQuery
        └── RoleQuery
"""

from __future__ import annotations

import graphene

from .queries import (
    AddressQuery,
    ProfileQuery,
    RoleQuery,
    UserQuery,
)


class AccountsQuery(
    UserQuery,
    ProfileQuery,
    AddressQuery,
    RoleQuery,
    graphene.ObjectType,
):
    """
    Root query composition for the Accounts domain.

    Individual query responsibilities remain isolated in their
    respective query classes.

    This class exists only to compose them into a single GraphQL
    object that can be mounted on the application's root Query.
    """

    pass


__all__ = [
    "AccountsQuery",
]