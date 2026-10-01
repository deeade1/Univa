"""
Univa Accounts GraphQL domain.

Graphene:
    3.2.3

Relay:
    Global Relay Node IDs

Architecture
------------

The Accounts GraphQL domain is separated into:

    types/
        Relay GraphQL object types.

    queries/
        GraphQL query fields and composition.

    resolvers/
        Queryset construction and object resolution.

    filters/
        GraphQL filtering.

    mutations/
        State-changing GraphQL operations.

    subscriptions/
        Real-time GraphQL operations.

This package initializer intentionally contains no business logic
and does not eagerly import domain types, queries, filters, or
resolvers.

Import from the appropriate subpackage instead, for example:

    from graphq.accounts.types import UserNode
    from graphq.accounts.queries import UserQuery
"""