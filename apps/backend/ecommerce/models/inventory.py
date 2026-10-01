# apps/backend/ecommerce/models/inventory.py

"""
Inventory and stock models for the ecommerce application.

ARCHITECTURE
------------
This module owns stock, allocation, reservation, transfer, and inventory management.
"""

import uuid
from collections.abc import Iterable
from typing import Optional, Union

from django.conf import settings
from django.contrib.postgres.indexes import BTreeIndex, GinIndex
from django.db import models, transaction
from django.db.models import (
    F,
    OuterRef,
    Prefetch,
    Q,
    QuerySet,
    Subquery,
    Sum,
)
from django.db.models.functions import Coalesce
from django.utils import timezone

from core.models.metadata import ModelWithMetadata
from ecommerce.models.channel import Channel
from ecommerce.models.checkout import CheckoutLine
from ecommerce.models.order import OrderLine
from ecommerce.models.product import (
    Product,
    ProductVariant,
    ProductVariantChannelListing,
)
from ecommerce.models.warehouse import Warehouse


# ============================================================================
# STOCK MODELS
# ============================================================================


class StockQuerySet(models.QuerySet["Stock"]):
    def annotate_available_quantity(self) -> QuerySet["Stock"]:
        """Annotate each stock row with the quantity currently available after allocations."""
        return self.annotate(
            available_quantity=(
                F("quantity")
                - Coalesce(
                    Sum(
                        "allocations__quantity_allocated",
                        filter=Q(
                            allocations__quantity_allocated__gt=0,
                        ),
                    ),
                    0,
                )
            ),
        )

    def annotate_reserved_quantity(self) -> QuerySet["Stock"]:
        """Annotate each stock row with currently reserved quantity."""
        return self.annotate(
            reserved_quantity=Coalesce(
                Sum(
                    "reservations__quantity_reserved",
                    filter=Q(
                        reservations__reserved_until__gt=timezone.now(),
                    ),
                ),
                0,
            ),
        )

    def for_channel_and_click_and_collect(
        self,
        channel_slug: str,
    ) -> QuerySet["Stock"]:
        return (
            self.filter(
                warehouse__channelwarehouse__channel__slug=channel_slug,
            )
            .select_related(
                "product_variant",
                "warehouse",
            )
            .distinct()
        )

    def for_channel_and_country(
        self,
        channel_slug: str,
        country_code: Optional[str] = None,
        include_cc_warehouses: bool = False,
    ) -> QuerySet["Stock"]:
        qs = (
            self.select_related(
                "product_variant",
                "warehouse",
            )
            .filter(
                warehouse__channelwarehouse__channel__slug=channel_slug,
            )
        )

        if country_code:
            qs = qs.filter(
                warehouse__shipping_zones__countries__contains=country_code,
                warehouse__shipping_zones__channel__slug=channel_slug,
            )

        if include_cc_warehouses or not country_code:
            from .constants import WarehouseClickAndCollectOption
            qs = qs.filter(
                Q(
                    warehouse__click_and_collect_option__in=[
                        WarehouseClickAndCollectOption.LOCAL_STOCK,
                        WarehouseClickAndCollectOption.ALL_WAREHOUSES,
                    ]
                )
            )

        return qs.distinct()

    def get_variant_stocks_for_country(
        self,
        country_code: str,
        channel_slug: str,
        product_variant: ProductVariant,
    ) -> "Stock":
        return self.for_channel_and_country(
            channel_slug,
            country_code,
        ).get(
            product_variant=product_variant,
        )

    def get_variants_stocks_for_country(
        self,
        country_code: str,
        channel_slug: str,
        products_variants: Iterable[ProductVariant],
    ) -> QuerySet["Stock"]:
        return self.for_channel_and_country(
            channel_slug,
            country_code,
        ).filter(
            product_variant__in=products_variants,
        )

    def get_product_stocks_for_country_and_channel(
        self,
        country_code: str,
        channel_slug: str,
        product: Product,
    ) -> QuerySet["Stock"]:
        return self.for_channel_and_country(
            channel_slug,
            country_code,
        ).filter(
            product_variant__product_id=product.pk,
        )


