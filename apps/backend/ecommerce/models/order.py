# apps/backend/ecommerce/models/order.py

"""
Order models for Univa.

Core entities:

    Order                   — a purchase (from checkout, draft, etc.)
    OrderLine               — a line item on an order
    Fulfillment             — a shipment or pickup
    FulfillmentLine         — a line within a fulfillment
    OrderEvent              — audit trail of state changes
    OrderGrantedRefund      — a refund granted to a customer
    OrderGrantedRefundLine  — a line within a granted refund
    OrderTrackingEvent      — real-time tracking events

Design notes:

  * `OrderLine.quantity` is Decimal — supports weighted market items
    (2.5 kg of beef) as well as discrete catalog items.

  * `OrderLine.quantity_unit` is denormalized from the variant at
    checkout so historical orders preserve their unit even if the
    variant changes.

  * Money is stored as paired `*_amount` DecimalField + `currency`
    CharField and exposed as `MoneyField` / `TaxedMoneyField`
    descriptors from `core.pricing`.

  * The `Invoice` for an order lives in the `invoice` app, which
    holds a `ForeignKey` back to `Order`. This module does NOT
    import or reference Invoice.

  * Fields removed in Phase 8.B (analytics, fraud, CEM, ESG) belong
    in dedicated satellite models, not on Order itself. See git
    history for what they were.
"""

from __future__ import annotations

from decimal import Decimal
from re import match
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import BTreeIndex, GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import F, JSONField, Max, Q
from django.utils.timezone import now
from django_measurement.models import MeasurementField
from measurement.measures import Weight

from core.models.metadata import (
    ModelWithExternalReference,
    ModelWithMetadata,
)
from core.models.utils.json_serializer import CustomJsonEncoder
from core.pricing import Money, MoneyField, TaxedMoneyField
from core.pricing.quantity_unit import QuantityUnit
from core.units import WeightUnits
from core.weight import zero_weight
from ecommerce.models.channel import Channel
from ecommerce.models.discount import Voucher
from ecommerce.models.giftcard import GiftCard
from ecommerce.models.shipping import ShippingMethod
from payment.constants import ChargeStatus, TransactionKind
from payment.model_helpers import get_subtotal
from payment.models import Payment

from .constants import (
    DiscountValueType,
    FulfillmentStatus,
    OrderAuthorizeStatus,
    OrderChargeStatus,
    OrderEvents,
    OrderGrantedRefundStatus,
    OrderOrigin,
    OrderStatus,
)

if TYPE_CHECKING:
    from accounts.models import User


# =====================================================================
# ORDER QUERYSET
# =====================================================================


class OrderQueryset(models.QuerySet["Order"]):
    def get_by_checkout_token(self, token):
        """Return non-draft order with matched checkout token."""
        return (
            self.non_draft()
            .select_related(
                "user",
                "billing_address",
                "shipping_address",
                "channel",
            )
            .filter(checkout_token=token)
            .first()
        )

    def confirmed(self):
        """Return orders that aren't draft or unconfirmed."""
        return self.exclude(
            status__in=[
                OrderStatus.DRAFT,
                OrderStatus.UNCONFIRMED,
            ]
        )

    def non_draft(self):
        """Return orders that aren't draft."""
        return (
            self.exclude(status=OrderStatus.DRAFT)
            .prefetch_related("payments")
        )

    def drafts(self):
        """Return draft orders with minimal fields."""
        return self.filter(
            status=OrderStatus.DRAFT
        ).only(
            "id",
            "number",
            "status",
        )

    def ready_to_fulfill(self):
        """Return orders ready to fulfill."""
        statuses = {
            OrderStatus.UNFULFILLED,
            OrderStatus.PARTIALLY_FULFILLED,
        }

        return (
            self.filter(
                status__in=statuses,
                total_gross_amount__lte=F("total_charged_amount"),
            )
            .filter(
                payments__is_active=True,
            )
            .distinct()
            .prefetch_related("lines")
        )

    def ready_to_capture(self):
        """Return orders ready to capture."""
        return (
            self.exclude(
                status__in={
                    OrderStatus.DRAFT,
                    OrderStatus.CANCELED,
                    OrderStatus.EXPIRED,
                }
            )
            .filter(
                payments__is_active=True,
                payments__charge_status=ChargeStatus.NOT_CHARGED,
            )
            .distinct()
        )

    def ready_to_confirm(self):
        """Return unconfirmed orders."""
        return (
            self.filter(
                status=OrderStatus.UNCONFIRMED
            )
            .select_related("channel")
        )

    def with_related_data(self):
        """Return orders with commonly required related data."""
        return (
            self.select_related(
                "user",
                "billing_address",
                "shipping_address",
                "channel",
                "shipping_method",
                "collection_point",
                "voucher",
            )
            .prefetch_related(
                "lines",
                "payments",
                "fulfillments",
                "gift_cards",
            )
        )


OrderManager = models.Manager.from_queryset(OrderQueryset)


