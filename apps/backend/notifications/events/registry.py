# apps/backend/notifications/events/registry.py

"""
Notification event registry for Univa.

The registry is the presentation/configuration layer for notification
events.

Architecture:

    Domain Application
            │
            ▼
    NotificationEvent
            │
            ▼
    EventDefinition
            │
            ▼
    Notification Service
            │
            ├── UserNotification
            │
            └── NotificationPush
                    │
                    ▼
                  Celery

Responsibilities
----------------
This module ONLY describes how registered notification events should
appear to users.

It does NOT:

    - create database records
    - resolve recipients
    - call Celery
    - send push notifications
    - access notification preferences
    - import notification services
    - contain provider-specific logic

Domain applications should emit registered event types through:

    notifications.events.emitter.emit_notification_event()

Example:

    emit_notification_event(
        event_type=constants.ORDER_CREATED,
        module="order",
        actor=user,
        object_type="Order",
        object_id=order.pk,
        payload={
            "recipient_id": user.pk,
        },
    )
"""

from __future__ import annotations

from dataclasses import dataclass

from . import constants


# ============================================================================
# VALIDATION CONSTANTS
# ============================================================================

VALID_CHANNELS: frozenset[str] = frozenset(
    {
        "in_app",
        "push",
        "email",
        "sms",
    }
)

VALID_PRIORITIES: frozenset[str] = frozenset(
    {
        "low",
        "normal",
        "high",
        "urgent",
    }
)


# ============================================================================
# EVENT DEFINITION
# ============================================================================


@dataclass(frozen=True, slots=True)
class EventDefinition:
    """
    Defines how a NotificationEvent is presented to a user.

    Attributes
    ----------
    event_type:
        Canonical notification event identifier.

    title:
        Default notification title.

    body:
        Default notification body.

    category:
        Notification preference category.

    channels:
        Preferred notification channels.

        Supported channels:

            in_app
            push
            email
            sms

    priority:
        Notification priority.

    action_url:
        Optional application route.

        Supported placeholders:

            {object_id}
            {event_id}
    """

    event_type: str
    title: str
    body: str
    category: str
    channels: tuple[str, ...] = ("in_app", "push")
    priority: str = "normal"
    action_url: str | None = None


# ============================================================================
# EVENT REGISTRY
# ============================================================================

EVENT_REGISTRY: dict[str, EventDefinition] = {}


def _register(
    event_type: str,
    *,
    title: str,
    body: str,
    category: str,
    channels: tuple[str, ...] = ("in_app", "push"),
    priority: str = "normal",
    action_url: str | None = None,
) -> None:
    """
    Register one notification event definition.

    Registration is centralized so every event follows the same
    configuration rules.
    """

    event_type = str(event_type).strip()
    title = str(title).strip()
    body = str(body).strip()
    category = str(category).strip().lower()
    priority = str(priority).strip().lower()

    if not event_type:
        raise ValueError(
            "Notification event type cannot be empty."
        )

    if event_type not in constants.ALL_EVENT_TYPES:
        raise ValueError(
            "Attempted to register an unknown notification event: "
            f"{event_type!r}"
        )

    if event_type in EVENT_REGISTRY:
        raise ValueError(
            "Duplicate notification event registration: "
            f"{event_type}"
        )

    if not title:
        raise ValueError(
            f"Notification event {event_type!r} has an empty title."
        )

    if not body:
        raise ValueError(
            f"Notification event {event_type!r} has an empty body."
        )

    if not category:
        raise ValueError(
            f"Notification event {event_type!r} has an empty category."
        )

    if priority not in VALID_PRIORITIES:
        raise ValueError(
            f"Notification event {event_type!r} has invalid "
            f"priority: {priority!r}"
        )

    normalized_channels = tuple(
        str(channel).strip().lower()
        for channel in channels
        if str(channel).strip()
    )

    if not normalized_channels:
        raise ValueError(
            f"Notification event {event_type!r} must define "
            "at least one channel."
        )

    invalid_channels = (
        set(normalized_channels) - VALID_CHANNELS
    )

    if invalid_channels:
        raise ValueError(
            f"Notification event {event_type!r} contains unsupported "
            f"channels: {sorted(invalid_channels)}"
        )

    if len(normalized_channels) != len(set(normalized_channels)):
        raise ValueError(
            f"Notification event {event_type!r} contains duplicate "
            "notification channels."
        )

    if action_url is not None:
        action_url = str(action_url).strip() or None

    EVENT_REGISTRY[event_type] = EventDefinition(
        event_type=event_type,
        title=title,
        body=body,
        category=category,
        channels=normalized_channels,
        priority=priority,
        action_url=action_url,
    )


