# apps/backend/ecommerce/models/order.py

from decimal import Decimal
from operator import attrgetter
from re import match
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import BTreeIndex, GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.core.validators import MinValueValidator
from django.db import connection, models, transaction
from django.db.models import F, JSONField, Max, Q
from django.db.models.expressions import Exists, OuterRef
from django.utils.timezone import now
from django_measurement.models import MeasurementField
from measurement.measures import Weight

from ecommerce.models.channel import Channel
from ecommerce.models.discount import Voucher
from ecommerce.models.giftcard import GiftCard
from ecommerce.models.shipping import ShippingMethod

from core.models.metadata import ModelWithExternalReference, ModelWithMetadata
from core.models.utils.json_serializer import CustomJsonEncoder
from core.pricing import MoneyField, TaxedMoneyField
from core.units import WeightUnits
from core.weight import zero_weight

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


def get_order_number():
    """
    Generate the next order number.

    The import is intentionally local so model initialization does not
    create a circular import.
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


class Order(ModelWithMetadata, ModelWithExternalReference):
    """Customer order."""

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

    use_old_id = models.BooleanField(default=False)

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

    origin = models.CharField(
        max_length=32,
        choices=OrderOrigin.CHOICES,
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

    channel = models.ForeignKey(
        Channel,
        related_name="orders",
        on_delete=models.PROTECT,
        db_index=True,
    )

    # ------------------------------------------------------------------
    # Shipping prices
    # ------------------------------------------------------------------

    shipping_price_net_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
        editable=False,
    )

    shipping_price_net = MoneyField(
        amount_field="shipping_price_net_amount",
        currency_field="currency",
    )

    shipping_price_gross_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
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
        default=Decimal("0.0"),
    )

    base_shipping_price = MoneyField(
        amount_field="base_shipping_price_amount",
        currency_field="currency",
    )

    undiscounted_base_shipping_price_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )

    undiscounted_base_shipping_price = MoneyField(
        amount_field="undiscounted_base_shipping_price_amount",
        currency_field="currency",
    )

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

    checkout_token = models.CharField(
        max_length=36,
        blank=True,
        db_index=True,
    )

    # ------------------------------------------------------------------
    # Total prices
    # ------------------------------------------------------------------

    total_net_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )

    undiscounted_total_net_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
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
        default=Decimal("0.0"),
    )

    undiscounted_total_gross_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
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
        default=Decimal("0.0"),
    )

    total_authorized_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
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
    # General order information
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

    search_document = models.TextField(
        blank=True,
        default="",
    )

    search_vector = SearchVectorField(
        blank=True,
        null=True,
    )

    should_refresh_prices = models.BooleanField(default=True)

    tax_exemption = models.BooleanField(default=False)

    tax_error = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    # ------------------------------------------------------------------
    # Priority / flags
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
    # Delivery promise
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

    # ------------------------------------------------------------------
    # Customer experience
    # ------------------------------------------------------------------

    customer_satisfaction_score = models.IntegerField(
        null=True,
        blank=True,
    )

    net_promoter_score = models.IntegerField(
        null=True,
        blank=True,
    )

    would_repurchase = models.BooleanField(
        null=True,
    )

    review_id = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
    )

    # ------------------------------------------------------------------
    # Fraud / risk
    # ------------------------------------------------------------------

    fraud_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
    )

    fraud_risk_level = models.CharField(
        max_length=20,
        blank=True,
    )

    requires_manual_review = models.BooleanField(
        default=False,
    )

    reviewed_by_fraud_team = models.BooleanField(
        default=False,
    )

    # ------------------------------------------------------------------
    # Analytics / attribution
    # ------------------------------------------------------------------

    acquisition_channel = models.CharField(
        max_length=100,
        blank=True,
    )

    campaign_id = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
    )

    attribution_model = models.CharField(
        max_length=50,
        blank=True,
    )

    lifetime_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # ------------------------------------------------------------------
    # Environmental impact
    # ------------------------------------------------------------------

    carbon_footprint_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
    )

    is_carbon_neutral = models.BooleanField(
        default=False,
    )

    objects = OrderManager()

    class Meta:
        ordering = ("-number",)

        permissions = (
            ("manage_orders", "Manage orders."),
            ("manage_orders_import", "Manage orders import."),
        )

        indexes = [
            GinIndex(
                name="order_search_gin",
                fields=["search_document"],
                opclasses=["gin_trgm_ops"],
            ),
            GinIndex(
                name="order_tsearch",
                fields=["search_vector"],
            ),
            BTreeIndex(
                fields=["created_at"],
                name="order_created_at_idx",
            ),
            BTreeIndex(
                fields=["status"],
                name="order_status_idx",
            ),
            BTreeIndex(
                fields=["user_email"],
                name="order_user_email_idx",
            ),
            BTreeIndex(
                fields=["checkout_token"],
                name="order_checkout_token_idx",
            ),
            BTreeIndex(
                fields=["voucher_code"],
                name="order_voucher_code_idx",
            ),
            BTreeIndex(
                fields=["created_at", "status"],
                name="order_created_status_idx",
            ),
            BTreeIndex(
                fields=["priority_level", "created_at"],
            ),
            BTreeIndex(
                fields=["is_prime", "status"],
            ),
            BTreeIndex(
                fields=["promised_delivery_date", "status"],
            ),
            BTreeIndex(
                fields=["fraud_score", "created_at"],
            ),
            BTreeIndex(
                fields=["acquisition_channel", "created_at"],
            ),
        ]

    def __str__(self):
        return f"#{self.id}"

    def save(self, *args, **kwargs):
        """Update the search document before saving."""
        if (
            not self.pk
            or "update_fields" not in kwargs
            or "search_document" in kwargs["update_fields"]
        ):
            self.update_search_document()

        super().save(*args, **kwargs)

    def update_search_document(self):
        """Generate the searchable order document."""
        parts = [
            str(self.number),
            self.user_email,
            self.customer_note,
        ]

        if self.user:
            parts.extend(
                [
                    self.user.email,
                    self.user.first_name,
                    self.user.last_name,
                ]
            )

        if self.billing_address:
            parts.extend(
                [
                    self.billing_address.first_name,
                    self.billing_address.last_name,
                    self.billing_address.street_address_1,
                    self.billing_address.street_address_2,
                    self.billing_address.city,
                    self.billing_address.postal_code,
                ]
            )

        self.search_document = " ".join(
            part for part in parts if part
        )

    def is_fully_paid(self):
        """Return whether the order has been fully paid."""
        return self.total_charged_amount >= self.total_gross_amount

    def is_partly_paid(self):
        """Return whether the order has received any payment."""
        return self.total_charged_amount > 0

    def get_customer_email(self):
        """Return the customer's email address."""
        return self.user.email if self.user_id else self.user_email

    def get_last_payment(self) -> Optional[Payment]:
        """Return the most recent active payment."""
        if not hasattr(self, "_last_payment"):
            self._last_payment = (
                self.payments
                .exclude(partial=True)
                .order_by("-pk")
                .first()
            )

        return self._last_payment

    def is_pre_authorized(self):
        """Return whether the order has a successful authorization."""
        return self.payments.filter(
            is_active=True,
            transactions__kind=TransactionKind.AUTH,
            transactions__action_required=False,
            transactions__is_success=True,
        ).exists()

    def is_captured(self):
        """Return whether the order has a successful capture."""
        return self.payments.filter(
            is_active=True,
            transactions__kind=TransactionKind.CAPTURE,
            transactions__action_required=False,
            transactions__is_success=True,
        ).exists()

    def get_subtotal(self):
        """Calculate the subtotal using cached lines."""
        if not hasattr(self, "_lines"):
            self._lines = list(self.lines.all())

        return get_subtotal(
            self._lines,
            self.currency,
        )

    def is_shipping_required(self):
        """Return whether any order line requires shipping."""
        if not hasattr(self, "_lines"):
            self._lines = list(self.lines.all())

        return any(
            line.is_shipping_required
            for line in self._lines
        )

    def get_total_quantity(self):
        """Return total quantity across all order lines."""
        if not hasattr(self, "_lines"):
            self._lines = list(self.lines.all())

        return sum(
            line.quantity
            for line in self._lines
        )

    def is_draft(self):
        return self.status == OrderStatus.DRAFT

    def is_unconfirmed(self):
        return self.status == OrderStatus.UNCONFIRMED

    def is_expired(self):
        return self.status == OrderStatus.EXPIRED

    def is_open(self):
        statuses = {
            OrderStatus.UNFULFILLED,
            OrderStatus.PARTIALLY_FULFILLED,
        }

        return self.status in statuses

    def can_cancel(self):
        """Return whether the order can be cancelled."""
        if self.status in {
            OrderStatus.CANCELED,
            OrderStatus.DRAFT,
            OrderStatus.EXPIRED,
        }:
            return False

        if not hasattr(self, "_fulfillments"):
            self._fulfillments = list(
                self.fulfillments.all()
            )

        allowed_statuses = {
            FulfillmentStatus.CANCELED,
            FulfillmentStatus.REFUNDED,
            FulfillmentStatus.REPLACED,
            FulfillmentStatus.REFUNDED_AND_RETURNED,
            FulfillmentStatus.RETURNED,
        }

        return all(
            fulfillment.status in allowed_statuses
            for fulfillment in self._fulfillments
        )

    def can_capture(self, payment=None):
        """Return whether the order can be captured."""
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

    def can_void(self, payment=None):
        """Return whether the order can be voided."""
        if payment is None:
            payment = self.get_last_payment()

        return payment.can_void() if payment else False

    def can_refund(self, payment=None):
        """Return whether the order can be refunded."""
        if payment is None:
            payment = self.get_last_payment()

        return payment.can_refund() if payment else False

    def can_mark_as_paid(self):
        """Return whether the order can be manually marked as paid."""
        return not self.payments.exists()

    @property
    def total_balance(self):
        """Return the current payment balance."""
        return Money(
            amount=(
                self.total_charged_amount
                - self.total_gross_amount
            ),
            currency=self.currency,
        )


