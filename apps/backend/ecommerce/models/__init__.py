# apps/backend/ecommerce/models/__init__.py

# ---------------------------------------------------------------------
# Attribute
# ---------------------------------------------------------------------
from .attribute import (
    AssignedAttribute,
    Attribute,
    AttributeScopeLink,
    AttributeTranslation,
    AttributeValue,
    AttributeValueTranslation,
)

# ---------------------------------------------------------------------
# Channel
# ---------------------------------------------------------------------
from .channel import Channel

# ---------------------------------------------------------------------
# Checkout
# ---------------------------------------------------------------------
from .checkout import (
    Checkout,
    CheckoutLine,
    CheckoutMetadata,
)

# ---------------------------------------------------------------------
# Discount
# ---------------------------------------------------------------------
from .discount import (
    CheckoutDiscount,
    CheckoutLineDiscount,
    OrderDiscount,
    OrderLineDiscount,
    Promotion,
    PromotionEvent,
    PromotionRule,
    PromotionRuleTranslation,
    PromotionRule_Variants,
    PromotionTranslation,
    Voucher,
    VoucherChannelListing,
    VoucherCode,
    VoucherCustomer,
    VoucherTranslation,
)

# Constants — re-exported for convenience
from .constants import (
    AllocationStrategy,
    DiscountType,
    DiscountValueType,
    MarkAsPaidStrategy,
    PromotionEvents,
    PromotionType,
    RewardType,
    RewardValueType,
    TransactionFlowStrategy,
    VoucherType,
)

# ---------------------------------------------------------------------
# Gift card
# ---------------------------------------------------------------------
from .giftcard import (
    GiftCard,
    GiftCardEvent,
    GiftCardTag,
)

# ---------------------------------------------------------------------
# Gotomarket
# ---------------------------------------------------------------------
from .gotomarket import (
    Freshness,
    MarketItemMetadata,
    SourcingType,
)

# ---------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------
from .order import (
    Fulfillment,
    FulfillmentLine,
    Order,
    OrderEvent,
    OrderGrantedRefund,
    OrderGrantedRefundLine,
    OrderLine,
    OrderTrackingEvent,
)

# ---------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------
from .category import (
    Category,
    CategoryTranslation,
)

# ---------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------
from .product import (
    DigitalContent,
    DigitalContentUrl,
    Product,
    ProductChannelListing,
    ProductMedia,
    ProductReview,
    ProductTranslation,
    ProductType,
    ProductVariant,
    ProductVariantChannelListing,
    ProductVariantTranslation,
    VariantChannelListingPromotionRule,
    VariantMedia,
)

# ---------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------
from .collection import (
    Collection,
    CollectionChannelListing,
    CollectionProduct,
    CollectionTranslation,
)

# ---------------------------------------------------------------------
# Shipping
# ---------------------------------------------------------------------
from .shipping import (
    ShippingMethod,
    ShippingMethodChannelListing,
    ShippingMethodTranslation,
    ShippingZone,
)

# ---------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------
# ---------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------
from .inventory import (
    Allocation,
    PreorderAllocation,
    PreorderReservation,
    Reservation,
    Stock,
    StockHistory,
)
# ---------------------------------------------------------------------
# Warehouse
# ---------------------------------------------------------------------
from .warehouse import (
    ChannelWarehouse,
    Warehouse,
)

__all__ = [
    # Attribute
    "AssignedAttribute",
    "Attribute",
    "AttributeScopeLink",
    "AttributeTranslation",
    "AttributeValue",
    "AttributeValueTranslation",
    # Channel
    "Channel",
    # Checkout
    "Checkout",
    "CheckoutLine",
    "CheckoutMetadata",
    # Discount
    "CheckoutDiscount",
    "CheckoutLineDiscount",
    "OrderDiscount",
    "OrderLineDiscount",
    "Promotion",
    "PromotionEvent",
    "PromotionRule",
    "PromotionRuleTranslation",
    "PromotionRule_Variants",
    "PromotionTranslation",
    "Voucher",
    "VoucherChannelListing",
    "VoucherCode",
    "VoucherCustomer",
    "VoucherTranslation",
    # Discount constants
    "AllocationStrategy",
    "DiscountType",
    "DiscountValueType",
    "MarkAsPaidStrategy",
    "PromotionEvents",
    "PromotionType",
    "RewardType",
    "RewardValueType",
    "TransactionFlowStrategy",
    "VoucherType",
    # Gift card
    "GiftCard",
    "GiftCardEvent",
    "GiftCardTag",
    # Gotomarket
    "Freshness",
    "MarketItemMetadata",
    "SourcingType",
    # Order
    "Fulfillment",
    "FulfillmentLine",
    "Order",
    "OrderEvent",
    "OrderGrantedRefund",
    "OrderGrantedRefundLine",
    "OrderLine",
    "OrderTrackingEvent",
    # Category
    "Category",
    "CategoryTranslation",
    # Product
    "DigitalContent",
    "DigitalContentUrl",
    "Product",
    "ProductChannelListing",
    "ProductMedia",
    "ProductReview",
    "ProductTranslation",
    "ProductType",
    "ProductVariant",
    "ProductVariantChannelListing",
    "ProductVariantTranslation",
    "VariantChannelListingPromotionRule",
    "VariantMedia",
    # Collection
    "Collection",
    "CollectionChannelListing",
    "CollectionProduct",
    "CollectionTranslation",
    # Shipping
    "ShippingMethod",
    "ShippingMethodChannelListing",
    "ShippingMethodTranslation",
    "ShippingZone",
    
    # Inventory
    "Allocation",
    "PreorderAllocation",
    "PreorderReservation",
    "Reservation",
    "Stock",
    "StockHistory",
    
    # Warehouse
    "ChannelWarehouse",
    "Warehouse",
]