# ============================================================================
# ACCOUNT
# ============================================================================

_register(
    constants.ACCOUNT_CREATED,
    title="Account created",
    body="Your Univa account has been created successfully.",
    category="account",
    action_url="/account/profile",
)

_register(
    constants.ACCOUNT_VERIFIED,
    title="Account verified",
    body="Your account has been successfully verified.",
    category="account",
    priority="high",
    action_url="/account/profile",
)

_register(
    constants.ACCOUNT_LOGIN,
    title="New login",
    body="Your Univa account was accessed.",
    category="account",
    action_url="/account/security",
)

_register(
    constants.ACCOUNT_PASSWORD_CHANGED,
    title="Password changed",
    body="Your account password has been changed.",
    category="account",
    priority="high",
    action_url="/account/security",
)

_register(
    constants.ACCOUNT_PASSWORD_RESET,
    title="Password reset",
    body="Your account password has been reset.",
    category="account",
    priority="high",
    action_url="/account/security",
)

_register(
    constants.ACCOUNT_MAGIC_LINK_REQUESTED,
    title="Magic link requested",
    body="You requested a magic link to sign in to your Univa account.",
    category="account",
    action_url="/account/magic-link",
)

_register(
    constants.ACCOUNT_MAGIC_LINK_SENT,
    title="Magic link sent",
    body="A magic link has been sent to your email address. Check your inbox to sign in.",
    category="account",
    priority="high",
    action_url="/account/magic-link",
)

_register(
    constants.ACCOUNT_MAGIC_LINK_FAILED,
    title="Magic link failed",
    body="Your magic link sign-in attempt was unsuccessful. Please request a new link.",
    category="account",
    priority="high",
    action_url="/account/magic-link",
)

# ============================================================================
# ORDER
# ============================================================================

_register(
    constants.ORDER_CREATED,
    title="Order received",
    body="Your order has been received.",
    category="order",
    channels=("in_app", "push", "email"),
    action_url="/orders/{object_id}",
)

_register(
    constants.ORDER_CONFIRMED,
    title="Order confirmed",
    body="Your order has been confirmed.",
    category="order",
    channels=("in_app", "push", "email"),
    action_url="/orders/{object_id}",
)

_register(
    constants.ORDER_PROCESSING,
    title="Order processing",
    body="Your order is now being processed.",
    category="order",
    action_url="/orders/{object_id}",
)

_register(
    constants.ORDER_SHIPPED,
    title="Order shipped",
    body="Your order has been shipped.",
    category="order",
    action_url="/orders/{object_id}",
)

_register(
    constants.ORDER_DELIVERED,
    title="Order delivered",
    body="Your order has been delivered.",
    category="order",
    channels=("in_app", "push", "email"),
    action_url="/orders/{object_id}",
)

_register(
    constants.ORDER_CANCELLED,
    title="Order cancelled",
    body="Your order has been cancelled.",
    category="order",
    priority="high",
    channels=("in_app", "push", "email"),
    action_url="/orders/{object_id}",
)

_register(
    constants.ORDER_REFUNDED,
    title="Order refunded",
    body="Your order has been refunded.",
    category="order",
    priority="high",
    channels=("in_app", "push", "email"),
    action_url="/orders/{object_id}",
)


# ============================================================================
# PAYMENT
# ============================================================================

_register(
    constants.PAYMENT_INITIATED,
    title="Payment initiated",
    body="Your payment has been initiated.",
    category="payment",
    action_url="/payments/{object_id}",
)

_register(
    constants.PAYMENT_SUCCESSFUL,
    title="Payment successful",
    body="Your payment was successful.",
    category="payment",
    priority="high",
    channels=("in_app", "push", "email"),
    action_url="/payments/{object_id}",
)

_register(
    constants.PAYMENT_FAILED,
    title="Payment failed",
    body="Your payment could not be completed.",
    category="payment",
    priority="high",
    channels=("in_app", "push", "email"),
    action_url="/payments/{object_id}",
)

_register(
    constants.PAYMENT_REFUNDED,
    title="Payment refunded",
    body="Your payment has been refunded.",
    category="payment",
    priority="high",
    action_url="/payments/{object_id}",
)


# ============================================================================
# BANKING
# ============================================================================