StockManager = models.Manager.from_queryset(StockQuerySet)


class Stock(models.Model):
    """Stock model for tracking inventory at warehouses."""

    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="stocks",
        db_index=True,
    )

    product_variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name="stocks",
        db_index=True,
    )

    quantity = models.IntegerField(
        default=0,
    )

    quantity_allocated = models.IntegerField(
        default=0,
    )

    low_stock_threshold = models.PositiveIntegerField(
        default=10,
        help_text="Alert when stock falls below this level",
    )

    last_restocked_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    restock_lead_time_days = models.PositiveIntegerField(
        default=7,
        help_text="Days to restock",
    )

    objects = StockManager()

    class Meta:
        ordering = ("pk",)
        indexes = [
            BTreeIndex(
                fields=["quantity"],
                name="stock_quantity_idx",
            ),
            BTreeIndex(
                fields=["quantity_allocated"],
                name="stock_allocated_idx",
            ),
            BTreeIndex(
                fields=[
                    "warehouse",
                    "product_variant",
                    "quantity",
                ],
                name="stock_warehouse_variant_idx",
            ),
            BTreeIndex(
                fields=["low_stock_threshold"],
                name="stock_low_threshold_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["warehouse", "product_variant"],
                name="unique_warehouse_product_variant",
            ),
            models.CheckConstraint(
                condition=Q(quantity__gte=0),
                name="stock_quantity_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(quantity_allocated__gte=0),
                name="stock_allocated_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.product_variant} at {self.warehouse}"

    @transaction.atomic
    def increase_stock(
        self,
        quantity: int,
        commit: bool = True,
        reason: str = "",
        user=None,
    ) -> None:
        """Increase stock quantity and create an audit history record."""
        if quantity <= 0:
            raise ValueError(
                "Stock increase quantity must be greater than zero."
            )

        previous_quantity = self.quantity

        if commit:
            self.quantity = F("quantity") + quantity
            self.save(
                update_fields=["quantity"],
            )
            self.refresh_from_db(
                fields=["quantity"],
            )

            StockHistory.objects.create(
                stock=self,
                product_variant=self.product_variant,
                warehouse=self.warehouse,
                quantity_change=quantity,
                previous_quantity=previous_quantity,
                new_quantity=self.quantity,
                change_type=StockHistory.ChangeType.RESTOCK,
                reason=reason or "Restock",
                user=user,
            )
        else:
            self.quantity = previous_quantity + quantity

    @transaction.atomic
    def decrease_stock(
        self,
        quantity: int,
        commit: bool = True,
        reason: str = "",
        user=None,
    ) -> None:
        """Decrease stock quantity and create an audit history record."""
        if quantity <= 0:
            raise ValueError(
                "Stock decrease quantity must be greater than zero."
            )

        if quantity > self.available_quantity:
            raise ValueError(
                f"Cannot decrease stock by {quantity}; "
                f"only {self.available_quantity} units are available."
            )

        previous_quantity = self.quantity

        if commit:
            self.quantity = F("quantity") - quantity
            self.save(
                update_fields=["quantity"],
            )
            self.refresh_from_db(
                fields=["quantity"],
            )

            StockHistory.objects.create(
                stock=self,
                product_variant=self.product_variant,
                warehouse=self.warehouse,
                quantity_change=-quantity,
                previous_quantity=previous_quantity,
                new_quantity=self.quantity,
                change_type=StockHistory.ChangeType.REMOVAL,
                reason=reason or "Removal",
                user=user,
            )
        else:
            self.quantity = previous_quantity - quantity

    @property
    def available_quantity(self) -> int:
        allocated = (
            self.allocations.aggregate(
                total=Coalesce(
                    Sum("quantity_allocated"),
                    0,
                )
            )["total"]
            or 0
        )

        return max(
            self.quantity - allocated,
            0,
        )

    @property
    def is_low_stock(self) -> bool:
        return self.available_quantity <= self.low_stock_threshold


# ============================================================================
# STOCK HISTORY MODEL
# ============================================================================


class StockHistory(models.Model):
    """Complete audit trail for stock movements."""

    class ChangeType(models.TextChoices):
        RESTOCK = "restock", "Restock"
        REMOVAL = "removal", "Removal"
        RESERVED = "reserved", "Reserved"
        RELEASED = "released", "Released"
        ADJUSTMENT = "adjustment", "Adjustment"
        RETURN = "return", "Return"
        DAMAGED = "damaged", "Damaged"
        LOST = "lost", "Lost"
        TRANSFER_OUT = "transfer_out", "Transfer Out"
        TRANSFER_IN = "transfer_in", "Transfer In"
        COUNTED = "counted", "Counted"
        SYSTEM_ADJUSTMENT = "system_adjustment", "System Adjustment"

    stock = models.ForeignKey(
        Stock,
        related_name="history",
        on_delete=models.CASCADE,
        db_index=True,
        help_text="Stock record this history belongs to",
    )

    product_variant = models.ForeignKey(
        ProductVariant,
        related_name="stock_history",
        on_delete=models.CASCADE,
        db_index=True,
        help_text="Product variant",
    )

    warehouse = models.ForeignKey(
        Warehouse,
        related_name="stock_history",
        on_delete=models.CASCADE,
        db_index=True,
        help_text="Warehouse location",
    )

    quantity_change = models.IntegerField(
        help_text="Change in quantity (positive for increase, negative for decrease)",
    )

    previous_quantity = models.PositiveIntegerField(
        help_text="Quantity before the change",
    )

    new_quantity = models.PositiveIntegerField(
        help_text="Quantity after the change",
    )

    reserved_change = models.IntegerField(
        default=0,
        help_text="Change in reserved quantity",
    )

    previous_reserved = models.PositiveIntegerField(
        default=0,
        help_text="Reserved quantity before the change",
    )

    new_reserved = models.PositiveIntegerField(
        default=0,
        help_text="Reserved quantity after the change",
    )

    change_type = models.CharField(
        max_length=20,
        choices=ChangeType.choices,
        db_index=True,
        help_text="Type of stock change",
    )

    reason = models.TextField(
        blank=True,
        help_text="Reason for the change",
    )

    reference = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        help_text="Reference number (order ID, transfer ID, etc.)",
    )

    order = models.ForeignKey(
        "ecommerce.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_history",
        help_text="Related order",
    )

    order_line = models.ForeignKey(
        OrderLine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_history",
        help_text="Related order line",
    )

    fulfillment = models.ForeignKey(
        "ecommerce.Fulfillment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_history",
        help_text="Related fulfillment",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_changes",
        help_text="User who performed the change",
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When the change occurred",
    )

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            BTreeIndex(
                fields=["stock", "created_at"],
                name="stock_history_stock_created_idx",
            ),
            BTreeIndex(
                fields=["product_variant", "change_type"],
                name="stock_history_variant_type_idx",
            ),
            BTreeIndex(
                fields=["warehouse", "created_at"],
                name="stock_wh_created_idx",
            ),
            BTreeIndex(
                fields=["change_type", "created_at"],
                name="stock_history_type_created_idx",
            ),
            BTreeIndex(
                fields=["reference"],
                name="stock_history_reference_idx",
            ),
            BTreeIndex(
                fields=["order"],
                name="stock_history_order_idx",
            ),
            GinIndex(
                fields=["reason"],
                name="stock_history_reason_gin",
                opclasses=["gin_trgm_ops"],
            ),
        ]
        verbose_name = "Stock History"
        verbose_name_plural = "Stock Histories"

    def __str__(self) -> str:
        return (
            f"{self.product_variant.sku} - "
            f"{self.change_type} - "
            f"{self.quantity_change} at {self.created_at}"
        )

    @property
    def is_increase(self) -> bool:
        return self.quantity_change > 0

    @property
    def is_decrease(self) -> bool:
        return self.quantity_change < 0

    @classmethod
    def create_from_stock_change(
        cls,
        stock: Stock,
        quantity_change: int,
        change_type: str,
        reason: str = "",
        reference: str = "",
        user=None,
        **kwargs,
    ) -> "StockHistory":
        """Create a stock history entry from an existing stock change."""
        new_quantity = stock.quantity
        previous_quantity = max(
            new_quantity - quantity_change,
            0,
        )

        return cls.objects.create(
            stock=stock,
            product_variant=stock.product_variant,
            warehouse=stock.warehouse,
            quantity_change=quantity_change,
            previous_quantity=previous_quantity,
            new_quantity=new_quantity,
            change_type=change_type,
            reason=reason,
            reference=reference,
            user=user,
            **kwargs,
        )