def get_order_number() -> int:
    """
    Generate the next order number.

    Uses SELECT FOR UPDATE on the last order row to serialize
    concurrent assignments. The import is local to avoid a
    circular import at module load.
    """
    from .order import Order

    with transaction.atomic():
        last_order = (
            Order.objects
            .select_for_update()
            .order_by("-number")
            .only("number")
            .first()
        )

        return (last_order.number + 1) if last_order else 1


# =====================================================================
# ORDER
# =====================================================================


class Order(ModelWithMetadata, ModelWithExternalReference):
    """
    Customer order.

    A single Order can mix catalog items ("iPhone 15") and market
    items ("2.5 kg of beef") because OrderLine.quantity is Decimal
    and OrderLine.quantity_unit records the unit.
    """

    id = models.UUIDField(
        primary_key=True,
        editable=False,
        unique=True,
        default=uuid4,
    )

    number = models.IntegerField(
        unique=True,
        default=get_order_number,
        editable=False,
    )

    created_at = models.DateTimeField(
        default=now,
        editable=False,
        db_index=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        editable=False,
        db_index=True,
    )

    expired_at = models.DateTimeField(
        blank=True,
        null=True,
        db_index=True,
    )

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    status = models.CharField(
        max_length=32,
        default=OrderStatus.UNFULFILLED,
        choices=OrderStatus.CHOICES,
        db_index=True,
    )

    authorize_status = models.CharField(
        max_length=32,
        default=OrderAuthorizeStatus.NONE,
        choices=OrderAuthorizeStatus.CHOICES,
        db_index=True,
    )

    charge_status = models.CharField(
        max_length=32,
        default=OrderChargeStatus.NONE,
        choices=OrderChargeStatus.CHOICES,
        db_index=True,
    )

    origin = models.CharField(
        max_length=32,
        choices=OrderOrigin.CHOICES,
        db_index=True,
    )

    # ------------------------------------------------------------------
    # Customer
    # ------------------------------------------------------------------

    user = models.ForeignKey(
        "accounts.User",
        blank=True,
        null=True,
        related_name="orders",
        on_delete=models.SET_NULL,
        db_index=True,
    )

    user_email = models.EmailField(
        blank=True,
        default="",
        db_index=True,
    )

    language_code = models.CharField(
        max_length=35,
        choices=settings.LANGUAGES,
        default=settings.LANGUAGE_CODE,
    )

    tracking_client_id = models.CharField(
        max_length=36,
        blank=True,
        editable=False,
    )

    # ------------------------------------------------------------------
    # Addresses
    # ------------------------------------------------------------------

    billing_address = models.ForeignKey(
        "accounts.Address",
        related_name="+",
        editable=False,
        null=True,
        on_delete=models.SET_NULL,
    )

    shipping_address = models.ForeignKey(
        "accounts.Address",
        related_name="+",
        editable=False,
        null=True,
        on_delete=models.SET_NULL,
    )

    original = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_index=True,
    )

    # ------------------------------------------------------------------
    # Channel and shipping
    # ------------------------------------------------------------------

    channel = models.ForeignKey(
        Channel,
        related_name="orders",
        on_delete=models.PROTECT,
        db_index=True,
    )

    currency = models.CharField(
        max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH,
        db_index=True,
    )

    shipping_method = models.ForeignKey(
        ShippingMethod,
        blank=True,
        null=True,
        related_name="orders",
        on_delete=models.SET_NULL,
    )

    collection_point = models.ForeignKey(
        "ecommerce.Warehouse",
        blank=True,
        null=True,
        related_name="orders",
        on_delete=models.SET_NULL,
    )

    shipping_method_name = models.CharField(
        max_length=255,
        null=True,
        default=None,
        blank=True,
        editable=False,
    )

    collection_point_name = models.CharField(
        max_length=255,
        null=True,
        default=None,
        blank=True,
        editable=False,
    )

    checkout_token = models.CharField(
        max_length=36,
        blank=True,
        db_index=True,
    )

    # ------------------------------------------------------------------
    # Shipping prices
    # ------------------------------------------------------------------

    shipping_price_net_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
        editable=False,
    )

    shipping_price_net = MoneyField(
        amount_field="shipping_price_net_amount",
        currency_field="currency",
    )

    shipping_price_gross_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
        editable=False,
    )

    shipping_price_gross = MoneyField(
        amount_field="shipping_price_gross_amount",
        currency_field="currency",
    )

    shipping_price = TaxedMoneyField(
        net_amount_field="shipping_price_net_amount",
        gross_amount_field="shipping_price_gross_amount",
        currency_field="currency",
    )

    base_shipping_price_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )

    base_shipping_price = MoneyField(
        amount_field="base_shipping_price_amount",
        currency_field="currency",
    )

    undiscounted_base_shipping_price_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )

    undiscounted_base_shipping_price = MoneyField(
        amount_field="undiscounted_base_shipping_price_amount",
        currency_field="currency",
    )

    # ------------------------------------------------------------------
    # Tax (shipping)
    # ------------------------------------------------------------------

    shipping_tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        blank=True,
        null=True,
    )

    shipping_tax_class = models.ForeignKey(
        "tax.TaxClass",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    shipping_tax_class_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    shipping_tax_class_private_metadata = JSONField(
        blank=True,
        null=True,
        default=dict,
        encoder=CustomJsonEncoder,
    )

    shipping_tax_class_metadata = JSONField(
        blank=True,
        null=True,
        default=dict,
        encoder=CustomJsonEncoder,
    )

    # ------------------------------------------------------------------
    # Totals
    # ------------------------------------------------------------------

    total_net_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )

    undiscounted_total_net_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )

    total_net = MoneyField(
        amount_field="total_net_amount",
        currency_field="currency",
    )

    undiscounted_total_net = MoneyField(
        amount_field="undiscounted_total_net_amount",
        currency_field="currency",
    )

    total_gross_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )

    undiscounted_total_gross_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )

    total_gross = MoneyField(
        amount_field="total_gross_amount",
        currency_field="currency",
    )

    undiscounted_total_gross = MoneyField(
        amount_field="undiscounted_total_gross_amount",
        currency_field="currency",
    )

    total = TaxedMoneyField(
        net_amount_field="total_net_amount",
        gross_amount_field="total_gross_amount",
        currency_field="currency",
    )

    undiscounted_total = TaxedMoneyField(
        net_amount_field="undiscounted_total_net_amount",
        gross_amount_field="undiscounted_total_gross_amount",
        currency_field="currency",
    )

    # ------------------------------------------------------------------
    # Payment amounts
    # ------------------------------------------------------------------

    total_charged_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )

    total_authorized_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )

    total_authorized = MoneyField(
        amount_field="total_authorized_amount",
        currency_field="currency",
    )

    total_charged = MoneyField(
        amount_field="total_charged_amount",
        currency_field="currency",
    )

    # ------------------------------------------------------------------
    # Subtotal
    # ------------------------------------------------------------------

    subtotal_net_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )

    subtotal_gross_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )

    subtotal = TaxedMoneyField(
        net_amount_field="subtotal_net_amount",
        gross_amount_field="subtotal_gross_amount",
        currency_field="currency",
    )

    # ------------------------------------------------------------------
    # Vouchers / gift cards
    # ------------------------------------------------------------------

    voucher = models.ForeignKey(
        Voucher,
        blank=True,
        null=True,
        related_name="+",
        on_delete=models.SET_NULL,
        db_index=True,
    )

    voucher_code = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
    )

    gift_cards = models.ManyToManyField(
        GiftCard,
        blank=True,
        related_name="orders",
    )

    # ------------------------------------------------------------------
    # Customer-facing metadata
    # ------------------------------------------------------------------

    display_gross_prices = models.BooleanField(default=True)

    customer_note = models.TextField(
        blank=True,
        default="",
    )

    weight = MeasurementField(
        measurement=Weight,
        unit_choices=WeightUnits.CHOICES,
        default=zero_weight,
    )

    redirect_url = models.URLField(
        blank=True,
        null=True,
    )

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    search_document = models.TextField(
        blank=True,
        default="",
    )

    search_vector = SearchVectorField(
        blank=True,
        null=True,
    )

    # ------------------------------------------------------------------
    # Pricing state
    # ------------------------------------------------------------------

    should_refresh_prices = models.BooleanField(default=True)

    tax_exemption = models.BooleanField(default=False)

    tax_error = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    # ------------------------------------------------------------------
    # Order type flags
    # ------------------------------------------------------------------

    priority_level = models.IntegerField(
        default=0,
        db_index=True,
    )

    is_prime = models.BooleanField(
        default=False,
        db_index=True,
    )

    is_business = models.BooleanField(
        default=False,
        db_index=True,
    )

    is_express = models.BooleanField(
        default=False,
        db_index=True,
    )

    # ------------------------------------------------------------------
    # Fulfillment optimization
    # ------------------------------------------------------------------

    preferred_warehouse = models.ForeignKey(
        "ecommerce.Warehouse",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="preferred_orders",
    )

    fulfillment_strategy = models.CharField(
        max_length=50,
        choices=[
            ("SINGLE_SHIPMENT", "Single Shipment"),
            ("MULTI_SHIPMENT", "Multi-Shipment"),
            ("SPLIT_ORDER", "Split Order"),
            ("MERGE_ORDERS", "Merge Orders"),
        ],
        default="SINGLE_SHIPMENT",
    )

    # ------------------------------------------------------------------
    # Delivery
    # ------------------------------------------------------------------

    promised_delivery_date = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )

    actual_delivery_date = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )

    delivery_window_start = models.DateTimeField(
        null=True,
        blank=True,
    )

    delivery_window_end = models.DateTimeField(
        null=True,
        blank=True,
    )

    # ------------------------------------------------------------------
    # Cost / profitability
    # ------------------------------------------------------------------

    cost_of_goods_sold = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        null=True,
        blank=True,
    )

    fulfillment_cost = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        null=True,
        blank=True,
    )

    shipping_cost_actual = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        null=True,
        blank=True,
    )

    gross_margin = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
    )

    objects = OrderManager()

    class Meta:
        ordering = ("-number",)
        permissions = (
            ("manage_orders", "Manage orders."),
            ("manage_orders_import", "Manage orders import."),
        )
        indexes = [
            # Search
            GinIndex(
                name="order_search_gin",
                fields=["search_document"],
                opclasses=["gin_trgm_ops"],
            ),
            GinIndex(
                name="order_tsearch",
                fields=["search_vector"],
            ),
            # Storefront / admin queries
            models.Index(
                fields=["user", "-created_at"],
                name="order_user_created_idx",
            ),
            models.Index(
                fields=["channel", "status", "-created_at"],
                name="order_channel_status_idx",
            ),
            models.Index(
                fields=["status", "-created_at"],
                name="order_status_created_idx",
            ),
            # Operational
            BTreeIndex(
                fields=["created_at", "status"],
                name="order_created_status_idx",
            ),
            BTreeIndex(
                fields=["priority_level", "created_at"],
                name="order_priority_idx",
            ),
            BTreeIndex(
                fields=["is_prime", "status"],
                name="order_prime_status_idx",
            ),
            BTreeIndex(
                fields=["promised_delivery_date", "status"],
                name="order_promised_status_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(number__gt=0),
                name="order_number_positive",
            ),
            models.CheckConstraint(
                condition=Q(total_gross_amount__gte=0),
                name="order_total_gross_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(total_net_amount__gte=0),
                name="order_total_net_non_negative",
            ),
        ]

    def __str__(self):
        return f"#{self.id}"

    def save(self, *args, **kwargs):
        """
        Persist the order.

        The search document is rebuilt only when:
          * the object is new, or
          * the caller explicitly included 'search_document' in
            update_fields.

        This avoids recomputing (and rewriting) the search blob on
        every state change.
        """
        update_fields = kwargs.get("update_fields")

        if self._state.adding:
            self.update_search_document()
        elif update_fields and "search_document" in update_fields:
            self.update_search_document()

        super().save(*args, **kwargs)

    def update_search_document(self):
        """Generate the searchable order document."""
        parts = [
            str(self.number),
            self.user_email,
            self.customer_note,
        ]

        if self.user_id:
            parts.extend(
                [
                    self.user.email,
                    self.user.first_name,
                    self.user.last_name,
                ]
            )

        if self.billing_address_id:
            addr = self.billing_address
            parts.extend(
                [
                    addr.first_name,
                    addr.last_name,
                    addr.street_address_1,
                    addr.street_address_2,
                    addr.city,
                    addr.postal_code,
                ]
            )

        self.search_document = " ".join(
            part for part in parts if part
        )

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------

    def is_fully_paid(self) -> bool:
        return self.total_charged_amount >= self.total_gross_amount

    def is_partly_paid(self) -> bool:
        return self.total_charged_amount > 0

    def is_draft(self) -> bool:
        return self.status == OrderStatus.DRAFT

    def is_unconfirmed(self) -> bool:
        return self.status == OrderStatus.UNCONFIRMED

    def is_expired(self) -> bool:
        return self.status == OrderStatus.EXPIRED

    def is_open(self) -> bool:
        return self.status in {
            OrderStatus.UNFULFILLED,
            OrderStatus.PARTIALLY_FULFILLED,
        }

    # ------------------------------------------------------------------
    # Customer
    # ------------------------------------------------------------------

    def get_customer_email(self) -> str:
        return self.user.email if self.user_id else self.user_email

    # ------------------------------------------------------------------
    # Payment helpers
    # ------------------------------------------------------------------

    def get_last_payment(self) -> Optional[Payment]:
        if not hasattr(self, "_last_payment"):
            self._last_payment = (
                self.payments
                .exclude(partial=True)
                .order_by("-pk")
                .first()
            )
        return self._last_payment

    def is_pre_authorized(self) -> bool:
        return self.payments.filter(
            is_active=True,
            transactions__kind=TransactionKind.AUTH,
            transactions__action_required=False,
            transactions__is_success=True,
        ).exists()

    def is_captured(self) -> bool:
        return self.payments.filter(
            is_active=True,
            transactions__kind=TransactionKind.CAPTURE,
            transactions__action_required=False,
            transactions__is_success=True,
        ).exists()

    def can_capture(self, payment=None) -> bool:
        if payment is None:
            payment = self.get_last_payment()
        if not payment:
            return False
        return (
            payment.can_capture()
            and self.status not in {
                OrderStatus.DRAFT,
                OrderStatus.CANCELED,
                OrderStatus.EXPIRED,
            }
        )

    def can_void(self, payment=None) -> bool:
        if payment is None:
            payment = self.get_last_payment()
        return payment.can_void() if payment else False

    def can_refund(self, payment=None) -> bool:
        if payment is None:
            payment = self.get_last_payment()
        return payment.can_refund() if payment else False

    def can_mark_as_paid(self) -> bool:
        return not self.payments.exists()

    # ------------------------------------------------------------------
    # Line helpers
    # ------------------------------------------------------------------

    def _ensure_lines(self) -> None:
        if not hasattr(self, "_lines"):
            self._lines = list(self.lines.all())

    def get_subtotal(self):
        """Calculate the subtotal using cached lines."""
        self._ensure_lines()
        return get_subtotal(self._lines, self.currency)

    def is_shipping_required(self) -> bool:
        self._ensure_lines()
        return any(line.is_shipping_required for line in self._lines)

    def get_total_quantity(self) -> Decimal:
        """Total quantity across all lines, as Decimal."""
        self._ensure_lines()
        return sum(
            (line.quantity for line in self._lines),
            start=Decimal("0"),
        )

    # ------------------------------------------------------------------
    # Cancellation
    # ------------------------------------------------------------------

    def can_cancel(self) -> bool:
        if self.status in {
            OrderStatus.CANCELED,
            OrderStatus.DRAFT,
            OrderStatus.EXPIRED,
        }:
            return False

        if not hasattr(self, "_fulfillments"):
            self._fulfillments = list(self.fulfillments.all())

        allowed_statuses = {
            FulfillmentStatus.CANCELED,
            FulfillmentStatus.REFUNDED,
            FulfillmentStatus.REPLACED,
            FulfillmentStatus.REFUNDED_AND_RETURNED,
            FulfillmentStatus.RETURNED,
        }

        return all(
            f.status in allowed_statuses for f in self._fulfillments
        )

    # ------------------------------------------------------------------
    # Money
    # ------------------------------------------------------------------

    @property
    def total_balance(self) -> Money:
        return Money(
            amount=(self.total_charged_amount - self.total_gross_amount),
            currency=self.currency,
        )