_register(
    constants.BANK_TRANSFER_INITIATED,
    title="Transfer initiated",
    body="Your bank transfer has been initiated.",
    category="banking",
    action_url="/banking/transfers/{object_id}",
)

_register(
    constants.BANK_TRANSFER_SUCCESSFUL,
    title="Transfer successful",
    body="Your bank transfer was successful.",
    category="banking",
    priority="high",
    action_url="/banking/transfers/{object_id}",
)

_register(
    constants.BANK_TRANSFER_FAILED,
    title="Transfer failed",
    body="Your bank transfer could not be completed.",
    category="banking",
    priority="high",
    action_url="/banking/transfers/{object_id}",
)

_register(
    constants.WALLET_CREDITED,
    title="Wallet credited",
    body="Your wallet has been credited.",
    category="banking",
    priority="high",
    action_url="/banking/wallet",
)

_register(
    constants.WALLET_DEBITED,
    title="Wallet debited",
    body="Your wallet has been debited.",
    category="banking",
    priority="high",
    action_url="/banking/wallet",
)

_register(
    constants.BILL_PAYMENT_SUCCESSFUL,
    title="Bill payment successful",
    body="Your bill payment was successful.",
    category="banking",
    priority="high",
    action_url="/banking/bills/{object_id}",
)

_register(
    constants.BILL_PAYMENT_FAILED,
    title="Bill payment failed",
    body="Your bill payment could not be completed.",
    category="banking",
    priority="high",
    action_url="/banking/bills/{object_id}",
)

_register(
    constants.AIRTIME_PURCHASE_SUCCESSFUL,
    title="Airtime purchase successful",
    body="Your airtime purchase was successful.",
    category="banking",
    priority="high",
    action_url="/banking/airtime/{object_id}",
)

_register(
    constants.AIRTIME_PURCHASE_FAILED,
    title="Airtime purchase failed",
    body="Your airtime purchase could not be completed.",
    category="banking",
    priority="high",
    action_url="/banking/airtime/{object_id}",
)
_register(
    constants.DATA_BUNDLE_PURCHASE_SUCCESSFUL,
    title="Data bundle purchase successful",
    body="Your data bundle purchase was successful.",
    category="banking",
    priority="high",
    action_url="/banking/data/{object_id}",
)

_register(
    constants.DATA_BUNDLE_PURCHASE_FAILED,
    title="Data bundle purchase failed",
    body="Your data bundle purchase could not be completed.",
    category="banking",
    priority="high",
    action_url="/banking/data/{object_id}",
)
_register(
    constants.BANK_TRANSFER_RECEIVED,
    title="Money received",
    body="You have received a bank transfer.",
    category="banking",
    priority="high",
    action_url="/banking/transfers/{object_id}",
)

_register(
    constants.BANK_WALLET_CREATED,
    title="Wallet created",
    body="Your Univa wallet is ready.",
    category="banking",
    action_url="/banking/wallet",
)

_register(
    constants.BANK_WALLET_CLOSED,
    title="Wallet closed",
    body="Your Univa wallet has been closed.",
    category="banking",
    priority="high",
    action_url="/banking/wallet",
)

_register(
    constants.BANK_WALLET_SUSPENDED,
    title="Wallet suspended",
    body="Your Univa wallet has been temporarily suspended.",
    category="banking",
    priority="high",
    action_url="/banking/wallet",
)

_register(
    constants.BANK_WALLET_DAILY_LIMIT_REACHED,
    title="Daily limit reached",
    body="You have reached your daily transaction limit.",
    category="banking",
    priority="high",
    action_url="/banking/wallet",
)

_register(
    constants.BANK_EXTERNAL_TRANSFER_INITIATED,
    title="Transfer initiated",
    body="Your external transfer is being processed.",
    category="banking",
    action_url="/banking/transfers/{object_id}",
)

_register(
    constants.BANK_EXTERNAL_TRANSFER_FAILED,
    title="External transfer failed",
    body="Your external transfer could not be completed.",
    category="banking",
    priority="high",
    action_url="/banking/transfers/{object_id}",
)

_register(
    constants.BANK_KYC_SUBMITTED,
    title="KYC submitted",
    body="Your KYC document has been submitted for review.",
    category="banking",
    action_url="/banking/kyc",
)

_register(
    constants.BANK_KYC_VERIFIED,
    title="KYC verified",
    body="Your KYC has been verified.",
    category="banking",
    priority="high",
    action_url="/banking/kyc",
)