class OrderLineQueryset(models.QuerySet["OrderLine"]):
    def digital(self):
        """Return digital order lines."""
        return self.filter(
            variant__is_digital=True,
            variant__digital_content__isnull=False,
        )

    def physical(self):
        """Return physical order lines."""
        return self.filter(
            Q(variant__is_digital=False)
            | Q(variant__digital_content__isnull=True)
        )

    def with_related_data(self):
        """Return order lines with related product data."""
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

    product_name = models.CharField(
        max_length=386,
    )

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

    is_shipping_required = models.BooleanField(
        db_index=True,
    )

    is_gift_card = models.BooleanField(
        db_index=True,
    )

    is_gift = models.BooleanField(
        default=False,
        db_index=True,
    )

    quantity = models.IntegerField(
        validators=[MinValueValidator(1)],
    )

    quantity_fulfilled = models.IntegerField(
        validators=[MinValueValidator(0)],
        default=0,
    )

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
        default=Decimal("0.0"),
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
        default=Decimal("0.0"),
    )

    # ------------------------------------------------------------------
    # Unit price
    #
    # IMPORTANT:
    # TaxedMoneyField receives the amount field names and the actual
    # currency field separately.
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
        default=Decimal("0.0"),
    )

    undiscounted_unit_price_net_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
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
        default=Decimal("0.0"),
    )

    undiscounted_total_price_net_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
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
        default=Decimal("0.0"),
    )

    base_unit_price = MoneyField(
        amount_field="base_unit_price_amount",
        currency_field="currency",
    )

    undiscounted_base_unit_price_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
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

    bin_location = models.CharField(
        max_length=100,
        blank=True,
    )

    pick_path_sequence = models.IntegerField(
        null=True,
    )

    # ------------------------------------------------------------------
    # Quality / returns
    # ------------------------------------------------------------------

    return_reason = models.CharField(
        max_length=100,
        blank=True,
    )

    return_condition = models.CharField(
        max_length=50,
        blank=True,
    )

    is_defective = models.BooleanField(
        default=False,
    )

    defect_type = models.CharField(
        max_length=100,
        blank=True,
    )

    # ------------------------------------------------------------------
    # Customer experience
    # ------------------------------------------------------------------

    line_rating = models.IntegerField(
        null=True,
        blank=True,
    )

    line_review = models.TextField(
        blank=True,
    )

    # ------------------------------------------------------------------
    # Promotions / attribution
    # ------------------------------------------------------------------

    promotion_ids = ArrayField(
        models.CharField(max_length=100),
        blank=True,
        default=list,
    )

    attribution_tags = JSONField(
        default=dict,
        blank=True,
    )

    objects = OrderLineManager()

    class Meta(ModelWithMetadata.Meta):
        ordering = ("created_at", "id")

        indexes = [
            BTreeIndex(
                fields=["order"],
                name="orderline_order_idx",
            ),
            BTreeIndex(
                fields=["product_sku"],
                name="orderline_sku_idx",
            ),
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
            BTreeIndex(
                fields=["allocated_warehouse", "order"],
            ),
            BTreeIndex(
                fields=["unit_cost"],
            ),
            BTreeIndex(
                fields=["return_reason", "created_at"],
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
    def quantity_unfulfilled(self):
        return self.quantity - self.quantity_fulfilled

    @property
    def is_digital(self) -> bool:
        """Return whether the related product variant is digital."""
        if not hasattr(self, "_variant"):
            self._variant = self.variant

        return bool(
            self._variant
            and self._variant.is_digital()
            and hasattr(self._variant, "digital_content")
        )


class FulfillmentQueryset(models.QuerySet["Fulfillment"]):
    def with_related_data(self):
        """Return fulfillments with related order and lines."""
        return (
            self.select_related("order")
            .prefetch_related(
                "lines",
                "lines__order_line",
            )
        )


FulfillmentManager = models.Manager.from_queryset(
    FulfillmentQueryset
)


class Fulfillment(ModelWithMetadata):
    fulfillment_order = models.PositiveIntegerField(
        editable=False,
    )

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
            BTreeIndex(
                fields=["order"],
                name="fulfillment_order_idx",
            ),
            BTreeIndex(
                fields=["status"],
                name="fulfillment_status_idx",
            ),
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
        """Assign the fulfillment sequence number when creating."""
        if not self.pk:
            max_order = self.order.fulfillments.aggregate(
                Max("fulfillment_order")
            )

            self.fulfillment_order = (
                max_order.get("fulfillment_order__max") or 0
            ) + 1

        super().save(*args, **kwargs)

    @property
    def composed_id(self):
        return f"{self.order.number}-{self.fulfillment_order}"

    def can_edit(self):
        return self.status != FulfillmentStatus.CANCELED

    def get_total_quantity(self):
        """Return total quantity across fulfillment lines."""
        if not hasattr(self, "_lines"):
            self._lines = list(self.lines.all())

        return sum(
            line.quantity
            for line in self._lines
        )

    @property
    def is_tracking_number_url(self):
        """Return whether the tracking number is a URL."""
        return bool(
            self.tracking_number
        ) and match(
            r"^[-\w]+://",
            self.tracking_number,
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

    quantity = models.PositiveIntegerField()

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
        return (
            f"{self.order_line.product_name} x {self.quantity}"
        )


class OrderEventQueryset(models.QuerySet["OrderEvent"]):
    def with_related_data(self):
        """Return events with related order and user."""
        return self.select_related(
            "order",
            "user",
        )


OrderEventManager = models.Manager.from_queryset(
    OrderEventQueryset
)


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
            BTreeIndex(
                fields=["type"],
                name="orderevent_type_idx",
            ),
            BTreeIndex(
                fields=["order"],
                name="orderevent_order_idx",
            ),
            BTreeIndex(
                fields=["date"],
                name="orderevent_date_idx",
            ),
            BTreeIndex(
                fields=["user"],
                name="orderevent_user_idx",
            ),
            BTreeIndex(
                fields=["related"],
                name="orderevent_related_idx",
            ),
        ]

    def __repr__(self):
        return (
            f"{self.__class__.__name__}"
            f"(type={self.type!r}, user={self.user!r})"
        )


class OrderGrantedRefundQueryset(
    models.QuerySet["OrderGrantedRefund"]
):
    def with_related_data(self):
        """Return refunds with related objects."""
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

    shipping_costs_included = models.BooleanField(
        default=False,
    )

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
            BTreeIndex(
                fields=["order"],
                name="orderrefund_order_idx",
            ),
            BTreeIndex(
                fields=["status"],
                name="orderrefund_status_idx",
            ),
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

    quantity = models.PositiveIntegerField()

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


class OrderPerformanceMetrics(models.Model):
    """Order performance tracking."""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="metrics",
    )

    calculated_at = models.DateTimeField(
        auto_now_add=True,
    )

    customer_lifetime_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    customer_acquisition_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    customer_retention_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
    )

    days_to_fulfill = models.IntegerField()

    days_to_deliver = models.IntegerField()

    same_day_fulfillment_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
    )

    two_day_fulfillment_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
    )

    gross_margin = models.DecimalField(
        max_digits=5,
        decimal_places=4,
    )

    contribution_margin = models.DecimalField(
        max_digits=5,
        decimal_places=4,
    )

    fulfillment_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    shipping_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    packaging_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    perfect_order_score = models.IntegerField()

    defect_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
    )

    return_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
    )

    net_promoter_score = models.IntegerField(
        null=True,
    )

    customer_satisfaction_score = models.IntegerField(
        null=True,
    )

    review_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["order", "calculated_at"]
            ),
            models.Index(
                fields=["customer_retention_score"]
            ),
            models.Index(
                fields=["perfect_order_score"]
            ),
        ]

        ordering = ["-calculated_at"]

    def __str__(self):
        return (
            f"Metrics for Order #{self.order.number} "
            f"at {self.calculated_at}"
        )


