# apps/backend/inventory/mutations/inventory.py

"""
Inventory Management Mutations for Relay GraphQL API.
"""
import graphene

from graphql_relay import from_global_id
from graphene import relay 
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
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



# =============================================================================
# Create Stock Mutation
# =============================================================================

class CreateStockMutation(relay.ClientIDMutation):
    """Create a new stock record."""
    
    class Input:
        warehouse_id = graphene.ID(required=True)
        product_variant_id = graphene.ID(required=True)
        quantity = graphene.Int(required=False, default_value=0)
        low_stock_threshold = graphene.Int(required=False, default_value=10)
        restock_lead_time_days = graphene.Int(required=False, default_value=7)
        quantity_allocated = graphene.Int(required=False, default_value=0)
        low_stock_threshold = graphene.Int(required=False, default_value=10)
        last_restocked_at = graphene.DateTime()
        restock_lead_time_days = graphene.Int(required=False, default=7)
        
    stock = graphene.Field(StockNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Create a new stock record.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: StockCreateInput data
        
        Returns:
            CreateStockMutation instance
        """
        errors = {}
        
        # Extract input
        warehouse_id = input.get('warehouse_id')
        product_variant_id = input.get('product_variant_id')
        quantity = input.get('quantity', 0)
        low_stock_threshold = input.get('low_stock_threshold', 10)
        restock_lead_time_days = input.get('restock_lead_time_days', 7)
        
        # Validate quantity
        if quantity < 0:
            errors['quantity'] = ['Quantity cannot be negative.']
            return cls(success=False, errors=errors)
        
        # Resolve warehouse
        try:
            from ..models.warehouse import Warehouse
            pk = from_global_id(warehouse_id)[1]
            warehouse = Warehouse.objects.get(pk=pk)
        except Exception as e:
            errors['warehouse_id'] = ['Warehouse not found.']
            return cls(success=False, errors=errors)
        
        # Resolve product variant
        try:
            from ..models.product import ProductVariant
            pk = from_global_id(product_variant_id)[1]
            product_variant = ProductVariant.objects.get(pk=pk)
        except Exception as e:
            errors['product_variant_id'] = ['Product variant not found.']
            return cls(success=False, errors=errors)
        
        # Check if stock already exists
        if Stock.objects.filter(warehouse=warehouse, product_variant=product_variant).exists():
            errors['stock'] = ['Stock already exists for this warehouse and variant.']
            return cls(success=False, errors=errors)
        
        try:
            # Get user
            user = info.context.user if hasattr(info.context, 'user') else None
            
            # Create stock
            stock = Stock.objects.create(
                warehouse=warehouse,
                product_variant=product_variant,
                quantity=quantity,
                quantity_allocated=0,
                low_stock_threshold=low_stock_threshold,
                restock_lead_time_days=restock_lead_time_days,
            )
            
            # Create history entry if quantity > 0
            if quantity > 0:
                StockHistory.objects.create(
                    stock=stock,
                    product_variant=product_variant,
                    warehouse=warehouse,
                    quantity_change=quantity,
                    previous_quantity=0,
                    new_quantity=quantity,
                    change_type=StockHistory.ChangeType.RESTOCK,
                    reason='Initial stock creation',
                    reference='',
                    user=user,
                )
            
            return cls(
                stock=stock,
                success=True,
                errors={}
            )
            
        except ValidationError as e:
            errors['validation'] = e.message_dict
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Update Stock Mutation
# =============================================================================

class UpdateStockMutation(relay.ClientIDMutation):
    """Update an existing stock record."""
    
    class Input:
        warehouse_id = graphene.ID(required=True)
        product_variant_id = graphene.ID(required=True)
        quantity = graphene.Int(required=False, default_value=0)
        low_stock_threshold = graphene.Int(required=False, default_value=10)
        restock_lead_time_days = graphene.Int(required=False, default_value=7)
        quantity_allocated = graphene.Int(required=False, default_value=0)
        low_stock_threshold = graphene.Int(required=False, default_value=10)
        last_restocked_at = graphene.DateTime()
        restock_lead_time_days = graphene.Int(required=False, default=7)
    
    stock = graphene.Field(StockNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Update an existing stock record.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: StockUpdateInput data
        
        Returns:
            UpdateStockMutation instance
        """
        errors = {}
        
        # Extract input
        stock_id = input.get('id')
        low_stock_threshold = input.get('low_stock_threshold')
        restock_lead_time_days = input.get('restock_lead_time_days')
        
        # Resolve stock
        try:
            pk = from_global_id(stock_id)[1]
            stock = Stock.objects.get(pk=pk)
        except Stock.DoesNotExist:
            errors['id'] = ['Stock not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        try:
            # Update fields
            if low_stock_threshold is not None:
                if low_stock_threshold < 0:
                    errors['low_stock_threshold'] = ['Threshold cannot be negative.']
                    return cls(success=False, errors=errors)
                stock.low_stock_threshold = low_stock_threshold
            
            if restock_lead_time_days is not None:
                if restock_lead_time_days < 1:
                    errors['restock_lead_time_days'] = ['Lead time must be at least 1 day.']
                    return cls(success=False, errors=errors)
                stock.restock_lead_time_days = restock_lead_time_days
            
            stock.save()
            
            return cls(
                stock=stock,
                success=True,
                errors={}
            )
            
        except ValidationError as e:
            errors['validation'] = e.message_dict
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Increase Stock Mutation
# =============================================================================

class IncreaseStockMutation(relay.ClientIDMutation):
    """Increase stock quantity."""
    
    class Input:
        warehouse_id = graphene.ID(required=True)
        product_variant_id = graphene.ID(required=True)
        quantity = graphene.Int(required=False, default_value=0)
        low_stock_threshold = graphene.Int(required=False, default_value=10)
        restock_lead_time_days = graphene.Int(required=False, default_value=7)
        quantity_allocated = graphene.Int(required=False, default_value=0)
        low_stock_threshold = graphene.Int(required=False, default_value=10)
        last_restocked_at = graphene.DateTime()
        restock_lead_time_days = graphene.Int(required=False, default=7)
    
    stock = graphene.Field(StockNode)
    history_entry = graphene.Field(StockHistoryNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Increase stock quantity.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            stock_id: Stock ID
            quantity: Quantity to increase
            kwargs: Additional fields (reason, reference)
        
        Returns:
            IncreaseStockMutation instance
        """
        errors = {}
        
        # Validate quantity
        if quantity <= 0:
            errors['quantity'] = ['Quantity must be greater than zero.']
            return cls(success=False, errors=errors)
        
        # Resolve stock
        try:
            pk = from_global_id(stock_id)[1]
            stock = Stock.objects.get(pk=pk)
        except Stock.DoesNotExist:
            errors['stock_id'] = ['Stock not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['stock_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        try:
            # Get user
            user = info.context.user if hasattr(info.context, 'user') else None
            
            # Get previous quantity
            previous_quantity = stock.quantity
            
            # Increase stock
            stock.quantity = F('quantity') + quantity
            stock.last_restocked_at = timezone.now()
            stock.save(update_fields=['quantity', 'last_restocked_at'])
            stock.refresh_from_db(fields=['quantity'])
            
            # Create history entry
            history = StockHistory.objects.create(
                stock=stock,
                product_variant=stock.product_variant,
                warehouse=stock.warehouse,
                quantity_change=quantity,
                previous_quantity=previous_quantity,
                new_quantity=stock.quantity,
                change_type=StockHistory.ChangeType.RESTOCK,
                reason=kwargs.get('reason', 'Restock'),
                reference=kwargs.get('reference', ''),
                user=user,
            )
            
            return cls(
                stock=stock,
                history_entry=history,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Decrease Stock Mutation
# =============================================================================

class DecreaseStockMutation(relay.ClientIDMutation):
    """Decrease stock quantity."""
    
    class Input:
        warehouse_id = graphene.ID(required=True)
        product_variant_id = graphene.ID(required=True)
        quantity = graphene.Int(required=False, default_value=0)
        low_stock_threshold = graphene.Int(required=False, default_value=10)
        restock_lead_time_days = graphene.Int(required=False, default_value=7)
        quantity_allocated = graphene.Int(required=False, default_value=0)
        low_stock_threshold = graphene.Int(required=False, default_value=10)
        last_restocked_at = graphene.DateTime()
        restock_lead_time_days = graphene.Int(required=False, default=7)
    
    stock = graphene.Field(StockNode)
    history_entry = graphene.Field(StockHistoryNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Decrease stock quantity.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            stock_id: Stock ID
            quantity: Quantity to decrease
            kwargs: Additional fields (reason, reference, force)
        
        Returns:
            DecreaseStockMutation instance
        """
        errors = {}
        
        # Validate quantity
        if quantity <= 0:
            errors['quantity'] = ['Quantity must be greater than zero.']
            return cls(success=False, errors=errors)
        
        # Resolve stock
        try:
            pk = from_global_id(stock_id)[1]
            stock = Stock.objects.get(pk=pk)
        except Stock.DoesNotExist:
            errors['stock_id'] = ['Stock not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['stock_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check available quantity
        force = kwargs.get('force', False)
        available = stock.available_quantity
        
        if quantity > available and not force:
            errors['quantity'] = [
                f'Insufficient stock. Available: {available}, '
                f'Requested: {quantity}'
            ]
            return cls(success=False, errors=errors)
        
        if quantity > stock.quantity and not force:
            errors['quantity'] = [
                f'Insufficient total stock. Total: {stock.quantity}, '
                f'Requested: {quantity}'
            ]
            return cls(success=False, errors=errors)
        
        try:
            # Get user
            user = info.context.user if hasattr(info.context, 'user') else None
            
            # Get previous quantity
            previous_quantity = stock.quantity
            
            # Determine change type
            change_type = StockHistory.ChangeType.REMOVAL
            reason = kwargs.get('reason', 'Removal')
            
            if 'damaged' in reason.lower() or kwargs.get('is_damaged', False):
                change_type = StockHistory.ChangeType.DAMAGED
            elif 'lost' in reason.lower() or kwargs.get('is_lost', False):
                change_type = StockHistory.ChangeType.LOST
            elif 'transfer' in reason.lower() or kwargs.get('is_transfer', False):
                change_type = StockHistory.ChangeType.TRANSFER_OUT
            
            # Decrease stock
            stock.quantity = F('quantity') - quantity
            stock.save(update_fields=['quantity'])
            stock.refresh_from_db(fields=['quantity'])
            
            # Create history entry
            history = StockHistory.objects.create(
                stock=stock,
                product_variant=stock.product_variant,
                warehouse=stock.warehouse,
                quantity_change=-quantity,
                previous_quantity=previous_quantity,
                new_quantity=stock.quantity,
                change_type=change_type,
                reason=reason,
                reference=kwargs.get('reference', ''),
                user=user,
            )
            
            return cls(
                stock=stock,
                history_entry=history,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Adjust Stock Mutation
# =============================================================================

class AdjustStockMutation(relay.ClientIDMutation):
    """Adjust stock quantity (manual adjustment)."""
    
    class Input:
        warehouse_id = graphene.ID(required=True)
        product_variant_id = graphene.ID(required=True)
        quantity = graphene.Int(required=False, default_value=0)
        low_stock_threshold = graphene.Int(required=False, default_value=10)
        restock_lead_time_days = graphene.Int(required=False, default_value=7)
        quantity_allocated = graphene.Int(required=False, default_value=0)
        low_stock_threshold = graphene.Int(required=False, default_value=10)
        last_restocked_at = graphene.DateTime()
        restock_lead_time_days = graphene.Int(required=False, default=7)
    
    stock = graphene.Field(StockNode)
    history_entry = graphene.Field(StockHistoryNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Adjust stock quantity to a specific value.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            stock_id: Stock ID
            new_quantity: New quantity value
            kwargs: Additional fields (reason, reference)
        
        Returns:
            AdjustStockMutation instance
        """
        errors = {}
        
        # Validate quantity
        if new_quantity < 0:
            errors['new_quantity'] = ['Quantity cannot be negative.']
            return cls(success=False, errors=errors)
        
        # Resolve stock
        try:
            pk = from_global_id(stock_id)[1]
            stock = Stock.objects.get(pk=pk)
        except Stock.DoesNotExist:
            errors['stock_id'] = ['Stock not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['stock_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        try:
            # Get user
            user = info.context.user if hasattr(info.context, 'user') else None
            
            # Calculate change
            previous_quantity = stock.quantity
            quantity_change = new_quantity - previous_quantity
            
            if quantity_change == 0:
                return cls(
                    stock=stock,
                    history_entry=None,
                    success=True,
                    errors={}
                )
            
            # Update stock
            stock.quantity = new_quantity
            stock.save(update_fields=['quantity'])
            
            # Create history entry
            history = StockHistory.objects.create(
                stock=stock,
                product_variant=stock.product_variant,
                warehouse=stock.warehouse,
                quantity_change=quantity_change,
                previous_quantity=previous_quantity,
                new_quantity=new_quantity,
                change_type=StockHistory.ChangeType.ADJUSTMENT,
                reason=kwargs.get('reason', 'Manual adjustment'),
                reference=kwargs.get('reference', ''),
                user=user,
            )
            
            return cls(
                stock=stock,
                history_entry=history,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Count Stock Mutation
# =============================================================================

class CountStockMutation(relay.ClientIDMutation):
    """Update stock quantity based on physical count."""
    
    class Input:
        warehouse_id = graphene.ID(required=True)
        product_variant_id = graphene.ID(required=True)
        quantity = graphene.Int(required=False, default_value=0)
        low_stock_threshold = graphene.Int(required=False, default_value=10)
        restock_lead_time_days = graphene.Int(required=False, default_value=7)
        quantity_allocated = graphene.Int(required=False, default_value=0)
        low_stock_threshold = graphene.Int(required=False, default_value=10)
        last_restocked_at = graphene.DateTime()
        restock_lead_time_days = graphene.Int(required=False, default=7)
    
    stock = graphene.Field(StockNode)
    history_entry = graphene.Field(StockHistoryNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Update stock based on physical count.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            stock_id: Stock ID
            counted_quantity: Quantity counted
            kwargs: Additional fields (notes)
        
        Returns:
            CountStockMutation instance
        """
        errors = {}
        
        # Validate quantity
        if counted_quantity < 0:
            errors['counted_quantity'] = ['Quantity cannot be negative.']
            return cls(success=False, errors=errors)
        
        # Resolve stock
        try:
            pk = from_global_id(stock_id)[1]
            stock = Stock.objects.get(pk=pk)
        except Stock.DoesNotExist:
            errors['stock_id'] = ['Stock not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['stock_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        try:
            # Get user
            user = info.context.user if hasattr(info.context, 'user') else None
            
            # Calculate change
            previous_quantity = stock.quantity
            quantity_change = counted_quantity - previous_quantity
            
            # Update stock
            stock.quantity = counted_quantity
            stock.save(update_fields=['quantity'])
            
            # Create history entry
            metadata = {'notes': kwargs.get('notes', '')}
            history = StockHistory.objects.create(
                stock=stock,
                product_variant=stock.product_variant,
                warehouse=stock.warehouse,
                quantity_change=quantity_change,
                previous_quantity=previous_quantity,
                new_quantity=counted_quantity,
                change_type=StockHistory.ChangeType.COUNTED,
                reason=f'Physical count: {kwargs.get("notes", "No notes")}',
                reference='',
                user=user,
                metadata=metadata,
            )
            
            return cls(
                stock=stock,
                history_entry=history,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# System Adjustment Mutation
# =============================================================================

class SystemAdjustmentMutation(relay.ClientIDMutation):
    """System-level stock adjustment (for reconciliation)."""
    
    class Input:
        warehouse_id = graphene.ID(required=True)
        product_variant_id = graphene.ID(required=True)
        quantity = graphene.Int(required=False, default_value=0)
        low_stock_threshold = graphene.Int(required=False, default_value=10)
        restock_lead_time_days = graphene.Int(required=False, default_value=7)
        quantity_allocated = graphene.Int(required=False, default_value=0)
        low_stock_threshold = graphene.Int(required=False, default_value=10)
        last_restocked_at = graphene.DateTime()
        restock_lead_time_days = graphene.Int(required=False, default=7)
    
    stock = graphene.Field(StockNode)
    history_entry = graphene.Field(StockHistoryNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        System-level stock adjustment.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            stock_id: Stock ID
            new_quantity: New quantity value
            kwargs: Additional fields
        
        Returns:
            SystemAdjustmentMutation instance
        """
        errors = {}
        
        # Validate quantity
        if new_quantity < 0:
            errors['new_quantity'] = ['Quantity cannot be negative.']
            return cls(success=False, errors=errors)
        
        # Resolve stock
        try:
            pk = from_global_id(stock_id)[1]
            stock = Stock.objects.get(pk=pk)
        except Stock.DoesNotExist:
            errors['stock_id'] = ['Stock not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['stock_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        try:
            # Calculate change
            previous_quantity = stock.quantity
            quantity_change = new_quantity - previous_quantity
            
            if quantity_change == 0:
                return cls(
                    stock=stock,
                    history_entry=None,
                    success=True,
                    errors={}
                )
            
            # Update stock
            stock.quantity = new_quantity
            stock.save(update_fields=['quantity'])
            
            # Create history entry
            history = StockHistory.objects.create(
                stock=stock,
                product_variant=stock.product_variant,
                warehouse=stock.warehouse,
                quantity_change=quantity_change,
                previous_quantity=previous_quantity,
                new_quantity=new_quantity,
                change_type=StockHistory.ChangeType.SYSTEM_ADJUSTMENT,
                reason=kwargs.get('reason', 'System adjustment'),
                reference=kwargs.get('reference', ''),
                user=None,  # System adjustment, no user
                metadata={'adjustment_type': kwargs.get('adjustment_type', 'system_adjustment')},
            )
            
            return cls(
                stock=stock,
                history_entry=history,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Delete Stock Mutation
# =============================================================================

class DeleteStockMutation(relay.ClientIDMutation):
    """Delete a stock record."""
    
    class Input:
        id = graphene.ID(required=True)
        force = graphene.Boolean(required=False, default_value=False)
    
    deleted_id = graphene.ID()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id, force=False):
        """
        Delete a stock record.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Stock ID to delete
            force: Force deletion even if stock > 0
        
        Returns:
            DeleteStockMutation instance
        """
        errors = {}
        
        # Resolve stock
        try:
            pk = from_global_id(id)[1]
            stock = Stock.objects.get(pk=pk)
        except Stock.DoesNotExist:
            errors['id'] = ['Stock not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check if stock has positive quantity
        if stock.quantity > 0 and not force:
            errors['id'] = [
                f'Cannot delete stock with positive quantity ({stock.quantity}). '
                'Set quantity to 0 first or use force=True.'
            ]
            return cls(success=False, errors=errors)
        
        # Check if stock has allocations
        if stock.allocations.exists() and not force:
            errors['id'] = [
                'Cannot delete stock with active allocations. '
                'Clear allocations first or use force=True.'
            ]
            return cls(success=False, errors=errors)
        
        try:
            deleted_id = id
            stock.delete()
            
            return cls(
                deleted_id=deleted_id,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Bulk Stock Operations
# =============================================================================

class BulkIncreaseStockMutation(relay.ClientIDMutation):
    """Bulk increase stock for multiple items."""
    
    class Input:
        warehouse_id = graphene.ID(required=True)
        product_variant_id = graphene.ID(required=True)
        quantity = graphene.Int(required=False, default_value=0)
        low_stock_threshold = graphene.Int(required=False, default_value=10)
        restock_lead_time_days = graphene.Int(required=False, default_value=7)
        quantity_allocated = graphene.Int(required=False, default_value=0)
        low_stock_threshold = graphene.Int(required=False, default_value=10)
        last_restocked_at = graphene.DateTime()
        restock_lead_time_days = graphene.Int(required=False, default=7)

    results = graphene.JSONString()
    success_count = graphene.Int()
    failure_count = graphene.Int()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Bulk increase stock for multiple items.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            adjustments: List of stock adjustments
        
        Returns:
            BulkIncreaseStockMutation instance
        """
        errors = {}
        results = []
        success_count = 0
        failure_count = 0
        
        for idx, adjustment in enumerate(adjustments):
            try:
                stock_id = adjustment.get('stock_id')
                quantity = adjustment.get('quantity')
                reason = adjustment.get('reason', 'Bulk restock')
                reference = adjustment.get('reference', '')
                
                # Call increase stock mutation
                result = IncreaseStockMutation.mutate_and_get_payload(
                    root, info, stock_id, quantity,
                    reason=reason, reference=reference
                )
                
                if result.success:
                    success_count += 1
                    results.append({
                        'stock_id': stock_id,
                        'status': 'success',
                        'new_quantity': result.stock.quantity,
                    })
                else:
                    failure_count += 1
                    errors[f'item_{idx}'] = result.errors
                    results.append({
                        'stock_id': stock_id,
                        'status': 'failed',
                        'errors': result.errors,
                    })
                    
            except Exception as e:
                failure_count += 1
                errors[f'item_{idx}'] = [str(e)]
                results.append({
                    'stock_id': adjustment.get('stock_id'),
                    'status': 'failed',
                    'errors': [str(e)],
                })
        
        return cls(
            results=results,
            success_count=success_count,
            failure_count=failure_count,
            success=failure_count == 0,
            errors=errors if errors else {}
        )


class BulkAdjustStockMutation(relay.ClientIDMutation):
    """Bulk adjust stock for multiple items."""
    
    class Input:
        warehouse_id = graphene.ID(required=True)
        product_variant_id = graphene.ID(required=True)
        quantity = graphene.Int(required=False, default_value=0)
        low_stock_threshold = graphene.Int(required=False, default_value=10)
        restock_lead_time_days = graphene.Int(required=False, default_value=7)
        quantity_allocated = graphene.Int(required=False, default_value=0)
        low_stock_threshold = graphene.Int(required=False, default_value=10)
        last_restocked_at = graphene.DateTime()
        restock_lead_time_days = graphene.Int(required=False, default=7)
        
    results = graphene.JSONString()
    success_count = graphene.Int()
    failure_count = graphene.Int()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Bulk adjust stock for multiple items.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            adjustments: List of stock adjustments
        
        Returns:
            BulkAdjustStockMutation instance
        """
        errors = {}
        results = []
        success_count = 0
        failure_count = 0
        
        for idx, adjustment in enumerate(adjustments):
            try:
                stock_id = adjustment.get('stock_id')
                quantity = adjustment.get('quantity')
                reason = adjustment.get('reason', 'Bulk adjustment')
                reference = adjustment.get('reference', '')
                
                # Resolve stock to get current quantity
                pk = from_global_id(stock_id)[1]
                stock = Stock.objects.get(pk=pk)
                
                # Calculate new quantity
                new_quantity = stock.quantity + quantity
                
                if quantity > 0:
                    result = IncreaseStockMutation.mutate_and_get_payload(
                        root, info, stock_id, quantity,
                        reason=reason, reference=reference
                    )
                elif quantity < 0:
                    result = DecreaseStockMutation.mutate_and_get_payload(
                        root, info, stock_id, abs(quantity),
                        reason=reason, reference=reference, force=True
                    )
                else:
                    # No change
                    results.append({
                        'stock_id': stock_id,
                        'status': 'no_change',
                    })
                    success_count += 1
                    continue
                
                if result.success:
                    success_count += 1
                    results.append({
                        'stock_id': stock_id,
                        'status': 'success',
                        'new_quantity': result.stock.quantity,
                    })
                else:
                    failure_count += 1
                    errors[f'item_{idx}'] = result.errors
                    results.append({
                        'stock_id': stock_id,
                        'status': 'failed',
                        'errors': result.errors,
                    })
                    
            except Exception as e:
                failure_count += 1
                errors[f'item_{idx}'] = [str(e)]
                results.append({
                    'stock_id': adjustment.get('stock_id'),
                    'status': 'failed',
                    'errors': [str(e)],
                })
        
        return cls(
            results=results,
            success_count=success_count,
            failure_count=failure_count,
            success=failure_count == 0,
            errors=errors if errors else {}
        )


# =============================================================================
# Query Stock History Mutation
# =============================================================================

class CreateStockHistoryMutation(relay.ClientIDMutation):
    """Create a new stock history entry."""
    
    class Input:
        stock_id = graphene.ID(required=True)
        product_variant_id = graphene.ID(required=True)
        warehouse_id = graphene.ID(required=True)
        quantity_change = graphene.Int(required=True)
        previous_quantity = graphene.Int(required=True)
        new_quantity = graphene.Int(required=True)
        reserved_change = graphene.Int(required=False, default_value=0)
        previous_reserved = graphene.Int(required=False, default_value=0)
        new_reserved = graphene.Int(required=False, default_value=0)
        change_type = graphene.String(required=True)
        reason = graphene.String(required=False)
        reference = graphene.String(required=False)
        order_id = graphene.ID(required=False)
        order_line_id = graphene.ID(required=False)
        fulfillment_id = graphene.ID(required=False)
        metadata = graphene.JSONString(required=False, default_value={})
    
    history_entry = graphene.Field(StockHistoryNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Create a new stock history entry.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: CreateStockHistoryInput data
        
        Returns:
            CreateStockHistoryMutation instance
        """
        errors = {}
        
        # Extract input
        stock_id = input.get('stock_id')
        product_variant_id = input.get('product_variant_id')
        warehouse_id = input.get('warehouse_id')
        quantity_change = input.get('quantity_change')
        previous_quantity = input.get('previous_quantity')
        new_quantity = input.get('new_quantity')
        reserved_change = input.get('reserved_change', 0)
        previous_reserved = input.get('previous_reserved', 0)
        new_reserved = input.get('new_reserved', 0)
        change_type = input.get('change_type')
        reason = input.get('reason', '')
        reference = input.get('reference', '')
        order_id = input.get('order_id')
        order_line_id = input.get('order_line_id')
        fulfillment_id = input.get('fulfillment_id')
        metadata = input.get('metadata', {})
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Check permission - only staff can create history entries
        if not user.is_staff:
            errors['permission'] = ['Only staff members can create stock history entries.']
            return cls(success=False, errors=errors)
        
        # Resolve stock
        try:
            pk = from_global_id(stock_id)[1]
            stock = Stock.objects.get(pk=pk)
        except Stock.DoesNotExist:
            errors['stock_id'] = ['Stock not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['stock_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Validate quantity change
        if quantity_change == 0:
            errors['quantity_change'] = ['Quantity change cannot be zero.']
            return cls(success=False, errors=errors)
        
        # Validate change type
        valid_change_types = [
            choice[0] for choice in StockHistory.ChangeType.choices
        ]
        if change_type not in valid_change_types:
            errors['change_type'] = [
                f'Invalid change type. Must be one of: {", ".join(valid_change_types)}'
            ]
            return cls(success=False, errors=errors)
        
        # Resolve order if provided
        order = None
        if order_id:
            try:
                from ..models.order import Order
                pk = from_global_id(order_id)[1]
                order = Order.objects.get(pk=pk)
            except Exception as e:
                errors['order_id'] = ['Order not found.']
                return cls(success=False, errors=errors)
        
        # Resolve order line if provided
        order_line = None
        if order_line_id:
            try:
                from ..models.order import OrderLine
                pk = from_global_id(order_line_id)[1]
                order_line = OrderLine.objects.get(pk=pk)
            except Exception as e:
                errors['order_line_id'] = ['Order line not found.']
                return cls(success=False, errors=errors)
        
        # Resolve fulfillment if provided
        fulfillment = None
        if fulfillment_id:
            try:
                from ..models.fulfillment import Fulfillment
                pk = from_global_id(fulfillment_id)[1]
                fulfillment = Fulfillment.objects.get(pk=pk)
            except Exception as e:
                errors['fulfillment_id'] = ['Fulfillment not found.']
                return cls(success=False, errors=errors)
        
        try:
            # Create stock history entry
            history_entry = StockHistory.objects.create(
                stock=stock,
                product_variant=stock.product_variant,
                warehouse=stock.warehouse,
                quantity_change=quantity_change,
                previous_quantity=previous_quantity,
                new_quantity=new_quantity,
                reserved_change=reserved_change,
                previous_reserved=previous_reserved,
                new_reserved=new_reserved,
                change_type=change_type,
                reason=reason,
                reference=reference,
                order=order,
                order_line=order_line,
                fulfillment=fulfillment,
                user=user,
                metadata=metadata,
            )
            
            return cls(
                history_entry=history_entry,
                success=True,
                errors={}
            )
            
        except ValidationError as e:
            errors['validation'] = e.message_dict
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Update Stock History Mutation
# =============================================================================

class UpdateStockHistoryMutation(relay.ClientIDMutation):
    """Update an existing stock history entry."""
    
    class Input:
        id = graphene.ID(required=True)
        reason = graphene.String(required=False)
        reference = graphene.String(required=False)
        metadata = graphene.JSONString(required=False)
    
    history_entry = graphene.Field(StockHistoryNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Update an existing stock history entry.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: UpdateStockHistoryInput data
        
        Returns:
            UpdateStockHistoryMutation instance
        """
        errors = {}
        
        # Extract input
        history_id = input.get('id')
        reason = input.get('reason')
        reference = input.get('reference')
        metadata = input.get('metadata')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Check permission - only staff can update history entries
        if not user.is_staff:
            errors['permission'] = ['Only staff members can update stock history entries.']
            return cls(success=False, errors=errors)
        
        # Resolve history entry
        try:
            pk = from_global_id(history_id)[1]
            history_entry = StockHistory.objects.get(pk=pk)
        except StockHistory.DoesNotExist:
            errors['id'] = ['Stock history entry not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        try:
            # Update fields
            if reason is not None:
                history_entry.reason = reason
            if reference is not None:
                history_entry.reference = reference
            if metadata is not None:
                history_entry.metadata = metadata
            
            history_entry.full_clean()
            history_entry.save()
            
            return cls(
                history_entry=history_entry,
                success=True,
                errors={}
            )
            
        except ValidationError as e:
            errors['validation'] = e.message_dict
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Delete Stock History Mutation
# =============================================================================

class DeleteStockHistoryMutation(relay.ClientIDMutation):
    """Delete a stock history entry."""
    
    class Input:
        id = graphene.ID(required=True)
        force = graphene.Boolean(required=False, default_value=False)
    
    deleted_id = graphene.ID()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Delete a stock history entry.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: DeleteStockHistoryInput data
        
        Returns:
            DeleteStockHistoryMutation instance
        """
        errors = {}
        
        # Extract input
        history_id = input.get('id')
        force = input.get('force', False)
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Check permission - only staff can delete history entries
        if not user.is_staff:
            errors['permission'] = ['Only staff members can delete stock history entries.']
            return cls(success=False, errors=errors)
        
        # Resolve history entry
        try:
            pk = from_global_id(history_id)[1]
            history_entry = StockHistory.objects.get(pk=pk)
        except StockHistory.DoesNotExist:
            errors['id'] = ['Stock history entry not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check if this is the only history entry for the stock
        if not force:
            entry_count = StockHistory.objects.filter(
                stock=history_entry.stock
            ).count()
            
            if entry_count <= 1:
                errors['force'] = [
                    'This is the last history entry for this stock. '
                    'Use force=True to delete it.'
                ]
                return cls(success=False, errors=errors)
        
        try:
            deleted_id = history_id
            history_entry.delete()
            
            return cls(
                deleted_id=deleted_id,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Get Stock History Mutation (Query)
# =============================================================================

class GetStockHistoryMutation(relay.ClientIDMutation):
    """Query stock history with filters."""
    
    class Input:
        stock_id = graphene.ID(required=False)
        product_variant_id = graphene.ID(required=False)
        warehouse_id = graphene.ID(required=False)
        change_type = graphene.String(required=False)
        start_date = graphene.DateTime(required=False)
        end_date = graphene.DateTime(required=False)
        limit = graphene.Int(required=False, default_value=100)
        offset = graphene.Int(required=False, default_value=0)
    
    history = graphene.Field(StockHistoryNode)
    total_count = graphene.Int()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Query stock history with filters.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: Filter input
        
        Returns:
            GetStockHistoryMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        try:
            queryset = StockHistory.objects.all()
            
            # Filter by stock
            if input.get('stock_id'):
                try:
                    pk = from_global_id(input['stock_id'])[1]
                    queryset = queryset.filter(stock_id=pk)
                except Exception:
                    errors['stock_id'] = ['Invalid stock ID.']
            
            # Filter by product variant
            if input.get('product_variant_id'):
                try:
                    pk = from_global_id(input['product_variant_id'])[1]
                    queryset = queryset.filter(product_variant_id=pk)
                except Exception:
                    errors['product_variant_id'] = ['Invalid product variant ID.']
            
            # Filter by warehouse
            if input.get('warehouse_id'):
                try:
                    pk = from_global_id(input['warehouse_id'])[1]
                    queryset = queryset.filter(warehouse_id=pk)
                except Exception:
                    errors['warehouse_id'] = ['Invalid warehouse ID.']
            
            # Filter by change type
            if input.get('change_type'):
                queryset = queryset.filter(change_type=input['change_type'])
            
            # Filter by date range
            if input.get('start_date'):
                queryset = queryset.filter(created_at__gte=input['start_date'])
            if input.get('end_date'):
                queryset = queryset.filter(created_at__lte=input['end_date'])
            
            # Count total
            total_count = queryset.count()
            
            # Apply pagination
            limit = input.get('limit', 100)
            offset = input.get('offset', 0)
            history = queryset[offset:offset + limit]
            
            return cls(
                history=history,
                total_count=total_count,
                success=True,
                errors=errors if errors else {}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(
                history=[],
                total_count=0,
                success=False,
                errors=errors
            )




# =============================================================================
# Create Allocation Mutation
# =============================================================================

class CreateAllocationMutation(relay.ClientIDMutation):
    """Create a new stock allocation."""
    
    class Input:
        order_line_id = graphene.ID(required=True)
        stock_id = graphene.ID(required=True)
        quantity_allocated = graphene.Int(required=True)
    
    allocation = graphene.Field(AllocationNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Create a new allocation.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: AllocationInput data
        
        Returns:
            CreateAllocationMutation instance
        """
        errors = {}
        
        # Extract input
        order_line_id = input.get('order_line_id')
        stock_id = input.get('stock_id')
        quantity_allocated = input.get('quantity_allocated')
        
        # Validate quantity
        if quantity_allocated <= 0:
            errors['quantity_allocated'] = ['Quantity must be greater than 0.']
            return cls(success=False, errors=errors)
        
        # Resolve order line
        try:
            from ..models.order import OrderLine
            pk = from_global_id(order_line_id)[1]
            order_line = OrderLine.objects.get(pk=pk)
        except Exception as e:
            errors['order_line_id'] = ['Order line not found.']
            return cls(success=False, errors=errors)
        
        # Resolve stock
        try:
            from ..models.stock import Stock
            pk = from_global_id(stock_id)[1]
            stock = Stock.objects.get(pk=pk)
        except Exception as e:
            errors['stock_id'] = ['Stock not found.']
            return cls(success=False, errors=errors)
        
        # Check if allocation already exists
        if Allocation.objects.filter(order_line=order_line, stock=stock).exists():
            errors['allocation'] = ['Allocation already exists for this order line and stock.']
            return cls(success=False, errors=errors)
        
        # Check stock availability
        if stock.available_quantity < quantity_allocated:
            errors['quantity_allocated'] = [
                f'Insufficient stock. Available: {stock.available_quantity}'
            ]
            return cls(success=False, errors=errors)
        
        try:
            # Create allocation
            allocation = Allocation.objects.create(
                order_line=order_line,
                stock=stock,
                quantity_allocated=quantity_allocated,
            )
            
            # Update stock
            stock.quantity_allocated = F('quantity_allocated') + quantity_allocated
            stock.save()
            
            return cls(
                allocation=allocation,
                success=True,
                errors={}
            )
            
        except ValidationError as e:
            errors['validation'] = e.message_dict
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Update Allocation Mutation
# =============================================================================

class UpdateAllocationMutation(relay.ClientIDMutation):
    """Update an existing stock allocation."""
    
    class Input:
        id = graphene.ID(required=True)
        quantity_allocated = graphene.Int(required=True)
    
    allocation = graphene.Field(AllocationNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Update an existing allocation.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: UpdateAllocationInput data
        
        Returns:
            UpdateAllocationMutation instance
        """
        errors = {}
        
        # Extract input
        allocation_id = input.get('id')
        quantity_allocated = input.get('quantity_allocated')
        
        # Validate quantity
        if quantity_allocated <= 0:
            errors['quantity_allocated'] = ['Quantity must be greater than 0.']
            return cls(success=False, errors=errors)
        
        # Resolve allocation
        try:
            pk = from_global_id(allocation_id)[1]
            allocation = Allocation.objects.get(pk=pk)
        except Allocation.DoesNotExist:
            errors['id'] = ['Allocation not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check stock availability for the quantity difference
        stock = allocation.stock
        quantity_difference = quantity_allocated - allocation.quantity_allocated
        
        if quantity_difference > 0 and stock.available_quantity < quantity_difference:
            errors['quantity_allocated'] = [
                f'Insufficient stock for increase. Available: {stock.available_quantity}'
            ]
            return cls(success=False, errors=errors)
        
        try:
            # Update allocation
            old_quantity = allocation.quantity_allocated
            
            # Update stock allocation quantity
            stock.quantity_allocated = F('quantity_allocated') - old_quantity + quantity_allocated
            stock.save()
            
            # Update allocation
            allocation.quantity_allocated = quantity_allocated
            allocation.save()
            
            return cls(
                allocation=allocation,
                success=True,
                errors={}
            )
            
        except ValidationError as e:
            errors['validation'] = e.message_dict
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Delete Allocation Mutation
# =============================================================================

class DeleteAllocationMutation(relay.ClientIDMutation):
    """Delete an existing stock allocation."""
    
    class Input:
        id = graphene.ID(required=True)
    
    deleted_id = graphene.ID()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Delete an allocation.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: DeleteAllocationInput data
        
        Returns:
            DeleteAllocationMutation instance
        """
        errors = {}
        
        # Extract input
        allocation_id = input.get('id')
        
        # Resolve allocation
        try:
            pk = from_global_id(allocation_id)[1]
            allocation = Allocation.objects.get(pk=pk)
        except Allocation.DoesNotExist:
            errors['id'] = ['Allocation not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        try:
            # Update stock - remove allocated quantity
            stock = allocation.stock
            stock.quantity_allocated = F('quantity_allocated') - allocation.quantity_allocated
            stock.save()
            
            # Delete allocation
            deleted_id = allocation_id
            allocation.delete()
            
            return cls(
                deleted_id=deleted_id,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Create Reservation Mutation
# =============================================================================

class CreateReservationMutation(relay.ClientIDMutation):
    """Create a new stock reservation."""
    
    class Input:
        checkout_line_id = graphene.ID(required=True)
        stock_id = graphene.ID(required=True)
        quantity_reserved = graphene.Int(required=True)
        reserved_until = graphene.DateTime(required=True)
    
    reservation = graphene.Field(ReservationNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Create a new reservation.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: ReservationInput data
        
        Returns:
            CreateReservationMutation instance
        """
        errors = {}
        
        # Extract input
        checkout_line_id = input.get('checkout_line_id')
        stock_id = input.get('stock_id')
        quantity_reserved = input.get('quantity_reserved')
        reserved_until = input.get('reserved_until')
        
        # Validate quantity
        if quantity_reserved <= 0:
            errors['quantity_reserved'] = ['Quantity must be greater than 0.']
            return cls(success=False, errors=errors)
        
        # Validate reserved until
        if reserved_until <= timezone.now():
            errors['reserved_until'] = ['Reserved until must be in the future.']
            return cls(success=False, errors=errors)
        
        # Resolve checkout line
        try:
            from ..models.checkout import CheckoutLine
            pk = from_global_id(checkout_line_id)[1]
            checkout_line = CheckoutLine.objects.get(pk=pk)
        except Exception as e:
            errors['checkout_line_id'] = ['Checkout line not found.']
            return cls(success=False, errors=errors)
        
        # Resolve stock
        try:
            from ..models.stock import Stock
            pk = from_global_id(stock_id)[1]
            stock = Stock.objects.get(pk=pk)
        except Exception as e:
            errors['stock_id'] = ['Stock not found.']
            return cls(success=False, errors=errors)
        
        # Check if reservation already exists
        if Reservation.objects.filter(checkout_line=checkout_line, stock=stock).exists():
            errors['reservation'] = ['Reservation already exists for this checkout line and stock.']
            return cls(success=False, errors=errors)
        
        # Check stock availability
        if stock.available_quantity < quantity_reserved:
            errors['quantity_reserved'] = [
                f'Insufficient stock. Available: {stock.available_quantity}'
            ]
            return cls(success=False, errors=errors)
        
        try:
            # Create reservation
            reservation = Reservation.objects.create(
                checkout_line=checkout_line,
                stock=stock,
                quantity_reserved=quantity_reserved,
                reserved_until=reserved_until,
            )
            
            # Update stock
            stock.quantity_reserved = F('quantity_reserved') + quantity_reserved
            stock.save()
            
            return cls(
                reservation=reservation,
                success=True,
                errors={}
            )
            
        except ValidationError as e:
            errors['validation'] = e.message_dict
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Update Reservation Mutation
# =============================================================================

class UpdateReservationMutation(relay.ClientIDMutation):
    """Update an existing stock reservation."""
    
    class Input:
        id = graphene.ID(required=True)
        quantity_reserved = graphene.Int(required=False)
        reserved_until = graphene.DateTime(required=False)
    
    reservation = graphene.Field(ReservationNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Update an existing reservation.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: UpdateReservationInput data
        
        Returns:
            UpdateReservationMutation instance
        """
        errors = {}
        
        # Extract input
        reservation_id = input.get('id')
        quantity_reserved = input.get('quantity_reserved')
        reserved_until = input.get('reserved_until')
        
        # Resolve reservation
        try:
            pk = from_global_id(reservation_id)[1]
            reservation = Reservation.objects.get(pk=pk)
        except Reservation.DoesNotExist:
            errors['id'] = ['Reservation not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Validate reserved until if provided
        if reserved_until is not None and reserved_until <= timezone.now():
            errors['reserved_until'] = ['Reserved until must be in the future.']
            return cls(success=False, errors=errors)
        
        try:
            stock = reservation.stock
            old_quantity = reservation.quantity_reserved
            
            # Update quantity if provided
            if quantity_reserved is not None:
                if quantity_reserved <= 0:
                    errors['quantity_reserved'] = ['Quantity must be greater than 0.']
                    return cls(success=False, errors=errors)
                
                quantity_difference = quantity_reserved - old_quantity
                
                if quantity_difference > 0 and stock.available_quantity < quantity_difference:
                    errors['quantity_reserved'] = [
                        f'Insufficient stock for increase. Available: {stock.available_quantity}'
                    ]
                    return cls(success=False, errors=errors)
                
                # Update stock reserved quantity
                stock.quantity_reserved = F('quantity_reserved') - old_quantity + quantity_reserved
                stock.save()
                
                reservation.quantity_reserved = quantity_reserved
            
            # Update reserved_until if provided
            if reserved_until is not None:
                reservation.reserved_until = reserved_until
            
            reservation.save()
            
            return cls(
                reservation=reservation,
                success=True,
                errors={}
            )
            
        except ValidationError as e:
            errors['validation'] = e.message_dict
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Delete Reservation Mutation
# =============================================================================

class DeleteReservationMutation(relay.ClientIDMutation):
    """Delete an existing stock reservation."""
    
    class Input:
        id = graphene.ID(required=True)
    
    deleted_id = graphene.ID()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Delete a reservation.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: DeleteReservationInput data
        
        Returns:
            DeleteReservationMutation instance
        """
        errors = {}
        
        # Extract input
        reservation_id = input.get('id')
        
        # Resolve reservation
        try:
            pk = from_global_id(reservation_id)[1]
            reservation = Reservation.objects.get(pk=pk)
        except Reservation.DoesNotExist:
            errors['id'] = ['Reservation not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        try:
            # Update stock - remove reserved quantity
            stock = reservation.stock
            stock.quantity_reserved = F('quantity_reserved') - reservation.quantity_reserved
            stock.save()
            
            # Delete reservation
            deleted_id = reservation_id
            reservation.delete()
            
            return cls(
                deleted_id=deleted_id,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)



# =============================================================================
# Create Return Mutation
# =============================================================================

class CreateReturnMutation(relay.ClientIDMutation):
    """Create a new return."""
    
    class Input:
        order_id = graphene.ID(required=True)
        variant_id = graphene.ID(required=True)
        warehouse_id = graphene.ID(required=True)
        quantity_returned = graphene.Int(required=True)
        quantity_restockable = graphene.Int(required=False)
        quantity_damaged = graphene.Int(required=False)
        return_reason = graphene.String(required=True)
        return_category = graphene.String(required=True)
        inspection_notes = graphene.String(required=False)
        refund_amount = graphene.Decimal(required=False)
        restocking_fee = graphene.Decimal(required=False, default_value=Decimal('0.00'))
        disposal_cost = graphene.Decimal(required=False, default_value=Decimal('0.00'))
        quality_score = graphene.Int(required=False)
        customer_satisfaction_score = graphene.Int(required=False)
    
    return_item = graphene.Field(ReturnsManagementNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, input):
        """
        Create a new return.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: ReturnItemInput data
        
        Returns:
            CreateReturnMutation instance
        """
        errors = {}
        
        # Extract input
        order_id = input.get('order_id')
        variant_id = input.get('variant_id')
        warehouse_id = input.get('warehouse_id')
        quantity_returned = input.get('quantity_returned')
        quantity_restockable = input.get('quantity_restockable', quantity_returned)
        quantity_damaged = input.get('quantity_damaged', 0)
        return_reason = input.get('return_reason')
        return_category = input.get('return_category')
        inspection_notes = input.get('inspection_notes', '')
        refund_amount = input.get('refund_amount')
        restocking_fee = input.get('restocking_fee', Decimal('0.00'))
        disposal_cost = input.get('disposal_cost', Decimal('0.00'))
        quality_score = input.get('quality_score')
        customer_satisfaction_score = input.get('customer_satisfaction_score')
        
        # Validate quantity
        if quantity_returned <= 0:
            errors['quantity_returned'] = ['Quantity must be greater than 0.']
            return cls(success=False, errors=errors)
        
        if quantity_restockable < 0 or quantity_damaged < 0:
            errors['quantity'] = ['Quantities cannot be negative.']
            return cls(success=False, errors=errors)
        
        if quantity_restockable + quantity_damaged != quantity_returned:
            errors['quantity'] = [
                'Sum of restockable and damaged quantities must equal returned quantity.'
            ]
            return cls(success=False, errors=errors)
        
        # Resolve order
        try:
            pk = from_global_id(order_id)[1]
            order = Order.objects.get(pk=pk)
        except Exception as e:
            errors['order_id'] = ['Order not found.']
            return cls(success=False, errors=errors)
        
        # Resolve variant
        try:
            pk = from_global_id(variant_id)[1]
            variant = ProductVariant.objects.get(pk=pk)
        except Exception as e:
            errors['variant_id'] = ['Variant not found.']
            return cls(success=False, errors=errors)
        
        # Resolve warehouse
        try:
            pk = from_global_id(warehouse_id)[1]
            warehouse = Warehouse.objects.get(pk=pk)
        except Exception as e:
            errors['warehouse_id'] = ['Warehouse not found.']
            return cls(success=False, errors=errors)
        
        # Generate RMA number
        rma_number = f"RMA-{timezone.now().strftime('%Y%m%d')}-{timezone.now().microsecond % 10000:04d}"
        
        try:
            # Get current user
            user = info.context.user if hasattr(info.context, 'user') else None
            
            # Create return
            return_item = ReturnsManagement.objects.create(
                rma_number=rma_number,
                quantity_returned=quantity_returned,
                quantity_restockable=quantity_restockable,
                quantity_damaged=quantity_damaged,
                inspection_notes=inspection_notes,
                quality_score=quality_score,
                refund_amount=refund_amount,
                restocking_fee=restocking_fee,
                disposal_cost=disposal_cost,
                received_at=timezone.now(),
                return_reason=return_reason,
                return_category=return_category,
                customer_satisfaction_score=customer_satisfaction_score,
                inspector=user if user and user.is_authenticated else None,
                order=order,
                variant=variant,
                warehouse=warehouse,
            )
            
            # Update stock if restockable
            if quantity_restockable > 0:
                stock, created = Stock.objects.get_or_create(
                    product_variant=variant,
                    warehouse=warehouse,
                    defaults={'quantity': 0}
                )
                stock.quantity = F('quantity') + quantity_restockable
                stock.save()
            
            return cls(
                return_item=return_item,
                success=True,
                errors={}
            )
            
        except ValidationError as e:
            errors['validation'] = e.message_dict
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Update Return Mutation
# =============================================================================

class UpdateReturnMutation(relay.ClientIDMutation):
    """Update an existing return."""
    
    class Input:
        id = graphene.ID(required=True)
        quantity_returned = graphene.Int(required=False)
        quantity_restockable = graphene.Int(required=False)
        quantity_damaged = graphene.Int(required=False)
        return_reason = graphene.String(required=False)
        return_category = graphene.String(required=False)
        inspection_notes = graphene.String(required=False)
        refund_amount = graphene.Decimal(required=False)
        restocking_fee = graphene.Decimal(required=False)
        disposal_cost = graphene.Decimal(required=False)
        quality_score = graphene.Int(required=False)
        customer_satisfaction_score = graphene.Int(required=False)
    
    return_item = graphene.Field(ReturnsManagementNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, input):
        """
        Update an existing return.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: UpdateReturnInput data
        
        Returns:
            UpdateReturnMutation instance
        """
        errors = {}
        
        # Extract input
        return_id = input.get('id')
        
        # Resolve return
        try:
            pk = from_global_id(return_id)[1]
            return_item = ReturnsManagement.objects.get(pk=pk)
        except ReturnsManagement.DoesNotExist:
            errors['id'] = ['Return not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        try:
            # Update fields
            if 'quantity_returned' in input:
                return_item.quantity_returned = input['quantity_returned']
            if 'quantity_restockable' in input:
                return_item.quantity_restockable = input['quantity_restockable']
            if 'quantity_damaged' in input:
                return_item.quantity_damaged = input['quantity_damaged']
            if 'return_reason' in input:
                return_item.return_reason = input['return_reason']
            if 'return_category' in input:
                return_item.return_category = input['return_category']
            if 'inspection_notes' in input:
                return_item.inspection_notes = input['inspection_notes']
            if 'refund_amount' in input:
                return_item.refund_amount = input['refund_amount']
            if 'restocking_fee' in input:
                return_item.restocking_fee = input['restocking_fee']
            if 'disposal_cost' in input:
                return_item.disposal_cost = input['disposal_cost']
            if 'quality_score' in input:
                return_item.quality_score = input['quality_score']
            if 'customer_satisfaction_score' in input:
                return_item.customer_satisfaction_score = input['customer_satisfaction_score']
            
            return_item.full_clean()
            return_item.save()
            
            return cls(
                return_item=return_item,
                success=True,
                errors={}
            )
            
        except ValidationError as e:
            errors['validation'] = e.message_dict
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Delete Return Mutation
# =============================================================================

class DeleteReturnMutation(relay.ClientIDMutation):
    """Delete a return."""
    
    class Input:
        id = graphene.ID(required=True)
        force = graphene.Boolean(required=False, default_value=False)
    
    deleted_id = graphene.ID()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, input):
        """
        Delete a return.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: DeleteReturnInput data
        
        Returns:
            DeleteReturnMutation instance
        """
        errors = {}
        
        # Extract input
        return_id = input.get('id')
        force = input.get('force', False)
        
        # Resolve return
        try:
            pk = from_global_id(return_id)[1]
            return_item = ReturnsManagement.objects.get(pk=pk)
        except ReturnsManagement.DoesNotExist:
            errors['id'] = ['Return not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check if return is already processed
        if return_item.restocked_at and not force:
            errors['force'] = ['Return has been restocked. Use force=True to delete.']
            return cls(success=False, errors=errors)
        
        try:
            deleted_id = return_id
            return_item.delete()
            
            return cls(
                deleted_id=deleted_id,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Update Return Status Mutation
# =============================================================================

class UpdateReturnStatusMutation(relay.ClientIDMutation):
    """Update return status."""
    
    class Input:
        return_id = graphene.ID(required=True)
        status = graphene.String(required=True)
        inspection_notes = graphene.String(required=False)
        quality_score = graphene.Int(required=False)
        refund_amount = graphene.Decimal(required=False)
    
    return_item = graphene.Field(ReturnsManagementNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, input):
        """
        Update return status.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: UpdateReturnStatusInput data
        
        Returns:
            UpdateReturnStatusMutation instance
        """
        errors = {}
        
        # Extract input
        return_id = input.get('return_id')
        status = input.get('status')
        inspection_notes = input.get('inspection_notes')
        quality_score = input.get('quality_score')
        refund_amount = input.get('refund_amount')
        
        # Resolve return
        try:
            pk = from_global_id(return_id)[1]
            return_item = ReturnsManagement.objects.get(pk=pk)
        except ReturnsManagement.DoesNotExist:
            errors['return_id'] = ['Return not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['return_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        try:
            # Update based on status
            if status == 'INSPECTED':
                return_item.inspected_at = timezone.now()
                if inspection_notes is not None:
                    return_item.inspection_notes = inspection_notes
                if quality_score is not None:
                    return_item.quality_score = quality_score
                if refund_amount is not None:
                    return_item.refund_amount = refund_amount
                
            elif status == 'RESTOCKED':
                return_item.restocked_at = timezone.now()
                
            elif status == 'COMPLETED':
                return_item.completed_at = timezone.now()
            
            return_item.save()
            
            return cls(
                return_item=return_item,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Update Transfer Mutation
# =============================================================================

class UpdateTransferMutation(relay.ClientIDMutation):
    """Update an existing transfer."""
    
    class Input:
        id = graphene.ID(required=True)
        carrier = graphene.String(required=False)
        tracking_number = graphene.String(required=False)
        estimated_transit_days = graphene.Int(required=False)
        transfer_cost = graphene.Decimal(required=False)
        shipping_cost = graphene.Decimal(required=False)
        handling_cost = graphene.Decimal(required=False)
        expected_transfer_date = graphene.Date(required=False)
    
    transfer = graphene.Field(InterWarehouseTransferNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, input):
        """
        Update an existing transfer.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: UpdateTransferInput data
        
        Returns:
            UpdateTransferMutation instance
        """
        errors = {}
        
        # Extract input
        transfer_id = input.get('id')
        
        # Resolve transfer
        try:
            pk = from_global_id(transfer_id)[1]
            transfer = InterWarehouseTransfer.objects.get(pk=pk)
        except InterWarehouseTransfer.DoesNotExist:
            errors['id'] = ['Transfer not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check if transfer can be updated
        if transfer.status in ['COMPLETED', 'CANCELLED']:
            errors['status'] = ['Cannot update a completed or cancelled transfer.']
            return cls(success=False, errors=errors)
        
        try:
            # Update fields
            if 'carrier' in input:
                transfer.carrier = input['carrier']
            if 'tracking_number' in input:
                transfer.tracking_number = input['tracking_number']
            if 'estimated_transit_days' in input:
                transfer.estimated_transit_days = input['estimated_transit_days']
            if 'transfer_cost' in input:
                transfer.transfer_cost = input['transfer_cost']
            if 'shipping_cost' in input:
                transfer.shipping_cost = input['shipping_cost']
            if 'handling_cost' in input:
                transfer.handling_cost = input['handling_cost']
            if 'expected_transfer_date' in input:
                transfer.expected_transfer_date = input['expected_transfer_date']
            
            transfer.full_clean()
            transfer.save()
            
            return cls(
                transfer=transfer,
                success=True,
                errors={}
            )
            
        except ValidationError as e:
            errors['validation'] = e.message_dict
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Delete Transfer Mutation
# =============================================================================

class DeleteTransferMutation(relay.ClientIDMutation):
    """Delete a transfer."""
    
    class Input:
        id = graphene.ID(required=True)
        force = graphene.Boolean(required=False, default_value=False)
    
    deleted_id = graphene.ID()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, input):
        """
        Delete a transfer.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: DeleteTransferInput data
        
        Returns:
            DeleteTransferMutation instance
        """
        errors = {}
        
        # Extract input
        transfer_id = input.get('id')
        force = input.get('force', False)
        
        # Resolve transfer
        try:
            pk = from_global_id(transfer_id)[1]
            transfer = InterWarehouseTransfer.objects.get(pk=pk)
        except InterWarehouseTransfer.DoesNotExist:
            errors['id'] = ['Transfer not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check if transfer can be deleted
        if transfer.status in ['IN_TRANSIT', 'RECEIVING', 'COMPLETED'] and not force:
            errors['force'] = [
                f'Cannot delete transfer with status "{transfer.status}". '
                'Use force=True to override.'
            ]
            return cls(success=False, errors=errors)
        
        try:
            # Release reserved stock if transfer is not completed
            if transfer.status != 'CANCELLED':
                from ..models.stock import Stock
                for item in transfer.items:
                    try:
                        source_stock = Stock.objects.get(
                            product_variant_id=item['variant_id'],
                            warehouse=transfer.source_warehouse
                        )
                        source_stock.quantity_reserved = F('quantity_reserved') - item['quantity']
                        source_stock.save()
                    except Stock.DoesNotExist:
                        pass
            
            deleted_id = transfer_id
            transfer.delete()
            
            return cls(
                deleted_id=deleted_id,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Update Transfer Status Mutation
# =============================================================================

class UpdateTransferStatusMutation(relay.ClientIDMutation):
    """Update transfer status."""
    
    class Input:
        transfer_id = graphene.ID(required=True)
        status = graphene.String(required=True)
        actual_transfer_date = graphene.Date(required=False)
        tracking_number = graphene.String(required=False)
        carrier = graphene.String(required=False)
    
    transfer = graphene.Field(InterWarehouseTransferNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, input):
        """
        Update transfer status.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: UpdateTransferStatusInput data
        
        Returns:
            UpdateTransferStatusMutation instance
        """
        errors = {}
        
        # Extract input
        transfer_id = input.get('transfer_id')
        status = input.get('status')
        
        # Resolve transfer
        try:
            pk = from_global_id(transfer_id)[1]
            transfer = InterWarehouseTransfer.objects.get(pk=pk)
        except InterWarehouseTransfer.DoesNotExist:
            errors['transfer_id'] = ['Transfer not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['transfer_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        try:
            # Update fields
            if 'actual_transfer_date' in input:
                transfer.actual_transfer_date = input['actual_transfer_date']
            if 'tracking_number' in input:
                transfer.tracking_number = input['tracking_number']
            if 'carrier' in input:
                transfer.carrier = input['carrier']
            
            # Handle special status transitions
            if status == 'COMPLETED':
                # Release stock at source and add to destination
                from ..models.stock import Stock
                for item in transfer.items:
                    # Reduce stock at source
                    try:
                        source_stock = Stock.objects.get(
                            product_variant_id=item['variant_id'],
                            warehouse=transfer.source_warehouse
                        )
                        source_stock.quantity = F('quantity') - item['quantity']
                        source_stock.quantity_reserved = F('quantity_reserved') - item['quantity']
                        source_stock.save()
                    except Stock.DoesNotExist:
                        pass
                    
                    # Add stock at destination
                    dest_stock, created = Stock.objects.get_or_create(
                        product_variant_id=item['variant_id'],
                        warehouse=transfer.destination_warehouse,
                        defaults={'quantity': 0}
                    )
                    dest_stock.quantity = F('quantity') + item['quantity']
                    dest_stock.save()
                    
            elif status == 'CANCELLED':
                # Release reserved stock at source
                from ..models.stock import Stock
                for item in transfer.items:
                    try:
                        source_stock = Stock.objects.get(
                            product_variant_id=item['variant_id'],
                            warehouse=transfer.source_warehouse
                        )
                        source_stock.quantity_reserved = F('quantity_reserved') - item['quantity']
                        source_stock.save()
                    except Stock.DoesNotExist:
                        pass
            
            transfer.status = status
            transfer.save()
            
            return cls(
                transfer=transfer,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Update Warehouse Task Mutation
# =============================================================================

class UpdateWarehouseTaskMutation(relay.ClientIDMutation):
    """Update an existing warehouse task."""
    
    class Input:
        id = graphene.ID(required=True)
        priority = graphene.String(required=False)
        assigned_to_id = graphene.ID(required=False)
        scheduled_date = graphene.DateTime(required=False)
        notes = graphene.String(required=False)
        items = graphene.JSONString(required=False)
    
    task = graphene.Field(WarehouseTaskNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, input):
        """
        Update an existing warehouse task.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: UpdateWarehouseTaskInput data
        
        Returns:
            UpdateWarehouseTaskMutation instance
        """
        errors = {}
        
        # Extract input
        task_id = input.get('id')
        priority = input.get('priority')
        assigned_to_id = input.get('assigned_to_id')
        scheduled_date = input.get('scheduled_date')
        notes = input.get('notes')
        items = input.get('items')
        
        # Resolve task
        try:
            pk = from_global_id(task_id)[1]
            task = WarehouseTask.objects.get(pk=pk)
        except WarehouseTask.DoesNotExist:
            errors['id'] = ['Task not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check if task can be updated
        if task.status in ['COMPLETED', 'CANCELLED']:
            errors['status'] = ['Cannot update a completed or cancelled task.']
            return cls(success=False, errors=errors)
        
        # Validate priority if provided
        if priority is not None:
            valid_priorities = ['LOW', 'MEDIUM', 'HIGH', 'URGENT']
            if priority not in valid_priorities:
                errors['priority'] = [
                    f'Invalid priority. Must be one of: {", ".join(valid_priorities)}'
                ]
                return cls(success=False, errors=errors)
        
        # Resolve assigned user if provided
        assigned_to = None
        if assigned_to_id:
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                pk = from_global_id(assigned_to_id)[1]
                assigned_to = User.objects.get(pk=pk)
            except Exception as e:
                errors['assigned_to_id'] = ['User not found.']
                return cls(success=False, errors=errors)
        
        try:
            # Update fields
            if priority is not None:
                task.priority = priority
            if assigned_to_id is not None:
                task.assigned_to = assigned_to
            if scheduled_date is not None:
                task.scheduled_date = scheduled_date
            if notes is not None:
                task.notes = notes
            if items is not None:
                task.items = items
            
            task.full_clean()
            task.save()
            
            return cls(
                task=task,
                success=True,
                errors={}
            )
            
        except ValidationError as e:
            errors['validation'] = e.message_dict
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Delete Warehouse Task Mutation
# =============================================================================

class DeleteWarehouseTaskMutation(relay.ClientIDMutation):
    """Delete a warehouse task."""
    
    class Input:
        id = graphene.ID(required=True)
        force = graphene.Boolean(required=False, default_value=False)
    
    deleted_id = graphene.ID()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Delete a warehouse task.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: DeleteWarehouseTaskInput data
        
        Returns:
            DeleteWarehouseTaskMutation instance
        """
        errors = {}
        
        # Extract input
        task_id = input.get('id')
        force = input.get('force', False)
        
        # Resolve task
        try:
            pk = from_global_id(task_id)[1]
            task = WarehouseTask.objects.get(pk=pk)
        except WarehouseTask.DoesNotExist:
            errors['id'] = ['Task not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check if task can be deleted
        if task.status in ['IN_PROGRESS', 'COMPLETED'] and not force:
            errors['force'] = [
                f'Cannot delete task with status "{task.status}". '
                'Use force=True to override.'
            ]
            return cls(success=False, errors=errors)
        
        try:
            deleted_id = task_id
            task.delete()
            
            return cls(
                deleted_id=deleted_id,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Update Task Status Mutation
# =============================================================================

class UpdateTaskStatusMutation(relay.ClientIDMutation):
    """Update warehouse task status."""
    
    class Input:
        task_id = graphene.ID(required=True)
        status = graphene.String(required=True)
        notes = graphene.String(required=False)
    
    task = graphene.Field(WarehouseTaskNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Update task status.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: UpdateTaskStatusInput data
        
        Returns:
            UpdateTaskStatusMutation instance
        """
        errors = {}
        
        # Extract input
        task_id = input.get('task_id')
        status = input.get('status')
        notes = input.get('notes')
        
        # Resolve task
        try:
            pk = from_global_id(task_id)[1]
            task = WarehouseTask.objects.get(pk=pk)
        except WarehouseTask.DoesNotExist:
            errors['task_id'] = ['Task not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['task_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Validate status
        valid_statuses = ['PENDING', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED']
        if status not in valid_statuses:
            errors['status'] = [
                f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
            ]
            return cls(success=False, errors=errors)
        
        try:
            # Update based on status
            if status == 'ASSIGNED':
                pass
            elif status == 'IN_PROGRESS':
                task.started_at = timezone.now()
            elif status == 'COMPLETED':
                task.completed_at = timezone.now()
                if task.started_at:
                    task.duration_minutes = (task.completed_at - task.started_at).total_seconds() / 60
            elif status == 'CANCELLED':
                pass
            
            if notes is not None:
                task.notes = notes
            
            task.status = status
            task.save()
            
            return cls(
                task=task,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Batch Operations
# =============================================================================

class BulkCreateReservationsMutation(relay.ClientIDMutation):
    """Bulk create reservations."""
    
    class Input:
        checkout_line_id = graphene.ID(required=True)
        stock_id = graphene.ID(required=True)
        quantity_reserved = graphene.Int(required=True)
        reserved_until = graphene.DateTime(required=True)
    
    created_count = graphene.Int()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, reservations):
        """
        Bulk create reservations.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            reservations: List of reservation inputs
        
        Returns:
            BulkCreateReservationsMutation instance
        """
        errors = {}
        created_count = 0
        
        for idx, reservation_input in enumerate(reservations):
            try:
                # Process each reservation
                result = CreateReservationMutation.mutate_and_get_payload(
                    root, info, reservation_input
                )
                if result.success:
                    created_count += 1
                else:
                    errors[f'reservation_{idx}'] = result.errors
            except Exception as e:
                errors[f'reservation_{idx}'] = [str(e)]
        
        return cls(
            created_count=created_count,
            success=len(errors) == 0,
            errors=errors if errors else {}
        )


class BulkUpdateAllocationsMutation(relay.ClientIDMutation):
    """Bulk update allocations."""
    
    class Input:
        order_line_id = graphene.ID(required=True)
        stock_id = graphene.ID(required=True)
        quantity_allocated = graphene.Int(required=True)
    
    updated_count = graphene.Int()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Bulk update allocations.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            allocations: List of allocation updates
        
        Returns:
            BulkUpdateAllocationsMutation instance
        """
        errors = {}
        updated_count = 0
        
        for idx, allocation_data in enumerate(allocations):
            try:
                allocation_id = allocation_data.get('id')
                quantity = allocation_data.get('quantity_allocated')
                
                pk = from_global_id(allocation_id)[1]
                allocation = Allocation.objects.get(pk=pk)
               
                # Update quantity
                if quantity > 0:
                    # Adjust stock quantities
                    stock = allocation.stock
                    stock.quantity_allocated = F('quantity_allocated') - allocation.quantity_allocated + quantity
                    stock.save()
                    
                    allocation.quantity_allocated = quantity
                    allocation.save()
                    updated_count += 1
                else:
                    errors[f'allocation_{idx}'] = ['Quantity must be greater than 0.']
                    
            except Allocation.DoesNotExist:
                errors[f'allocation_{idx}'] = ['Allocation not found.']
            except Exception as e:
                errors[f'allocation_{idx}'] = [str(e)]
        
        return cls(
            updated_count=updated_count,
            success=len(errors) == 0,
            errors=errors if errors else {}
        )


# =============================================================================
# Export Mutations
# =============================================================================

class InventoryMutations(graphene.ObjectType):
    """All inventory mutations."""

    
    # Stock CRUD
    create_stock = CreateStockMutation.Field()
    update_stock = UpdateStockMutation.Field()
    delete_stock = DeleteStockMutation.Field()
    
    # Stock adjustments
    increase_stock = IncreaseStockMutation.Field()
    decrease_stock = DecreaseStockMutation.Field()
    adjust_stock = AdjustStockMutation.Field()
    count_stock = CountStockMutation.Field()
    system_adjustment = SystemAdjustmentMutation.Field()
    
    # Bulk operations
    bulk_increase_stock = BulkIncreaseStockMutation.Field()
    bulk_adjust_stock = BulkAdjustStockMutation.Field()
    
    # History
    
    create_stock_history = CreateStockHistoryMutation.Field()
    update_stock_history = UpdateStockHistoryMutation.Field()
    delete_stock_history = DeleteStockHistoryMutation.Field()
    get_stock_history = GetStockHistoryMutation.Field()
    

   
    # Allocation mutations
    create_allocation = CreateAllocationMutation.Field()
    update_allocation = UpdateAllocationMutation.Field()
    delete_allocation = DeleteAllocationMutation.Field()
    bulk_update_allocations = BulkUpdateAllocationsMutation.Field()
    
    # Reservation mutations
    create_reservation = CreateReservationMutation.Field()
    update_reservation = UpdateReservationMutation.Field()
    delete_reservation = DeleteReservationMutation.Field()
    bulk_create_reservations = BulkCreateReservationsMutation.Field()
    
    # Return mutations
    create_return = CreateReturnMutation.Field()
    update_return = UpdateReturnMutation.Field()
    delete_return = DeleteReturnMutation.Field()
    update_return_status = UpdateReturnStatusMutation.Field()
    
    # Transfer mutations
    #create_transfer = CreateTransferMutation.Field()
    update_transfer = UpdateTransferMutation.Field()
    delete_transfer = DeleteTransferMutation.Field()
    update_transfer_status = UpdateTransferStatusMutation.Field()
    
    # Task mutations
    #create_warehouse_task = CreateWarehouseTaskMutation.Field()
    update_warehouse_task = UpdateWarehouseTaskMutation.Field()
    delete_warehouse_task = DeleteWarehouseTaskMutation.Field()
    update_task_status = UpdateTaskStatusMutation.Field()
    