_register(
    constants.BANK_KYC_REJECTED,
    title="KYC rejected",
    body="Your KYC document was rejected. Please review and resubmit.",
    category="banking",
    priority="high",
    action_url="/banking/kyc",
)

_register(
    constants.BANK_DISPUTE_OPENED,
    title="Dispute opened",
    body="Your transaction dispute has been opened.",
    category="banking",
    action_url="/banking/disputes/{object_id}",
)

_register(
    constants.BANK_DISPUTE_RESOLVED,
    title="Dispute resolved",
    body="Your transaction dispute has been resolved.",
    category="banking",
    priority="high",
    action_url="/banking/disputes/{object_id}",
)

_register(
    constants.BANK_CARD_ISSUED,
    title="Card issued",
    body="Your new card has been issued.",
    category="banking",
    action_url="/banking/cards/{object_id}",
)

_register(
    constants.BANK_CARD_AUTHORIZED,
    title="Card authorization",
    body="A card transaction has been authorized.",
    category="banking",
    action_url="/banking/cards/{object_id}",
)

_register(
    constants.BANK_CARD_SETTLED,
    title="Card transaction settled",
    body="A card transaction has been settled.",
    category="banking",
    action_url="/banking/cards/{object_id}",
)

_register(
    constants.BANK_CARD_DECLINED,
    title="Card transaction declined",
    body="A card transaction was declined.",
    category="banking",
    priority="high",
    action_url="/banking/cards/{object_id}",
)

_register(
    constants.BANK_CARD_BLOCKED,
    title="Card blocked",
    body="Your card has been blocked.",
    category="banking",
    priority="high",
    action_url="/banking/cards/{object_id}",
)

_register(
    constants.BANK_QR_PAYMENT_SUCCESSFUL,
    title="QR payment successful",
    body="Your QR payment was successful.",
    category="banking",
    priority="high",
    action_url="/banking/qr/{object_id}",
)

_register(
    constants.BANK_QR_PAYMENT_FAILED,
    title="QR payment failed",
    body="Your QR payment could not be completed.",
    category="banking",
    priority="high",
    action_url="/banking/qr/{object_id}",
)

# ----------------------------------------------------------------------------
# BANKING — SAVINGS
# ----------------------------------------------------------------------------

_register(
    constants.BANK_SAVINGS_GOAL_CREATED,
    title="Savings goal created",
    body="Your savings goal has been created.",
    category="banking",
    action_url="/banking/savings/{object_id}",
)

_register(
    constants.BANK_SAVINGS_DEPOSIT,
    title="Savings deposit",
    body="You added money to your savings goal.",
    category="banking",
    action_url="/banking/savings/{object_id}",
)

_register(
    constants.BANK_SAVINGS_WITHDRAWAL,
    title="Savings withdrawal",
    body="You withdrew money from your savings goal.",
    category="banking",
    action_url="/banking/savings/{object_id}",
)

_register(
    constants.BANK_SAVINGS_GOAL_COMPLETED,
    title="Savings goal completed",
    body="Congratulations! You reached your savings goal.",
    category="banking",
    priority="high",
    action_url="/banking/savings/{object_id}",
)

_register(
    constants.BANK_SAVINGS_INTEREST_PAID,
    title="Savings interest paid",
    body="You have earned interest on your savings goal.",
    category="banking",
    priority="high",
    action_url="/banking/savings/{object_id}",
)

# ----------------------------------------------------------------------------
# BANKING — SECURITY
# ----------------------------------------------------------------------------

_register(
    constants.BANK_SECURITY_PIN_CHANGED,
    title="Banking PIN changed",
    body="Your banking PIN has been changed.",
    category="banking",
    priority="high",
    action_url="/account/security",
)

_register(
    constants.BANK_SECURITY_PIN_LOCKED,
    title="Banking PIN locked",
    body="Your banking PIN has been locked after too many failed attempts.",
    category="banking",
    priority="urgent",
    action_url="/account/security",
)

_register(
    constants.BANK_SECURITY_PHONE_CHANGE_REQUESTED,
    title="Phone change requested",
    body="A phone number change has been requested on your account.",
    category="banking",
    priority="high",
    action_url="/account/security",
)

_register(
    constants.BANK_SECURITY_PHONE_CHANGED,
    title="Phone number changed",
    body="Your account phone number has been changed.",
    category="banking",
    priority="high",
    action_url="/account/security",
)

_register(
    constants.BANK_SECURITY_FRAUD_ALERT,
    title="Fraud alert",
    body="A suspicious activity was detected on your account.",
    category="banking",
    priority="urgent",
    action_url="/account/security",
)

