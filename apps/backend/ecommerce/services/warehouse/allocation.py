# ecommerce/services/warehouse/allocation.py

"""
Stock allocation and reservation services.

This module is the single source of truth for stock operations:

    - Checking availability ("can I add 3 more to the cart?")
    - Reserving stock (short-term hold during checkout)
    - Allocating stock (long-term hold for a confirmed order)
    - Releasing reservations and allocations

All quantities are Decimal, since market items can be sold by
continuous units (2.5 kg, 0.75 l). The unit of a variant is
recorded on `ProductVariant.quantity_unit`.

Stock tracking is optional per variant (`track_inventory=False`
means the variant is not stock-limited — digital goods, made-to-order,
etc.).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Iterable, Optional

from django.db import transaction
from django.db.models import QuerySet, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from core.exceptions import (
    AllocationError,
    InsufficientStock,
    InsufficientStockData,
)
from ecommerce.models.channel import Channel
from ecommerce.models.checkout import CheckoutLine
from ecommerce.models.inventory import (
    Allocation,
    Reservation,
    Stock,
    StockQuerySet,
)

from ecommerce.models.order import OrderLine
from ecommerce.models.product import ProductVariant
from ecommerce.models.warehouse import Warehouse


ZERO = Decimal("0")


# =====================================================================
# QUERY HELPERS
# =====================================================================


def get_available_quantity(
    variant: ProductVariant,
    channel: Channel,
    *,
    exclude_checkout_lines: Optional[Iterable[CheckoutLine]] = None,
) -> Decimal:
    """
    Return the currently available quantity for a variant in a channel.

    Availability = physical stock − allocations − active reservations.

    Returns Decimal("0") for variants that don't track inventory
    (they're always "available" in the sense that there's no cap).

    Returns Decimal("0") if there are no stocks in the channel.
    """
    if not variant.track_inventory:
        # Unlimited — not a stock-tracked variant.
        return Decimal("1e12")  # sentinel "very large"

    stocks = _get_variant_stocks(variant, channel)
    if not stocks.exists():
        return ZERO

    return _compute_available(stocks, exclude_checkout_lines)


def check_stock_availability(
    variant: ProductVariant,
    quantity: Decimal,
    channel: Channel,
    *,
    order_line: Optional[OrderLine] = None,
    checkout_line: Optional[CheckoutLine] = None,
) -> None:
    """
    Raise InsufficientStock if the variant cannot supply the requested
    quantity.

    A no-op for variants that don't track inventory.
    """
    if not variant.track_inventory:
        return

    stocks = _get_variant_stocks(variant, channel)
    if not stocks.exists():
        raise InsufficientStock(
            [
                InsufficientStockData(
                    variant=variant,
                    available_quantity=ZERO,
                    order_line=order_line,
                    checkout_line=checkout_line,
                )
            ]
        )

    available = _compute_available(stocks)
    if quantity > available:
        raise InsufficientStock(
            [
                InsufficientStockData(
                    variant=variant,
                    available_quantity=available,
                    order_line=order_line,
                    checkout_line=checkout_line,
                )
            ]
        )


# =====================================================================
# RESERVATIONS (short-term hold during checkout)
# =====================================================================


def reserve_for_checkout_line(
    checkout_line: CheckoutLine,
    channel: Channel,
    *,
    ttl_minutes: int = 30,
) -> list[Reservation]:
    """
    Reserve stock for a checkout line.

    Splits the reservation across available stocks in the channel
    according to `Channel.allocation_strategy`.

    A no-op for variants that don't track inventory.

    Raises InsufficientStock if the requested quantity is not
    available.
    """
    variant = checkout_line.variant
    quantity = checkout_line.quantity

    if not variant.track_inventory or quantity <= ZERO:
        return []

    # Idempotency: clear any previous reservation for this line.
    Reservation.objects.filter(checkout_line=checkout_line).delete()

    with transaction.atomic():
        # Fetch PKs first (no FOR UPDATE), then lock by PK.
        # Postgres rejects FOR UPDATE on DISTINCT queries, so we split
        # the operation: pick the stock rows, then lock the exact rows.
        stock_pks = list(
            _get_variant_stocks(variant, channel)
            .order_by("pk")
            .values_list("pk", flat=True)
        )
        stocks = list(
            Stock.objects.filter(pk__in=stock_pks)
            .select_for_update(of=("self",))
            .order_by("pk")
        )

        # Account for existing reservations and allocations.
        allocations_by_stock = _allocations_by_stock(stocks)
        reservations_by_stock = _reservations_by_stock(stocks)
        available_by_stock = {
            stock.pk: max(
                stock.quantity
                - allocations_by_stock.get(stock.pk, ZERO)
                - reservations_by_stock.get(stock.pk, ZERO),
                ZERO,
            )
            for stock in stocks
        }

        # Sort stocks by allocation strategy.
        stocks = _sort_stocks(stocks, channel, available_by_stock)

        expires_at = timezone.now() + timezone.timedelta(minutes=ttl_minutes)
        reservations: list[Reservation] = []
        remaining = quantity

        for stock in stocks:
            if remaining <= ZERO:
                break
            take = min(remaining, available_by_stock[stock.pk])
            if take <= ZERO:
                continue
            reservations.append(
                Reservation(
                    checkout_line=checkout_line,
                    stock=stock,
                    quantity_reserved=take,
                    reserved_until=expires_at,
                )
            )
            remaining -= take

        if remaining > ZERO:
            raise InsufficientStock(
                [
                    InsufficientStockData(
                        variant=variant,
                        available_quantity=quantity - remaining,
                        checkout_line=checkout_line,
                    )
                ]
            )

        return Reservation.objects.bulk_create(reservations)


def release_reservation(reservation: Reservation) -> None:
    """Delete a single reservation."""
    reservation.delete()


def release_reservations_for_checkout_line(checkout_line: CheckoutLine) -> None:
    """Delete all reservations for a checkout line."""
    Reservation.objects.filter(checkout_line=checkout_line).delete()


def release_expired_reservations() -> int:
    """
    Delete all expired reservations.

    Returns the number of reservations deleted.

    Intended to be called periodically (e.g. by a Celery beat task).
    """
    deleted, _ = Reservation.objects.filter(
        reserved_until__lt=timezone.now()
    ).delete()
    return deleted


# =====================================================================
# ALLOCATIONS (long-term hold for a confirmed order)
# =====================================================================


def allocate_for_order_line(
    order_line: OrderLine,
    channel: Channel,
) -> list[Allocation]:
    """
    Allocate stock for an order line.

    Called when an order is confirmed. Converts stock into
    allocations that will be fulfilled, then decreases the physical
    stock when fulfillment completes.

    Splits across available stocks according to
    `Channel.allocation_strategy`.

    A no-op for variants that don't track inventory.

    Raises InsufficientStock if there isn't enough available stock.
    """
    variant = order_line.variant
    quantity = order_line.quantity

    if variant is None:
        # Ad-hoc market line without a variant reference.
        return []

    if not variant.track_inventory or quantity <= ZERO:
        return []

    # Idempotency: clear any previous allocation for this line.
    Allocation.objects.filter(order_line=order_line).delete()

    with transaction.atomic():
        # Fetch PKs first, then lock by PK (see reserve_for_checkout_line).
        stock_pks = list(
            _get_variant_stocks(variant, channel)
            .order_by("pk")
            .values_list("pk", flat=True)
        )
        stocks = list(
            Stock.objects.filter(pk__in=stock_pks)
            .select_for_update(of=("self",))
            .order_by("pk")
        )

        allocations_by_stock = _allocations_by_stock(stocks)
        reservations_by_stock = _reservations_by_stock(stocks)
        available_by_stock = {
            stock.pk: max(
                stock.quantity
                - allocations_by_stock.get(stock.pk, ZERO)
                - reservations_by_stock.get(stock.pk, ZERO),
                ZERO,
            )
            for stock in stocks
        }

        stocks = _sort_stocks(stocks, channel, available_by_stock)

        allocations: list[Allocation] = []
        remaining = quantity

        for stock in stocks:
            if remaining <= ZERO:
                break
            take = min(remaining, available_by_stock[stock.pk])
            if take <= ZERO:
                continue
            allocations.append(
                Allocation(
                    order_line=order_line,
                    stock=stock,
                    quantity_allocated=take,
                )
            )
            remaining -= take

        if remaining > ZERO:
            raise InsufficientStock(
                [
                    InsufficientStockData(
                        variant=variant,
                        available_quantity=quantity - remaining,
                        order_line=order_line,
                    )
                ]
            )

        # Allocation rows are the source of truth for availability.
        # No cached counter to maintain on Stock.
        return Allocation.objects.bulk_create(allocations)


def deallocate_for_order_line(order_line: OrderLine) -> None:
    """
    Release all allocations for an order line.

    Called when an order line is cancelled, refunded, or the order
    is deleted.

    Allocation rows are the source of truth; availability is
    computed from them directly, so no cached counter needs
    updating.
    """
    with transaction.atomic():
        Allocation.objects.filter(
            order_line=order_line
        ).select_for_update(of=("self",)).delete()


def deallocate_for_order(order) -> None:
    """Release all allocations for every line of an order."""
    for line in order.lines.all():
        deallocate_for_order_line(line)


# =====================================================================
# INTERNAL HELPERS
# =====================================================================


def _get_variant_stocks(
    variant: ProductVariant,
    channel: Channel,
) -> StockQuerySet:
    """
    Return the stock queryset for a variant in a channel.

    Filters to warehouses linked to the channel. Uses a subquery
    (`warehouse__in=...`) instead of a join+distinct so the queryset
    remains compatible with `select_for_update()` — Postgres does not
    allow FOR UPDATE on a DISTINCT query.
    """
    return Stock.objects.filter(
        product_variant=variant,
        warehouse__in=Warehouse.objects.filter(
            channelwarehouse__channel=channel,
        ).values("pk"),
    )


def _compute_available(
    stocks: StockQuerySet,
    exclude_checkout_lines: Optional[Iterable[CheckoutLine]] = None,
) -> Decimal:
    """
    Compute the total available quantity across a set of stocks.

    availability = sum(quantity) − sum(allocations) − sum(active reservations)

    `exclude_checkout_lines` lets the caller ignore reservations
    belonging to a specific set of checkout lines (e.g. the caller's
    own cart), so that "can I add another unit?" doesn't count the
    caller's existing hold against them.
    """
    totals = stocks.aggregate(
        total_quantity=Coalesce(Sum("quantity"), ZERO),
        allocated=Coalesce(Sum("allocations__quantity_allocated"), ZERO),
    )
    total_quantity = totals["total_quantity"] or ZERO
    allocated = totals["allocated"] or ZERO

    reservations_qs = Reservation.objects.filter(
        stock__in=stocks,
        reserved_until__gt=timezone.now(),
    )
    if exclude_checkout_lines:
        reservations_qs = reservations_qs.exclude(
            checkout_line__in=exclude_checkout_lines
        )
    reserved = (
        reservations_qs.aggregate(
            total=Coalesce(Sum("quantity_reserved"), ZERO)
        )["total"]
        or ZERO
    )

    return max(total_quantity - allocated - reserved, ZERO)


def _allocations_by_stock(
    stocks: Iterable[Stock],
) -> dict[int, Decimal]:
    """Map stock_id → total quantity_allocated."""
    result = (
        Allocation.objects.filter(stock__in=stocks)
        .values("stock_id")
        .annotate(total=Coalesce(Sum("quantity_allocated"), ZERO))
    )
    return {row["stock_id"]: row["total"] for row in result}


def _reservations_by_stock(
    stocks: Iterable[Stock],
) -> dict[int, Decimal]:
    """Map stock_id → active reserved quantity."""
    result = (
        Reservation.objects.filter(
            stock__in=stocks,
            reserved_until__gt=timezone.now(),
        )
        .values("stock_id")
        .annotate(total=Coalesce(Sum("quantity_reserved"), ZERO))
    )
    return {row["stock_id"]: row["total"] for row in result}


def _sort_stocks(
    stocks: list[Stock],
    channel: Channel,
    available_by_stock: dict[int, Decimal],
) -> list[Stock]:
    """
    Sort stocks by the channel's allocation strategy.

    Supported strategies:

        PRIORITIZE_HIGH_STOCK
            Largest available quantity first — minimizes
            fragmentation. Default.

        PRIORITIZE_LOW_STOCK
            Smallest available quantity first — clears
            near-empty warehouses.

        PRIORITIZE_SORTING_ORDER
            Falls back to a stable ordering by pk.
    """
    strategy = getattr(channel, "allocation_strategy", None)

    if strategy == "prioritize-high-stock":
        return sorted(
            stocks,
            key=lambda s: available_by_stock.get(s.pk, ZERO),
            reverse=True,
        )

    if strategy == "prioritize-low-stock":
        return sorted(
            stocks,
            key=lambda s: available_by_stock.get(s.pk, ZERO),
        )

    # Default: stable order by pk.
    return sorted(stocks, key=lambda s: s.pk)