# ============================================================================
# RESERVATION & ALLOCATION MODELS
# ============================================================================


class AllocationQueryset(models.QuerySet["Allocation"]):
    def annotate_stock_available_quantity(
        self,
    ) -> QuerySet["Allocation"]:
        return self.annotate(
            stock_available_quantity=(
                F("stock__quantity")
                - Coalesce(
                    Sum(
                        "stock__allocations__quantity_allocated",
                    ),
                    0,
                )
            )
        )

    def available_quantity_for_stock(
        self,
        stock: Stock,
    ) -> int:
        allocated = (
            self.filter(stock=stock).aggregate(
                total=Sum("quantity_allocated"),
            )["total"]
            or 0
        )

        return max(
            stock.quantity - allocated,
            0,
        )


AllocationManager = models.Manager.from_queryset(AllocationQueryset)


class Allocation(models.Model):
    """Stock allocation for order lines."""

    order_line = models.ForeignKey(
        OrderLine,
        on_delete=models.CASCADE,
        related_name="allocations",
        db_index=True,
    )

    stock = models.ForeignKey(
        Stock,
        on_delete=models.CASCADE,
        related_name="allocations",
        db_index=True,
    )

    quantity_allocated = models.PositiveIntegerField(
        default=0,
    )

    objects = AllocationManager()

    class Meta:
        ordering = ("pk",)
        indexes = [
            BTreeIndex(
                fields=["quantity_allocated"],
                name="allocation_qty_idx",
            ),
            BTreeIndex(
                fields=[
                    "order_line",
                    "stock",
                    "quantity_allocated",
                ],
                name="allocation_order_stock_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["order_line", "stock"],
                name="unique_allocation_order_line_stock",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.order_line} allocated "
            f"{self.quantity_allocated}"
        )