# ----------------------------------------------------------------------------
# BANKING — INVESTMENTS
# ----------------------------------------------------------------------------

_register(
    constants.BANK_INVESTMENT_PURCHASED,
    title="Investment purchased",
    body="Your investment has been created.",
    category="banking",
    action_url="/banking/investments/{object_id}",
)

_register(
    constants.BANK_INVESTMENT_MATURED,
    title="Investment matured",
    body="Your investment has matured and funds have been returned.",
    category="banking",
    priority="high",
    action_url="/banking/investments/{object_id}",
)

_register(
    constants.BANK_INVESTMENT_WITHDRAWN,
    title="Investment withdrawn",
    body="Your investment has been withdrawn.",
    category="banking",
    priority="high",
    action_url="/banking/investments/{object_id}",
)

_register(
    constants.BANK_INVESTMENT_CANCELLED,
    title="Investment cancelled",
    body="Your investment has been cancelled and refunded.",
    category="banking",
    priority="high",
    action_url="/banking/investments/{object_id}",
)

_register(
    constants.BANK_INVESTMENT_EARNINGS_PAID,
    title="Investment earnings paid",
    body="You have received investment earnings.",
    category="banking",
    priority="high",
    action_url="/banking/investments/{object_id}",
)

# ----------------------------------------------------------------------------
# BANKING — MERCHANTS
# ----------------------------------------------------------------------------

_register(
    constants.BANK_MERCHANT_CREATED,
    title="Merchant account created",
    body="Your merchant account has been created and is pending verification.",
    category="banking",
    action_url="/banking/merchant/{object_id}",
)

_register(
    constants.BANK_MERCHANT_VERIFIED,
    title="Merchant verified",
    body="Your merchant account has been verified.",
    category="banking",
    priority="high",
    action_url="/banking/merchant/{object_id}",
)

_register(
    constants.BANK_MERCHANT_REJECTED,
    title="Merchant verification rejected",
    body="Your merchant verification was rejected. Please review and resubmit.",
    category="banking",
    priority="high",
    action_url="/banking/merchant/{object_id}",
)

_register(
    constants.BANK_MERCHANT_SUSPENDED,
    title="Merchant suspended",
    body="Your merchant account has been suspended.",
    category="banking",
    priority="urgent",
    action_url="/banking/merchant/{object_id}",
)

_register(
    constants.BANK_MERCHANT_SALE,
    title="New sale",
    body="You have received a new merchant sale.",
    category="banking",
    priority="high",
    action_url="/banking/merchant/transactions/{object_id}",
)

_register(
    constants.BANK_MERCHANT_REFUND,
    title="Sale refunded",
    body="A merchant sale has been refunded.",
    category="banking",
    priority="high",
    action_url="/banking/merchant/transactions/{object_id}",
)

_register(
    constants.BANK_MERCHANT_SETTLEMENT,
    title="Settlement completed",
    body="Your merchant settlement has been completed.",
    category="banking",
    priority="high",
    action_url="/banking/merchant/settlements/{object_id}",
)

# ============================================================================
# BIOMETRIC
# ============================================================================

_register(
    constants.BIOMETRIC_VERIFICATION_FAILED,
    title="Biometric verification failed",
    body=(
        "Your biometric verification was unsuccessful. "
        "For your security, the account has been temporarily locked."
    ),
    category="biometric",
    priority="high",
    action_url="/account/security",
)

_register(
    constants.BIOMETRIC_ENROLLMENT_COMPLETED,
    title="Biometric enrollment complete",
    body=(
        "Your face has been successfully enrolled for biometric "
        "authentication."
    ),
    category="biometric",
    action_url="/account/security",
)

_register(
    constants.BIOMETRIC_DEVICE_REGISTERED,
    title="New biometric device",
    body=(
        "A new device has been registered for biometric "
        "authentication on your account."
    ),
    category="biometric",
    priority="high",
    action_url="/account/security",
)

# ============================================================================
# TRANSPORT
# ============================================================================

_register(
    constants.RIDE_REQUESTED,
    title="Ride requested",
    body="Your ride request has been received.",
    category="transport",
    action_url="/transport/rides/{object_id}",
)

_register(
    constants.RIDE_ACCEPTED,
    title="Ride accepted",
    body="Your ride request has been accepted.",
    category="transport",
    priority="high",
    action_url="/transport/rides/{object_id}",
)