# =====================================================================
# ORDER LINE
# =====================================================================


class OrderLineQueryset(models.QuerySet["OrderLine"]):
    def digital(self):
        return self.filter(
            variant__is_digital=True,
            variant__digital_content__isnull=False,
        )

    def physical(self):
        return self.filter(
            Q(variant__is_digital=False)
            | Q(variant__digital_content__isnull=True)
        )

    def with_related_data(self):
        return self.select_related(
            "variant",
            "variant__product",
            "order",
        )


OrderLineManager = models.Manager.from_queryset(OrderLineQueryset)


class OrderLine(ModelWithMetadata):
    id = models.UUIDField(
        primary_key=True,
        editable=False,
        unique=True,
        default=uuid4,
    )

    old_id = models.PositiveIntegerField(
        unique=True,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    order = models.ForeignKey(
        Order,
        related_name="lines",
        editable=False,
        on_delete=models.CASCADE,
        db_index=True,
    )

    variant = models.ForeignKey(
        "ecommerce.ProductVariant",
        related_name="order_lines",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        db_index=True,
    )

    product_name = models.CharField(max_length=386)

    variant_name = models.CharField(
        max_length=255,
        default="",
        blank=True,
    )

    translated_product_name = models.CharField(
        max_length=386,
        default="",
        blank=True,
    )

    translated_variant_name = models.CharField(
        max_length=255,
        default="",
        blank=True,
    )

    product_sku = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
    )

    product_variant_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    is_shipping_required = models.BooleanField(db_index=True)
    is_gift_card = models.BooleanField(db_index=True)
    is_gift = models.BooleanField(default=False, db_index=True)

    # ------------------------------------------------------------------
    # Quantity
    # ------------------------------------------------------------------

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )

    quantity_fulfilled = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )

    quantity_unit = models.CharField(
        max_length=16,
        choices=QuantityUnit.choices(),
        default=QuantityUnit.UNIT.value,
        db_index=True,
        help_text=(
            "Unit of measure for this line. Denormalized from the "
            "variant at checkout time so historical orders preserve "
            "their unit even if the variant changes."
        ),
    )

    # ------------------------------------------------------------------
    # Currency
    # ------------------------------------------------------------------

    currency = models.CharField(
        max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH,
        db_index=True,
    )

    # ------------------------------------------------------------------
    # Discounts
    # ------------------------------------------------------------------

    unit_discount_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )

    unit_discount = MoneyField(
        amount_field="unit_discount_amount",
        currency_field="currency",
    )

    unit_discount_type = models.CharField(
        max_length=10,
        choices=DiscountValueType.CHOICES,
        null=True,
        blank=True,
    )

    unit_discount_reason = models.TextField(
        blank=True,
        null=True,
    )

    unit_discount_value = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )

    # ------------------------------------------------------------------
    # Unit price
    # ------------------------------------------------------------------

    unit_price_net_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
    )

    unit_price_net = MoneyField(
        amount_field="unit_price_net_amount",
        currency_field="currency",
    )

    unit_price_gross_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
    )

    unit_price_gross = MoneyField(
        amount_field="unit_price_gross_amount",
        currency_field="currency",
    )

    unit_price = TaxedMoneyField(
        net_amount_field="unit_price_net_amount",
        gross_amount_field="unit_price_gross_amount",
        currency_field="currency",
    )

    # ------------------------------------------------------------------
    # Total price
    # ------------------------------------------------------------------

    total_price_net_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
    )

    total_price_net = MoneyField(
        amount_field="total_price_net_amount",
        currency_field="currency",
    )

    total_price_gross_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
    )

    total_price_gross = MoneyField(
        amount_field="total_price_gross_amount",
        currency_field="currency",
    )

    total_price = TaxedMoneyField(
        net_amount_field="total_price_net_amount",
        gross_amount_field="total_price_gross_amount",
        currency_field="currency",
    )

    # ------------------------------------------------------------------
    # Undiscounted unit price
    # ------------------------------------------------------------------

    undiscounted_unit_price_gross_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )

    undiscounted_unit_price_net_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )

    undiscounted_unit_price = TaxedMoneyField(
        net_amount_field="undiscounted_unit_price_net_amount",
        gross_amount_field="undiscounted_unit_price_gross_amount",
        currency_field="currency",
    )

    # ------------------------------------------------------------------
    # Undiscounted total price
    # ------------------------------------------------------------------

    undiscounted_total_price_gross_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )

    undiscounted_total_price_net_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )

    undiscounted_total_price = TaxedMoneyField(
        net_amount_field="undiscounted_total_price_net_amount",
        gross_amount_field="undiscounted_total_price_gross_amount",
        currency_field="currency",
    )

    # ------------------------------------------------------------------
    # Base prices
    # ------------------------------------------------------------------

    base_unit_price_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )

    base_unit_price = MoneyField(
        amount_field="base_unit_price_amount",
        currency_field="currency",
    )

    undiscounted_base_unit_price_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )

    undiscounted_base_unit_price = MoneyField(
        amount_field="undiscounted_base_unit_price_amount",
        currency_field="currency",
    )

    # ------------------------------------------------------------------
    # Tax
    # ------------------------------------------------------------------

    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        blank=True,
        null=True,
    )

    tax_class = models.ForeignKey(
        "tax.TaxClass",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    tax_class_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    tax_class_private_metadata = JSONField(
        blank=True,
        null=True,
        default=dict,
        encoder=CustomJsonEncoder,
    )

    tax_class_metadata = JSONField(
        blank=True,
        null=True,
        default=dict,
        encoder=CustomJsonEncoder,
    )

    is_price_overridden = models.BooleanField(
        null=True,
        blank=True,
    )

    # ------------------------------------------------------------------
    # Discounts / costing
    # ------------------------------------------------------------------

    voucher_code = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
    )

    sale_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
    )

    unit_cost = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        null=True,
        blank=True,
    )

    landed_cost = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        null=True,
        blank=True,
    )

    # ------------------------------------------------------------------
    # Inventory / fulfillment
    # ------------------------------------------------------------------

    allocated_warehouse = models.ForeignKey(
        "ecommerce.Warehouse",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="allocated_lines",
    )

    bin_location = models.CharField(max_length=100, blank=True)

    pick_path_sequence = models.IntegerField(null=True, blank=True)

    # ------------------------------------------------------------------
    # Quality / returns
    # ------------------------------------------------------------------

    return_reason = models.CharField(max_length=100, blank=True)
    return_condition = models.CharField(max_length=50, blank=True)
    is_defective = models.BooleanField(default=False)
    defect_type = models.CharField(max_length=100, blank=True)

    # ------------------------------------------------------------------
    # Customer experience
    # ------------------------------------------------------------------

    line_rating = models.IntegerField(null=True, blank=True)
    line_review = models.TextField(blank=True)

    # ------------------------------------------------------------------
    # Promotions / attribution
    # ------------------------------------------------------------------

    promotion_ids = ArrayField(
        models.CharField(max_length=100),
        blank=True,
        default=list,
    )

    attribution_tags = JSONField(default=dict, blank=True)

    objects = OrderLineManager()

    class Meta(ModelWithMetadata.Meta):
        ordering = ("created_at", "id")
        indexes = [
            BTreeIndex(fields=["order"], name="orderline_order_idx"),
            BTreeIndex(fields=["product_sku"], name="orderline_sku_idx"),
            BTreeIndex(
                fields=["is_shipping_required"],
                name="orderline_shipping_idx",
            ),
            BTreeIndex(
                fields=["is_gift_card"],
                name="orderline_giftcard_idx",
            ),
            BTreeIndex(
                fields=["created_at"],
                name="orderline_created_idx",
            ),
            BTreeIndex(fields=["allocated_warehouse", "order"]),
            BTreeIndex(fields=["unit_cost"]),
            BTreeIndex(fields=["return_reason", "created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="orderline_quantity_positive",
            ),
            models.CheckConstraint(
                condition=Q(quantity_fulfilled__gte=0),
                name="orderline_quantity_fulfilled_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(quantity_fulfilled__lte=F("quantity")),
                name="orderline_quantity_fulfilled_lte_ordered",
            ),
        ]

    def __str__(self):
        return (
            f"{self.product_name} ({self.variant_name})"
            if self.variant_name
            else self.product_name
        )

    __hash__ = models.Model.__hash__

    def __eq__(self, other):
        if not isinstance(other, OrderLine):
            return NotImplemented
        return (
            self.variant == other.variant
            and self.quantity == other.quantity
        )

    def __ne__(self, other):
        return not self == other

    def __getstate__(self):
        return self.variant, self.quantity

    def __setstate__(self, data):
        self.variant, self.quantity = data

    @property
    def quantity_unfulfilled(self) -> Decimal:
        return self.quantity - self.quantity_fulfilled

    @property
    def is_digital(self) -> bool:
        if not hasattr(self, "_variant"):
            self._variant = self.variant
        return bool(
            self._variant
            and self._variant.is_digital()
            and hasattr(self._variant, "digital_content")
        )


# =====================================================================
# FULFILLMENT
# =====================================================================


class FulfillmentQueryset(models.QuerySet["Fulfillment"]):
    def with_related_data(self):
        return (
            self.select_related("order")
            .prefetch_related(
                "lines",
                "lines__order_line",
            )
        )


FulfillmentManager = models.Manager.from_queryset(FulfillmentQueryset)


class Fulfillment(ModelWithMetadata):
    fulfillment_order = models.PositiveIntegerField(editable=False)

    order = models.ForeignKey(
        Order,
        related_name="fulfillments",
        editable=False,
        on_delete=models.CASCADE,
        db_index=True,
    )

    status = models.CharField(
        max_length=32,
        default=FulfillmentStatus.FULFILLED,
        choices=FulfillmentStatus.CHOICES,
        db_index=True,
    )

    tracking_number = models.CharField(
        max_length=255,
        default="",
        blank=True,
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    shipping_refund_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        null=True,
        blank=True,
    )

    total_refund_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        null=True,
        blank=True,
    )

    objects = FulfillmentManager()

    class Meta(ModelWithMetadata.Meta):
        ordering = ("pk",)
        indexes = [
            BTreeIndex(fields=["order"], name="fulfillment_order_idx"),
            BTreeIndex(fields=["status"], name="fulfillment_status_idx"),
            BTreeIndex(
                fields=["tracking_number"],
                name="fulfillment_tracking_idx",
            ),
            BTreeIndex(
                fields=["created_at"],
                name="fulfillment_created_idx",
            ),
        ]

    def __str__(self):
        return f"Fulfillment #{self.composed_id}"

    def save(self, *args, **kwargs):
        if not self.pk:
            max_order = self.order.fulfillments.aggregate(
                Max("fulfillment_order")
            )
            self.fulfillment_order = (
                max_order.get("fulfillment_order__max") or 0
            ) + 1
        super().save(*args, **kwargs)

    @property
    def composed_id(self) -> str:
        return f"{self.order.number}-{self.fulfillment_order}"

    def can_edit(self) -> bool:
        return self.status != FulfillmentStatus.CANCELED

    def get_total_quantity(self) -> Decimal:
        if not hasattr(self, "_lines"):
            self._lines = list(self.lines.all())
        return sum(
            (line.quantity for line in self._lines),
            start=Decimal("0"),
        )

    @property
    def is_tracking_number_url(self) -> bool:
        return bool(self.tracking_number) and bool(
            match(r"^[-\w]+://", self.tracking_number)
        )


