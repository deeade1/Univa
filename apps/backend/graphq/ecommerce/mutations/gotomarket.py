# apps/backend/ecommerce/mutations/gotomarket.py

"""
GoToMarket Mutations for Relay GraphQL API.
"""

import graphene
from graphql_relay import from_global_id
from graphene import relay
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from ecommerce.models.gotomarket import (
    MarketItem,
    Purchase,
    PurchaseItem,
    PurchaseCounter,
    ItemCategory,
)

from graphq.ecommerce.types.gotomarket import (
    MarketItemNode,
    PurchaseNode,
    PurchaseItemNode
)




# =============================================================================
# Create Market Item Mutation
# =============================================================================

class CreateMarketItemMutation(graphene.relay.ClientIDMutation):
    """Create a new market item."""
    
    class Input:
        name = graphene.String(required=True)
        category = graphene.String(required=True)
        subcategory = graphene.String(required=False)
        description = graphene.String(required=False)
        price_per_unit = graphene.Decimal(required=True)
        stock = graphene.Int(required=False, default_value=0)
        unit = graphene.String(required=False, default_value="KG")
        quantity_on_hand = graphene.Int(required=False, default_value=0)
        quantity_committed = graphene.Int(required=False, default_value=0)
        restock_threshold = graphene.Int(required=False, default_value=10)
        lead_time_days = graphene.Int(required=False, default_value=3)
        supplier = graphene.String(required=False)
        supplier_contact = graphene.String(required=False)
        image = graphene.String(required=False)
        is_seasonal = graphene.Boolean(required=False, default_value=False)
        season_start = graphene.Date(required=False)
        season_end = graphene.Date(required=False)
        is_organic = graphene.Boolean(required=False, default_value=False)
        is_locally_sourced = graphene.Boolean(required=False, default_value=True)
        origin_region = graphene.String(required=False)
        is_available = graphene.Boolean(required=False, default_value=True)
        is_featured = graphene.Boolean(required=False, default_value=False)
        is_bestseller = graphene.Boolean(required=False, default_value=False)

    market_item = graphene.Field(MarketItemNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Create a new market item.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: MarketItemInput data
        
        Returns:
            CreateMarketItemMutation instance
        """
        errors = {}
        
        # Extract input
        name = input.get('name')
        category = input.get('category')
        subcategory = input.get('subcategory')
        description = input.get('description', '')
        price_per_unit = input.get('price_per_unit')
        stock = input.get('stock', 0)
        unit = input.get('unit', 'KG')
        quantity_on_hand = input.get('quantity_on_hand', 0)
        quantity_committed = input.get('quantity_committed', 0)
        restock_threshold = input.get('restock_threshold', 10)
        lead_time_days = input.get('lead_time_days', 3)
        supplier = input.get('supplier', '')
        supplier_contact = input.get('supplier_contact', '')
        image = input.get('image')
        is_seasonal = input.get('is_seasonal', False)
        season_start = input.get('season_start')
        season_end = input.get('season_end')
        is_organic = input.get('is_organic', False)
        is_locally_sourced = input.get('is_locally_sourced', True)
        origin_region = input.get('origin_region', '')
        is_available = input.get('is_available', True)
        is_featured = input.get('is_featured', False)
        is_bestseller = input.get('is_bestseller', False)
        
        # Validate required fields
        if not name:
            errors['name'] = ['This field is required.']
            return cls(success=False, errors=errors)
        
        if not category:
            errors['category'] = ['This field is required.']
            return cls(success=False, errors=errors)
        
        if category not in [choice[0] for choice in ItemCategory.choices]:
            errors['category'] = ['Invalid category.']
            return cls(success=False, errors=errors)
        
        if price_per_unit is None or price_per_unit <= 0:
            errors['price_per_unit'] = ['Must be greater than 0.']
            return cls(success=False, errors=errors)
        
        # Validate subcategory
        if subcategory:
            valid_subcategories = dict(MarketItem.ALL_SUBCATEGORIES)
            if subcategory not in valid_subcategories:
                errors['subcategory'] = ['Invalid subcategory.']
                return cls(success=False, errors=errors)
        
        # Validate seasonal dates
        if is_seasonal and (not season_start or not season_end):
            errors['season'] = ['Both season_start and season_end are required for seasonal items.']
            return cls(success=False, errors=errors)
        
        if season_start and season_end and season_start > season_end:
            errors['season'] = ['season_start must be before season_end.']
            return cls(success=False, errors=errors)
        
        try:
            # Get current user
            user = info.context.user if hasattr(info.context, 'user') else None
            if not user or not user.is_authenticated:
                errors['user'] = ['Authentication required.']
                return cls(success=False, errors=errors)
            
            # Create market item
            market_item = MarketItem.objects.create(
                name=name,
                category=category,
                subcategory=subcategory,
                description=description,
                price_per_unit=price_per_unit,
                stock=stock,
                unit=unit,
                quantity_on_hand=quantity_on_hand,
                quantity_committed=quantity_committed,
                restock_threshold=restock_threshold,
                lead_time_days=lead_time_days,
                supplier=supplier,
                supplier_contact=supplier_contact,
                image=image,
                is_seasonal=is_seasonal,
                season_start=season_start,
                season_end=season_end,
                is_organic=is_organic,
                is_locally_sourced=is_locally_sourced,
                origin_region=origin_region,
                is_available=is_available,
                is_featured=is_featured,
                is_bestseller=is_bestseller,
                created_by=user,
            )
            
            return cls(
                market_item=market_item,
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
# Update Market Item Mutation
# =============================================================================

class UpdateMarketItemMutation(graphene.relay.ClientIDMutation):
    """Update an existing market item."""
    
    class Input:
        name = graphene.String(required=True)
        category = graphene.String(required=True)
        subcategory = graphene.String(required=False)
        description = graphene.String(required=False)
        price_per_unit = graphene.Decimal(required=True)
        stock = graphene.Int(required=False, default_value=0)
        unit = graphene.String(required=False, default_value="KG")
        quantity_on_hand = graphene.Int(required=False, default_value=0)
        quantity_committed = graphene.Int(required=False, default_value=0)
        restock_threshold = graphene.Int(required=False, default_value=10)
        lead_time_days = graphene.Int(required=False, default_value=3)
        supplier = graphene.String(required=False)
        supplier_contact = graphene.String(required=False)
        image = graphene.String(required=False)
        is_seasonal = graphene.Boolean(required=False, default_value=False)
        season_start = graphene.Date(required=False)
        season_end = graphene.Date(required=False)
        is_organic = graphene.Boolean(required=False, default_value=False)
        is_locally_sourced = graphene.Boolean(required=False, default_value=True)
        origin_region = graphene.String(required=False)
        is_available = graphene.Boolean(required=False, default_value=True)
        is_featured = graphene.Boolean(required=False, default_value=False)
        is_bestseller = graphene.Boolean(required=False, default_value=False)


    
    market_item = graphene.Field(MarketItemNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, input):
        """
        Update an existing market item.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: UpdateMarketItemInput data
        
        Returns:
            UpdateMarketItemMutation instance
        """
        errors = {}
        
        # Extract input
        item_id = input.get('id')
        name = input.get('name')
        category = input.get('category')
        subcategory = input.get('subcategory')
        description = input.get('description')
        price_per_unit = input.get('price_per_unit')
        stock = input.get('stock')
        unit = input.get('unit')
        quantity_on_hand = input.get('quantity_on_hand')
        quantity_committed = input.get('quantity_committed')
        restock_threshold = input.get('restock_threshold')
        lead_time_days = input.get('lead_time_days')
        supplier = input.get('supplier')
        supplier_contact = input.get('supplier_contact')
        image = input.get('image')
        is_seasonal = input.get('is_seasonal')
        season_start = input.get('season_start')
        season_end = input.get('season_end')
        is_organic = input.get('is_organic')
        is_locally_sourced = input.get('is_locally_sourced')
        origin_region = input.get('origin_region')
        is_available = input.get('is_available')
        is_featured = input.get('is_featured')
        is_bestseller = input.get('is_bestseller')
        
        # Resolve item
        try:
            pk = from_global_id(item_id)[1]
            market_item = MarketItem.objects.get(pk=pk)
        except MarketItem.DoesNotExist:
            errors['id'] = ['Market item not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Validate category
        if category and category not in [choice[0] for choice in ItemCategory.choices]:
            errors['category'] = ['Invalid category.']
            return cls(success=False, errors=errors)
        
        # Validate subcategory
        if subcategory:
            valid_subcategories = dict(MarketItem.ALL_SUBCATEGORIES)
            if subcategory not in valid_subcategories:
                errors['subcategory'] = ['Invalid subcategory.']
                return cls(success=False, errors=errors)
        
        # Validate price
        if price_per_unit is not None and price_per_unit <= 0:
            errors['price_per_unit'] = ['Must be greater than 0.']
            return cls(success=False, errors=errors)
        
        # Validate seasonal dates
        is_seasonal_val = is_seasonal if is_seasonal is not None else market_item.is_seasonal
        if is_seasonal_val:
            season_start_val = season_start if season_start is not None else market_item.season_start
            season_end_val = season_end if season_end is not None else market_item.season_end
            if not season_start_val or not season_end_val:
                errors['season'] = ['Both season_start and season_end are required for seasonal items.']
                return cls(success=False, errors=errors)
            if season_start_val and season_end_val and season_start_val > season_end_val:
                errors['season'] = ['season_start must be before season_end.']
                return cls(success=False, errors=errors)
        
        try:
            # Update fields
            if name is not None:
                market_item.name = name
            if category is not None:
                market_item.category = category
            if subcategory is not None:
                market_item.subcategory = subcategory
            if description is not None:
                market_item.description = description
            if price_per_unit is not None:
                market_item.price_per_unit = price_per_unit
            if stock is not None:
                market_item.stock = stock
            if unit is not None:
                market_item.unit = unit
            if quantity_on_hand is not None:
                market_item.quantity_on_hand = quantity_on_hand
            if quantity_committed is not None:
                market_item.quantity_committed = quantity_committed
            if restock_threshold is not None:
                market_item.restock_threshold = restock_threshold
            if lead_time_days is not None:
                market_item.lead_time_days = lead_time_days
            if supplier is not None:
                market_item.supplier = supplier
            if supplier_contact is not None:
                market_item.supplier_contact = supplier_contact
            if image is not None:
                market_item.image = image
            if is_seasonal is not None:
                market_item.is_seasonal = is_seasonal
            if season_start is not None:
                market_item.season_start = season_start
            if season_end is not None:
                market_item.season_end = season_end
            if is_organic is not None:
                market_item.is_organic = is_organic
            if is_locally_sourced is not None:
                market_item.is_locally_sourced = is_locally_sourced
            if origin_region is not None:
                market_item.origin_region = origin_region
            if is_available is not None:
                market_item.is_available = is_available
            if is_featured is not None:
                market_item.is_featured = is_featured
            if is_bestseller is not None:
                market_item.is_bestseller = is_bestseller
            
            market_item.save()
            
            return cls(
                market_item=market_item,
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
# Delete Market Item Mutation
# =============================================================================

class DeleteMarketItemMutation(graphene.relay.ClientIDMutation):
    """Delete a market item."""
    
    class Input:
        id = graphene.ID(required=True)
    
    deleted_id = graphene.ID()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id):
        """
        Delete a market item.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: MarketItem ID to delete
        
        Returns:
            DeleteMarketItemMutation instance
        """
        errors = {}
        
        try:
            pk = from_global_id(id)[1]
            market_item = MarketItem.objects.get(pk=pk)
        except MarketItem.DoesNotExist:
            errors['id'] = ['Market item not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check if item is referenced in any purchases
        if market_item.purchase_items.exists():
            errors['id'] = [
                'Cannot delete market item that is referenced in purchases. '
                'Remove the item from purchases first.'
            ]
            return cls(success=False, errors=errors)
        
        try:
            deleted_id = id
            market_item.delete()
            
            return cls(
                deleted_id=deleted_id,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Create Purchase Mutation
# =============================================================================

class CreatePurchaseMutation(graphene.relay.ClientIDMutation):
    """Create a new purchase."""
    
    class Input:
        delivery_address = graphene.String(required=False)
        delivery_date = graphene.DateTime(required=False)
        delivery_instructions = graphene.String(required=False)
        items = graphene.String(required=True)
        vat_rate = graphene.Decimal(required=False)
        discount = graphene.Decimal(required=False)
    
    purchase = graphene.Field(PurchaseNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, input):
        """
        Create a new purchase with items.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: PurchaseInput data
        
        Returns:
            CreatePurchaseMutation instance
        """
        errors = {}
        
        # Extract input
        delivery_address = input.get('delivery_address', '')
        delivery_date = input.get('delivery_date')
        delivery_instructions = input.get('delivery_instructions', '')
        items_data = input.get('items', [])
        vat_rate = input.get('vat_rate')
        discount = input.get('discount', Decimal('0.00'))
        
        # Validate items
        if not items_data:
            errors['items'] = ['At least one item is required.']
            return cls(success=False, errors=errors)
        
        # Get user
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['user'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        try:
            # Get VAT rate from settings or input
            if vat_rate is None:
                vat_rate = Decimal(str(getattr(settings, 'DEFAULT_VAT_RATE', 0.075)))
            
            # Create purchase
            purchase = Purchase.objects.create(
                user=user,
                status='DRAFT',
                delivery_address=delivery_address,
                delivery_date=delivery_date,
                delivery_instructions=delivery_instructions,
                vat_rate=vat_rate,
                discount=discount,
            )
            
            # Create purchase items
            for item_data in items_data:
                product_name = item_data.get('product_name')
                unit_price = item_data.get('unit_price')
                quantity = item_data.get('quantity')
                market_item_id = item_data.get('market_item_id')
                
                # Validate item data
                if not product_name:
                    errors.setdefault('items', []).append('Product name is required.')
                    continue
                
                if unit_price is None or unit_price <= 0:
                    errors.setdefault('items', []).append(
                        f'Invalid unit price for {product_name}.'
                    )
                    continue
                
                if quantity is None or quantity <= 0:
                    errors.setdefault('items', []).append(
                        f'Invalid quantity for {product_name}.'
                    )
                    continue
                
                # Resolve market item if provided
                market_item = None
                if market_item_id:
                    try:
                        pk = from_global_id(market_item_id)[1]
                        market_item = MarketItem.objects.get(pk=pk)
                    except MarketItem.DoesNotExist:
                        errors.setdefault('items', []).append(
                            f'Market item with ID {market_item_id} not found.'
                        )
                    except Exception as e:
                        errors.setdefault('items', []).append(str(e))
                
                # Create purchase item
                line_total = Decimal(str(quantity)) * Decimal(str(unit_price))
                PurchaseItem.objects.create(
                    purchase=purchase,
                    product_name=product_name,
                    unit_price=unit_price,
                    quantity=quantity,
                    line_total=line_total.quantize(Decimal('0.01')),
                    market_item=market_item,
                )
            
            # Recalculate totals
            purchase.calculate_totals()
            purchase.save()
            
            # Check if there were any errors creating items
            if errors.get('items'):
                # Still return the purchase but with errors
                return cls(
                    purchase=purchase,
                    success=False,
                    errors=errors
                )
            
            return cls(
                purchase=purchase,
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
# Update Purchase Status Mutation
# =============================================================================

class UpdatePurchaseStatusMutation(relay.ClientIDMutation):
    """Update purchase status."""
    
    class Input:
        purchase_id = graphene.ID(required=True)
        status = graphene.String(required=True)
        reason = graphene.String(required=False)
        payment_method = graphene.String(required=False)
        payment_reference = graphene.String(required=False)
        
    
    purchase = graphene.Field(PurchaseNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, purchase_id, status, **kwargs):
        """
        Update purchase status with proper transitions.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            purchase_id: Purchase ID
            status: New status
            kwargs: Additional fields (reason, payment_method, payment_reference)
        
        Returns:
            UpdatePurchaseStatusMutation instance
        """
        errors = {}
        
        # Resolve purchase
        try:
            pk = from_global_id(purchase_id)[1]
            purchase = Purchase.objects.get(pk=pk)
        except Purchase.DoesNotExist:
            errors['purchase_id'] = ['Purchase not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['purchase_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Validate status transition
        valid_statuses = [choice[0] for choice in Purchase.PURCHASE_STATUS]
        if status not in valid_statuses:
            errors['status'] = [f'Invalid status. Must be one of: {", ".join(valid_statuses)}']
            return cls(success=False, errors=errors)
        
        # Get user
        user = info.context.user if hasattr(info.context, 'user') else None
        
        try:
            # Handle status transitions
            if status == 'CONFIRMED':
                purchase.mark_as_confirmed()
                
            elif status == 'PAID':
                payment_method = kwargs.get('payment_method', '')
                payment_reference = kwargs.get('payment_reference', '')
                purchase.mark_as_paid(
                    payment_method=payment_method,
                    payment_reference=payment_reference,
                    verified_by=user
                )
                
            elif status == 'CANCELLED':
                reason = kwargs.get('reason', '')
                purchase.cancel_purchase(
                    reason=reason,
                    cancelled_by=user
                )
                
            elif status == 'REFUNDED':
                purchase.refund_purchase()
                
            else:
                # Direct status update for DRAFT
                purchase.status = status
                purchase.save()
            
            return cls(
                purchase=purchase,
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
# Add Items to Purchase Mutation
# =============================================================================

class AddItemsToPurchaseMutation(graphene.relay.ClientIDMutation):
    """Add items to an existing purchase."""
    
    class Input:
        purchase_id = graphene.ID(required=True)
        product_name = graphene.String(required=True)
        unit_price = graphene.Decimal(required=True)
        quantity = graphene.Int(required=True)
        market_item_id = graphene.ID(required=False)
    
    purchase = graphene.Field(PurchaseNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, purchase_id, items):
        """
        Add items to a purchase.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            purchase_id: Purchase ID
            items: List of items to add
        
        Returns:
            AddItemsToPurchaseMutation instance
        """
        errors = {}
        
        # Resolve purchase
        try:
            pk = from_global_id(purchase_id)[1]
            purchase = Purchase.objects.get(pk=pk)
        except Purchase.DoesNotExist:
            errors['purchase_id'] = ['Purchase not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['purchase_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check if purchase can be modified
        if purchase.status not in ['DRAFT']:
            errors['purchase'] = ['Cannot add items to a purchase that is not in draft status.']
            return cls(success=False, errors=errors)
        
        try:
            added_items = []
            
            for item_data in items:
                product_name = item_data.get('product_name')
                unit_price = item_data.get('unit_price')
                quantity = item_data.get('quantity')
                market_item_id = item_data.get('market_item_id')
                
                # Validate item data
                if not product_name:
                    errors.setdefault('items', []).append('Product name is required.')
                    continue
                
                if unit_price is None or unit_price <= 0:
                    errors.setdefault('items', []).append(
                        f'Invalid unit price for {product_name}.'
                    )
                    continue
                
                if quantity is None or quantity <= 0:
                    errors.setdefault('items', []).append(
                        f'Invalid quantity for {product_name}.'
                    )
                    continue
                
                # Resolve market item if provided
                market_item = None
                if market_item_id:
                    try:
                        pk = from_global_id(market_item_id)[1]
                        market_item = MarketItem.objects.get(pk=pk)
                    except MarketItem.DoesNotExist:
                        errors.setdefault('items', []).append(
                            f'Market item with ID {market_item_id} not found.'
                        )
                    except Exception as e:
                        errors.setdefault('items', []).append(str(e))
                
                # Create purchase item
                line_total = Decimal(str(quantity)) * Decimal(str(unit_price))
                item = PurchaseItem.objects.create(
                    purchase=purchase,
                    product_name=product_name,
                    unit_price=unit_price,
                    quantity=quantity,
                    line_total=line_total.quantize(Decimal('0.01')),
                    market_item=market_item,
                )
                added_items.append(item)
            
            # Recalculate totals
            purchase.calculate_totals()
            purchase.save()
            
            return cls(
                purchase=purchase,
                success=len(errors) == 0,
                errors=errors
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Remove Item from Purchase Mutation
# =============================================================================

class RemoveItemFromPurchaseMutation(graphene.relay.ClientIDMutation):
    """Remove an item from a purchase."""
    
    class Input:
        purchase_item_id = graphene.ID(required=True)
    
    purchase = graphene.Field(PurchaseNode)
    deleted_id = graphene.ID()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, purchase_item_id):
        """
        Remove an item from a purchase.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            purchase_item_id: PurchaseItem ID to remove
        
        Returns:
            RemoveItemFromPurchaseMutation instance
        """
        errors = {}
        
        try:
            pk = from_global_id(purchase_item_id)[1]
            purchase_item = PurchaseItem.objects.select_related('purchase').get(pk=pk)
        except PurchaseItem.DoesNotExist:
            errors['purchase_item_id'] = ['Purchase item not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['purchase_item_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        purchase = purchase_item.purchase
        
        # Check if purchase can be modified
        if purchase.status not in ['DRAFT']:
            errors['purchase'] = ['Cannot remove items from a purchase that is not in draft status.']
            return cls(success=False, errors=errors)
        
        try:
            deleted_id = purchase_item_id
            purchase_item.delete()
            
            # Recalculate totals
            purchase.calculate_totals()
            purchase.save()
            
            return cls(
                purchase=purchase,
                deleted_id=deleted_id,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Bulk Operations
# =============================================================================

class BulkUpdateMarketItemsMutation(graphene.relay.ClientIDMutation):
    """Bulk update multiple market items."""
    
    class Input:
        ids = graphene.List(graphene.ID, required=True)
        updates = graphene.JSONString(required=True, description="JSON object with fields to update")
    
    success = graphene.Boolean()
    errors = graphene.JSONString()
    updated_count = graphene.Int()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, ids, updates):
        """
        Bulk update market items.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            ids: List of item IDs to update
            updates: JSON object with fields to update
        
        Returns:
            BulkUpdateMarketItemsMutation instance
        """
        errors = {}
        updated_count = 0
        
        for item_id in ids:
            try:
                pk = from_global_id(item_id)[1]
                market_item = MarketItem.objects.get(pk=pk)
                
                # Apply updates
                for key, value in updates.items():
                    if hasattr(market_item, key):
                        setattr(market_item, key, value)
                
                market_item.save()
                updated_count += 1
                
            except MarketItem.DoesNotExist:
                errors[item_id] = ['Market item not found.']
            except Exception as e:
                errors[item_id] = [str(e)]
        
        return cls(
            success=len(errors) == 0,
            errors=errors if errors else {},
            updated_count=updated_count
        )


# =============================================================================
# Export Mutations
# =============================================================================

class GoToMarketMutations(graphene.ObjectType):
    """All GoToMarket mutations."""
    
    # Market Item mutations
    create_market_item = CreateMarketItemMutation.Field()
    update_market_item = UpdateMarketItemMutation.Field()
    delete_market_item = DeleteMarketItemMutation.Field()
    bulk_update_market_items = BulkUpdateMarketItemsMutation.Field()
    
    # Purchase mutations
    create_purchase = CreatePurchaseMutation.Field()
    update_purchase_status = UpdatePurchaseStatusMutation.Field()
    add_items_to_purchase = AddItemsToPurchaseMutation.Field()
    remove_item_from_purchase = RemoveItemFromPurchaseMutation.Field()