_register(
    constants.RIDE_DRIVER_ARRIVED,
    title="Driver arrived",
    body="Your driver has arrived.",
    category="transport",
    priority="high",
    action_url="/transport/rides/{object_id}",
)

_register(
    constants.RIDE_STARTED,
    title="Ride started",
    body="Your ride has started.",
    category="transport",
    action_url="/transport/rides/{object_id}",
)

_register(
    constants.RIDE_COMPLETED,
    title="Ride completed",
    body="Your ride has been completed.",
    category="transport",
    action_url="/transport/rides/{object_id}",
)

_register(
    constants.RIDE_CANCELLED,
    title="Ride cancelled",
    body="Your ride has been cancelled.",
    category="transport",
    priority="high",
    action_url="/transport/rides/{object_id}",
)

_register(
    constants.DELIVERY_REQUESTED,
    title="Delivery requested",
    body="Your delivery request has been received.",
    category="transport",
    action_url="/transport/deliveries/{object_id}",
)

_register(
    constants.DELIVERY_ASSIGNED,
    title="Delivery assigned",
    body="A delivery has been assigned to you.",
    category="transport",
    priority="high",
    action_url="/transport/deliveries/{object_id}",
)

_register(
    constants.DELIVERY_PICKED_UP,
    title="Delivery picked up",
    body="Your delivery has been picked up.",
    category="transport",
    action_url="/transport/deliveries/{object_id}",
)

_register(
    constants.DELIVERY_IN_TRANSIT,
    title="Delivery in transit",
    body="Your delivery is currently in transit.",
    category="transport",
    action_url="/transport/deliveries/{object_id}",
)

_register(
    constants.DELIVERY_DELIVERED,
    title="Delivery completed",
    body="Your delivery has been completed.",
    category="transport",
    action_url="/transport/deliveries/{object_id}",
)

_register(
    constants.DELIVERY_CANCELLED,
    title="Delivery cancelled",
    body="Your delivery has been cancelled.",
    category="transport",
    priority="high",
    action_url="/transport/deliveries/{object_id}",
)


# ============================================================================
# CHAT
# ============================================================================

_register(
    constants.MESSAGE_RECEIVED,
    title="New message",
    body="You have received a new message.",
    category="chat",
    action_url="/chat/{object_id}",
)

_register(
    constants.MESSAGE_REACTION,
    title="Message reaction",
    body="Someone reacted to your message.",
    category="chat",
    action_url="/chat/{object_id}",
)

_register(
    constants.CHAT_REQUEST_RECEIVED,
    title="New chat request",
    body="You have received a new chat request.",
    category="chat",
    action_url="/chat/requests",
)


# ============================================================================
# SOCIAL
# ============================================================================

_register(
    constants.SOCIAL_FOLLOW,
    title="New follower",
    body="Someone started following you.",
    category="social",
    action_url="/social/profile/{object_id}",
)

_register(
    constants.SOCIAL_LIKE,
    title="New like",
    body="Someone liked your post.",
    category="social",
    action_url="/social/posts/{object_id}",
)

_register(
    constants.SOCIAL_COMMENT,
    title="New comment",
    body="Someone commented on your post.",
    category="social",
    action_url="/social/posts/{object_id}",
)

_register(
    constants.SOCIAL_MENTION,
    title="You were mentioned",
    body="Someone mentioned you.",
    category="social",
    action_url="/social/posts/{object_id}",
)


# ============================================================================
# REAL ESTATE
# ============================================================================

_register(
    constants.PROPERTY_CREATED,
    title="Property listed",
    body="A new property has been listed.",
    category="realestate",
    action_url="/real-estate/properties/{object_id}",
)

_register(
    constants.PROPERTY_UPDATED,
    title="Property updated",
    body="A property listing has been updated.",
    category="realestate",
    action_url="/real-estate/properties/{object_id}",
)

_register(
    constants.PROPERTY_SAVED,
    title="Property saved",
    body="A property has been saved to your favourites.",
    category="realestate",
    action_url="/real-estate/properties/{object_id}",
)

_register(
    constants.OFFER_RECEIVED,
    title="New property offer",
    body="You have received a new property offer.",
    category="realestate",
    priority="high",
    action_url="/real-estate/offers/{object_id}",
)

_register(
    constants.OFFER_ACCEPTED,
    title="Offer accepted",
    body="Your property offer has been accepted.",
    category="realestate",
    priority="high",
    action_url="/real-estate/offers/{object_id}",
)

_register(
    constants.OFFER_REJECTED,
    title="Offer declined",
    body="Your property offer has been declined.",
    category="realestate",
    priority="high",
    action_url="/real-estate/offers/{object_id}",
)


