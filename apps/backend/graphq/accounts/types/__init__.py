"""
Accounts GraphQL types.

Graphene:
    3.2.3

Relay:
    Global Relay Node IDs

This package contains the GraphQL representations of the centralized
Accounts domain.

Architecture
------------

    models/
        Django domain models

    types/
        GraphQL Relay nodes

    filters/
        GraphQL filtering

    resolvers/
        Queryset construction and authorization-aware resolution

    queries/
        GraphQL query composition

    mutations/
        State-changing GraphQL operations

This module is intentionally an export boundary only.

No:
    - query logic
    - resolver logic
    - filtering logic
    - mutation logic
    - authorization logic
    - business logic

belongs here.
"""

from .address import AddressNode
from .profile import UserProfileNode
from .role import RoleNode, UserRoleNode
from .user import UserNode


__all__ = [
    "AddressNode",
    "RoleNode",
    "UserNode",
    "UserProfileNode",
    "UserRoleNode",
]