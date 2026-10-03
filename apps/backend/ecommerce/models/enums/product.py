# apps/backend/ecommerce/models/enums/product.py
"""Product enums."""

# QuantityUnit lives in core.pricing.quantity_unit and is re-exported
# here so that `from ecommerce.models.constants import QuantityUnit`
# keeps working during the refactor.
from core.pricing.quantity_unit import QuantityUnit  # noqa: F401


class ProductMediaTypes:
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"

    CHOICES = [
        (IMAGE, "An uploaded image or an URL to an image"),
        (VIDEO, "A URL to an external video"),
    ]


class ProductTypeKind:
    NORMAL = "normal"
    GIFT_CARD = "gift_card"
    MARKET_ITEM = "market_item"

    CHOICES = [
        (NORMAL, "A standard product type."),
        (GIFT_CARD, "A gift card product type."),
        (MARKET_ITEM, "A Nigerian local-market product type."),
    ]