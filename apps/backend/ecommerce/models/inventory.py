# apps/backend/ecommerce/models/inventory.py

"""
Inventory and stock models for the ecommerce application.

Core models:

    Stock                   — physical inventory at a warehouse
    StockHistory            — audit trail of stock movements
    Allocation              — stock reserved against an order line
    Reservation             — stock reserved against a checkout line
    PreorderAllocation      — preorder commitment for an order line
    PreorderReservation     — preorder commitment for a checkout line

Quantity fields are Decimal(12,3) so that weighted market items
(2.5 kg of beef) are tracked correctly alongside discrete catalog
items.

Availability is computed from `Allocation` and `Reservation` rows.
There is no denormalized allocation counter on `Stock` — a previous
version of this module had a `Stock.quantity_allocated` field, but
it was never read for any decision, only maintained as a mirror of
the `Allocation` aggregate. It was removed.
"""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal
from typing import Optional

from django.conf import settings
from django.contrib.postgres.indexes import BTreeIndex, GinIndex
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import F, Q, QuerySet, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from ecommerce.models.checkout import CheckoutLine
from ecommerce.models.order import OrderLine
from ecommerce.models.product import (
    Product,
    ProductVariant,
    ProductVariantChannelListing,
)
from ecommerce.models.warehouse import Warehouse

from .constants import WarehouseClickAndCollectOption
# =====================================================================
# CONSTANTS
# =====================================================================


QUANTITY_DECIMAL_PLACES = 3
QUANTITY_MAX_DIGITS = 12


# =====================================================================
# STOCK
# =====================================================================


