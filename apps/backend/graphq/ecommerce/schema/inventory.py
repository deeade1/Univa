# graphql/ecommerce/queries/inventory.py

import graphene
from graphene import Node
from graphene_django.filter import DjangoFilterConnectionField
from django.db.models import Q
from django.utils import timezone

from graphq.ecommerce.types.inventory import (
    StockNode,
    StockHistoryNode,
    AllocationNode,
    ReservationNode,
    PreorderAllocationNode,
    PreorderReservationNode,
    ReturnsManagementNode,
    InventoryPredictionNode,
    InventoryHealthMetricsNode,
    InterWarehouseTransferNode,
    WarehousePerformanceNode,
    WarehouseTaskNode,
)
from ecommerce.models.inventory import (
    Stock,
    StockHistory,
    Allocation,
    Reservation,
    PreorderAllocation,
    PreorderReservation,
    ReturnsManagement,
    InventoryPrediction,
    InventoryHealthMetrics,
    InterWarehouseTransfer,
    WarehousePerformance,
    WarehouseTask,
)


class InventoryQuery(graphene.ObjectType):
    """
    Inventory GraphQL Queries.
    """
    
    # ============================================================
    # Stock Queries
    # ============================================================
    
    stock = Node.Field(StockNode, description="Get a single stock by ID")
    all_stocks = DjangoFilterConnectionField(StockNode)
    
    # Custom stock queries
    stocks_by_warehouse = DjangoFilterConnectionField(StockNode)
    
    stocks_by_variant = DjangoFilterConnectionField(StockNode)
    
    stocks_low_stock = DjangoFilterConnectionField(StockNode)
    
    # ============================================================
    # Stock History Queries
    # ============================================================
    
    stock_history = Node.Field(StockHistoryNode, description="Get a single stock history entry by ID")
    all_stock_history = DjangoFilterConnectionField(StockHistoryNode)
    
    stock_history_by_stock = DjangoFilterConnectionField(StockHistoryNode)
    
    # ============================================================
    # Allocation Queries
    # ============================================================
    
    allocation = Node.Field(AllocationNode, description="Get a single allocation by ID")
    all_allocations = DjangoFilterConnectionField(AllocationNode)
    
    allocations_by_order_line = DjangoFilterConnectionField(AllocationNode)
    
    # ============================================================
    # Reservation Queries
    # ============================================================
    
    reservation = Node.Field(ReservationNode, description="Get a single reservation by ID")
    all_reservations = DjangoFilterConnectionField(ReservationNode)
    
    active_reservations = DjangoFilterConnectionField(ReservationNode)
    
    expired_reservations = DjangoFilterConnectionField(ReservationNode)
    
    # ============================================================
    # Preorder Allocation Queries
    # ============================================================
    
    preorder_allocation = Node.Field(PreorderAllocationNode, description="Get a single preorder allocation by ID")
    all_preorder_allocations = DjangoFilterConnectionField(PreorderAllocationNode)
    
    # ============================================================
    # Preorder Reservation Queries
    # ============================================================
    
    preorder_reservation = Node.Field(PreorderReservationNode, description="Get a single preorder reservation by ID")
    all_preorder_reservations = DjangoFilterConnectionField(PreorderReservationNode)
    
    # ============================================================
    # Returns Management Queries
    # ============================================================
    
    returns_management = Node.Field(ReturnsManagementNode, description="Get a single returns management entry by ID")
    all_returns_management = DjangoFilterConnectionField(ReturnsManagementNode)
    
    returns_by_order = DjangoFilterConnectionField(ReturnsManagementNode)
    
    returns_by_warehouse = DjangoFilterConnectionField(ReturnsManagementNode)
    
    # ============================================================
    # Inventory Prediction Queries
    # ============================================================
    
    inventory_prediction = Node.Field(InventoryPredictionNode, description="Get a single inventory prediction by ID")
    all_inventory_predictions = DjangoFilterConnectionField(InventoryPredictionNode)
    
    latest_inventory_predictions = DjangoFilterConnectionField(InventoryPredictionNode)
    
    # ============================================================
    # Inventory Health Metrics Queries
    # ============================================================
    
    inventory_health_metrics = Node.Field(InventoryHealthMetricsNode, description="Get a single inventory health metric by ID")
    all_inventory_health_metrics = DjangoFilterConnectionField(InventoryHealthMetricsNode)
    
    # ============================================================
    # Inter-Warehouse Transfer Queries
    # ============================================================
    
    inter_warehouse_transfer = Node.Field(InterWarehouseTransferNode, description="Get a single inter-warehouse transfer by ID")
    all_inter_warehouse_transfers = DjangoFilterConnectionField(InterWarehouseTransferNode)
    transfers_by_source = DjangoFilterConnectionField(InterWarehouseTransferNode)
    
    transfers_by_destination = DjangoFilterConnectionField(InterWarehouseTransferNode)
    
    pending_transfers = DjangoFilterConnectionField(InterWarehouseTransferNode)
    
    # ============================================================
    # Warehouse Performance Queries
    # ============================================================
    
    warehouse_performance = Node.Field(WarehousePerformanceNode, description="Get a single warehouse performance entry by ID")
    all_warehouse_performances = DjangoFilterConnectionField(WarehousePerformanceNode)
    
    latest_warehouse_performance = DjangoFilterConnectionField(WarehousePerformanceNode)
    
    # ============================================================
    # Warehouse Task Queries
    # ============================================================
    
    warehouse_task = Node.Field(WarehouseTaskNode, description="Get a single warehouse task by ID")
    all_warehouse_tasks = DjangoFilterConnectionField(WarehouseTaskNode)
    
    tasks_by_warehouse = DjangoFilterConnectionField(WarehouseTaskNode)
    
    tasks_by_assigned_to = DjangoFilterConnectionField(WarehouseTaskNode)
    
    tasks_by_status = DjangoFilterConnectionField(WarehouseTaskNode)
    
    # ============================================================
    # Resolvers
    # ============================================================
    
    def resolve_stocks_by_warehouse(self, info, warehouse_id):
        """Get stocks for a specific warehouse."""
        return Stock.objects.filter(warehouse_id=warehouse_id)
    
    def resolve_stocks_by_variant(self, info, variant_id):
        """Get stocks for a specific product variant."""
        return Stock.objects.filter(product_variant_id=variant_id)
    
    def resolve_stocks_low_stock(self, info, warehouse_id=None):
        """Get stocks that are below threshold."""
        queryset = Stock.objects.annotate_available_quantity().filter(
            available_quantity__lte=models.F('low_stock_threshold')
        )
        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)
        return queryset
    
    def resolve_stock_history_by_stock(self, info, stock_id, limit=20):
        """Get stock history for a specific stock."""
        return StockHistory.objects.filter(stock_id=stock_id)[:limit]
    
    def resolve_allocations_by_order_line(self, info, order_line_id):
        """Get allocations for a specific order line."""
        return Allocation.objects.filter(order_line_id=order_line_id)
    
    def resolve_active_reservations(self, info):
        """Get all active (non-expired) reservations."""
        return Reservation.objects.filter(reserved_until__gt=timezone.now())
    
    def resolve_expired_reservations(self, info):
        """Get all expired reservations."""
        return Reservation.objects.filter(reserved_until__lt=timezone.now())
    
    def resolve_returns_by_order(self, info, order_id):
        """Get returns for a specific order."""
        return ReturnsManagement.objects.filter(order_id=order_id)
    
    def resolve_returns_by_warehouse(self, info, warehouse_id):
        """Get returns for a specific warehouse."""
        return ReturnsManagement.objects.filter(warehouse_id=warehouse_id)
    
    def resolve_latest_inventory_predictions(self, info, variant_id, limit=5):
        """Get latest predictions for a variant."""
        return InventoryPrediction.objects.filter(
            variant_id=variant_id
        ).order_by('-prediction_date')[:limit]
    
    def resolve_transfers_by_source(self, info, warehouse_id):
        """Get transfers from a specific source warehouse."""
        return InterWarehouseTransfer.objects.filter(source_warehouse_id=warehouse_id)
    
    def resolve_transfers_by_destination(self, info, warehouse_id):
        """Get transfers to a specific destination warehouse."""
        return InterWarehouseTransfer.objects.filter(destination_warehouse_id=warehouse_id)
    
    def resolve_pending_transfers(self, info):
        """Get all pending transfers."""
        return InterWarehouseTransfer.objects.filter(
            status__in=['REQUESTED', 'APPROVED', 'PICKING']
        )
    
    def resolve_latest_warehouse_performance(self, info, warehouse_id):
        """Get the latest performance entry for a warehouse."""
        return WarehousePerformance.objects.filter(
            warehouse_id=warehouse_id
        ).order_by('-date').first()
    
    def resolve_tasks_by_warehouse(self, info, warehouse_id, status=None):
        """Get tasks for a specific warehouse."""
        queryset = WarehouseTask.objects.filter(warehouse_id=warehouse_id)
        if status:
            queryset = queryset.filter(task_status=status)
        return queryset
    
    def resolve_tasks_by_assigned_to(self, info, user_id):
        """Get tasks assigned to a specific user."""
        return WarehouseTask.objects.filter(assigned_to_id=user_id)
    
    def resolve_tasks_by_status(self, info, status):
        """Get tasks by status."""
        return WarehouseTask.objects.filter(task_status=status)