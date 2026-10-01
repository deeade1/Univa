# warehouse/services.py
"""
Unified Warehouse Service Layer
Consolidates: availability, management, reservations, and allocation logic
"""
from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Optional, Union
from uuid import UUID

from django.db import transaction
from django.db.models import F, Sum, Q, Count
from django.db.models.functions import Coalesce
from django.db.models.query import QuerySet  # ✅ ADD THIS IMPORT
from django.utils import timezone

from core.exceptions import InsufficientStock, InsufficientStockData
from ecommerce.models.product import ProductVariant, ProductVariantChannelListing

from ecommerce.models.warehouse import (
    ChannelWarehouse, 
     Warehouse
)
from ecommerce.models.inventory import (
    Allocation, PreorderAllocation,
    PreorderReservation, Reservation, Stock
)

if TYPE_CHECKING:
    from channel.models import Channel
    from checkout.models import CheckoutLine
    from order.models import Order, OrderLine
    


class StockData:
    """Stock data container."""
    def __init__(self, pk: int, quantity: int, warehouse_id: int):
        self.pk = pk
        self.quantity = quantity
        self.warehouse_id = warehouse_id


# ============================================================================
# DECORATOR REPLACEMENT
# ============================================================================

def atomic_transaction(func):
    """Decorator to wrap functions in an atomic transaction."""
    def wrapper(*args, **kwargs):
        with transaction.atomic():
            return func(*args, **kwargs)
    return wrapper