class OrderSplit(models.Model):
    """Order splitting for multi-fulfillment."""

    parent_order = models.ForeignKey(
        Order,
        related_name="child_splits",
        on_delete=models.CASCADE,
    )

    child_order = models.ForeignKey(
        Order,
        related_name="parent_splits",
        on_delete=models.CASCADE,
    )

    split_type = models.CharField(
        max_length=50,
        choices=[
            ("AUTOMATIC", "Automatic Split"),
            ("MANUAL", "Manual Split"),
            ("WAREHOUSE", "Warehouse Split"),
            ("SHIPPING", "Shipping Method Split"),
        ],
    )

    reason = models.TextField(
        blank=True,
    )

    split_at = models.DateTimeField(
        auto_now_add=True,
    )

    split_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["parent_order", "child_order"],
                name="unique_order_split",
            )
        ]

        indexes = [
            models.Index(
                fields=["parent_order", "split_type"]
            ),
        ]

        ordering = ["-split_at"]

    def __str__(self):
        return (
            f"Split Order #{self.parent_order.number} "
            f"-> #{self.child_order.number}"
        )


class OrderMerge(models.Model):
    """Order merging."""

    source_orders = models.ManyToManyField(
        Order,
        related_name="merged_from",
    )

    target_order = models.ForeignKey(
        Order,
        related_name="merged_to",
        on_delete=models.CASCADE,
    )

    merge_type = models.CharField(
        max_length=50,
        choices=[
            ("CUSTOMER_REQUEST", "Customer Request"),
            ("AUTOMATIC", "Automatic Merge"),
            ("OPERATIONS", "Operations Merge"),
        ],
    )

    merge_reason = models.TextField()

    merged_at = models.DateTimeField(
        auto_now_add=True,
    )

    merged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["target_order", "merged_at"]
            ),
        ]

        ordering = ["-merged_at"]

    def __str__(self):
        source_order_numbers = ", ".join(
            str(order.number)
            for order in self.source_orders.all()
        )

        return (
            f"Merged Orders [{source_order_numbers}] "
            f"-> #{self.target_order.number}"
        )


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

    location = models.CharField(
        max_length=500,
        blank=True,
    )

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
    )

    carrier = models.CharField(
        max_length=100,
        blank=True,
    )

    tracking_number = models.CharField(
        max_length=100,
        blank=True,
    )

    estimated_delivery = models.DateTimeField(
        null=True,
    )

    actual_delivery = models.DateTimeField(
        null=True,
    )

    event_data = JSONField(
        default=dict,
    )

    class Meta:
        ordering = ["event_timestamp"]

        indexes = [
            models.Index(
                fields=["order", "event_timestamp"]
            ),
            models.Index(
                fields=["event_type", "event_timestamp"]
            ),
            models.Index(
                fields=["tracking_number"]
            ),
        ]

    def __str__(self):
        return (
            f"Tracking Event {self.event_type} "
            f"for Order #{self.order.number} "
            f"at {self.event_timestamp}"
        )