# ============================================================================
# E-COMMERCE
# ============================================================================

_register(
    constants.PRODUCT_BACK_IN_STOCK,
    title="Product back in stock",
    body="A product on your list is back in stock.",
    category="product",
    action_url="/products/{object_id}",
)

_register(
    constants.PRICE_CHANGED,
    title="Product price changed",
    body="The price of a product has changed.",
    category="product",
    action_url="/products/{object_id}",
)

_register(
    constants.WISHLIST_PRICE_DROP,
    title="Wishlist price drop",
    body="A product on your wishlist is now cheaper.",
    category="product",
    priority="high",
    action_url="/products/{object_id}",
)


# ----------------------------------------------------------------------------
# INVOICE
# ----------------------------------------------------------------------------

_register(
    constants.INVOICE_SENT,
    title="Invoice ready",
    body="Your invoice is ready to view.",
    category="invoice",
    channels=("in_app", "push", "email"),
    action_url="/invoices/{object_id}",
)

_register(
    constants.INVOICE_PAID,
    title="Invoice paid",
    body="Your invoice has been paid in full.",
    category="invoice",
    priority="high",
    channels=("in_app", "push", "email"),
    action_url="/invoices/{object_id}",
)

_register(
    constants.INVOICE_OVERDUE,
    title="Invoice overdue",
    body="Your invoice is now overdue. Please complete payment.",
    category="invoice",
    priority="high",
    channels=("in_app", "push", "email"),
    action_url="/invoices/{object_id}",
)

_register(
    constants.INVOICE_CANCELLED,
    title="Invoice cancelled",
    body="Your invoice has been cancelled.",
    category="invoice",
    priority="high",
    channels=("in_app", "push", "email"),
    action_url="/invoices/{object_id}",
)

_register(
    constants.INVOICE_VOIDED,
    title="Invoice voided",
    body="Your invoice has been voided.",
    category="invoice",
    priority="high",
    channels=("in_app", "push", "email"),
    action_url="/invoices/{object_id}",
)

_register(
    constants.INVOICE_REFUNDED,
    title="Invoice refunded",
    body="Your invoice has been refunded.",
    category="invoice",
    priority="high",
    channels=("in_app", "push", "email"),
    action_url="/invoices/{object_id}",
)

# ============================================================================
# SYSTEM
# ============================================================================

_register(
    constants.SYSTEM_ANNOUNCEMENT,
    title="Announcement",
    body="You have a new announcement from Univa.",
    category="system",
    priority="high",
    action_url="/notifications",
)

_register(
    constants.SYSTEM_MAINTENANCE,
    title="System maintenance",
    body="Univa has scheduled system maintenance.",
    category="system",
    priority="high",
    action_url="/notifications",
)

_register(
    constants.SOCIAL_VIDEO_PROCESSED,
    title="Your video is ready!",
    body="Your video has been processed and is now live.",
    category="social",
    action_url="/social/videos/{object_id}",
)

_register(
    constants.SOCIAL_VIDEO_PROCESSING_FAILED,
    title="Video processing failed",
    body="We couldn't process your video. Please try again.",
    category="social",
    priority="high",
    action_url="/social/videos/{object_id}",
)


# ============================================================================
# STAFF
# ============================================================================

_register(
    constants.STAFF_MEMBER_CREATED,
    title="Staff profile created",
    body="Your Univa staff profile has been created.",
    category="staff",
    action_url="/staff/profile/{object_id}",
)

_register(
    constants.STAFF_MEMBER_EMPLOYMENT_STATUS_CHANGED,
    title="Employment status updated",
    body="Your Univa employment status has been updated.",
    category="staff",
    priority="high",
    action_url="/staff/profile/{object_id}",
)


# ============================================================================
# REGISTRY HELPERS
# ============================================================================


def get_event_definition(
    event_type: str,
) -> EventDefinition | None:
    """
    Return the definition registered for an event type.

    Unknown or empty event types return None.
    """

    if not event_type:
        return None

    return EVENT_REGISTRY.get(
        str(event_type).strip(),
    )


def is_registered_event(
    event_type: str,
) -> bool:
    """
    Return True when an event type is registered.
    """

    return get_event_definition(event_type) is not None


def registered_event_types() -> tuple[str, ...]:
    """
    Return all registered event types.

    The returned tuple cannot be modified by callers.
    """

    return tuple(EVENT_REGISTRY.keys())


