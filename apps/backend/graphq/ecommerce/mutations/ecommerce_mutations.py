# graphq/ecommerce/mutations/ecommerce_mutations.py

"""
GraphQL mutations for the ecommerce domain.
"""

import graphene
from graphq.ecommerce.mutations.admin_order import AdminOrderMutations
from graphq.ecommerce.mutations.category import CategoryMutations
from graphq.ecommerce.mutations.channel import ChannelMutations
from graphq.ecommerce.mutations.checkout import CheckoutMutations
from graphq.ecommerce.mutations.collection import CollectionMutations
from graphq.ecommerce.mutations.discount import DiscountMutations
from graphq.ecommerce.mutations.giftcard import GiftCardMutations
from graphq.ecommerce.mutations.order import OrderMutations
from graphq.ecommerce.mutations.product import ProductMutations
from graphq.ecommerce.mutations.shipping import ShippingMutations


class EcommerceMutations(
    AdminOrderMutations,  
    CategoryMutations,
    ChannelMutations,
    CollectionMutations,
    CheckoutMutations,
    DiscountMutations,
    GiftCardMutations,
    OrderMutations,
    ProductMutations,
    ShippingMutations,
    graphene.ObjectType,
):
    """Root mutation composition for the ecommerce domain."""

    pass