class OrderFraudAssessment(models.Model):
    """Order fraud detection assessment."""

    RISK_LEVELS = [
        ("LOW", "Low Risk"),
        ("MEDIUM", "Medium Risk"),
        ("HIGH", "High Risk"),
        ("VERY_HIGH", "Very High Risk"),
        ("BLOCKED", "Blocked"),
    ]

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="fraud_assessment",
    )

    risk_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
    )

    risk_level = models.CharField(
        max_length=20,
        choices=RISK_LEVELS,
    )

    assessment_reason = models.TextField()

    velocity_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
    )

    geo_risk_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
    )

    ip_risk_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
    )

    device_risk_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
    )

    behavioral_risk_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
    )

    is_email_verified = models.BooleanField(
        default=False,
    )

    is_phone_verified = models.BooleanField(
        default=False,
    )

    is_address_verified = models.BooleanField(
        default=False,
    )

    is_payment_verified = models.BooleanField(
        default=False,
    )

    model_version = models.CharField(
        max_length=50,
    )

    model_confidence = models.DecimalField(
        max_digits=5,
        decimal_places=4,
    )

    feature_vector = JSONField(
        default=dict,
    )

    assessed_at = models.DateTimeField(
        auto_now_add=True,
    )

    assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
    )

    review_required = models.BooleanField(
        default=False,
    )

    reviewed_at = models.DateTimeField(
        null=True,
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="fraud_reviews",
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["risk_level", "assessed_at"]
            ),
            models.Index(
                fields=["risk_score"]
            ),
            models.Index(
                fields=["review_required", "assessed_at"]
            ),
        ]

        ordering = ["-assessed_at"]

    def __str__(self):
        return (
            f"Fraud Assessment for Order #{self.order.number} "
            f"- Risk: {self.risk_level}"
        )


