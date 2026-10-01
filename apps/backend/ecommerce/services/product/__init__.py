# apps/backend/ecommerce/services/product/__init__.py
from .error_codes import ProductErrorCode
from .product_images import (
    handle_product_images,
    upload_product_image,
    delete_product_image,
)
from .search import (
    search_products,
    filter_products,
    sort_products,
)
from .utils.availability import (
    check_product_availability,
    get_available_quantity,
    is_product_available,
)
from .utils.costs import (
    calculate_product_cost,
    get_product_margin,
    get_product_profit,
)
from .utils.digital_products import (
    validate_digital_product,
    generate_download_link,
    handle_digital_delivery,
)
from .utils.product import (
    create_product,
    update_product,
    delete_product,
    get_product_by_slug,
)
from .utils.variants import (
    create_variant,
    update_variant,
    delete_variant,
    get_variant_by_sku,
)
from .utils.variant_prices import (
    calculate_variant_price,
    update_variant_prices,
    get_variant_discount_price,
)

__all__ = [
    'ProductErrorCode',
    'handle_product_images',
    'upload_product_image',
    'delete_product_image',
    'search_products',
    'filter_products',
    'sort_products',
    'check_product_availability',
    'get_available_quantity',
    'is_product_available',
    'calculate_product_cost',
    'get_product_margin',
    'get_product_profit',
    'validate_digital_product',
    'generate_download_link',
    'handle_digital_delivery',
    'create_product',
    'update_product',
    'delete_product',
    'get_product_by_slug',
    'create_variant',
    'update_variant',
    'delete_variant',
    'get_variant_by_sku',
    'calculate_variant_price',
    'update_variant_prices',
    'get_variant_discount_price',
]

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

    CHOICES = [
        (NORMAL, "A standard product type."),
        (GIFT_CARD, "A gift card product type."),
    ]
