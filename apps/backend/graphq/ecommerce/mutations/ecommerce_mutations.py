import graphene
from graphq.ecommerce.mutations.attribute import AttributeMutations
from graphq.ecommerce.mutations.category import CategoryMutations
from graphq.ecommerce.mutations.channel import ChannelMutations
from graphq.ecommerce.mutations.checkout import CheckoutMutations
from graphq.ecommerce.mutations.collection import CollectionMutations
from graphq.ecommerce.mutations.discount import DiscountMutations
from graphq.ecommerce.mutations.giftcard import GiftCardMutations
from graphq.ecommerce.mutations.gotomarket import GoToMarketMutations
from graphq.ecommerce.mutations.inventory import InventoryMutations
from graphq.ecommerce.mutations.order import OrderMutations
from graphq.ecommerce.mutations.product import ProductMutations
from graphq.ecommerce.mutations.shipping import ShippingMutations
from graphq.ecommerce.mutations.warehouse import WarehouseMutations


class EcommerceMutations(
    AttributeMutations,
    CategoryMutations,
    ChannelMutations,
    CheckoutMutations,
    CollectionMutations,
    DiscountMutations,
    GiftCardMutations,
    GoToMarketMutations,
    InventoryMutations,
    OrderMutations,
    ProductMutations,
    ShippingMutations,
    WarehouseMutations,
    graphene.ObjectType,
):
    pass
    