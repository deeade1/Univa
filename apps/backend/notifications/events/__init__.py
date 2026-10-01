# apps/backend/notifications/events/__init__.py

"""
Public API for the Univa notification event subsystem.

Domain applications should normally use:

    from notifications.events import emit_notification_event

The package exposes:

    1. Event constants
       Canonical notification event identifiers.

    2. Event emitter
       Creates NotificationEvent records and optionally queues them.

    3. Event registry
       Defines metadata and presentation behavior for registered events.

Event processing itself belongs to:

    notifications.events.processor

Celery orchestration belongs to:

    notifications.tasks.event_tasks
"""

# ============================================================================
# EVENT CONSTANTS
# ============================================================================

from .constants import *


# ============================================================================
# EVENT EMITTER
# ============================================================================

from .emitter import (
    NotificationEventError,
    create_notification_event,
    emit_and_queue_notification_event,
    emit_notification_event,
    queue_event_by_id,
)


# ============================================================================
# EVENT REGISTRY
# ============================================================================

from .registry import (
    EVENT_REGISTRY,
    EventDefinition,
    get_event_action_url,
    get_event_category,
    get_event_channels,
    get_event_definition,
    get_event_priority,
    is_registered_event,
    registered_event_types,
    validate_event_registry,
)


# ============================================================================
# PUBLIC API
# ============================================================================

__all__ = [
    # ------------------------------------------------------------------------
    # Event constants
    # ------------------------------------------------------------------------

    "ALL_EVENT_TYPES",

    # Account
    "ACCOUNT_CREATED",
    "ACCOUNT_VERIFIED",
    "ACCOUNT_LOGIN",
    "ACCOUNT_PASSWORD_CHANGED",
    "ACCOUNT_PASSWORD_RESET",

    # Order
    "ORDER_CREATED",
    "ORDER_CONFIRMED",
    "ORDER_PROCESSING",
    "ORDER_SHIPPED",
    "ORDER_DELIVERED",
    "ORDER_CANCELLED",
    "ORDER_REFUNDED",

    # Payment
    "PAYMENT_INITIATED",
    "PAYMENT_SUCCESSFUL",
    "PAYMENT_FAILED",
    "PAYMENT_REFUNDED",

    # Banking
    "BANK_TRANSFER_INITIATED",
    "BANK_TRANSFER_SUCCESSFUL",
    "BANK_TRANSFER_FAILED",
    "WALLET_CREDITED",
    "WALLET_DEBITED",
    "BILL_PAYMENT_SUCCESSFUL",
    "BILL_PAYMENT_FAILED",
    "AIRTIME_PURCHASE_SUCCESSFUL",
    "AIRTIME_PURCHASE_FAILED",

    # Transport
    "RIDE_REQUESTED",
    "RIDE_ACCEPTED",
    "RIDE_DRIVER_ARRIVED",
    "RIDE_STARTED",
    "RIDE_COMPLETED",
    "RIDE_CANCELLED",
    "DELIVERY_REQUESTED",
    "DELIVERY_ASSIGNED",
    "DELIVERY_PICKED_UP",
    "DELIVERY_IN_TRANSIT",
    "DELIVERY_DELIVERED",
    "DELIVERY_CANCELLED",

    # Chat
    "MESSAGE_RECEIVED",
    "MESSAGE_REACTION",
    "CHAT_REQUEST_RECEIVED",

    # Social
    "SOCIAL_FOLLOW",
    "SOCIAL_LIKE",
    "SOCIAL_COMMENT",
    "SOCIAL_MENTION",

    # Real estate
    "PROPERTY_CREATED",
    "PROPERTY_UPDATED",
    "PROPERTY_SAVED",
    "OFFER_RECEIVED",
    "OFFER_ACCEPTED",
    "OFFER_REJECTED",

    # E-commerce
    "PRODUCT_BACK_IN_STOCK",
    "PRICE_CHANGED",
    "WISHLIST_PRICE_DROP",

    # System
    "SYSTEM_ANNOUNCEMENT",
    "SYSTEM_MAINTENANCE",

    # ------------------------------------------------------------------------
    # Event emitter
    # ------------------------------------------------------------------------

    "NotificationEventError",
    "emit_notification_event",
    "emit_and_queue_notification_event",
    "create_notification_event",
    "queue_event_by_id",

    # ------------------------------------------------------------------------
    # Event registry
    # ------------------------------------------------------------------------

    "EVENT_REGISTRY",
    "EventDefinition",
    "get_event_action_url",
    "get_event_category",
    "get_event_channels",
    "get_event_definition",
    "get_event_priority",
    "is_registered_event",
    "registered_event_types",
    "validate_event_registry",
]