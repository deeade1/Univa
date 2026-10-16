# ecommerce/models/enums/errors.py

"""
Checkout and order error codes.

These are the canonical error codes returned by checkout and order
operations. They are consumed by GraphQL error responses and by
validation code paths.

Historically these lived in `ecommerce.services.checkout.error_codes`,
which coupled `core.exceptions` (loaded globally) to the services
layer. Moving them here breaks that coupling.
"""

from enum import Enum


class CheckoutErrorCode(Enum):
    BILLING_ADDRESS_NOT_SET = "billing_address_not_set"
    CHECKOUT_NOT_FULLY_PAID = "checkout_not_fully_paid"
    GRAPHQL_ERROR = "graphql_error"
    PRODUCT_NOT_PUBLISHED = "product_not_published"
    PRODUCT_UNAVAILABLE_FOR_PURCHASE = "product_unavailable_for_purchase"
    INSUFFICIENT_STOCK = "insufficient_stock"
    INVALID = "invalid"
    INVALID_SHIPPING_METHOD = "invalid_shipping_method"
    NOT_FOUND = "not_found"
    PAYMENT_ERROR = "payment_error"
    QUANTITY_GREATER_THAN_LIMIT = "quantity_greater_than_limit"
    REQUIRED = "required"
    SHIPPING_ADDRESS_NOT_SET = "shipping_address_not_set"
    SHIPPING_METHOD_NOT_APPLICABLE = "shipping_method_not_applicable"
    DELIVERY_METHOD_NOT_APPLICABLE = "delivery_method_not_applicable"
    SHIPPING_METHOD_NOT_SET = "shipping_method_not_set"
    SHIPPING_NOT_REQUIRED = "shipping_not_required"
    TAX_ERROR = "tax_error"
    UNIQUE = "unique"
    VOUCHER_NOT_APPLICABLE = "voucher_not_applicable"
    GIFT_CARD_NOT_APPLICABLE = "gift_card_not_applicable"
    ZERO_QUANTITY = "zero_quantity"
    MISSING_CHANNEL_SLUG = "missing_channel_slug"
    CHANNEL_INACTIVE = "channel_inactive"
    UNAVAILABLE_VARIANT_IN_CHANNEL = "unavailable_variant_in_channel"
    EMAIL_NOT_SET = "email_not_set"
    NO_LINES = "no_lines"
    INACTIVE_PAYMENT = "inactive_payment"
    NON_EDITABLE_GIFT_LINE = "non_editable_gift_line"
    NON_REMOVABLE_GIFT_LINE = "non_removable_gift_line"
    SHIPPING_CHANGE_FORBIDDEN = "shipping_change_forbidden"


class OrderCreateFromCheckoutErrorCode(Enum):
    GRAPHQL_ERROR = "graphql_error"
    CHECKOUT_NOT_FOUND = "checkout_not_found"
    CHANNEL_INACTIVE = "channel_inactive"
    INSUFFICIENT_STOCK = "insufficient_stock"
    VOUCHER_NOT_APPLICABLE = "voucher_not_applicable"
    GIFT_CARD_NOT_APPLICABLE = "gift_card_not_applicable"
    TAX_ERROR = "tax_error"
    SHIPPING_METHOD_NOT_SET = "shipping_method_not_set"
    BILLING_ADDRESS_NOT_SET = "billing_address_not_set"
    SHIPPING_ADDRESS_NOT_SET = "shipping_address_not_set"
    INVALID_SHIPPING_METHOD = "invalid_shipping_method"
    NO_LINES = "no_lines"
    EMAIL_NOT_SET = "email_not_set"
    UNAVAILABLE_VARIANT_IN_CHANNEL = "unavailable_variant_in_channel"


class CheckoutCreateFromOrderErrorCode(Enum):
    GRAPHQL_ERROR = "graphql_error"
    INVALID = "invalid"
    ORDER_NOT_FOUND = "order_not_found"
    CHANNEL_INACTIVE = "channel_inactive"
    TAX_ERROR = "tax_error"


class CheckoutCreateFromOrderUnavailableVariantErrorCode(Enum):
    NOT_FOUND = "not_found"
    PRODUCT_UNAVAILABLE_FOR_PURCHASE = "product_unavailable_for_purchase"
    UNAVAILABLE_VARIANT_IN_CHANNEL = "unavailable_variant_in_channel"
    PRODUCT_NOT_PUBLISHED = "product_not_published"
    QUANTITY_GREATER_THAN_LIMIT = "quantity_greater_than_limit"
    INSUFFICIENT_STOCK = "insufficient_stock"


class OrderErrorCode(Enum):
    """
    Canonical error codes for order mutations.

    These cover lifecycle transitions (cancel, confirm, mark-as-paid),
    fulfillment operations, and general order validation.
    """

    # --- Generic ---
    GRAPHQL_ERROR = "graphql_error"
    INVALID = "invalid"
    REQUIRED = "required"
    UNIQUE = "unique"
    NOT_FOUND = "not_found"

    # --- Lifecycle ---
    NOT_CANCELABLE = "not_cancelable"
    NOT_CONFIRMABLE = "not_confirmable"
    CANNOT_CANCEL_FULFILLMENT = "cannot_cancel_fulfillment"
    CANNOT_CANCEL_ORDER = "cannot_cancel_order"
    CANNOT_DELETE = "cannot_delete"
    CANNOT_FULFILL_UNPAID_ORDER = "cannot_fulfill_unpaid_order"
    CANNOT_MARK_AS_PAID = "cannot_mark_as_paid"
    CANNOT_REFUND = "cannot_refund"
    CANNOT_RETURN = "cannot_return"
    ORDER_ALREADY_PAID = "order_already_paid"
    ORDER_NOT_PAID = "order_not_paid"

    # --- Fulfillment ---
    FULFILLMENT_NOT_POSSIBLE = "fulfillment_not_possible"
    INSUFFICIENT_STOCK = "insufficient_stock"
    INVALID_QUANTITY = "invalid_quantity"
    QUANTITY_GREATER_THAN_AVAILABLE = "quantity_greater_than_available"

    # --- Payment ---
    PAYMENT_ERROR = "payment_error"
    ALREADY_PAID = "already_paid"
    
    NOT_STAFF = "not_staff"
    TRACKING_UPDATE_FAILED = "tracking_update_failed"
    # --- Refund ---
    NOT_REFUNDABLE = "not_refundable"
    REFUND_AMOUNT_INVALID = "refund_amount_invalid"

class ClaimErrorCode(Enum):
    """
    Error codes for checkout claim (guest → user transfer).
    """

    GRAPHQL_ERROR = "graphql_error"
    INVALID = "invalid"
    NOT_FOUND = "not_found"
    ALREADY_CLAIMED = "already_claimed"
    CHANNEL_MISMATCH = "channel_mismatch"
    COMPLETED = "completed"
    LOCKED = "locked"

__all__ = [
    "CheckoutErrorCode",
    "OrderCreateFromCheckoutErrorCode",
    "CheckoutCreateFromOrderErrorCode",
    "CheckoutCreateFromOrderUnavailableVariantErrorCode",
    "OrderErrorCode",
    "ClaimErrorCode"
]