# graphq/ecommerce/mutations/ecommerce_mutations.py

"""
GraphQL mutations for the ecommerce domain.

Order, Checkout, Warehouse, GoToMarket, and Inventory mutations are
temporarily removed pending the GraphQL layer rebuild on the new model
structure.
"""

import graphene

from graphq.ecommerce.mutations.category import CategoryMutations
from graphq.ecommerce.mutations.channel import ChannelMutations
from graphq.ecommerce.mutations.collection import CollectionMutations
from graphq.ecommerce.mutations.discount import DiscountMutations
from graphq.ecommerce.mutations.giftcard import GiftCardMutations
from graphq.ecommerce.mutations.product import ProductMutations
from graphq.ecommerce.mutations.shipping import ShippingMutations


class EcommerceMutations(
    CategoryMutations,
    ChannelMutations,
    CollectionMutations,
    DiscountMutations,
    GiftCardMutations,
    ProductMutations,
    ShippingMutations,
    graphene.ObjectType,
):
    """Root mutation composition for the ecommerce domain."""

    pass