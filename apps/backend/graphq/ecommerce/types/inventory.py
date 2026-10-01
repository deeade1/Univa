# graphql/ecommerce/types/warehouse.py

"""
GraphQL Nodes for Warehouse, Stock, Allocation, Reservation, and related inventory models.
"""

from graphene import Node, String, Boolean, Field, List, DateTime, Int, Decimal, UUID, JSONString, Float
from graphene_django_optimizer import OptimizedDjangoObjectType

from ecommerce.models.warehouse import Warehouse, ChannelWarehouse
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




class StockNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Stock with full stock management.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    available_quantity = Int(description="Quantity available after allocations")
    is_low_stock = Boolean(description="Whether stock is below threshold")
    is_out_of_stock = Boolean(description="Whether stock is out of stock")
    is_in_stock = Boolean(description="Whether stock is in stock")
    restock_lead_time_display = String(description="Formatted restock lead time")
    

    class Meta:
        model = Stock
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Foreign keys
            'warehouse': ['exact'],
            'product_variant': ['exact'],
            
            # Numeric fields
            'quantity': ['exact', 'gte', 'lte'],
            'quantity_allocated': ['exact', 'gte', 'lte'],
            'low_stock_threshold': ['exact', 'gte', 'lte'],
            'restock_lead_time_days': ['exact', 'gte', 'lte'],
            
            # Date fields
            'last_restocked_at': ['exact', 'gte', 'lte', 'isnull'],
        }
        
    
    def resolve_available_quantity(self, info):
        """Resolve quantity available after allocations."""
        return self.available_quantity
    
    def resolve_is_low_stock(self, info):
        """Resolve whether stock is below threshold."""
        return self.is_low_stock
    
    def resolve_is_out_of_stock(self, info):
        """Resolve whether stock is out of stock."""
        return self.available_quantity <= 0
    
    def resolve_is_in_stock(self, info):
        """Resolve whether stock is in stock."""
        return self.available_quantity > 0
    
    def resolve_restock_lead_time_display(self, info):
        """Resolve formatted restock lead time."""
        return f"{self.restock_lead_time_days} days"
    
    def resolve_warehouse_details(self, info):
        """Resolve warehouse details."""
        return self.warehouse
    
    def resolve_product_variant_details(self, info):
        """Resolve product variant details."""
        return self.product_variant
    
    def resolve_history(self, info):
        """Resolve stock history."""
        return self.history.all().order_by('-created_at')
    
    def resolve_allocations(self, info):
        """Resolve allocations."""
        return self.allocations.all()
    
    def resolve_reservations(self, info):
        """Resolve reservations."""
        return self.reservations.all()


class StockHistoryNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Stock History.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    change_type_display = String(description="Human-readable change type display")
    is_increase = Boolean(description="Whether quantity increased")
    is_decrease = Boolean(description="Whether quantity decreased")
    change_display = String(description="Formatted change display")
    
    class Meta:
        model = StockHistory
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Foreign keys
            'stock': ['exact'],
            'product_variant': ['exact'],
            'warehouse': ['exact'],
            'order': ['exact'],
            'order_line': ['exact'],
            'user': ['exact'],
            
            # String fields
            'change_type': ['exact'],
            'reason': ['exact', 'icontains'],
            'reference': ['exact', 'icontains'],
            
            # Numeric fields
            'quantity_change': ['exact', 'gte', 'lte'],
            'previous_quantity': ['exact', 'gte', 'lte'],
            'new_quantity': ['exact', 'gte', 'lte'],
            
            # Date fields
            'created_at': ['exact', 'gte', 'lte'],
        }
    
    def resolve_change_type_display(self, info):
        """Resolve human-readable change type display."""
        return dict(StockHistory.ChangeType.choices).get(self.change_type, self.change_type)
    
    def resolve_is_increase(self, info):
        """Resolve whether quantity increased."""
        return self.is_increase
    
    def resolve_is_decrease(self, info):
        """Resolve whether quantity decreased."""
        return self.is_decrease
    
    def resolve_change_display(self, info):
        """Resolve formatted change display."""
        if self.is_increase:
            return f"+{self.quantity_change}"
        return f"{self.quantity_change}"
    
    def resolve_stock_details(self, info):
        """Resolve stock details."""
        return self.stock
    
    def resolve_product_variant_details(self, info):
        """Resolve product variant details."""
        return self.product_variant
    
    def resolve_warehouse_details(self, info):
        """Resolve warehouse details."""
        return self.warehouse
    
    def resolve_order_details(self, info):
        """Resolve order details."""
        return self.order
    
    def resolve_order_line_details(self, info):
        """Resolve order line details."""
        return self.order_line
    
    def resolve_user_details(self, info):
        """Resolve user who performed the change."""
        return self.user


class AllocationNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Allocation.
    """

    class Meta:
        model = Allocation
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            'order_line': ['exact'],
            'stock': ['exact'],
            'quantity_allocated': ['exact', 'gte', 'lte'],
        }
       
    
    def resolve_order_line_details(self, info):
        """Resolve order line details."""
        return self.order_line
    
    def resolve_stock_details(self, info):
        """Resolve stock details."""
        return self.stock


class ReservationNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Reservation.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    is_expired = Boolean(description="Whether reservation has expired")
    time_remaining_minutes = Float(description="Minutes remaining until expiration")
    
    class Meta:
        model = Reservation
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            'checkout_line': ['exact'],
            'stock': ['exact'],
            'quantity_reserved': ['exact', 'gte', 'lte'],
            'reserved_until': ['exact', 'gte', 'lte'],
        }
    
    def resolve_is_expired(self, info):
        """Resolve whether reservation has expired."""
        return timezone.now() > self.reserved_until
    
    def resolve_time_remaining_minutes(self, info):
        """Resolve minutes remaining until expiration."""
        if self.reserved_until:
            remaining = (self.reserved_until - timezone.now()).total_seconds() / 60
            return max(0, remaining)
        return None
    
    def resolve_checkout_line_details(self, info):
        """Resolve checkout line details."""
        return self.checkout_line
    
    def resolve_stock_details(self, info):
        """Resolve stock details."""
        return self.stock


class PreorderAllocationNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Preorder Allocation.
    """

    class Meta:
        model = PreorderAllocation
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            'order_line': ['exact'],
            'product_variant_channel_listing': ['exact'],
            'quantity': ['exact', 'gte', 'lte'],
        }
        
    
    def resolve_order_line_details(self, info):
        """Resolve order line details."""
        return self.order_line
    
    def resolve_product_variant_channel_listing_details(self, info):
        """Resolve product variant channel listing details."""
        return self.product_variant_channel_listing


class PreorderReservationNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Preorder Reservation.
    """

    class Meta:
        model = PreorderReservation
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            'checkout_line': ['exact'],
            'product_variant_channel_listing': ['exact'],
            'quantity_reserved': ['exact', 'gte', 'lte'],
            'reserved_until': ['exact', 'gte', 'lte'],
        }
    
    def resolve_checkout_line_details(self, info):
        """Resolve checkout line details."""
        return self.checkout_line
    
    def resolve_product_variant_channel_listing_details(self, info):
        """Resolve product variant channel listing details."""
        return self.product_variant_channel_listing


class ReturnsManagementNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Returns Management.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    return_reason_display = String(description="Return reason")
    return_category_display = String(description="Return category")
    refund_amount_display = String(description="Formatted refund amount")
    restocking_fee_display = String(description="Formatted restocking fee")
    disposal_cost_display = String(description="Formatted disposal cost")
    is_completed = Boolean(description="Whether return is completed")
    is_inspected = Boolean(description="Whether return has been inspected")
    is_restocked = Boolean(description="Whether return has been restocked")
    
    class Meta:
        model = ReturnsManagement
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            'rma_number': ['exact', 'icontains'],
            'order': ['exact'],
            'variant': ['exact'],
            'warehouse': ['exact'],
            'inspector': ['exact'],
            'quantity_returned': ['exact', 'gte', 'lte'],
            'quantity_restockable': ['exact', 'gte', 'lte'],
            'quantity_damaged': ['exact', 'gte', 'lte'],
            'quality_score': ['exact', 'gte', 'lte', 'isnull'],
            'refund_amount': ['exact', 'gte', 'lte', 'isnull'],
            'return_reason': ['exact', 'icontains'],
            'return_category': ['exact', 'icontains'],
            'inspection_notes': ['exact', 'icontains'],
            'received_at': ['exact', 'gte', 'lte'],
            'inspection_date': ['exact', 'gte', 'lte', 'isnull'],
            'inspected_at': ['exact', 'gte', 'lte', 'isnull'],
            'restocked_at': ['exact', 'gte', 'lte', 'isnull'],
            'completed_at': ['exact', 'gte', 'lte', 'isnull'],
        }
        
    
    def resolve_return_reason_display(self, info):
        """Resolve return reason."""
        return self.return_reason
    
    def resolve_return_category_display(self, info):
        """Resolve return category."""
        return self.return_category
    
    def resolve_refund_amount_display(self, info):
        """Resolve formatted refund amount."""
        if self.refund_amount:
            return f"${self.refund_amount:,.2f}"
        return None
    
    def resolve_restocking_fee_display(self, info):
        """Resolve formatted restocking fee."""
        return f"${self.restocking_fee:,.2f}"
    
    def resolve_disposal_cost_display(self, info):
        """Resolve formatted disposal cost."""
        return f"${self.disposal_cost:,.2f}"
    
    def resolve_is_completed(self, info):
        """Resolve whether return is completed."""
        return self.completed_at is not None
    
    def resolve_is_inspected(self, info):
        """Resolve whether return has been inspected."""
        return self.inspected_at is not None
    
    def resolve_is_restocked(self, info):
        """Resolve whether return has been restocked."""
        return self.restocked_at is not None
    
    def resolve_order_details(self, info):
        """Resolve order details."""
        return self.order
    
    def resolve_variant_details(self, info):
        """Resolve variant details."""
        return self.variant
    
    def resolve_warehouse_details(self, info):
        """Resolve warehouse details."""
        return self.warehouse
    
    def resolve_inspector_details(self, info):
        """Resolve inspector details."""
        return self.inspector


class InventoryPredictionNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Inventory Prediction.
    """

    class Meta:
        model = InventoryPrediction
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            'variant': ['exact'],
            'warehouse': ['exact'],
            'prediction_date': ['exact', 'gte', 'lte'],
            'forecast_day_7': ['exact', 'gte', 'lte'],
            'forecast_day_14': ['exact', 'gte', 'lte'],
            'forecast_day_30': ['exact', 'gte', 'lte'],
            'forecast_day_60': ['exact', 'gte', 'lte'],
            'forecast_day_90': ['exact', 'gte', 'lte'],
            'confidence_low': ['exact', 'gte', 'lte'],
            'confidence_high': ['exact', 'gte', 'lte'],
            'reorder_point': ['exact', 'gte', 'lte'],
            'reorder_quantity': ['exact', 'gte', 'lte'],
        }
    
    def resolve_variant_details(self, info):
        """Resolve variant details."""
        return self.variant
    
    def resolve_warehouse_details(self, info):
        """Resolve warehouse details."""
        return self.warehouse


class InventoryHealthMetricsNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Inventory Health Metrics.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    aging_bucket_display = String(description="Human-readable aging bucket display")
    recommended_action_display = String(description="Human-readable recommended action display")
    inventory_value_display = String(description="Formatted inventory value")
    holding_cost_display = String(description="Formatted holding cost")
    stock_turnover_display = String(description="Formatted stock turnover")
    
    class Meta:
        model = InventoryHealthMetrics
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            'variant': ['exact'],
            'warehouse': ['exact'],
            'calculated_date': ['exact', 'gte', 'lte'],
            'days_of_supply': ['exact', 'gte', 'lte'],
            'stock_turnover_ratio': ['exact', 'gte', 'lte'],
            'aging_bucket': ['exact'],
            'inventory_value': ['exact', 'gte', 'lte'],
            'obsolescence_risk_score': ['exact', 'gte', 'lte'],
            'recommended_action': ['exact'],
        }
        
    
    def resolve_aging_bucket_display(self, info):
        """Resolve human-readable aging bucket display."""
        return dict(InventoryHealthMetrics.AGING_BUCKET_CHOICES).get(self.aging_bucket, self.aging_bucket)
    
    def resolve_recommended_action_display(self, info):
        """Resolve human-readable recommended action display."""
        return dict(InventoryHealthMetrics.ACTION_CHOICES).get(self.recommended_action, self.recommended_action)
    
    def resolve_inventory_value_display(self, info):
        """Resolve formatted inventory value."""
        return f"${self.inventory_value:,.2f}"
    
    def resolve_holding_cost_display(self, info):
        """Resolve formatted holding cost."""
        return f"${self.holding_cost_per_day:,.2f}/day"
    
    def resolve_stock_turnover_display(self, info):
        """Resolve formatted stock turnover."""
        return f"{self.stock_turnover_ratio:.2f}x"
    
    def resolve_variant_details(self, info):
        """Resolve variant details."""
        return self.variant
    
    def resolve_warehouse_details(self, info):
        """Resolve warehouse details."""
        return self.warehouse


class InterWarehouseTransferNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Inter-Warehouse Transfer.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    status_display = String(description="Human-readable status display")
    transfer_cost_display = String(description="Formatted transfer cost")
    shipping_cost_display = String(description="Formatted shipping cost")
    handling_cost_display = String(description="Formatted handling cost")
    item_count = Int(description="Number of items in transfer")
    is_completed = Boolean(description="Whether transfer is completed")
    is_cancelled = Boolean(description="Whether transfer is cancelled")
    is_in_transit = Boolean(description="Whether transfer is in transit")
    

    class Meta:
        model = InterWarehouseTransfer
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            'transfer_number': ['exact', 'icontains'],
            'status': ['exact'],
            'source_warehouse': ['exact'],
            'destination_warehouse': ['exact'],
            'requested_by': ['exact'],
            'expected_transfer_date': ['exact', 'gte', 'lte'],
            'actual_transfer_date': ['exact', 'gte', 'lte', 'isnull'],
            'requested_date': ['exact', 'gte', 'lte'],
            'carrier': ['exact', 'icontains'],
            'tracking_number': ['exact', 'icontains'],
            'transfer_cost': ['exact', 'gte', 'lte'],
            'shipping_cost': ['exact', 'gte', 'lte'],
        }
        
    
    def resolve_status_display(self, info):
        """Resolve human-readable status display."""
        return dict(InterWarehouseTransfer.STATUS_CHOICES).get(self.status, self.status)
    
    def resolve_transfer_cost_display(self, info):
        """Resolve formatted transfer cost."""
        return f"${self.transfer_cost:,.2f}"
    
    def resolve_shipping_cost_display(self, info):
        """Resolve formatted shipping cost."""
        return f"${self.shipping_cost:,.2f}"
    
    def resolve_handling_cost_display(self, info):
        """Resolve formatted handling cost."""
        return f"${self.handling_cost:,.2f}"
    
    def resolve_item_count(self, info):
        """Resolve number of items in transfer."""
        return len(self.items) if self.items else 0
    
    def resolve_is_completed(self, info):
        """Resolve whether transfer is completed."""
        return self.status == "COMPLETED"
    
    def resolve_is_cancelled(self, info):
        """Resolve whether transfer is cancelled."""
        return self.status == "CANCELLED"
    
    def resolve_is_in_transit(self, info):
        """Resolve whether transfer is in transit."""
        return self.status == "IN_TRANSIT"
    
    def resolve_source_warehouse_details(self, info):
        """Resolve source warehouse details."""
        return self.source_warehouse
    
    def resolve_destination_warehouse_details(self, info):
        """Resolve destination warehouse details."""
        return self.destination_warehouse
    
    def resolve_requested_by_details(self, info):
        """Resolve requested by user."""
        return self.requested_by


class WarehousePerformanceNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Warehouse Performance.
    """
    
   
    class Meta:
        model = WarehousePerformance
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            'warehouse': ['exact'],
            'date': ['exact', 'gte', 'lte'],
            'total_orders_fulfilled': ['exact', 'gte', 'lte'],
            'total_units_picked': ['exact', 'gte', 'lte'],
            'total_shipments': ['exact', 'gte', 'lte'],
            'picks_per_hour': ['exact', 'gte', 'lte'],
            'order_cycle_time_minutes': ['exact', 'gte', 'lte'],
            'inventory_accuracy_rate': ['exact', 'gte', 'lte'],
            'fulfillment_cost_per_order': ['exact', 'gte', 'lte'],
            'perfect_order_rate': ['exact', 'gte', 'lte'],
        }
        
    
    def resolve_warehouse_details(self, info):
        """Resolve warehouse details."""
        return self.warehouse


class WarehouseTaskNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Warehouse Task.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    task_type_display = String(description="Human-readable task type display")
    task_status_display = String(description="Human-readable task status display")
    is_completed = Boolean(description="Whether task is completed")
    is_in_progress = Boolean(description="Whether task is in progress")
    is_created = Boolean(description="Whether task is created")
    duration_actual_display = String(description="Formatted actual duration")
    duration_estimated_display = String(description="Formatted estimated duration")
    efficiency_score = Float(description="Task efficiency score")
    

    class Meta:
        model = WarehouseTask
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            'task_id': ['exact', 'icontains'],
            'task_type': ['exact'],
            'task_status': ['exact'],
            'warehouse': ['exact'],
            'assigned_to': ['exact'],
            'priority': ['exact', 'gte', 'lte'],
            'created_at': ['exact', 'gte', 'lte'],
            'assigned_at': ['exact', 'gte', 'lte', 'isnull'],
            'started_at': ['exact', 'gte', 'lte', 'isnull'],
            'completed_at': ['exact', 'gte', 'lte', 'isnull'],
        }
        
    
    def resolve_task_type_display(self, info):
        """Resolve human-readable task type display."""
        return dict(WarehouseTask.TASK_TYPE_CHOICES).get(self.task_type, self.task_type)
    
    def resolve_task_status_display(self, info):
        """Resolve human-readable task status display."""
        return dict(WarehouseTask.TASK_STATUS_CHOICES).get(self.task_status, self.task_status)
    
    def resolve_is_completed(self, info):
        """Resolve whether task is completed."""
        return self.task_status == "COMPLETED"
    
    def resolve_is_in_progress(self, info):
        """Resolve whether task is in progress."""
        return self.task_status == "IN_PROGRESS"
    
    def resolve_is_created(self, info):
        """Resolve whether task is created."""
        return self.task_status == "CREATED"
    
    def resolve_duration_actual_display(self, info):
        """Resolve formatted actual duration."""
        if self.actual_duration_minutes:
            hours = self.actual_duration_minutes // 60
            minutes = self.actual_duration_minutes % 60
            if hours > 0:
                return f"{hours}h {minutes}m"
            return f"{minutes}m"
        return None
    
    def resolve_duration_estimated_display(self, info):
        """Resolve formatted estimated duration."""
        hours = self.estimated_duration_minutes // 60
        minutes = self.estimated_duration_minutes % 60
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    
    def resolve_efficiency_score(self, info):
        """Resolve task efficiency score."""
        if self.estimated_duration_minutes and self.actual_duration_minutes:
            efficiency = (self.estimated_duration_minutes / self.actual_duration_minutes) * 100
            return round(min(efficiency, 100), 2)
        return None
    
    def resolve_warehouse_details(self, info):
        """Resolve warehouse details."""
        return self.warehouse
    
    def resolve_assigned_to_details(self, info):
        """Resolve assigned to user."""
        return self.assigned_to