class ReservationQuerySet(models.QuerySet["Reservation"]):
    def not_expired(self) -> QuerySet["Reservation"]:
        return self.filter(
            reserved_until__gt=timezone.now(),
        )

    def exclude_checkout_lines(
        self,
        checkout_lines: Optional[
            Iterable[CheckoutLine]
        ],
    ) -> QuerySet["Reservation"]:
        if not checkout_lines:
            return self

        return self.exclude(
            checkout_line__in=checkout_lines,
        )


ReservationManager = models.Manager.from_queryset(ReservationQuerySet)


class Reservation(models.Model):
    """Stock reservation for checkout lines."""

    checkout_line = models.ForeignKey(
        CheckoutLine,
        on_delete=models.CASCADE,
        related_name="reservations",
        db_index=True,
    )

    stock = models.ForeignKey(
        Stock,
        on_delete=models.CASCADE,
        related_name="reservations",
        db_index=True,
    )

    quantity_reserved = models.PositiveIntegerField(
        default=0,
    )

    reserved_until = models.DateTimeField(
        db_index=True,
    )

    objects = ReservationManager()

    class Meta:
        indexes = [
            BTreeIndex(
                fields=[
                    "checkout_line",
                    "reserved_until",
                ],
                name="reservation_line_until_idx",
            ),
            BTreeIndex(
                fields=[
                    "stock",
                    "reserved_until",
                ],
                name="reservation_stock_until_idx",
            ),
        ]
        ordering = ("pk",)
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "checkout_line",
                    "stock",
                ],
                name="unique_reservation_checkout_line_stock",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Reserved {self.quantity_reserved} "
            f"until {self.reserved_until}"
        )