class FulfillmentLine(models.Model):
    order_line = models.ForeignKey(
        OrderLine,
        related_name="fulfillment_lines",
        on_delete=models.CASCADE,
        db_index=True,
    )

    fulfillment = models.ForeignKey(
        Fulfillment,
        related_name="lines",
        on_delete=models.CASCADE,
        db_index=True,
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )

    stock = models.ForeignKey(
        "ecommerce.Stock",
        related_name="fulfillment_lines",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["-id"]
        indexes = [
            BTreeIndex(
                fields=["order_line"],
                name="fulfillmentline_orderline_idx",
            ),
            BTreeIndex(
                fields=["fulfillment"],
                name="fulfillmentline_fulfillment_idx",
            ),
        ]

    def __str__(self):
        return f"{self.order_line.product_name} x {self.quantity}"


# =====================================================================
# ORDER EVENT
# =====================================================================


class OrderEventQueryset(models.QuerySet["OrderEvent"]):
    def with_related_data(self):
        return self.select_related("order", "user")


OrderEventManager = models.Manager.from_queryset(OrderEventQueryset)


class OrderEvent(models.Model):
    date = models.DateTimeField(
        default=now,
        editable=False,
        db_index=True,
    )

    type = models.CharField(
        max_length=255,
        choices=[
            (type_name.upper(), type_name)
            for type_name, _ in OrderEvents.CHOICES
        ],
        db_index=True,
    )

    order = models.ForeignKey(
        Order,
        related_name="events",
        on_delete=models.CASCADE,
        db_index=True,
    )

    parameters = JSONField(
        blank=True,
        default=dict,
        encoder=CustomJsonEncoder,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    related = models.ForeignKey(
        "self",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="related_events",
    )

    objects = OrderEventManager()

    class Meta:
        ordering = ("date",)
        indexes = [
            BTreeIndex(fields=["type"], name="orderevent_type_idx"),
            BTreeIndex(fields=["order"], name="orderevent_order_idx"),
            BTreeIndex(fields=["date"], name="orderevent_date_idx"),
            BTreeIndex(fields=["user"], name="orderevent_user_idx"),
            BTreeIndex(fields=["related"], name="orderevent_related_idx"),
        ]

    def __repr__(self):
        return (
            f"{self.__class__.__name__}"
            f"(type={self.type!r}, user={self.user!r})"
        )


# =====================================================================
# ORDER GRANTED REFUND
# =====================================================================


class OrderGrantedRefundQueryset(
    models.QuerySet["OrderGrantedRefund"]
):
    def with_related_data(self):
        return (
            self.select_related(
                "order",
                "user",
                "transaction_item",
            )
            .prefetch_related("lines")
        )


OrderGrantedRefundManager = models.Manager.from_queryset(
    OrderGrantedRefundQueryset
)


class OrderGrantedRefund(models.Model):
    created_at = models.DateTimeField(
        default=now,
        editable=False,
        db_index=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        editable=False,
        db_index=True,
    )

    amount_value = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )

    currency = models.CharField(
        max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH,
    )

    amount = MoneyField(
        amount_field="amount_value",
        currency_field="currency",
    )

    reason = models.TextField(
        blank=True,
        default="",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    order = models.ForeignKey(
        Order,
        related_name="granted_refunds",
        on_delete=models.CASCADE,
        db_index=True,
    )

    shipping_costs_included = models.BooleanField(default=False)

    transaction_item = models.ForeignKey(
        "payment.TransactionItem",
        related_name="granted_refund",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    status = models.CharField(
        choices=OrderGrantedRefundStatus.CHOICES,
        default=OrderGrantedRefundStatus.NONE,
        max_length=128,
        db_index=True,
    )

    objects = OrderGrantedRefundManager()

    class Meta:
        ordering = ("created_at", "id")
        indexes = [
            BTreeIndex(fields=["order"], name="orderrefund_order_idx"),
            BTreeIndex(fields=["status"], name="orderrefund_status_idx"),
            BTreeIndex(
                fields=["created_at"],
                name="orderrefund_created_idx",
            ),
            BTreeIndex(
                fields=["updated_at"],
                name="orderrefund_updated_idx",
            ),
        ]


class OrderGrantedRefundLine(models.Model):
    order_line = models.ForeignKey(
        OrderLine,
        related_name="granted_refund_lines",
        on_delete=models.CASCADE,
        db_index=True,
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )

    reason = models.TextField(
        blank=True,
        null=True,
        default="",
    )

    granted_refund = models.ForeignKey(
        OrderGrantedRefund,
        related_name="lines",
        on_delete=models.CASCADE,
        db_index=True,
    )

    class Meta:
        indexes = [
            BTreeIndex(
                fields=["order_line"],
                name="orderrefundline_orderline_idx",
            ),
            BTreeIndex(
                fields=["granted_refund"],
                name="orderrefundline_refund_idx",
            ),
        ]


# =====================================================================
# ORDER TRACKING EVENT
# =====================================================================


class OrderTrackingEvent(models.Model):
    """Real-time order tracking events."""

    EVENT_TYPES = [
        ("ORDER_PLACED", "Order Placed"),
        ("PAYMENT_AUTHORIZED", "Payment Authorized"),
        ("PAYMENT_CAPTURED", "Payment Captured"),
        ("ORDER_CONFIRMED", "Order Confirmed"),
        ("INVENTORY_ALLOCATED", "Inventory Allocated"),
        ("ORDER_SPLIT", "Order Split"),
        ("ITEM_PICKED", "Item Picked"),
        ("ITEM_PACKED", "Item Packed"),
        ("SHIPPING_LABEL_CREATED", "Shipping Label Created"),
        ("CARRIER_PICKUP", "Carrier Pickup"),
        ("IN_TRANSIT", "In Transit"),
        ("OUT_FOR_DELIVERY", "Out for Delivery"),
        ("DELIVERED", "Delivered"),
        ("DELIVERY_ATTEMPTED", "Delivery Attempted"),
        ("DELIVERY_FAILED", "Delivery Failed"),
        ("RETURN_REQUESTED", "Return Requested"),
        ("RETURN_RECEIVED", "Return Received"),
        ("REFUND_PROCESSED", "Refund Processed"),
    ]

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="tracking_events",
    )

    event_type = models.CharField(
        max_length=50,
        choices=EVENT_TYPES,
    )

    event_timestamp = models.DateTimeField()

    location = models.CharField(max_length=500, blank=True)

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )

    carrier = models.CharField(max_length=100, blank=True)

    tracking_number = models.CharField(max_length=100, blank=True)

    estimated_delivery = models.DateTimeField(null=True, blank=True)

    actual_delivery = models.DateTimeField(null=True, blank=True)

    event_data = JSONField(default=dict)

    class Meta:
        ordering = ["event_timestamp"]
        indexes = [
            models.Index(
                fields=["order", "event_timestamp"],
                name="tracking_order_time_idx",
            ),
            models.Index(
                fields=["event_type", "event_timestamp"],
                name="tracking_type_time_idx",
            ),
            models.Index(
                fields=["tracking_number"],
                name="tracking_number_idx",
            ),
        ]

    def __str__(self):
        return (
            f"Tracking Event {self.event_type} "
            f"for Order #{self.order.number} "
            f"at {self.event_timestamp}"
        )