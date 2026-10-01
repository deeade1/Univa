import graphene
from graphq.ecommerce.schema.attribute import AttributeQuery
from graphq.ecommerce.schema.category import CategoryQuery
from graphq.ecommerce.schema.channel import ChannelQuery
from graphq.ecommerce.schema.checkout import CheckoutQuery
from graphq.ecommerce.schema.collection import CollectionQuery
from graphq.ecommerce.schema.discount import DiscountQuery
from graphq.ecommerce.schema.giftcard import GiftCardQuery
from graphq.ecommerce.schema.gotomarket import GoToMarketQuery
from graphq.ecommerce.schema.inventory import InventoryQuery
from graphq.ecommerce.schema.order import OrderQuery
from graphq.ecommerce.schema.product import ProductQuery
from graphq.ecommerce.schema.shipping import ShippingQuery
from graphq.ecommerce.schema.warehouse import WarehouseQuery



class EcommerceQueries(
    AttributeQuery,
    CategoryQuery,
    ChannelQuery,
    CheckoutQuery,
    CollectionQuery,
    DiscountQuery,
    GiftCardQuery,
    GoToMarketQuery,
    InventoryQuery,
    OrderQuery,
    ProductQuery,
    ShippingQuery,
    WarehouseQuery,
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