class PreorderAllocation(models.Model):
    """Preorder allocation for order lines."""

    order_line = models.ForeignKey(
        OrderLine,
        on_delete=models.CASCADE,
        related_name="preorder_allocations",
        db_index=True,
    )

    quantity = models.PositiveIntegerField(
        default=0,
    )

    product_variant_channel_listing = models.ForeignKey(
        ProductVariantChannelListing,
        on_delete=models.CASCADE,
        related_name="preorder_allocations",
        db_index=True,
    )

    class Meta:
        ordering = ("pk",)
        indexes = [
            BTreeIndex(
                fields=[
                    "order_line",
                    "product_variant_channel_listing",
                ],
                name="prealloc_order_list_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "order_line",
                    "product_variant_channel_listing",
                ],
                name="unique_preorder_allocation_order_listing",
            ),
        ]


class PreorderReservation(models.Model):
    """Preorder reservation for checkout lines."""

    checkout_line = models.ForeignKey(
        CheckoutLine,
        on_delete=models.CASCADE,
        related_name="preorder_reservations",
        db_index=True,
    )

    product_variant_channel_listing = models.ForeignKey(
        ProductVariantChannelListing,
        on_delete=models.CASCADE,
        related_name="preorder_reservations",
        db_index=True,
    )

    quantity_reserved = models.PositiveIntegerField(
        default=0,
    )

    reserved_until = models.DateTimeField(
        db_index=True,
    )

    objects = ReservationManager()

    class Meta:
        indexes = [
            BTreeIndex(
                fields=[
                    "checkout_line",
                    "reserved_until",
                ],
                name="preorder_res_line_until_idx",
            ),
            BTreeIndex(
                fields=["reserved_until"],
                name="preorder_reservation_until_idx",
            ),
        ]
        ordering = ("pk",)
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "checkout_line",
                    "product_variant_channel_listing",
                ],
                name="unique_preorder_reservation_checkout_listing",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Preorder {self.quantity_reserved} "
            f"until {self.reserved_until}"
        )


# ============================================================================
# RETURNS MANAGEMENT
# ============================================================================


class ReturnsManagement(models.Model):
    """Returns management for inventory."""

    rma_number = models.CharField(
        max_length=50,
        unique=True,
    )

    quantity_returned = models.IntegerField()

    quantity_restockable = models.IntegerField(
        default=0,
    )

    quantity_damaged = models.IntegerField(
        default=0,
    )

    inspection_date = models.DateTimeField(
        null=True,
    )

    inspection_notes = models.TextField(
        blank=True,
    )

    quality_score = models.IntegerField(
        null=True,
    )

    refund_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
    )

    restocking_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    disposal_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    received_at = models.DateTimeField()

    inspected_at = models.DateTimeField(
        null=True,
    )

    restocked_at = models.DateTimeField(
        null=True,
    )

    completed_at = models.DateTimeField(
        null=True,
    )

    return_reason = models.CharField(
        max_length=100,
    )

    return_category = models.CharField(
        max_length=50,
    )

    customer_satisfaction_score = models.IntegerField(
        null=True,
    )

    inspector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
    )

    order = models.ForeignKey(
        "ecommerce.Order",
        on_delete=models.CASCADE,
    )

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
    )

    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["rma_number"],
                name="returns_rma_number_idx",
            ),
            models.Index(
                fields=["warehouse", "received_at"],
                name="returns_warehouse_received_idx",
            ),
            models.Index(
                fields=["return_reason", "return_category"],
                name="returns_reason_category_idx",
            ),
        ]

    def __str__(self) -> str:
        return self.rma_number


# ============================================================================
# INVENTORY PREDICTION
# ============================================================================


class InventoryPrediction(models.Model):
    """Inventory demand prediction."""

    prediction_date = models.DateField()

    forecast_day_7 = models.IntegerField(
        default=0,
    )

    forecast_day_14 = models.IntegerField(
        default=0,
    )

    forecast_day_30 = models.IntegerField(
        default=0,
    )

    forecast_day_60 = models.IntegerField(
        default=0,
    )

    forecast_day_90 = models.IntegerField(
        default=0,
    )

    confidence_low = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0.8,
    )

    confidence_high = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0.95,
    )

    seasonal_factor = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=1.0,
    )

    promotion_factor = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=1.0,
    )

    supplier_lead_time_days = models.IntegerField(
        default=14,
    )

    safety_stock_days = models.IntegerField(
        default=7,
    )

    reorder_point = models.IntegerField(
        default=0,
    )

    reorder_quantity = models.IntegerField(
        default=0,
    )

    economic_order_quantity = models.IntegerField(
        default=0,
    )

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
    )

    warehouse = models.ForeignKey(
        Warehouse,
        null=True,
        on_delete=models.CASCADE,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "variant",
                    "-prediction_date",
                ],
                name="inv_prediction_var_date_idx",
            ),
            models.Index(
                fields=[
                    "warehouse",
                    "prediction_date",
                    "reorder_point",
                ],
                name="inv_prediction_wh_date_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "variant",
                    "warehouse",
                    "prediction_date",
                ],
                name="unique_inventory_prediction",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.variant} - "
            f"{self.prediction_date}"
        )