class OrderPromise(models.Model):
    """Order delivery and service promises."""

    PROMISE_TYPES = [
        ("DELIVERY", "Delivery Promise"),
        ("SHIPPING", "Shipping Promise"),
        ("AVAILABILITY", "Availability Promise"),
        ("PRICE", "Price Promise"),
    ]

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="promises",
    )

    promise_type = models.CharField(
        max_length=20,
        choices=PROMISE_TYPES,
    )

    promised_by = models.DateTimeField()

    promised_value = models.CharField(
        max_length=500,
    )

    actual_value = models.CharField(
        max_length=500,
        null=True,
        blank=True,
    )

    fulfilled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    is_met = models.BooleanField(
        null=True,
    )

    broken_reason = models.TextField(
        blank=True,
    )

    compensation_applied = models.BooleanField(
        default=False,
    )

    compensation_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
    )

    compensation_type = models.CharField(
        max_length=50,
        blank=True,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["order", "promise_type"]
            ),
            models.Index(
                fields=["is_met", "promised_by"]
            ),
        ]

        ordering = ["-promised_by"]

    def __str__(self):
        if self.is_met:
            status = "Met"
        elif self.is_met is False:
            status = "Broken"
        else:
            status = "Pending"

        return (
            f"{self.promise_type} Promise "
            f"for Order #{self.order.number} - {status}"
        )
