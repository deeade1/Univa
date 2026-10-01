"""
Root GraphQL schema for Univa.

Architecture
------------

The root schema is responsible only for composing domain-level
GraphQL query, mutation, and subscription objects.

Domain logic belongs inside the corresponding application.

Example:

    Accounts
        ├── types
        ├── filters
        ├── resolvers
        ├── queries
        └── mutations

The root schema must NOT contain:
    - Django ORM queries
    - business logic
    - authorization logic
    - filtering logic
    - resolver implementations
"""

from __future__ import annotations

import graphene
from graphene import ObjectType, Schema
from graphene_django.debug import DjangoDebug


# ============================================================================
# GraphQL Type / Converter Registration
# ============================================================================

# Register custom GraphQL converters before importing/building the schema.
#
# These converters extend Graphene-Django's normal Django field handling.
try:
    from graphq.core.types import money  # noqa: F401

except ImportError:
    # The schema can still load when the optional custom converter
    # package is unavailable.
    pass

# ============================================================================
# Automatic Filter Registration
# ============================================================================


# ============================================================================
# Accounts
# ============================================================================
from graphq.accounts.mutations.account import AccountMutations
from graphq.accounts.schema import AccountsQuery
from graphq.accounts.subscriptions import AccountSubscriptions


# ============================================================================
# E-Commerce
# ============================================================================


from graphq.ecommerce.mutations.ecommerce_mutations import EcommerceMutations
from graphq.ecommerce.schema.ecommerce_schema import EcommerceQueries


# ============================================================================
# Other Domains
# ============================================================================

# Banking
from graphq.banking.mutations.banking import BankingMutations
from graphq.banking.schema import BankingQueries, SecurityQueries

# Biometrics
from graphq.biometrics.schema import BiometricsQueries
from graphq.biometrics.mutations import BiometricsMutations
# Blog
from graphq.blog.mutations import BlogMutations
from graphq.blog.schema import BlogQueries


# Chat
from graphq.chat.mutations import ChatMutations
from graphq.chat.schema import ChatQueries
from graphq.chat.subscription import ChatSubscriptions


# Invoice
from graphq.invoice.mutations import InvoiceMutations
from graphq.invoice.schema import InvoiceQuery


# Payments
from graphq.payment.mutations import PaymentMutations
from graphq.payment.schema import PaymentQueries


# Real Estate
from graphq.realestate.mutations.realestate_mutations import RealEstateMutations
from graphq.realestate.schema import RealestateQueries
from graphq.realestate.subscriptions import RealEstateSubscriptions


# Social
from graphq.social.mutations import SocialMutations
from graphq.social.schema import SocialQueries
from graphq.social.subscription import SocialSubscriptions


# Tax
from graphq.tax.mutations import TaxMutations
from graphq.tax.schema import TaxQueries


# Transport
from graphq.transport.mutations.transport_mutation import TransportMutations
from graphq.transport.schema import TransportQuery
#from graphq.transport.subscriptions import TransportSubscriptions

# Staff
from graphq.staff.schema import StaffQuery
from graphq.staff.schema import StaffMutation
# ============================================================================
# Core
# ============================================================================

#from graphq.core.mutations.location_mutations import LocationMutations
#from graphq.core.queries.location_queries import LocationQuery
#from graphq.core.subscriptions.location_subscriptions import (LocationUpdatedSubscription,)



# ============================================================================
# Root Query
# ============================================================================


class Query(
    # ------------------------------------------------------------------
    # Accounts
    # ------------------------------------------------------------------
    AccountsQuery,

    # ------------------------------------------------------------------
    # E-Commerce
    # ------------------------------------------------------------------
    EcommerceQueries,

    # ------------------------------------------------------------------
    # Other Domains
    # ------------------------------------------------------------------
    BankingQueries,
    SecurityQueries,
    BlogQueries,
    ChatQueries,
    SocialQueries,
    InvoiceQuery,
    PaymentQueries,
    RealestateQueries,
    TransportQuery,
    TaxQueries,
    StaffQuery,
    
    BiometricsQueries,
    # ------------------------------------------------------------------
    # Core
    # ------------------------------------------------------------------
    #LocationQuery,

    # ------------------------------------------------------------------
    # Graphene
    # ------------------------------------------------------------------
    ObjectType,
):
    """
    Root GraphQL Query.

    This class is composition only.

    Domain query implementations remain inside their respective
    applications.
    """

    debug = graphene.Field(
        DjangoDebug,
        name="_debug",
    )


# ============================================================================
# Root Mutation
# ============================================================================


class Mutation(
    # ------------------------------------------------------------------
    # Accounts
    # ------------------------------------------------------------------
    AccountMutations,

    # ------------------------------------------------------------------
    # E-Commerce
    # ------------------------------------------------------------------
    EcommerceMutations,
   

    # ------------------------------------------------------------------
    # Other Domains
    # ------------------------------------------------------------------
    BankingMutations,
    BlogMutations,
    ChatMutations,
    SocialMutations,
    InvoiceMutations,
    PaymentMutations,
    RealEstateMutations,
    TransportMutations,
    TaxMutations,
    StaffMutation,
    BiometricsMutations,
    # ------------------------------------------------------------------
    # Core
    # ------------------------------------------------------------------
    #LocationMutations,

    # ------------------------------------------------------------------
    # Graphene
    # ------------------------------------------------------------------
    ObjectType,
):
    """
    Root GraphQL Mutation.

    Composition only.
    """

    pass


# ============================================================================
# Root Subscription
# ============================================================================


class Subscription(
    # ------------------------------------------------------------------
    # Accounts
    # ------------------------------------------------------------------
    AccountSubscriptions,

    # ------------------------------------------------------------------
    # Other Domains
    # ------------------------------------------------------------------
    ChatSubscriptions,
    SocialSubscriptions,
    RealEstateSubscriptions,
    #TransportSubscriptions,

    # ------------------------------------------------------------------
    # Core
    # ------------------------------------------------------------------
    #LocationUpdatedSubscription,

    # ------------------------------------------------------------------
    # Graphene
    # ------------------------------------------------------------------
    ObjectType,
):
    """
    Root GraphQL Subscription.

    Composition only.
    """

    pass


# ============================================================================
# Schema
# ============================================================================


schema = Schema(
    query=Query,
    mutation=Mutation,
    subscription=Subscription,
)