# ============================================================================
# INVENTORY HEALTH METRICS
# ============================================================================


class InventoryHealthMetrics(models.Model):
    """Inventory health metrics for stock management."""

    AGING_BUCKET_CHOICES = [
        ("FRESH", "< 30 days"),
        ("CURRENT", "30-60 days"),
        ("AGING", "60-90 days"),
        ("OLD", "90-180 days"),
        ("OBSOLETE", "> 180 days"),
    ]

    ACTION_CHOICES = [
        ("INCREASE", "Increase Stock"),
        ("DECREASE", "Decrease Stock"),
        ("HOLD", "Maintain Current Level"),
        ("LIQUIDATE", "Liquidate Stock"),
        ("TRANSFER", "Transfer to Another Warehouse"),
    ]

    calculated_date = models.DateField(
        auto_now_add=True,
    )

    days_of_supply = models.IntegerField(
        default=0,
    )

    stock_turnover_ratio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    sell_through_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0,
    )

    inventory_age_days = models.IntegerField(
        default=0,
    )

    aging_bucket = models.CharField(
        max_length=20,
        choices=AGING_BUCKET_CHOICES,
    )

    inventory_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    holding_cost_per_day = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    obsolescence_risk_score = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0,
    )

    in_stock_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=1.0,
    )

    fill_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=1.0,
    )

    backorder_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0,
    )

    recommended_action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
    )

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
    )

    warehouse = models.ForeignKey(
        Warehouse,
        null=True,
        on_delete=models.CASCADE,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "variant",
                    "-calculated_date",
                ],
                name="inv_health_vart_date_idx",
            ),
            models.Index(
                fields=[
                    "warehouse",
                    "aging_bucket",
                    "obsolescence_risk_score",
                ],
                name="inventory_health_wh_aging_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "variant",
                    "warehouse",
                    "calculated_date",
                ],
                name="unique_inventory_health_metrics",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.variant} - "
            f"{self.warehouse} - "
            f"{self.calculated_date}"
        )


# ============================================================================
# INTER-WAREHOUSE TRANSFERS
# ============================================================================


class InterWarehouseTransfer(models.Model):
    """Inter-warehouse stock transfer."""

    STATUS_CHOICES = [
        ("REQUESTED", "Transfer Requested"),
        ("APPROVED", "Approved"),
        ("PICKING", "Picking at Source"),
        ("IN_TRANSIT", "In Transit"),
        ("RECEIVING", "Receiving at Destination"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    ]

    transfer_number = models.CharField(
        max_length=50,
        unique=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="REQUESTED",
        db_index=True,
    )

    requested_date = models.DateTimeField(
        auto_now_add=True,
    )

    expected_transfer_date = models.DateField()

    actual_transfer_date = models.DateField(
        blank=True,
        null=True,
    )

    items = models.JSONField(
        default=list,
    )

    carrier = models.CharField(
        max_length=100,
        blank=True,
    )

    tracking_number = models.CharField(
        max_length=100,
        blank=True,
    )

    estimated_transit_days = models.IntegerField(
        default=2,
    )

    transfer_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    shipping_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    handling_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

    destination_warehouse = models.ForeignKey(
        Warehouse,
        related_name="inbound_transfers",
        on_delete=models.CASCADE,
    )

    source_warehouse = models.ForeignKey(
        Warehouse,
        related_name="outbound_transfers",
        on_delete=models.CASCADE,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["transfer_number"],
                name="transfer_number_idx",
            ),
            models.Index(
                fields=[
                    "source_warehouse",
                    "expected_transfer_date",
                ],
                name="transfer_source_expected_idx",
            ),
            models.Index(
                fields=[
                    "destination_warehouse",
                    "status",
                ],
                name="transfer_dest_status_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~Q(
                    source_warehouse=F("destination_warehouse")
                ),
                name="transfer_source_destination_different",
            ),
        ]

    def __str__(self) -> str:
        return self.transfer_number


