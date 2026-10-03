# apps/backend/ecommerce/models/enums/__init__.py

"""
Canonical location for ecommerce enums.

Everything that used to live in `ecommerce.models.constants` is
importable from here. `ecommerce.models.constants` is now a thin
shim that re-exports this package.

New code should import from `ecommerce.models.enums`.

Grouped by domain:
    - discount
    - channel
    - checkout
    - order
    - shipping
    - giftcard
    - product
    - warehouse
    - attribute
"""

from .attribute import (  # noqa: F401
    AttributeDataType,
    AttributeEntityType,
    AttributeInputType,
    AttributeReferenceType,
    AttributeScope,
    AttributeType,
    AttributeWidget,
)
from .channel import (  # noqa: F401
    AllocationStrategy,
    MarkAsPaidStrategy,
    TransactionFlowStrategy,
)
from .checkout import (  # noqa: F401
    CheckoutAuthorizeStatus,
    CheckoutChargeStatus,
)
from .discount import (  # noqa: F401
    DiscountType,
    DiscountValueType,
    PromotionEvents,
    PromotionRuleInfo,
    PromotionType,
    RewardType,
    RewardValueType,
    VoucherType,
)
from .giftcard import (  # noqa: F401
    GiftCardEvents,
    GiftCardStatus,
)
from .order import (  # noqa: F401
    ORDER_EDITABLE_STATUS,
    FulfillmentLineData,
    FulfillmentStatus,
    OrderAuthorizeStatus,
    OrderChargeStatus,
    OrderEvents,
    OrderEventsEmails,
    OrderGrantedRefundStatus,
    OrderOrigin,
    OrderStatus,
    StockUpdatePolicy,
)
from .product import (  # noqa: F401
    ProductMediaTypes,
    ProductTypeKind,
    QuantityUnit,
)
from .shipping import (  # noqa: F401
    PostalCodeRuleInclusionType,
    ShippingMethodStatus,
    ShippingMethodType,
)
from .warehouse import (  # noqa: F401
    WarehouseClickAndCollectOption,
)


__all__ = [
    # attribute
    "AttributeType",
    "AttributeInputType",
    "AttributeEntityType",
    "AttributeScope",
    "AttributeDataType",
    "AttributeWidget",
    "AttributeReferenceType",
    # channel
    "AllocationStrategy",
    "MarkAsPaidStrategy",
    "TransactionFlowStrategy",
    # checkout
    "CheckoutAuthorizeStatus",
    "CheckoutChargeStatus",
    # discount
    "VoucherType",
    "DiscountValueType",
    "DiscountType",
    "PromotionType",
    "RewardType",
    "RewardValueType",
    "PromotionEvents",
    "PromotionRuleInfo",
    # giftcard
    "GiftCardEvents",
    "GiftCardStatus",
    # order
    "OrderStatus",
    "ORDER_EDITABLE_STATUS",
    "OrderOrigin",
    "FulfillmentStatus",
    "OrderEvents",
    "OrderEventsEmails",
    "OrderAuthorizeStatus",
    "OrderChargeStatus",
    "OrderGrantedRefundStatus",
    "StockUpdatePolicy",
    "FulfillmentLineData",
    # product
    "ProductMediaTypes",
    "ProductTypeKind",
    "QuantityUnit",
    # shipping
    "ShippingMethodType",
    "PostalCodeRuleInclusionType",
    "ShippingMethodStatus",
    # warehouse
    "WarehouseClickAndCollectOption",
]