class WarehouseService:
    """
    Unified warehouse service for all warehouse operations.
    Combines: availability checks, stock management, reservations, allocations.
    """
    
    # ========================================================================
    # AVAILABILITY CHECKS
    # ========================================================================
    
    @staticmethod
    def get_available_quantity(
        variant: ProductVariant,
        country_code: str,
        channel_slug: str,
        checkout_lines: Optional[list["CheckoutLine"]] = None,
        check_reservations: bool = False,
    ) -> int:
        """
        Return available quantity for a variant in a given country and channel.
        """
        stocks = Stock.objects.get_variant_stocks_for_country(
            country_code, channel_slug, variant
        )
        if not stocks:
            return 0
        return WarehouseService._get_available_quantity(
            stocks, checkout_lines, check_reservations
        )
    
    @staticmethod
    def check_availability(
        variant: ProductVariant,
        quantity: int,
        channel: "Channel",
        country_code: str,
        include_reservations: bool = True,
    ) -> tuple[bool, int]:
        """Check if a variant is available in the requested quantity."""
        stocks = Stock.objects.for_channel_and_country(
            channel.slug, country_code
        ).filter(product_variant=variant)
        
        total_available = 0
        for stock in stocks:
            available = stock.available_quantity
            if include_reservations:
                reserved = stock.reservations.filter(
                    reserved_until__gt=timezone.now()
                ).aggregate(total=Coalesce(Sum('quantity_reserved'), 0))['total']
                available -= reserved
            total_available += max(available, 0)
        
        return total_available >= quantity, total_available
    
    @staticmethod
    def check_bulk_availability(
        variants: list[ProductVariant],
        quantities: list[int],
        channel: "Channel",
        country_code: str,
    ) -> dict[int, dict]:
        """Check availability for multiple variants."""
        results = {}
        variant_ids = [v.id for v in variants]
        
        stocks = Stock.objects.for_channel_and_country(
            channel.slug, country_code
        ).filter(
            product_variant_id__in=variant_ids
        ).annotate_available_quantity()
        
        variant_stocks = defaultdict(list)
        for stock in stocks:
            variant_stocks[stock.product_variant_id].append(stock)
        
        for variant, quantity in zip(variants, quantities):
            available = sum(
                s.available_quantity for s in variant_stocks.get(variant.id, [])
            )
            results[variant.id] = {
                'available': available,
                'sufficient': available >= quantity,
                'quantity_requested': quantity
            }
        
        return results
    
    @staticmethod
    def is_product_in_stock(
        product: "Product",
        country_code: str,
        channel_slug: str
    ) -> bool:
        """Check if there is any variant of a product available in a country."""
        stocks = Stock.objects.get_product_stocks_for_country_and_channel(
            country_code, channel_slug, product
        ).annotate_available_quantity()
        return any(stocks.values_list("available_quantity", flat=True))
    
    @staticmethod
    def _get_available_quantity(
        stocks: QuerySet[Stock],
        checkout_lines: Optional[list["CheckoutLine"]] = None,
        check_reservations: bool = False,
    ) -> int:
        """Internal method to calculate available quantity from stocks."""
        results = stocks.aggregate(
            total_quantity=Coalesce(Sum("quantity", distinct=True), 0),
            quantity_allocated=Coalesce(Sum("allocations__quantity_allocated"), 0),
        )
        total_quantity = results["total_quantity"]
        quantity_allocated = results["quantity_allocated"]
        
        if check_reservations:
            quantity_reserved = WarehouseService._get_reserved_stock_quantity(
                stocks, checkout_lines
            )
        else:
            quantity_reserved = 0
        
        return max(total_quantity - quantity_allocated - quantity_reserved, 0)
    
    @staticmethod
    def _get_reserved_stock_quantity(
        stocks: QuerySet[Stock],
        lines: Optional[list["CheckoutLine"]] = None
    ) -> int:
        """Get total reserved quantity for stocks."""
        result = Reservation.objects.filter(
            stock__in=stocks,
        ).not_expired().exclude_checkout_lines(lines).aggregate(
            quantity_reserved=Coalesce(Sum("quantity_reserved"), 0),
        )
        return result["quantity_reserved"]
    
    @staticmethod
    def _get_reserved_stock_quantity_bulk(
        stocks: Iterable[Stock],
        checkout_lines: Iterable["CheckoutLine"],
    ) -> dict[int, int]:
        """Get reserved quantities for multiple stocks."""
        reservations: dict[int, int] = defaultdict(int)
        if not stocks:
            return reservations
        
        result = Reservation.objects.filter(
            stock__in=stocks,
        ).not_expired().exclude_checkout_lines(checkout_lines).values("stock_id").annotate(
            quantity_reserved=Coalesce(Sum("quantity_reserved"), 0),
        )
        
        stocks_variants = {stock.id: stock.product_variant_id for stock in stocks}
        for stock_reservations in result:
            variant_id = stocks_variants.get(stock_reservations["stock_id"])
            if variant_id:
                reservations[variant_id] += stock_reservations["quantity_reserved"]
        
        return reservations
    
    # ========================================================================
    # STOCK VALIDATION
    # ========================================================================
    
    @staticmethod
    def check_stock_and_preorder_quantity(
        variant: ProductVariant,
        country_code: str,
        channel_slug: str,
        quantity: int,
        checkout_lines: Optional[list["CheckoutLine"]] = None,
        check_reservations: bool = False,
        order_line: Optional["OrderLine"] = None,
    ) -> None:
        """
        Validate if there is stock/preorder available for a variant.
        
        :raises InsufficientStock: when there is not enough stock or preorder available.
        """
        if variant.is_preorder_active():
            WarehouseService.check_preorder_threshold_in_orders(
                variant, quantity, channel_slug, checkout_lines, check_reservations
            )
        else:
            WarehouseService._check_stock_quantity(
                variant, country_code, channel_slug, quantity,
                checkout_lines, check_reservations, order_line
            )
    
    @staticmethod
    def _check_stock_quantity(
        variant: ProductVariant,
        country_code: str,
        channel_slug: str,
        quantity: int,
        checkout_lines: Optional[list["CheckoutLine"]] = None,
        check_reservations: bool = False,
        order_line: Optional["OrderLine"] = None,
    ) -> None:
        """Validate stock quantity for a variant."""
        if variant.track_inventory:
            stocks = Stock.objects.get_variant_stocks_for_country(
                country_code, channel_slug, variant
            )
            if not stocks:
                raise InsufficientStock([
                    InsufficientStockData(
                        variant=variant, available_quantity=0, order_line=order_line
                    )
                ])
            
            available_quantity = WarehouseService._get_available_quantity(
                stocks, checkout_lines, check_reservations
            )
            if quantity > available_quantity:
                raise InsufficientStock([
                    InsufficientStockData(
                        variant=variant, available_quantity=available_quantity,
                        order_line=order_line
                    )
                ])
    
    @staticmethod
    def check_stock_and_preorder_quantity_bulk(
        variants: Iterable[ProductVariant],
        quantities: Iterable[int],
        country_code: str,
        channel_slug: str,
        existing_lines: Optional[Iterable["CheckoutLine"]] = None,
        check_reservations: bool = True,
        replace: bool = True,
        global_quantity_limit: Optional[int] = None,
    ) -> None:
        """
        Validate stock/preorder quantities for multiple variants.
        
        :raises InsufficientStock: when any variant cannot fulfill the requested quantity.
        """
        # Split into stock and preorder variants
        stock_variants, stock_quantities = [], []
        preorder_variants, preorder_quantities = [], []
        
        for variant, quantity in zip(variants, quantities):
            if variant.is_preorder_active():
                preorder_variants.append(variant)
                preorder_quantities.append(quantity)
            else:
                stock_variants.append(variant)
                stock_quantities.append(quantity)
        
        if stock_variants:
            WarehouseService._check_stock_quantity_bulk(
                stock_variants, stock_quantities, country_code, channel_slug,
                global_quantity_limit, existing_lines, replace, check_reservations
            )
        
        if preorder_variants:
            WarehouseService._check_preorder_threshold_bulk(
                preorder_variants, preorder_quantities, channel_slug,
                global_quantity_limit, existing_lines, replace, check_reservations
            )
    
    @staticmethod
    def _check_stock_quantity_bulk(
        variants: Iterable[ProductVariant],
        quantities: Iterable[int],
        country_code: str,
        channel_slug: str,
        global_quantity_limit: Optional[int],
        existing_lines: Optional[Iterable["CheckoutLine"]] = None,
        replace: bool = False,
        check_reservations: bool = False,
    ) -> None:
        """Bulk stock quantity validation."""
        filter_lookup = {"product_variant__in": variants}
        
        stocks = Stock.objects.for_channel_and_country(
            channel_slug, country_code, include_cc_warehouses=True
        ).filter(**filter_lookup).annotate_available_quantity()
        
        variant_stocks: dict[int, list[Stock]] = defaultdict(list)
        for stock in stocks:
            variant_stocks[stock.product_variant_id].append(stock)
        
        if check_reservations:
            variant_reservations = WarehouseService._get_reserved_stock_quantity_bulk(
                stocks, [line for line in existing_lines or []]
            )
        else:
            variant_reservations = defaultdict(int)
        
        insufficient_stocks: list[InsufficientStockData] = []
        variants_quantities = {
            line.variant.pk: line.quantity for line in existing_lines or []
        }
        
        for variant, quantity in zip(variants, quantities):
            if not replace:
                quantity += variants_quantities.get(variant.pk, 0)
            
            variant_stock_list = variant_stocks.get(variant.pk, [])
            available_quantity = sum([stock.available_quantity for stock in variant_stock_list])
            available_quantity = max(available_quantity - variant_reservations[variant.pk], 0)
            
            if quantity > 0:
                # Check quantity limits
                if global_quantity_limit and quantity > global_quantity_limit:
                    from django.core.exceptions import ValidationError
                    raise ValidationError(
                        f"Cannot add more than {global_quantity_limit} times this item."
                    )
                
                if variant.track_inventory and quantity > available_quantity:
                    insufficient_stocks.append(
                        InsufficientStockData(
                            variant=variant,
                            available_quantity=available_quantity
                        )
                    )
        
        if insufficient_stocks:
            raise InsufficientStock(insufficient_stocks)
    
    @staticmethod
    def _check_preorder_threshold_bulk(
        variants: Iterable[ProductVariant],
        quantities: Iterable[int],
        channel_slug: str,
        global_quantity_limit: Optional[int],
        existing_lines: Optional[Iterable["CheckoutLine"]] = None,
        replace: bool = False,
        check_reservations: bool = False,
    ) -> None:
        """Bulk preorder threshold validation."""
        # Get channel availability info
        variants_channel_availability, variants_global_allocations, all_variants_channel_listings, variant_channels = (
            WarehouseService._get_variants_channel_availability_info(variants, channel_slug)
        )
        
        if check_reservations:
            listings_reservations = WarehouseService._get_listings_reservations(
                existing_lines, all_variants_channel_listings
            )
        else:
            listings_reservations = defaultdict(int)
        
        insufficient_stocks: list[InsufficientStockData] = []
        
        for variant, quantity in zip(variants, quantities):
            if variant.id not in variants_channel_availability:
                continue
            
            # Check channel threshold
            if variants_channel_availability[variant.id].preorder_quantity_threshold is not None:
                channel_listing_id = variants_channel_availability[variant.id].listing_id
                available_channel_quantity = max(
                    variants_channel_availability[variant.id].preorder_quantity
                    - listings_reservations[channel_listing_id],
                    0
                )
                
                if quantity > available_channel_quantity:
                    insufficient_stocks.append(
                        InsufficientStockData(
                            variant=variant,
                            available_quantity=available_channel_quantity
                        )
                    )
            
            # Check global threshold
            if variant.preorder_global_threshold is not None:
                global_availability = max(
                    variant.preorder_global_threshold
                    - variants_global_allocations.get(variant.id, 0)
                    - sum(listings_reservations.get(listing.id, 0) 
                         for listing in variant_channels.get(variant.id, [])),
                    0
                )
                
                if quantity > global_availability:
                    insufficient_stocks.append(
                        InsufficientStockData(
                            variant=variant,
                            available_quantity=global_availability,
                        )
                    )
        
        if insufficient_stocks:
            raise InsufficientStock(insufficient_stocks)
    
    # ========================================================================
    # STOCK MANAGEMENT
    # ========================================================================
    
    @staticmethod
    @atomic_transaction
    def increase_stock(
        variant: ProductVariant,
        warehouse: Warehouse,
        quantity: int,
        allocate_to_order: Optional["OrderLine"] = None,
    ) -> Stock:
        """Increase stock quantity for a variant in a warehouse."""
        stock, created = Stock.objects.select_for_update().get_or_create(
            warehouse=warehouse,
            product_variant=variant,
            defaults={'quantity': 0}
        )
        stock.increase_stock(quantity)
        
        if allocate_to_order:
            Allocation.objects.create(
                order_line=allocate_to_order,
                stock=stock,
                quantity_allocated=quantity
            )
            stock.quantity_allocated = F("quantity_allocated") + quantity
            stock.save(update_fields=["quantity_allocated"])
        
        return stock
    
    @staticmethod
    @atomic_transaction
    def decrease_stock(
        variant: ProductVariant,
        warehouse: Warehouse,
        quantity: int,
        allow_negative: bool = False,
    ) -> Stock:
        """Decrease stock quantity for a variant in a warehouse."""
        stock = Stock.objects.select_for_update().get(
            warehouse=warehouse,
            product_variant=variant
        )
        
        available = stock.available_quantity
        if quantity > available and not allow_negative:
            raise InsufficientStock([InsufficientStockData(
                variant=variant,
                available_quantity=available,
                warehouse_pk=warehouse.pk
            )])
        
        stock.decrease_stock(quantity)
        return stock
    
    @staticmethod
    def decrease_stock_for_order_lines(
        order_lines_info: Iterable["OrderLineInfo"],
        manager: "PluginsManager",
        update_stocks: bool = True,
        allow_stock_to_be_exceeded: bool = False,
    ) -> None:
        """
        Decrease stock quantities for order lines.
        
        Args:
            order_lines_info: Order line info objects
            manager: Plugins manager for callbacks
            update_stocks: If False, only allocations are decreased
            allow_stock_to_be_exceeded: If True, quantity can go negative
        """
        tracked_lines = WarehouseService._get_order_lines_with_track_inventory(
            order_lines_info
        )
        if not tracked_lines:
            return
        
        # Deallocate first
        try:
            WarehouseService._deallocate_stock(order_lines_info, manager)
        except AllocationError as exc:
            Allocation.objects.filter(order_line__in=exc.order_lines).update(
                quantity_allocated=0
            )
        
        if update_stocks:
            WarehouseService._decrease_stock_quantity(
                tracked_lines, allow_stock_to_be_exceeded
            )
    
    @staticmethod
    def _decrease_stock_quantity(
        order_lines_info: Iterable["OrderLineInfo"],
        allow_stock_to_be_exceeded: bool = False,
    ) -> None:
        """Internal method to decrease stock quantities."""
        variants = [line_info.variant for line_info in order_lines_info]
        warehouse_pks = [line_info.warehouse_pk for line_info in order_lines_info]
        
        stocks = Stock.objects.select_for_update().filter(
            product_variant__in=variants,
            warehouse_id__in=warehouse_pks
        ).select_related("product_variant", "warehouse")
        
        variant_and_warehouse_to_stock: dict[int, dict[UUID, Stock]] = defaultdict(dict)
        for stock in stocks:
            variant_and_warehouse_to_stock[stock.product_variant_id][
                stock.warehouse_id
            ] = stock
        
        quantity_allocation_list = list(
            Allocation.objects.filter(stock__in=stocks, quantity_allocated__gt=0)
            .values("stock")
            .annotate(Sum("quantity_allocated"))
        )
        
        quantity_allocation_for_stocks: dict[int, int] = defaultdict(int)
        for allocation in quantity_allocation_list:
            quantity_allocation_for_stocks[allocation["stock"]] += allocation[
                "quantity_allocated__sum"
            ]
        
        insufficient_stocks: list[InsufficientStockData] = []
        stocks_to_update = []
        
        for line_info in order_lines_info:
            variant = line_info.variant
            warehouse_pk = line_info.warehouse_pk
            stock = variant_and_warehouse_to_stock.get(variant.pk, {}).get(warehouse_pk)
            
            if stock is None and not allow_stock_to_be_exceeded:
                insufficient_stocks.append(
                    InsufficientStockData(
                        variant=variant,
                        order_line=line_info.line,
                        warehouse_pk=warehouse_pk,
                        available_quantity=0,
                    )
                )
                continue
            
            if stock:
                quantity_allocated = quantity_allocation_for_stocks.get(stock.pk, 0)
                is_stock_exceeded = stock.quantity - quantity_allocated < line_info.quantity
                
                if is_stock_exceeded and not allow_stock_to_be_exceeded:
                    insufficient_stocks.append(
                        InsufficientStockData(
                            variant=variant,
                            order_line=line_info.line,
                            warehouse_pk=warehouse_pk,
                            available_quantity=0,
                        )
                    )
                    continue
                
                stock.quantity = stock.quantity - line_info.quantity
                stocks_to_update.append(stock)
        
        if insufficient_stocks:
            raise InsufficientStock(insufficient_stocks)
        
        Stock.objects.bulk_update(stocks_to_update, ["quantity"])
    
    @staticmethod
    def _get_order_lines_with_track_inventory(
        order_lines_info: Iterable["OrderLineInfo"],
    ) -> Iterable["OrderLineInfo"]:
        """Return order lines with variants that track inventory."""
        return [
            line_info for line_info in order_lines_info
            if line_info.variant and line_info.variant.track_inventory
            and not line_info.variant.is_preorder_active()
        ]
    
    # ========================================================================
    # ALLOCATION MANAGEMENT
    # ========================================================================
    
    @staticmethod
    @atomic_transaction
    def allocate_stock_for_order(
        order_lines: Iterable["OrderLine"],
        channel: "Channel",
        country_code: str,
    ) -> list[Allocation]:
        """Allocate stock for order lines."""
        allocations = []
        insufficient_stocks = []
        
        for line in order_lines:
            variant = line.variant
            if not variant or not variant.track_inventory:
                continue
            
            stocks = Stock.objects.for_channel_and_country(
                channel.slug, country_code
            ).filter(
                product_variant=variant
            ).select_for_update().order_by('warehouse__name')
            
            quantity_needed = line.quantity
            for stock in stocks:
                available = stock.available_quantity
                if available <= 0:
                    continue
                
                to_allocate = min(quantity_needed, available)
                allocations.append(Allocation(
                    order_line=line,
                    stock=stock,
                    quantity_allocated=to_allocate
                ))
                quantity_needed -= to_allocate
                
                if quantity_needed <= 0:
                    break
            
            if quantity_needed > 0:
                insufficient_stocks.append(InsufficientStockData(
                    variant=variant,
                    available_quantity=0,
                    order_line=line
                ))
        
        if insufficient_stocks:
            raise InsufficientStock(insufficient_stocks)
        
        if allocations:
            created = Allocation.objects.bulk_create(allocations)
            for alloc in created:
                alloc.stock.quantity_allocated = F("quantity_allocated") + alloc.quantity_allocated
            Stock.objects.bulk_update(
                [a.stock for a in created],
                ["quantity_allocated"]
            )
        
        return allocations
    
    @staticmethod
    @atomic_transaction
    def deallocate_stock_for_order(order: "Order") -> None:
        """Deallocate all stock for an order."""
        allocations = Allocation.objects.filter(
            order_line__order=order,
            quantity_allocated__gt=0
        ).select_related('stock')
        
        for alloc in allocations:
            alloc.stock.quantity_allocated = F("quantity_allocated") - alloc.quantity_allocated
            alloc.stock.save(update_fields=["quantity_allocated"])
        
        allocations.update(quantity_allocated=0)
    
    @staticmethod
    def _deallocate_stock(
        order_lines_info: Iterable["OrderLineInfo"],
        manager: "PluginsManager"
    ) -> None:
        """Internal method to deallocate stock for order lines."""
        lines = [line_info.line for line_info in order_lines_info]
        lines_allocations = (
            Allocation.objects.filter(order_line__in=lines)
            .select_related("stock")
            .select_for_update(of=("self", "stock"))
            .order_by("stock__pk")
        )
        
        line_to_allocations: dict[UUID, list[Allocation]] = defaultdict(list)
        for allocation in lines_allocations:
            line_to_allocations[allocation.order_line_id].append(allocation)
        
        allocations_to_update = []
        stocks_to_update = []
        not_deallocated_lines = []
        
        for line_info in order_lines_info:
            order_line = line_info.line
            quantity = line_info.quantity
            allocations = line_to_allocations[order_line.pk]
            quantity_deallocated = 0
            
            for allocation in allocations:
                quantity_to_deallocate = min(
                    (quantity - quantity_deallocated), allocation.quantity_allocated
                )
                if quantity_to_deallocate > 0:
                    allocation.quantity_allocated = (
                        allocation.quantity_allocated - quantity_to_deallocate
                    )
                    stock = allocation.stock
                    stock.quantity_allocated = (
                        F("quantity_allocated") - quantity_to_deallocate
                    )
                    stocks_to_update.append(stock)
                    quantity_deallocated += quantity_to_deallocate
                    allocations_to_update.append(allocation)
                    if quantity_deallocated == quantity:
                        break
            
            if quantity_deallocated != quantity:
                not_deallocated_lines.append(order_line)
        
        # Check stock availability before updating
        allocations_before_update = list(
            Allocation.objects.filter(
                id__in=[a.id for a in allocations_to_update]
            ).annotate_stock_available_quantity()
        )
        
        Allocation.objects.bulk_update(allocations_to_update, ["quantity_allocated"])
        
        for allocation_before_update in allocations_before_update:
            available_stock_now = Allocation.objects.available_quantity_for_stock(
                allocation_before_update.stock
            )
            if (
                allocation_before_update.stock_available_quantity <= 0
                and available_stock_now > 0
            ):
                transaction.on_commit(
                    lambda: manager.product_variant_back_in_stock(
                        allocation_before_update.stock
                    )
                )
        
        Stock.objects.bulk_update(stocks_to_update, ["quantity_allocated"])
        
        if not_deallocated_lines:
            raise AllocationError(not_deallocated_lines)
    
    # ========================================================================
    # PREORDER MANAGEMENT
    # ========================================================================
    
    @staticmethod
    @atomic_transaction
    def allocate_preorders(
        order_lines_info: Iterable["OrderLineInfo"],
        channel_slug: str,
        check_reservations: bool = False,
        checkout_lines: Optional[Iterable["CheckoutLine"]] = None,
    ) -> None:
        """Allocate preorder for order lines."""
        preorder_lines = WarehouseService._get_order_lines_with_preorder(
            order_lines_info
        )
        if not preorder_lines:
            return
        
        variants = [line_info.variant for line_info in preorder_lines]
        
        all_variants_channel_listings = (
            ProductVariantChannelListing.objects.filter(variant__in=variants)
            .select_for_update()
            .select_related("channel")
            .values("id", "channel__slug", "preorder_quantity_threshold", "variant_id")
        )
        all_variants_channel_listings_id = [
            channel_listing["id"] for channel_listing in all_variants_channel_listings
        ]
        
        quantity_allocation_list = list(
            PreorderAllocation.objects.filter(
                product_variant_channel_listing_id__in=all_variants_channel_listings_id,
                quantity__gt=0,
            )
            .values("product_variant_channel_listing")
            .annotate(preorder_quantity_allocated=Sum("quantity"))
        )
        
        quantity_allocation_for_channel: dict = defaultdict(int)
        for allocation in quantity_allocation_list:
            quantity_allocation_for_channel[
                allocation["product_variant_channel_listing"]
            ] = allocation["preorder_quantity_allocated"]
        
        variants_to_channel_listings = {
            channel_listing["variant_id"]: (
                channel_listing["id"],
                channel_listing["preorder_quantity_threshold"],
            )
            for channel_listing in all_variants_channel_listings
            if channel_listing["channel__slug"] == channel_slug
        }
        
        variants_channel_listings = defaultdict(list)
        for channel_listing in all_variants_channel_listings:
            variants_channel_listings[channel_listing["variant_id"]].append(
                channel_listing["id"]
            )
        
        if check_reservations:
            quantity_reservation_list = (
                PreorderReservation.objects.filter(
                    product_variant_channel_listing_id__in=all_variants_channel_listings_id,
                    quantity_reserved__gt=0,
                )
                .not_expired()
                .exclude_checkout_lines(checkout_lines)
                .values("product_variant_channel_listing")
                .annotate(quantity_reserved_sum=Sum("quantity_reserved"))
            )
            listings_reservations: dict = defaultdict(int)
            for reservation in quantity_reservation_list:
                listings_reservations[
                    reservation["product_variant_channel_listing"]
                ] += reservation["quantity_reserved_sum"]
        else:
            listings_reservations = defaultdict(int)
        
        variants_global_allocations: dict[int, int] = defaultdict(int)
        for channel_listing in all_variants_channel_listings:
            variants_global_allocations[
                channel_listing["variant_id"]
            ] += quantity_allocation_for_channel[channel_listing["id"]]
        
        insufficient_stocks: list[InsufficientStockData] = []
        allocations: list[PreorderAllocation] = []
        
        for line_info in preorder_lines:
            variant = line_info.variant
            quantity = line_info.quantity
            channel_listing_id, channel_quantity_threshold = variants_to_channel_listings[
                variant.id
            ]
            
            # Check channel threshold
            if channel_quantity_threshold is not None:
                channel_availability = max(
                    channel_quantity_threshold
                    - quantity_allocation_for_channel[channel_listing_id]
                    - listings_reservations[channel_listing_id],
                    0
                )
                
                if quantity > channel_availability:
                    insufficient_stocks.append(
                        InsufficientStockData(
                            variant=variant,
                            available_quantity=channel_availability,
                        )
                    )
                    continue
            
            # Check global threshold
            if variant.preorder_global_threshold is not None:
                global_availability = max(
                    variant.preorder_global_threshold
                    - variants_global_allocations[variant.id]
                    - sum(listings_reservations.get(listing_id, 0) 
                         for listing_id in variants_channel_listings[variant.id]),
                    0
                )
                
                if quantity > global_availability:
                    insufficient_stocks.append(
                        InsufficientStockData(
                            variant=variant,
                            available_quantity=global_availability,
                        )
                    )
                    continue
            
            allocations.append(
                PreorderAllocation(
                    order_line=line_info.line,
                    product_variant_channel_listing_id=channel_listing_id,
                    quantity=quantity,
                )
            )
        
        if insufficient_stocks:
            raise InsufficientStock(insufficient_stocks)
        
        if allocations:
            PreorderAllocation.objects.bulk_create(allocations)
    
    @staticmethod
    def _get_order_lines_with_preorder(
        order_lines_info: Iterable["OrderLineInfo"],
    ) -> Iterable["OrderLineInfo"]:
        """Return order lines with preorder variants."""
        return [
            line_info for line_info in order_lines_info
            if line_info.variant and line_info.variant.is_preorder_active()
        ]
    
    @staticmethod
    def check_preorder_threshold_in_orders(
        variant: ProductVariant,
        quantity: int,
        channel_slug: str,
        checkout_lines: Optional[Iterable["CheckoutLine"]],
        check_reservations: bool,
    ) -> None:
        """Check preorder threshold for a variant in orders."""
        variants_channel_availability, variants_global_allocations, all_variants_channel_listings, variant_channels = (
            WarehouseService._get_variants_channel_availability_info(
                [variant], channel_slug
            )
        )
        
        if check_reservations:
            listings_reservations = WarehouseService._get_listings_reservations(
                checkout_lines, all_variants_channel_listings
            )
        else:
            listings_reservations = defaultdict(int)
        
        insufficient_stocks: list[InsufficientStockData] = []
        
        if variant.id not in variants_channel_availability:
            return
        
        if variants_channel_availability[variant.id].preorder_quantity_threshold is not None:
            channel_listing_id = variants_channel_availability[variant.id].listing_id
            available_channel_quantity = max(
                variants_channel_availability[variant.id].preorder_quantity
                - listings_reservations[channel_listing_id],
                0
            )
            
            if quantity > available_channel_quantity:
                insufficient_stocks.append(
                    InsufficientStockData(
                        variant=variant,
                        available_quantity=available_channel_quantity
                    )
                )
            
            if variant.preorder_global_threshold is not None:
                global_availability = max(
                    variant.preorder_global_threshold
                    - variants_global_allocations[variant.id]
                    - sum(listings_reservations.get(listing.id, 0) 
                         for listing in variant_channels.get(variant.id, [])),
                    0
                )
                
                if quantity > global_availability:
                    insufficient_stocks.append(
                        InsufficientStockData(
                            variant=variant,
                            available_quantity=global_availability,
                        )
                    )
        
        if insufficient_stocks:
            raise InsufficientStock(insufficient_stocks)
    
    @staticmethod
    def _get_variants_channel_availability_info(
        variants: Iterable[ProductVariant],
        channel_slug: str,
    ) -> tuple:
        """Get channel availability info for variants."""
        all_variants_channel_listings = (
            ProductVariantChannelListing.objects.filter(variant__in=variants)
            .annotate_preorder_quantity_allocated()
            .annotate(
                available_preorder_quantity=F("preorder_quantity_threshold")
                - Coalesce(Sum("preorder_allocations__quantity"), 0),
            )
            .select_related("channel")
        )
        
        variants_channel_availability = {
            channel_listing.variant_id: ChannelListingPreorderAvailabilityInfo(
                channel_listing.available_preorder_quantity,
                channel_listing.preorder_quantity_threshold,
                channel_listing.id,
            )
            for channel_listing in all_variants_channel_listings
            if channel_listing.channel.slug == channel_slug
        }
        
        variant_channels: dict[int, list[ProductVariantChannelListing]] = defaultdict(list)
        for channel_listing in all_variants_channel_listings:
            variant_channels[channel_listing.variant_id].append(channel_listing)
        
        variants_global_allocations = {
            variant_id: sum(
                channel_listing.preorder_quantity_allocated
                for channel_listing in channel_listings
            )
            for variant_id, channel_listings in variant_channels.items()
        }
        
        return (
            variants_channel_availability,
            variants_global_allocations,
            all_variants_channel_listings,
            variant_channels,
        )
    
    @staticmethod
    def _get_listings_reservations(
        checkout_lines: Optional[Iterable["CheckoutLine"]],
        all_variants_channel_listings,
    ) -> dict[int, int]:
        """Get reservations for channel listings."""
        quantity_reservation_list = (
            PreorderReservation.objects.filter(
                product_variant_channel_listing__in=all_variants_channel_listings,
                quantity_reserved__gt=0,
            )
            .not_expired()
            .exclude_checkout_lines(checkout_lines)
            .values("product_variant_channel_listing")
            .annotate(quantity_reserved_sum=Sum("quantity_reserved"))
        )
        
        listings_reservations: dict = defaultdict(int)
        for reservation in quantity_reservation_list:
            listings_reservations[
                reservation["product_variant_channel_listing"]
            ] += reservation["quantity_reserved_sum"]
        
        return listings_reservations
    
    @staticmethod
    @atomic_transaction
    def deactivate_preorder_for_variant(product_variant: ProductVariant) -> None:
        """Deactivate preorder and convert to regular stock."""
        if not product_variant.is_preorder:
            return
        
        channel_listings = ProductVariantChannelListing.objects.filter(
            variant_id=product_variant.pk
        )
        channel_listings_pk = [channel_listing.id for channel_listing in channel_listings]
        
        preorder_allocations = PreorderAllocation.objects.filter(
            product_variant_channel_listing_id__in=channel_listings_pk
        ).select_for_update().select_related("order_line", "order_line__order")
        
        allocations_to_create = []
        stocks_to_create = []
        stocks_to_update = []
        
        for preorder_allocation in preorder_allocations:
            stock = WarehouseService._get_stock_for_preorder_allocation(
                preorder_allocation, product_variant
            )
            if stock._state.adding:
                stock.quantity_allocated += preorder_allocation.quantity
                stocks_to_create.append(stock)
            else:
                stock.quantity_allocated = F("quantity_allocated") + preorder_allocation.quantity
                stocks_to_update.append(stock)
            
            allocations_to_create.append(
                Allocation(
                    order_line=preorder_allocation.order_line,
                    stock=stock,
                    quantity_allocated=preorder_allocation.quantity,
                )
            )
        
        if stocks_to_create:
            Stock.objects.bulk_create(stocks_to_create)
        
        if stocks_to_update:
            Stock.objects.bulk_update(stocks_to_update, ["quantity_allocated"])
        
        if allocations_to_create:
            Allocation.objects.bulk_create(allocations_to_create)
        
        if preorder_allocations:
            preorder_allocations.delete()
        
        product_variant.preorder_global_threshold = None
        product_variant.preorder_end_date = None
        product_variant.is_preorder = False
        product_variant.save(
            update_fields=[
                "preorder_global_threshold",
                "preorder_end_date",
                "is_preorder",
                "updated_at",
            ]
        )
        
        ProductVariantChannelListing.objects.filter(variant_id=product_variant.pk).update(
            preorder_quantity_threshold=None
        )
    
    @staticmethod
    def _get_stock_for_preorder_allocation(
        preorder_allocation: PreorderAllocation,
        product_variant: ProductVariant
    ) -> Stock:
        """Get or create stock for a preorder allocation."""
        order = preorder_allocation.order_line.order
        shipping_method_id = order.shipping_method_id
        
        if shipping_method_id is not None:
            warehouse = Warehouse.objects.filter(
                shipping_zones__id=order.shipping_method.shipping_zone_id
            ).first()
        else:
            from ..order.utils import get_order_country
            country = get_order_country(order)
            warehouse = Warehouse.objects.filter(
                shipping_zones__countries__contains=country
            ).first()
        
        if not warehouse:
            raise PreorderAllocationError(preorder_allocation.order_line)
        
        stock = list(
            Stock.objects.select_for_update().filter(
                warehouse=warehouse, product_variant=product_variant
            )
        )
        
        return (stock[0] if stock else None) or Stock(
            warehouse=warehouse, product_variant=product_variant, quantity=0
        )
    
    # ========================================================================
    # RESERVATION MANAGEMENT
    # ========================================================================
    
    @staticmethod
    @atomic_transaction
    def reserve_stock(
        checkout_line: "CheckoutLine",
        quantity: int,
        duration_minutes: int,
    ) -> Reservation:
        """Reserve stock for a checkout line."""
        stock = Stock.objects.select_for_update().get(
            warehouse=checkout_line.variant.stocks.first().warehouse,
            product_variant=checkout_line.variant
        )
        
        if stock.available_quantity < quantity:
            raise InsufficientStock([InsufficientStockData(
                variant=checkout_line.variant,
                available_quantity=stock.available_quantity
            )])
        
        reservation, created = Reservation.objects.get_or_create(
            checkout_line=checkout_line,
            stock=stock,
            defaults={
                'quantity_reserved': quantity,
                'reserved_until': timezone.now() + timedelta(minutes=duration_minutes)
            }
        )
        
        if not created:
            reservation.quantity_reserved = quantity
            reservation.reserved_until = timezone.now() + timedelta(minutes=duration_minutes)
            reservation.save()
        
        return reservation
    
    @staticmethod
    @atomic_transaction
    def reserve_stocks_and_preorders(
        checkout_lines: Iterable["CheckoutLine"],
        lines_to_update_reservation_time: Iterable["CheckoutLine"],
        variants: Iterable[ProductVariant],
        country_code: str,
        channel: "Channel",
        length_in_minutes: int,
        replace: bool = True,
    ) -> None:
        """Reserve stocks and preorders for checkout lines."""
        stock_variants, stock_lines = [], []
        preorder_variants, preorder_lines = [], []
        
        for variant in variants:
            if variant.is_preorder_active():
                preorder_variants.append(variant)
            else:
                stock_variants.append(variant)
        
        for line in checkout_lines:
            if line.variant.is_preorder_active():
                preorder_lines.append(line)
            else:
                stock_lines.append(line)
        
        reserved_until = timezone.now() + timedelta(minutes=length_in_minutes)
        
        if stock_lines:
            WarehouseService._reserve_stocks(
                stock_lines, stock_variants, country_code, channel,
                reserved_until, replace
            )
            
            if lines_to_update_reservation_time:
                Reservation.objects.filter(
                    checkout_line__in=lines_to_update_reservation_time
                ).update(reserved_until=reserved_until)
        
        if preorder_lines:
            WarehouseService._reserve_preorders(
                preorder_lines, preorder_variants, channel.slug,
                reserved_until, replace
            )
            
            if lines_to_update_reservation_time:
                PreorderReservation.objects.filter(
                    checkout_line__in=lines_to_update_reservation_time
                ).update(reserved_until=reserved_until)
    
    @staticmethod
    def _reserve_stocks(
        checkout_lines: Iterable["CheckoutLine"],
        variants: Iterable[ProductVariant],
        country_code: str,
        channel: "Channel",
        reserved_until: datetime,
        replace: bool = True,
    ) -> None:
        """Internal method to reserve stocks."""
        variants_ids = [line.variant_id for line in checkout_lines]
        variants = [v for v in variants if v.pk in variants_ids]
        variants_map = {v.id: v for v in variants}
        
        checkout_lines = WarehouseService._get_checkout_lines_to_reserve(
            checkout_lines, variants_map
        )
        if not checkout_lines:
            return
        
        stocks = list(
            Stock.objects.select_for_update()
            .get_variants_stocks_for_country(country_code, channel.slug, variants)
            .order_by("pk")
            .values("id", "product_variant", "pk", "quantity", "warehouse_id")
        )
        stocks_id = [stock.pop("id") for stock in stocks]
        
        quantity_allocation_for_stocks = WarehouseService._get_quantity_allocation_for_stocks(
            stocks_id
        )
        quantity_reservation_for_stocks = WarehouseService._get_quantity_reservation_for_stocks(
            stocks_id, checkout_lines
        )
        
        stocks = WarehouseService._sort_stocks(
            channel.allocation_strategy,
            stocks,
            channel,
            quantity_allocation_for_stocks,
        )
        
        variant_to_stocks: dict[int, list[StockData]] = defaultdict(list)
        for stock_data in stocks:
            variant = stock_data.pop("product_variant")
            variant_to_stocks[variant].append(StockData(**stock_data))
        
        insufficient_stocks: list[InsufficientStockData] = []
        reservations: list[Reservation] = []
        
        for line in checkout_lines:
            insufficient_stocks, reserved_items = WarehouseService._create_stock_reservations(
                line,
                variants_map[line.variant_id],
                variant_to_stocks[line.variant_id],
                quantity_allocation_for_stocks,
                quantity_reservation_for_stocks,
                insufficient_stocks,
                reserved_until,
            )
            reservations.extend(reserved_items)
        
        if insufficient_stocks:
            raise InsufficientStock(insufficient_stocks)
        
        if reservations:
            if replace:
                Reservation.objects.filter(checkout_line__in=checkout_lines).delete()
            Reservation.objects.bulk_create(reservations)
    
    @staticmethod
    def _reserve_preorders(
        checkout_lines: Iterable["CheckoutLine"],
        variants: Iterable[ProductVariant],
        channel_slug: str,
        reserved_until: datetime,
        replace: bool = True,
    ) -> None:
        """Internal method to reserve preorders."""
        variants_ids = [line.variant_id for line in checkout_lines]
        variants = [v for v in variants if v.pk in variants_ids]
        variants_map = {v.id: v for v in variants}
        
        all_variants_channel_listings = (
            ProductVariantChannelListing.objects.filter(variant__in=variants)
            .annotate_preorder_quantity_allocated()
            .annotate(
                available_preorder_quantity=F("preorder_quantity_threshold")
                - Coalesce(Sum("preorder_allocations__quantity"), 0),
            )
            .select_related("channel")
        )
        
        variants_channel_listings = {
            cl.variant_id: cl for cl in all_variants_channel_listings
            if cl.channel.slug == channel_slug
        }
        
        checkout_lines_to_reserve = []
        for line in checkout_lines:
            line_variant_channel_listing = variants_channel_listings[line.variant_id]
            if (
                line.variant.preorder_global_threshold
                or line_variant_channel_listing.preorder_quantity_threshold is not None
            ):
                checkout_lines_to_reserve.append(line)
        
        if not checkout_lines_to_reserve:
            return
        
        variant_channels: dict[int, list[ProductVariantChannelListing]] = defaultdict(list)
        for channel_listing in all_variants_channel_listings:
            variant_channels[channel_listing.variant_id].append(channel_listing)
        
        variants_global_allocations = {
            variant_id: sum(
                channel_listing.preorder_quantity_allocated
                for channel_listing in channel_listings
            )
            for variant_id, channel_listings in variant_channels.items()
        }
        
        listings_reservations = WarehouseService._get_listings_reservations(
            checkout_lines, all_variants_channel_listings
        )
        
        insufficient_stocks: list[InsufficientStockData] = []
        reservations: list[PreorderReservation] = []
        
        for line in checkout_lines_to_reserve:
            insufficient_stocks, reservation = WarehouseService._create_preorder_reservation(
                line,
                variants_map[line.variant_id],
                variants_channel_listings[line.variant_id],
                variant_channels[line.variant_id],
                variants_global_allocations[line.variant_id],
                listings_reservations,
                insufficient_stocks,
                reserved_until,
            )
            if reservation:
                reservations.append(reservation)
        
        if insufficient_stocks:
            raise InsufficientStock(insufficient_stocks)
        
        if reservations:
            if replace:
                PreorderReservation.objects.filter(
                    checkout_line__in=checkout_lines_to_reserve
                ).delete()
            PreorderReservation.objects.bulk_create(reservations)
    
    @staticmethod
    def release_expired_reservations() -> int:
        """Release all expired reservations."""
        expired = Reservation.objects.filter(reserved_until__lt=timezone.now())
        count = expired.count()
        expired.delete()
        return count
    
    @staticmethod
    def _get_quantity_allocation_for_stocks(stocks_id: list) -> dict[int, int]:
        """Get quantity allocations for stocks."""
        quantity_allocation_list = list(
            Allocation.objects.filter(
                stock_id__in=stocks_id, quantity_allocated__gt=0
            )
            .values("stock")
            .annotate(quantity_allocated_sum=Sum("quantity_allocated"))
        )
        quantity_allocation_for_stocks: dict = defaultdict(int)
        for allocation in quantity_allocation_list:
            quantity_allocation_for_stocks[allocation["stock"]] += allocation[
                "quantity_allocated_sum"
            ]
        return quantity_allocation_for_stocks
    
    @staticmethod
    def _get_quantity_reservation_for_stocks(
        stocks_id: list,
        checkout_lines: Iterable["CheckoutLine"]
    ) -> dict[int, int]:
        """Get quantity reservations for stocks."""
        quantity_reservation_list = list(
            Reservation.objects.filter(
                stock_id__in=stocks_id, quantity_reserved__gt=0
            )
            .not_expired()
            .exclude_checkout_lines(checkout_lines)
            .values("stock")
            .annotate(quantity_reserved_sum=Sum("quantity_reserved"))
        )
        quantity_reservation_for_stocks: dict = defaultdict(int)
        for reservation in quantity_reservation_list:
            quantity_reservation_for_stocks[reservation["stock"]] += reservation[
                "quantity_reserved_sum"
            ]
        return quantity_reservation_for_stocks
    
    @staticmethod
    def _sort_stocks(
        allocation_strategy: str,
        stocks: list[dict],
        channel: "Channel",
        quantity_allocation_for_stocks: dict[int, int],
        collection_point_pk: Optional[UUID] = None,
    ) -> list[dict]:
        """Sort stocks based on allocation strategy."""
        warehouse_ids = [stock_data["warehouse_id"] for stock_data in stocks]
        channel_warehouse_ids = ChannelWarehouse.objects.filter(
            channel_id=channel.id, warehouse_id__in=warehouse_ids
        ).values_list("warehouse_id", flat=True)
        
        def sort_stocks_by_highest_stocks(stock_data):
            if stock_data.pop("warehouse_id") == collection_point_pk:
                return float('inf')
            return stock_data["quantity"] - quantity_allocation_for_stocks.get(
                stock_data["pk"], 0
            )
        
        def sort_stocks_by_warehouse_sorting_order(stock_data):
            sorted_warehouse_list = list(channel_warehouse_ids)
            warehouse_id = stock_data.pop("warehouse_id")
            if warehouse_id == collection_point_pk:
                return -float('inf')
            try:
                return sorted_warehouse_list.index(warehouse_id)
            except ValueError:
                return len(sorted_warehouse_list)
        
        allocation_strategy_to_sort_method = {
            "PRIORITIZE_HIGH_STOCK": (sort_stocks_by_highest_stocks, True),
            "PRIORITIZE_SORTING_ORDER": (sort_stocks_by_warehouse_sorting_order, False),
        }
        
        sort_method, reverse = allocation_strategy_to_sort_method.get(
            allocation_strategy, (sort_stocks_by_highest_stocks, True)
        )
        stocks.sort(key=sort_method, reverse=reverse)
        return stocks
    
    @staticmethod
    def _create_stock_reservations(
        line: "CheckoutLine",
        variant: ProductVariant,
        stocks: list[StockData],
        quantity_allocation_for_stocks: dict,
        quantity_reservation_for_stocks: dict,
        insufficient_stocks: list[InsufficientStockData],
        reserved_until: datetime,
    ) -> tuple[list[InsufficientStockData], list[Reservation]]:
        """Create stock reservations for a line."""
        quantity = line.quantity
        quantity_reserved = 0
        reservations = []
        
        for stock_data in stocks:
            quantity_allocated_in_stock = quantity_allocation_for_stocks.get(
                stock_data.pk, 0
            )
            quantity_reserved_in_stock = quantity_reservation_for_stocks.get(
                stock_data.pk, 0
            )
            
            quantity_available_in_stock = max(
                stock_data.quantity
                - quantity_allocated_in_stock
                - quantity_reserved_in_stock,
                0,
            )
            
            quantity_to_reserve = min(
                (quantity - quantity_reserved), quantity_available_in_stock
            )
            if quantity_to_reserve > 0:
                reservations.append(
                    Reservation(
                        checkout_line=line,
                        stock_id=stock_data.pk,
                        quantity_reserved=quantity_to_reserve,
                        reserved_until=reserved_until,
                    )
                )
                quantity_reserved += quantity_to_reserve
                if quantity_reserved == quantity:
                    return insufficient_stocks, reservations
        
        if quantity_reserved != quantity:
            insufficient_stocks.append(
                InsufficientStockData(
                    variant=variant,
                    available_quantity=quantity,
                )
            )
        
        return insufficient_stocks, []
    
    @staticmethod
    def _create_preorder_reservation(
        line: "CheckoutLine",
        variant: ProductVariant,
        listing: ProductVariantChannelListing,
        all_listings: list[ProductVariantChannelListing],
        global_allocations: int,
        listings_reservations: dict[int, int],
        insufficient_stocks: list[InsufficientStockData],
        reserved_until: datetime,
    ) -> tuple[list[InsufficientStockData], Optional[PreorderReservation]]:
        """Create preorder reservation for a line."""
        if listing.preorder_quantity_threshold is not None:
            available_channel_quantity = max(
                listing.available_preorder_quantity - listings_reservations[listing.id], 0
            )
            if line.quantity > available_channel_quantity:
                insufficient_stocks.append(
                    InsufficientStockData(
                        variant=variant,
                        available_quantity=available_channel_quantity,
                    )
                )
        
        if variant.preorder_global_threshold:
            available_global_quantity = max(
                variant.preorder_global_threshold
                - global_allocations
                - sum(listings_reservations[cl.id] for cl in all_listings),
                0
            )
            if line.quantity > available_global_quantity:
                insufficient_stocks.append(
                    InsufficientStockData(
                        variant=variant,
                        available_quantity=available_global_quantity,
                    )
                )
        
        if listing.preorder_quantity_threshold or variant.preorder_global_threshold:
            return insufficient_stocks, PreorderReservation(
                checkout_line=line,
                product_variant_channel_listing=listing,
                quantity_reserved=line.quantity,
                reserved_until=reserved_until,
            )
        
        return insufficient_stocks, None
    
    @staticmethod
    def _get_checkout_lines_to_reserve(
        lines: Iterable["CheckoutLine"],
        variants_map: dict[int, ProductVariant],
    ) -> Iterable["CheckoutLine"]:
        """Return checkout lines that can be reserved."""
        valid_lines = []
        for line in lines:
            if (
                line.quantity
                and line.variant_id
                and variants_map[line.variant_id].track_inventory
            ):
                valid_lines.append(line)
        return valid_lines
    
   
# ============================================================================
# HELPER CLASSES
# ============================================================================

class ChannelListingPreorderAvailabilityInfo:
    """Container for preorder availability info."""
    def __init__(self, preorder_quantity: int, preorder_quantity_threshold: int, listing_id: int):
        self.preorder_quantity = preorder_quantity
        self.preorder_quantity_threshold = preorder_quantity_threshold
        self.listing_id = listing_id


class AllocationError(Exception):
    """Exception raised when allocation fails."""
    def __init__(self, order_lines):
        self.order_lines = order_lines
        super().__init__(f"Allocation error for lines: {order_lines}")


class PreorderAllocationError(Exception):
    """Exception raised when preorder allocation fails."""
    def __init__(self, order_line):
        self.order_line = order_line
        super().__init__(f"Preorder allocation error for line: {order_line}")