# ============================================================================
# WAREHOUSE PERFORMANCE
# ============================================================================


class WarehousePerformance(models.Model):
    """Warehouse performance metrics."""

    date = models.DateField()

    total_orders_fulfilled = models.IntegerField(
        default=0,
    )

    total_units_picked = models.IntegerField(
        default=0,
    )

    total_shipments = models.IntegerField(
        default=0,
    )

    picks_per_hour = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    order_cycle_time_minutes = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    inventory_accuracy_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=1.0,
    )

    fulfillment_cost_per_order = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    shipping_cost_per_order = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    labor_cost_per_order = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    perfect_order_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=1.0,
    )

    damage_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0,
    )

    return_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0,
    )

    capacity_utilization = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0,
    )

    peak_utilization = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0,
    )

    available_capacity = models.IntegerField(
        default=0,
    )

    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "warehouse",
                    "-date",
                ],
                name="warehouse_perf_wh_date_idx",
            ),
            models.Index(
                fields=[
                    "date",
                    "perfect_order_rate",
                ],
                name="warehouse_perf_date_rate_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "warehouse",
                    "date",
                ],
                name="unique_warehouse_performance",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.warehouse} - "
            f"{self.date}"
        )


# ============================================================================
# WAREHOUSE TASK
# ============================================================================


class WarehouseTask(models.Model):
    """Warehouse task management."""

    TASK_TYPE_CHOICES = [
        ("PICKING", "Order Picking"),
        ("PACKING", "Order Packing"),
        ("RECEIVING", "Inventory Receiving"),
        ("PUTAWAY", "Stock Putaway"),
        ("COUNT", "Cycle Counting"),
        ("TRANSFER", "Stock Transfer"),
        ("VALUEADDED", "Value-Added Service"),
    ]

    TASK_STATUS_CHOICES = [
        ("CREATED", "Task Created"),
        ("ASSIGNED", "Assigned to Worker"),
        ("IN_PROGRESS", "In Progress"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    ]

    task_id = models.CharField(
        max_length=50,
        unique=True,
    )

    task_type = models.CharField(
        max_length=20,
        choices=TASK_TYPE_CHOICES,
    )

    task_status = models.CharField(
        max_length=20,
        choices=TASK_STATUS_CHOICES,
        default="CREATED",
        db_index=True,
    )

    assigned_at = models.DateTimeField(
        null=True,
    )

    priority = models.IntegerField(
        default=0,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    started_at = models.DateTimeField(
        null=True,
    )

    completed_at = models.DateTimeField(
        null=True,
    )

    estimated_duration_minutes = models.IntegerField()

    actual_duration_minutes = models.IntegerField(
        null=True,
    )

    reference_id = models.CharField(
        max_length=100,
        blank=True,
    )

    location_from = models.CharField(
        max_length=100,
        blank=True,
    )

    location_to = models.CharField(
        max_length=100,
        blank=True,
    )

    items = models.JSONField(
        default=list,
    )

    units_processed = models.IntegerField(
        default=0,
    )

    accuracy_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
    )

    quality_score = models.IntegerField(
        null=True,
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["task_id"],
                name="warehouse_task_id_idx",
            ),
            models.Index(
                fields=[
                    "warehouse",
                    "task_type",
                    "priority",
                ],
                name="ware_task_type_pri_idx",
            ),
            models.Index(
                fields=[
                    "assigned_to",
                    "task_status",
                ],
                name="ware_task_assigned_sta_idx",
            ),
            models.Index(
                fields=[
                    "created_at",
                    "task_status",
                ],
                name="ware_task_created_sta_idx",
            ),
        ]

    def __str__(self) -> str:
        return self.task_id