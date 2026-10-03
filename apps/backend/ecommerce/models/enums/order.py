# apps/backend/ecommerce/models/enums/order.py
"""Order, fulfillment, and payment-transaction enums."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ecommerce.models.order import FulfillmentLine


# =====================================================================
# ORDER STATUS
# =====================================================================


class OrderStatus:
    DRAFT = "draft"
    UNCONFIRMED = "unconfirmed"
    UNFULFILLED = "unfulfilled"
    PARTIALLY_FULFILLED = "partially_fulfilled"
    FULFILLED = "fulfilled"
    PARTIALLY_RETURNED = "partially_returned"
    RETURNED = "returned"
    CANCELED = "canceled"
    EXPIRED = "expired"

    CHOICES = [
        (DRAFT, "Draft"),
        (UNCONFIRMED, "Unconfirmed"),
        (UNFULFILLED, "Unfulfilled"),
        (PARTIALLY_FULFILLED, "Partially fulfilled"),
        (FULFILLED, "Fulfilled"),
        (PARTIALLY_RETURNED, "Partially returned"),
        (RETURNED, "Returned"),
        (CANCELED, "Canceled"),
        (EXPIRED, "Expired"),
    ]


ORDER_EDITABLE_STATUS = (OrderStatus.DRAFT, OrderStatus.UNCONFIRMED)


class OrderOrigin:
    CHECKOUT = "checkout"
    DRAFT = "draft"
    REISSUE = "reissue"
    BULK_CREATE = "bulk_create"

    CHOICES = [
        (CHECKOUT, "Checkout"),
        (DRAFT, "Draft"),
        (REISSUE, "Reissue"),
        (BULK_CREATE, "Bulk create"),
    ]


class FulfillmentStatus:
    FULFILLED = "fulfilled"
    REFUNDED = "refunded"
    RETURNED = "returned"
    REFUNDED_AND_RETURNED = "refunded_and_returned"
    REPLACED = "replaced"
    CANCELED = "canceled"
    WAITING_FOR_APPROVAL = "waiting_for_approval"

    CHOICES = [
        (FULFILLED, "Fulfilled"),
        (REFUNDED, "Refunded"),
        (RETURNED, "Returned"),
        (REPLACED, "Replaced"),
        (REFUNDED_AND_RETURNED, "Refunded and returned"),
        (CANCELED, "Canceled"),
        (WAITING_FOR_APPROVAL, "Waiting for approval"),
    ]


# =====================================================================
# ORDER EVENTS
# =====================================================================


class OrderEvents:
    CONFIRMED = "confirmed"
    DRAFT_CREATED = "draft_created"
    DRAFT_CREATED_FROM_REPLACE = "draft_created_from_replace"
    ADDED_PRODUCTS = "added_products"
    REMOVED_PRODUCTS = "removed_products"
    PLACED = "placed"
    PLACED_FROM_DRAFT = "placed_from_draft"
    OVERSOLD_ITEMS = "oversold_items"
    CANCELED = "canceled"
    EXPIRED = "expired"
    ORDER_MARKED_AS_PAID = "order_marked_as_paid"
    ORDER_FULLY_PAID = "order_fully_paid"
    ORDER_REPLACEMENT_CREATED = "order_replacement_created"
    ORDER_DISCOUNT_ADDED = "order_discount_added"
    ORDER_DISCOUNT_AUTOMATICALLY_UPDATED = "order_discount_automatically_updated"
    ORDER_DISCOUNT_UPDATED = "order_discount_updated"
    ORDER_DISCOUNT_DELETED = "order_discount_deleted"
    ORDER_LINE_DISCOUNT_UPDATED = "order_line_discount_updated"
    ORDER_LINE_DISCOUNT_REMOVED = "order_line_discount_removed"
    ORDER_LINE_PRODUCT_DELETED = "order_line_product_deleted"
    ORDER_LINE_VARIANT_DELETED = "order_line_variant_deleted"
    UPDATED_ADDRESS = "updated_address"
    EMAIL_SENT = "email_sent"
    PAYMENT_AUTHORIZED = "payment_authorized"
    PAYMENT_CAPTURED = "payment_captured"
    PAYMENT_REFUNDED = "payment_refunded"
    PAYMENT_VOIDED = "payment_voided"
    PAYMENT_FAILED = "payment_failed"
    TRANSACTION_EVENT = "transaction_event"
    TRANSACTION_CHARGE_REQUESTED = "transaction_charge_requested"
    TRANSACTION_REFUND_REQUESTED = "transaction_refund_requested"
    TRANSACTION_CANCEL_REQUESTED = "transaction_cancel_requested"
    TRANSACTION_MARK_AS_PAID_FAILED = "transaction_mark_as_paid_failed"
    EXTERNAL_SERVICE_NOTIFICATION = "external_service_notification"
    INVOICE_REQUESTED = "invoice_requested"
    INVOICE_GENERATED = "invoice_generated"
    INVOICE_UPDATED = "invoice_updated"
    INVOICE_SENT = "invoice_sent"
    FULFILLMENT_CANCELED = "fulfillment_canceled"
    FULFILLMENT_RESTOCKED_ITEMS = "fulfillment_restocked_items"
    FULFILLMENT_FULFILLED_ITEMS = "fulfillment_fulfilled_items"
    FULFILLMENT_REFUNDED = "fulfillment_refunded"
    FULFILLMENT_RETURNED = "fulfillment_returned"
    FULFILLMENT_REPLACED = "fulfillment_replaced"
    FULFILLMENT_AWAITS_APPROVAL = "fulfillment_awaits_approval"
    TRACKING_UPDATED = "tracking_updated"
    NOTE_ADDED = "note_added"
    NOTE_UPDATED = "note_updated"
    OTHER = "other"

    CHOICES = [
        (DRAFT_CREATED, "The draft order was created"),
        (DRAFT_CREATED_FROM_REPLACE, "The draft order with replace lines was created"),
        (ADDED_PRODUCTS, "Some products were added to the order"),
        (REMOVED_PRODUCTS, "Some products were removed from the order"),
        (PLACED, "The order was placed"),
        (PLACED_FROM_DRAFT, "The draft order was placed"),
        (OVERSOLD_ITEMS, "The draft order was placed with oversold items"),
        (CANCELED, "The order was canceled"),
        (EXPIRED, "The order was automatically expired"),
        (ORDER_MARKED_AS_PAID, "The order was manually marked as fully paid"),
        (ORDER_FULLY_PAID, "The order was fully paid"),
        (ORDER_REPLACEMENT_CREATED, "The draft order was created based on this order."),
        (ORDER_DISCOUNT_ADDED, "New order discount applied to this order."),
        (
            ORDER_DISCOUNT_AUTOMATICALLY_UPDATED,
            "Order discount was automatically updated after the changes in order.",
        ),
        (ORDER_DISCOUNT_UPDATED, "Order discount was updated for this order."),
        (ORDER_DISCOUNT_DELETED, "Order discount was deleted for this order."),
        (ORDER_LINE_DISCOUNT_UPDATED, "Order line was discounted."),
        (ORDER_LINE_DISCOUNT_REMOVED, "The discount for order line was removed."),
        (ORDER_LINE_PRODUCT_DELETED, "The order line product was removed."),
        (ORDER_LINE_VARIANT_DELETED, "The order line product variant was removed."),
        (UPDATED_ADDRESS, "The address from the placed order was updated"),
        (EMAIL_SENT, "The email was sent"),
        (CONFIRMED, "Order was confirmed"),
        (PAYMENT_AUTHORIZED, "The payment was authorized"),
        (PAYMENT_CAPTURED, "The payment was captured"),
        (EXTERNAL_SERVICE_NOTIFICATION, "Notification from external service"),
        (PAYMENT_REFUNDED, "The payment was refunded"),
        (PAYMENT_VOIDED, "The payment was voided"),
        (PAYMENT_FAILED, "The payment was failed"),
        (TRANSACTION_EVENT, "The transaction event"),
        (TRANSACTION_CHARGE_REQUESTED, "The charge requested for transaction"),
        (TRANSACTION_REFUND_REQUESTED, "The refund requested for transaction"),
        (TRANSACTION_CANCEL_REQUESTED, "The cancel requested for transaction"),
        (TRANSACTION_MARK_AS_PAID_FAILED, "The mark as paid failed for transaction"),
        (INVOICE_REQUESTED, "An invoice was requested"),
        (INVOICE_GENERATED, "An invoice was generated"),
        (INVOICE_UPDATED, "An invoice was updated"),
        (INVOICE_SENT, "An invoice was sent"),
        (FULFILLMENT_CANCELED, "A fulfillment was canceled"),
        (FULFILLMENT_RESTOCKED_ITEMS, "The items of the fulfillment were restocked"),
        (FULFILLMENT_FULFILLED_ITEMS, "Some items were fulfilled"),
        (FULFILLMENT_REFUNDED, "Some items were refunded"),
        (FULFILLMENT_RETURNED, "Some items were returned"),
        (FULFILLMENT_REPLACED, "Some items were replaced"),
        (FULFILLMENT_AWAITS_APPROVAL, "Fulfillments awaits approval"),
        (TRACKING_UPDATED, "The fulfillment's tracking code was updated"),
        (NOTE_ADDED, "A note was added to the order"),
        (NOTE_UPDATED, "A note was updated in the order"),
        (OTHER, "An unknown order event containing a message"),
    ]


class OrderEventsEmails:
    CONFIRMED = "confirmed"
    PAYMENT = "payment_confirmation"
    SHIPPING = "shipping_confirmation"
    TRACKING_UPDATED = "tracking_updated"
    ORDER_CONFIRMATION = "order_confirmation"
    ORDER_CANCEL = "order_cancel"
    ORDER_REFUND = "order_refund"
    FULFILLMENT = "fulfillment_confirmation"
    DIGITAL_LINKS = "digital_links"

    CHOICES = [
        (PAYMENT, "The payment confirmation email was sent"),
        (CONFIRMED, "The order confirmed email was sent"),
        (SHIPPING, "The shipping confirmation email was sent"),
        (TRACKING_UPDATED, "The fulfillment tracking code email was sent"),
        (ORDER_CONFIRMATION, "The order placement confirmation email was sent"),
        (ORDER_CANCEL, "The order cancel confirmation email was sent"),
        (ORDER_REFUND, "The order refund confirmation email was sent"),
        (FULFILLMENT, "The fulfillment confirmation email was sent"),
        (DIGITAL_LINKS, "The email containing the digital links was sent"),
    ]


class OrderAuthorizeStatus:
    NONE = "none"
    PARTIAL = "partial"
    FULL = "full"

    CHOICES = [
        (NONE, "The funds are not authorized"),
        (PARTIAL, "The funds that are authorized and charged don't cover fully the order's total"),
        (FULL, "The funds that are authorized and charged fully cover the order's total"),
    ]


class OrderChargeStatus:
    NONE = "none"
    PARTIAL = "partial"
    FULL = "full"
    OVERCHARGED = "overcharged"

    CHOICES = [
        (NONE, "The order is not charged."),
        (PARTIAL, "The order is partially charged"),
        (FULL, "The order is fully charged"),
        (OVERCHARGED, "The order is overcharged"),
    ]


class OrderGrantedRefundStatus:
    NONE = "none"
    PENDING = "pending"
    SUCCESS = "success"
    FAILURE = "failure"

    CHOICES = [
        (NONE, "The refund on related transactionItem is not processed"),
        (PENDING, "The refund on related transactionItem is pending"),
        (SUCCESS, "The refund on related transactionItem is successfully processed"),
        (FAILURE, "The refund on related transactionItem failed"),
    ]


class StockUpdatePolicy:
    SKIP = "skip"
    UPDATE = "update"
    FORCE = "force"

    CHOICES = [
        (SKIP, "Stocks are not checked and not updated."),
        (UPDATE, "Only do update, if there is enough stocks."),
        (FORCE, "Force update, if there is not enough stocks."),
    ]


# =====================================================================
# ORDER DATACLASSES
# =====================================================================


@dataclass
class FulfillmentLineData:
    """
    Payload for fulfillment operations.

    `quantity` is Decimal (not int) so that weighted market items
    (e.g. 2.5 kg of beef) can be fulfilled correctly.
    """
    line: "FulfillmentLine"
    quantity: Decimal
    replace: bool = False