class StockQuerySet(models.QuerySet["Stock"]):
    def annotate_available_quantity(self) -> QuerySet["Stock"]:
        """
        Annotate with available (unallocated) quantity.

        Availability is computed from `Allocation` rows, not from a
        stored counter. Every read path in the codebase uses this
        same source of truth.
        """
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
                    Decimal("0"),
                )
            ),
        )

    def annotate_reserved_quantity(self) -> QuerySet["Stock"]:
        """Annotate with currently reserved quantity."""
        return self.annotate(
            reserved_quantity=Coalesce(
                Sum(
                    "reservations__quantity_reserved",
                    filter=Q(
                        reservations__reserved_until__gt=timezone.now(),
                    ),
                ),
                Decimal("0"),
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
        """
        Return stock rows for a variant in a channel, optionally
        filtered by country.

        `include_cc_warehouses` controls whether click-and-collect
        warehouses are included:

            include_cc_warehouses=False (default)
                Only standard (non-CC) warehouses are returned, and
                only when a country is specified. When country is
                None, ALL warehouses on the channel are returned.

            include_cc_warehouses=True
                Only click-and-collect warehouses are returned,
                regardless of country.

        The previous implementation had inverted logic: passing no
        country filtered to click-and-collect warehouses, which was
        the opposite of what callers expected.
        """
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
                warehouse__shipping_zones__channels__slug=channel_slug,
            )

        if include_cc_warehouses:
            qs = qs.filter(
                Q(
                    warehouse__click_and_collect_option__in=[
                        WarehouseClickAndCollectOption.LOCAL_STOCK,
                        WarehouseClickAndCollectOption.ALL_WAREHOUSES,
                    ]
                )
            )
        elif country_code:
            # When a country is specified and CC is not requested,
            # exclude click-and-collect warehouses. A CC warehouse
            # is a pickup point, not a delivery origin.
            qs = qs.exclude(
                warehouse__click_and_collect_option__in=[
                    WarehouseClickAndCollectOption.LOCAL_STOCK,
                    WarehouseClickAndCollectOption.ALL_WAREHOUSES,
                ]
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
    """
    Physical inventory of a variant at a warehouse.

    Availability is derived from `Allocation` rows. There is no
    stored allocation counter on this model; the previous
    `quantity_allocated` field was write-only and has been removed.
    """

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

    quantity = models.DecimalField(
        max_digits=QUANTITY_MAX_DIGITS,
        decimal_places=QUANTITY_DECIMAL_PLACES,
        default=Decimal("0"),
        help_text=(
            "On-hand quantity. Decimal so that market items "
            "measured in kg, g, l, etc. can be tracked."
        ),
    )

    low_stock_threshold = models.DecimalField(
        max_digits=QUANTITY_MAX_DIGITS,
        decimal_places=QUANTITY_DECIMAL_PLACES,
        default=Decimal("10"),
        help_text="Alert when stock falls below this level.",
    )

    last_restocked_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    restock_lead_time_days = models.PositiveIntegerField(
        default=7,
        help_text="Days to restock.",
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
        ]

    def __str__(self) -> str:
        return f"{self.product_variant} at {self.warehouse}"

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    @transaction.atomic
    def increase_stock(
        self,
        quantity: Decimal,
        commit: bool = True,
        reason: str = "",
        user=None,
    ) -> None:
        """
        Increase stock and record a StockHistory entry.

        Locks the stock row before mutating so concurrent increases
        cannot lose updates. Raises ValidationError for non-positive
        quantities.
        """
        quantity = Decimal(str(quantity))
        if quantity <= 0:
            raise ValidationError(
                {
                    "quantity": (
                        "Stock increase quantity must be greater than zero."
                    )
                }
            )

        # Re-read under lock so the increment applies to the current
        # committed value.
        locked = (
            type(self)
            .objects
            .select_for_update()
            .get(pk=self.pk)
        )
        previous_quantity = locked.quantity

        if commit:
            locked.quantity = F("quantity") + quantity
            locked.save(update_fields=["quantity"])
            locked.refresh_from_db(fields=["quantity"])

            StockHistory.objects.create(
                stock=locked,
                product_variant=locked.product_variant,
                warehouse=locked.warehouse,
                quantity_change=quantity,
                previous_quantity=previous_quantity,
                new_quantity=locked.quantity,
                change_type=StockHistory.ChangeType.RESTOCK,
                reason=reason or "Restock",
                user=user,
            )

            # Keep the caller's instance in sync.
            self.quantity = locked.quantity
        else:
            self.quantity = previous_quantity + quantity

    @transaction.atomic
    def decrease_stock(
        self,
        quantity: Decimal,
        commit: bool = True,
        reason: str = "",
        user=None,
    ) -> None:
        """
        Decrease stock and record a StockHistory entry.

        Locks the stock row and re-reads availability inside the
        lock, so concurrent decreases cannot oversell. Raises
        ValidationError if the requested quantity exceeds what is
        available.
        """
        quantity = Decimal(str(quantity))
        if quantity <= 0:
            raise ValidationError(
                {
                    "quantity": (
                        "Stock decrease quantity must be greater than zero."
                    )
                }
            )

        # Lock the row, then read availability against the locked
        # state. `available_quantity` reads from `Allocation` rows,
        # which are also locked by the deallocation path — so this
        # is a stable snapshot within the transaction.
        locked = (
            type(self)
            .objects
            .select_for_update()
            .get(pk=self.pk)
        )

        available = locked.available_quantity
        if quantity > available:
            raise ValidationError(
                {
                    "quantity": (
                        f"Cannot decrease stock by {quantity}; "
                        f"only {available} available."
                    )
                }
            )

        previous_quantity = locked.quantity

        if commit:
            locked.quantity = F("quantity") - quantity
            locked.save(update_fields=["quantity"])
            locked.refresh_from_db(fields=["quantity"])

            StockHistory.objects.create(
                stock=locked,
                product_variant=locked.product_variant,
                warehouse=locked.warehouse,
                quantity_change=-quantity,
                previous_quantity=previous_quantity,
                new_quantity=locked.quantity,
                change_type=StockHistory.ChangeType.REMOVAL,
                reason=reason or "Removal",
                user=user,
            )

            self.quantity = locked.quantity
        else:
            self.quantity = previous_quantity - quantity

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def available_quantity(self) -> Decimal:
        """
        Physical stock minus allocations, floored at zero.

        Aggregates from `Allocation` rows. This is the single source
        of truth for availability.
        """
        allocated = (
            self.allocations.aggregate(
                total=Coalesce(
                    Sum("quantity_allocated"),
                    Decimal("0"),
                )
            )["total"]
            or Decimal("0")
        )

        return max(
            self.quantity - allocated,
            Decimal("0"),
        )

    @property
    def is_low_stock(self) -> bool:
        return self.available_quantity <= self.low_stock_threshold


# =====================================================================
# STOCK HISTORY
# =====================================================================


class StockHistory(models.Model):
    """Permanent audit trail of every stock movement."""

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
    )

    product_variant = models.ForeignKey(
        ProductVariant,
        related_name="stock_history",
        on_delete=models.CASCADE,
        db_index=True,
    )

    warehouse = models.ForeignKey(
        Warehouse,
        related_name="stock_history",
        on_delete=models.CASCADE,
        db_index=True,
    )

    quantity_change = models.DecimalField(
        max_digits=QUANTITY_MAX_DIGITS,
        decimal_places=QUANTITY_DECIMAL_PLACES,
        help_text=(
            "Signed change (positive = increase, negative = decrease)."
        ),
    )

    previous_quantity = models.DecimalField(
        max_digits=QUANTITY_MAX_DIGITS,
        decimal_places=QUANTITY_DECIMAL_PLACES,
        help_text="Quantity before this change.",
    )

    new_quantity = models.DecimalField(
        max_digits=QUANTITY_MAX_DIGITS,
        decimal_places=QUANTITY_DECIMAL_PLACES,
        help_text="Quantity after this change.",
    )

    reserved_change = models.DecimalField(
        max_digits=QUANTITY_MAX_DIGITS,
        decimal_places=QUANTITY_DECIMAL_PLACES,
        default=Decimal("0"),
    )

    previous_reserved = models.DecimalField(
        max_digits=QUANTITY_MAX_DIGITS,
        decimal_places=QUANTITY_DECIMAL_PLACES,
        default=Decimal("0"),
    )

    new_reserved = models.DecimalField(
        max_digits=QUANTITY_MAX_DIGITS,
        decimal_places=QUANTITY_DECIMAL_PLACES,
        default=Decimal("0"),
    )

    change_type = models.CharField(
        max_length=20,
        choices=ChangeType.choices,
        db_index=True,
    )

    reason = models.TextField(blank=True)

    reference = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        help_text="Reference (order number, transfer ID, etc.).",
    )

    order = models.ForeignKey(
        "ecommerce.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_history",
    )

    order_line = models.ForeignKey(
        OrderLine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_history",
    )

    fulfillment = models.ForeignKey(
        "ecommerce.Fulfillment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_history",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_changes",
    )

    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Stock History"
        verbose_name_plural = "Stock Histories"
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
        quantity_change: Decimal,
        change_type: str,
        reason: str = "",
        reference: str = "",
        user=None,
        **kwargs,
    ) -> "StockHistory":
        """
        Create a StockHistory from an already-applied stock change.

        The `stock.quantity` value must already reflect the change.
        `previous_quantity` is computed by reversing the change. If
        the reversal produces a negative value, that means the caller
        passed a change that is larger than the resulting stock — a
        data integrity error — and this method raises rather than
        silently clamping to zero.
        """
        quantity_change = Decimal(str(quantity_change))
        new_quantity = stock.quantity
        previous_quantity = new_quantity - quantity_change

        if previous_quantity < 0:
            raise ValidationError(
                {
                    "quantity_change": (
                        "The change implies a negative prior quantity "
                        f"({previous_quantity}); the stock row and the "
                        "change are inconsistent."
                    )
                }
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


# =====================================================================
# ALLOCATION
# =====================================================================


class AllocationQueryset(models.QuerySet["Allocation"]):
    def annotate_stock_available_quantity(
        self,
    ) -> QuerySet["Allocation"]:
        return self.annotate(
            stock_available_quantity=(
                F("stock__quantity")
                - Coalesce(
                    Sum("stock__allocations__quantity_allocated"),
                    Decimal("0"),
                )
            )
        )

    def available_quantity_for_stock(
        self,
        stock: Stock,
    ) -> Decimal:
        allocated = (
            self.filter(stock=stock).aggregate(
                total=Sum("quantity_allocated"),
            )["total"]
            or Decimal("0")
        )

        return max(
            stock.quantity - allocated,
            Decimal("0"),
        )


AllocationManager = models.Manager.from_queryset(AllocationQueryset)


class Allocation(models.Model):
    """Stock allocated against an order line."""

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

    quantity_allocated = models.DecimalField(
        max_digits=QUANTITY_MAX_DIGITS,
        decimal_places=QUANTITY_DECIMAL_PLACES,
        default=Decimal("0"),
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


# =====================================================================
# RESERVATION
# =====================================================================


class ReservedLineQuerySet(models.QuerySet):
    """
    Shared queryset for Reservation and PreorderReservation.

    Both models have a `checkout_line` FK and a `reserved_until`
    DateTimeField, so the shared queryset is safe.
    """

    def not_expired(self) -> QuerySet:
        return self.filter(reserved_until__gt=timezone.now())

    def exclude_checkout_lines(
        self,
        checkout_lines: Optional[Iterable[CheckoutLine]],
    ) -> QuerySet:
        if not checkout_lines:
            return self
        return self.exclude(checkout_line__in=checkout_lines)


ReservedLineManager = models.Manager.from_queryset(ReservedLineQuerySet)


class Reservation(models.Model):
    """Stock reserved against a checkout line."""

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

    quantity_reserved = models.DecimalField(
        max_digits=QUANTITY_MAX_DIGITS,
        decimal_places=QUANTITY_DECIMAL_PLACES,
        default=Decimal("0"),
    )

    reserved_until = models.DateTimeField(db_index=True)

    objects = ReservedLineManager()

    class Meta:
        ordering = ("pk",)
        indexes = [
            BTreeIndex(
                fields=["checkout_line", "reserved_until"],
                name="reservation_line_until_idx",
            ),
            BTreeIndex(
                fields=["stock", "reserved_until"],
                name="reservation_stock_until_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["checkout_line", "stock"],
                name="unique_reservation_checkout_line_stock",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Reserved {self.quantity_reserved} "
            f"until {self.reserved_until}"
        )


# =====================================================================
# PREORDER
# =====================================================================


class PreorderAllocation(models.Model):
    """Preorder commitment for an order line."""

    order_line = models.ForeignKey(
        OrderLine,
        on_delete=models.CASCADE,
        related_name="preorder_allocations",
        db_index=True,
    )

    quantity = models.DecimalField(
        max_digits=QUANTITY_MAX_DIGITS,
        decimal_places=QUANTITY_DECIMAL_PLACES,
        default=Decimal("0"),
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
    """Preorder commitment for a checkout line."""

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

    quantity_reserved = models.DecimalField(
        max_digits=QUANTITY_MAX_DIGITS,
        decimal_places=QUANTITY_DECIMAL_PLACES,
        default=Decimal("0"),
    )

    reserved_until = models.DateTimeField(db_index=True)

    objects = ReservedLineManager()

    class Meta:
        ordering = ("pk",)
        indexes = [
            BTreeIndex(
                fields=["checkout_line", "reserved_until"],
                name="preorder_res_line_until_idx",
            ),
            BTreeIndex(
                fields=["reserved_until"],
                name="preorder_reservation_until_idx",
            ),
        ]
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