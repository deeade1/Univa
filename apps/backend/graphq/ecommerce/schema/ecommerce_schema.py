# graphq/ecommerce/schema/ecommerce_schema.py

"""
Root query composition for the ecommerce domain.
"""

import graphene
from graphq.ecommerce.mutations.admin_order import AdminOrderMutations
from graphq.ecommerce.schema.category import CategoryQuery
from graphq.ecommerce.schema.channel import ChannelQuery
from graphq.ecommerce.schema.checkout import CheckoutQuery
from graphq.ecommerce.schema.collection import CollectionQuery
from graphq.ecommerce.schema.discount import DiscountQuery
from graphq.ecommerce.schema.giftcard import GiftCardQuery
from graphq.ecommerce.schema.order import OrderQuery
from graphq.ecommerce.schema.product import ProductQuery
from graphq.ecommerce.schema.shipping import ShippingQuery
from graphq.ecommerce.schema.warehouse import WarehouseQuery


class EcommerceQueries(
    AdminOrderMutations,
    CategoryQuery,
    ChannelQuery,
    CheckoutQuery,
    CollectionQuery,
    DiscountQuery,
    GiftCardQuery,
    OrderQuery,
    ProductQuery,
    ShippingQuery,
    WarehouseQuery,
    graphene.ObjectType,
):
    """Root query composition for the ecommerce domain."""

    pass