def get_event_category(
    event_type: str,
) -> str | None:
    """
    Return the notification category for an event type.
    """

    definition = get_event_definition(event_type)

    if definition is None:
        return None

    return definition.category


def get_event_channels(
    event_type: str,
) -> tuple[str, ...]:
    """
    Return the configured notification channels for an event.

    Unknown events return an empty tuple.
    """

    definition = get_event_definition(event_type)

    if definition is None:
        return ()

    return definition.channels


def get_event_priority(
    event_type: str,
) -> str | None:
    """
    Return the configured notification priority.
    """

    definition = get_event_definition(event_type)

    if definition is None:
        return None

    return definition.priority


def get_event_action_url(
    event_type: str,
) -> str | None:
    """
    Return the configured action URL template.
    """

    definition = get_event_definition(event_type)

    if definition is None:
        return None

    return definition.action_url


# ============================================================================
# REGISTRY VALIDATION
# ============================================================================


def validate_event_registry() -> None:
    """
    Validate the notification event registry.

    Checks:

        1. Every constant is registered.
        2. No unknown event was registered.
        3. Registry keys match EventDefinition.event_type.
        4. Required presentation fields are populated.
        5. Notification channels are valid.
        6. Priorities are valid.
        7. Action URL templates are valid.
    """

    registered = set(EVENT_REGISTRY)
    defined = set(constants.ALL_EVENT_TYPES)

    # ------------------------------------------------------------------
    # Missing events
    # ------------------------------------------------------------------

    missing = defined - registered

    if missing:
        raise ValueError(
            "Notification events defined in constants.py but missing "
            f"from EVENT_REGISTRY: {sorted(missing)}"
        )

    # ------------------------------------------------------------------
    # Unknown events
    # ------------------------------------------------------------------

    extra = registered - defined

    if extra:
        raise ValueError(
            "Notification events registered but missing from "
            f"constants.ALL_EVENT_TYPES: {sorted(extra)}"
        )

    # ------------------------------------------------------------------
    # Definition validation
    # ------------------------------------------------------------------

    for key, definition in EVENT_REGISTRY.items():

        if key != definition.event_type:
            raise ValueError(
                "Notification event registry key does not match "
                f"definition.event_type: {key!r}"
            )

        if not definition.title.strip():
            raise ValueError(
                f"Notification event {key!r} has an empty title."
            )

        if not definition.body.strip():
            raise ValueError(
                f"Notification event {key!r} has an empty body."
            )

        if not definition.category.strip():
            raise ValueError(
                f"Notification event {key!r} has an empty category."
            )

        if not definition.channels:
            raise ValueError(
                f"Notification event {key!r} has no channels."
            )

        invalid_channels = (
            set(definition.channels) - VALID_CHANNELS
        )

        if invalid_channels:
            raise ValueError(
                f"Notification event {key!r} contains unsupported "
                f"channels: {sorted(invalid_channels)}"
            )

        if len(definition.channels) != len(set(definition.channels)):
            raise ValueError(
                f"Notification event {key!r} contains duplicate "
                "channels."
            )

        if definition.priority not in VALID_PRIORITIES:
            raise ValueError(
                f"Notification event {key!r} has unsupported "
                f"priority: {definition.priority!r}"
            )

        # --------------------------------------------------------------
        # Action URL validation
        # --------------------------------------------------------------

        if definition.action_url:
            try:
                formatted_url = definition.action_url.format(
                    object_id="object-id",
                    event_id="event-id",
                )
            except (KeyError, ValueError, IndexError) as exc:
                raise ValueError(
                    "Invalid action_url for notification event "
                    f"{key!r}: {definition.action_url!r}"
                ) from exc

            if not isinstance(formatted_url, str):
                raise ValueError(
                    f"Invalid action_url for notification event "
                    f"{key!r}."
                )


# ============================================================================
# PUBLIC API
# ============================================================================

__all__ = [
    "VALID_CHANNELS",
    "VALID_PRIORITIES",
    "EventDefinition",
    "EVENT_REGISTRY",
    "get_event_definition",
    "is_registered_event",
    "registered_event_types",
    "get_event_category",
    "get_event_channels",
    "get_event_priority",
    "get_event_action_url",
    "validate_event_registry",
]


# ============================================================================
# DEVELOPMENT / TEST-TIME VALIDATION
# ============================================================================

# The registry is static configuration, so validating it immediately catches
# accidental inconsistencies between constants.py and registry.py during
# application startup/import.
validate_event_registry()