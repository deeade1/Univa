# graphq/ecommerce/schema/ecommerce_schema.py

"""
Root query composition for the ecommerce domain.

GoToMarket and Inventory queries are temporarily removed pending
the GraphQL layer rebuild on the new model structure.
"""

import graphene

from graphq.ecommerce.schema.category import CategoryQuery
from graphq.ecommerce.schema.channel import ChannelQuery
from graphq.ecommerce.schema.checkout import CheckoutQuery
from graphq.ecommerce.schema.collection import CollectionQuery
from graphq.ecommerce.schema.discount import DiscountQuery
from graphq.ecommerce.schema.giftcard import GiftCardQuery
from graphq.ecommerce.schema.product import ProductQuery
from graphq.ecommerce.schema.shipping import ShippingQuery
from graphq.ecommerce.schema.warehouse import WarehouseQuery


class EcommerceQueries(
    CategoryQuery,
    ChannelQuery,
    CheckoutQuery,
    CollectionQuery,
    DiscountQuery,
    GiftCardQuery,
    ProductQuery,
    ShippingQuery,
    WarehouseQuery,
    graphene.ObjectType,
):
    """Root query composition for the ecommerce domain."""

    pass