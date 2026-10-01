# apps/backend/realestate/mutations/market_trend.py

"""
Market Trend Mutations for Real Estate Relay GraphQL API.
"""

import graphene
from graphene import relay
from graphql_relay import from_global_id

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from realestate.models.market_trend import MarketTrend
from realestate.models.neighborhood import  Neighborhood

from graphq.realestate.types.market_trend import MarketTrendNode

# =============================================================================
# Create Market Trend Mutation
# =============================================================================

class CreateMarketTrendMutation(relay.ClientIDMutation):
    """
    Create a new market trend record.
    
    Market trends track real estate market metrics for neighborhoods over time.
    """
    
    class Input:
        id = graphene.ID(required=True)
        neighborhood_id = graphene.ID(required=False)
        date = graphene.Date(required=False)
        median_price = graphene.Decimal(required=False)
        listings_count = graphene.Int(required=False)
        avg_days_on_market = graphene.Int(required=False)
        price_per_sqft = graphene.Decimal(required=False)
    
    market_trend = graphene.Field(MarketTrendNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Create a new market trend record.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: MarketTrendInput data
        
        Returns:
            CreateMarketTrendMutation instance
        """
        errors = {}
        
        # Extract input
        neighborhood_id = input.get('neighborhood_id')
        date = input.get('date')
        median_price = input.get('median_price')
        listings_count = input.get('listings_count')
        avg_days_on_market = input.get('avg_days_on_market')
        price_per_sqft = input.get('price_per_sqft')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Check permission - only staff can create market trends
        if not user.is_staff:
            errors['permission'] = ['Only staff members can create market trends.']
            return cls(success=False, errors=errors)
        
        # Validate median price
        if median_price <= 0:
            errors['median_price'] = ['Median price must be greater than 0.']
            return cls(success=False, errors=errors)
        
        # Validate listings count
        if listings_count < 0:
            errors['listings_count'] = ['Listings count cannot be negative.']
            return cls(success=False, errors=errors)
        
        # Validate avg days on market
        if avg_days_on_market < 0:
            errors['avg_days_on_market'] = ['Average days on market cannot be negative.']
            return cls(success=False, errors=errors)
        
        # Validate price per sqft
        if price_per_sqft < 0:
            errors['price_per_sqft'] = ['Price per sqft cannot be negative.']
            return cls(success=False, errors=errors)
        
        # Resolve neighborhood
        try:
            pk = from_global_id(neighborhood_id)[1]
            neighborhood = Neighborhood.objects.get(pk=pk)
        except Neighborhood.DoesNotExist:
            errors['neighborhood_id'] = ['Neighborhood not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['neighborhood_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check if market trend already exists for this neighborhood and date
        if MarketTrend.objects.filter(neighborhood=neighborhood, date=date).exists():
            errors['date'] = ['Market trend already exists for this neighborhood on this date.']
            return cls(success=False, errors=errors)
        
        # Check if date is in the future
        if date > timezone.now().date():
            errors['date'] = ['Cannot create market trend for a future date.']
            return cls(success=False, errors=errors)
        
        try:
            # Create market trend
            market_trend = MarketTrend.objects.create(
                neighborhood=neighborhood,
                date=date,
                median_price=median_price,
                listings_count=listings_count,
                avg_days_on_market=avg_days_on_market,
                price_per_sqft=price_per_sqft,
            )
            
            return cls(
                market_trend=market_trend,
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
# Update Market Trend Mutation
# =============================================================================

class UpdateMarketTrendMutation(relay.ClientIDMutation):
    """
    Update an existing market trend record.
    
    Allows updating market metrics for a neighborhood on a specific date.
    """
    
    class Input:
        id = graphene.ID(required=True)
        neighborhood_id = graphene.ID(required=False)
        date = graphene.Date(required=False)
        median_price = graphene.Decimal(required=False)
        listings_count = graphene.Int(required=False)
        avg_days_on_market = graphene.Int(required=False)
        price_per_sqft = graphene.Decimal(required=False)
    
    market_trend = graphene.Field(MarketTrendNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Update an existing market trend record.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: MarketTrendUpdateInput data
        
        Returns:
            UpdateMarketTrendMutation instance
        """
        errors = {}
        
        # Extract input
        trend_id = input.get('id')
        neighborhood_id = input.get('neighborhood_id')
        date = input.get('date')
        median_price = input.get('median_price')
        listings_count = input.get('listings_count')
        avg_days_on_market = input.get('avg_days_on_market')
        price_per_sqft = input.get('price_per_sqft')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Check permission - only staff can update market trends
        if not user.is_staff:
            errors['permission'] = ['Only staff members can update market trends.']
            return cls(success=False, errors=errors)
        
        # Resolve market trend
        try:
            pk = from_global_id(trend_id)[1]
            market_trend = MarketTrend.objects.get(pk=pk)
        except MarketTrend.DoesNotExist:
            errors['id'] = ['Market trend not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Validate median price if provided
        if median_price is not None and median_price <= 0:
            errors['median_price'] = ['Median price must be greater than 0.']
            return cls(success=False, errors=errors)
        
        # Validate listings count if provided
        if listings_count is not None and listings_count < 0:
            errors['listings_count'] = ['Listings count cannot be negative.']
            return cls(success=False, errors=errors)
        
        # Validate avg days on market if provided
        if avg_days_on_market is not None and avg_days_on_market < 0:
            errors['avg_days_on_market'] = ['Average days on market cannot be negative.']
            return cls(success=False, errors=errors)
        
        # Validate price per sqft if provided
        if price_per_sqft is not None and price_per_sqft < 0:
            errors['price_per_sqft'] = ['Price per sqft cannot be negative.']
            return cls(success=False, errors=errors)
        
        # Resolve neighborhood if provided
        if neighborhood_id:
            try:
                pk = from_global_id(neighborhood_id)[1]
                neighborhood = Neighborhood.objects.get(pk=pk)
                market_trend.neighborhood = neighborhood
            except Neighborhood.DoesNotExist:
                errors['neighborhood_id'] = ['Neighborhood not found.']
                return cls(success=False, errors=errors)
        
        # Check for duplicate date if date is changing
        if date and date != market_trend.date:
            if date > timezone.now().date():
                errors['date'] = ['Cannot update to a future date.']
                return cls(success=False, errors=errors)
            
            if MarketTrend.objects.filter(
                neighborhood=market_trend.neighborhood,
                date=date
            ).exclude(pk=market_trend.pk).exists():
                errors['date'] = ['Market trend already exists for this neighborhood on this date.']
                return cls(success=False, errors=errors)
        
        try:
            # Update fields
            if date is not None:
                market_trend.date = date
            if median_price is not None:
                market_trend.median_price = median_price
            if listings_count is not None:
                market_trend.listings_count = listings_count
            if avg_days_on_market is not None:
                market_trend.avg_days_on_market = avg_days_on_market
            if price_per_sqft is not None:
                market_trend.price_per_sqft = price_per_sqft
            
            market_trend.full_clean()
            market_trend.save()
            
            return cls(
                market_trend=market_trend,
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
# Delete Market Trend Mutation
# =============================================================================

class DeleteMarketTrendMutation(relay.ClientIDMutation):
    """
    Delete a market trend record.
    
    Removes a market trend record from the database.
    """
    
    class Input:
        id = graphene.ID(required=True)
    
    deleted_id = graphene.ID()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id):
        """
        Delete a market trend record.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Market trend ID to delete
        
        Returns:
            DeleteMarketTrendMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Check permission - only staff can delete market trends
        if not user.is_staff:
            errors['permission'] = ['Only staff members can delete market trends.']
            return cls(success=False, errors=errors)
        
        # Resolve market trend
        try:
            pk = from_global_id(id)[1]
            market_trend = MarketTrend.objects.get(pk=pk)
        except MarketTrend.DoesNotExist:
            errors['id'] = ['Market trend not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        try:
            deleted_id = id
            market_trend.delete()
            
            return cls(
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

class BulkCreateMarketTrendsMutation(relay.ClientIDMutation):
    """
    Bulk create multiple market trend records.
    
    Allows creating multiple market trends at once for different neighborhoods or dates.
    """
    
    class Input:
        id = graphene.ID(required=True)
        neighborhood_id = graphene.ID(required=False)
        date = graphene.Date(required=False)
        median_price = graphene.Decimal(required=False)
        listings_count = graphene.Int(required=False)
        avg_days_on_market = graphene.Int(required=False)
        price_per_sqft = graphene.Decimal(required=False)
    
    success_count = graphene.Int()
    failure_count = graphene.Int()
    results = graphene.JSONString()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Bulk create market trends.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            trends: List of market trend inputs
        
        Returns:
            BulkCreateMarketTrendsMutation instance
        """
        errors = {}
        results = []
        success_count = 0
        failure_count = 0
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Check permission
        if not user.is_staff:
            errors['permission'] = ['Only staff members can create market trends.']
            return cls(success=False, errors=errors)
        
        for idx, trend_input in enumerate(trends):
            try:
                # Use the create mutation for each trend
                result = CreateMarketTrendMutation.mutate_and_get_payload(
                    root, info, trend_input
                )
                
                if result.success:
                    success_count += 1
                    results.append({
                        'index': idx,
                        'status': 'success',
                        'trend_id': result.market_trend.id if result.market_trend else None,
                    })
                else:
                    failure_count += 1
                    errors[f'trend_{idx}'] = result.errors
                    results.append({
                        'index': idx,
                        'status': 'failed',
                        'errors': result.errors,
                    })
                    
            except Exception as e:
                failure_count += 1
                errors[f'trend_{idx}'] = [str(e)]
                results.append({
                    'index': idx,
                    'status': 'failed',
                    'errors': [str(e)],
                })
        
        return cls(
            success_count=success_count,
            failure_count=failure_count,
            results=results,
            success=failure_count == 0,
            errors=errors if errors else {}
        )


class BulkDeleteMarketTrendsMutation(relay.ClientIDMutation):
    """
    Bulk delete multiple market trend records.
    
    Allows deleting multiple market trends at once.
    """
    
    class Input:
        ids = graphene.List(graphene.ID, required=True)
    
    deleted_ids = graphene.List(graphene.ID)
    success_count = graphene.Int()
    failure_count = graphene.Int()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, ids):
        """
        Bulk delete market trends.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            ids: List of market trend IDs to delete
        
        Returns:
            BulkDeleteMarketTrendsMutation instance
        """
        errors = {}
        deleted_ids = []
        success_count = 0
        failure_count = 0
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Check permission
        if not user.is_staff:
            errors['permission'] = ['Only staff members can delete market trends.']
            return cls(success=False, errors=errors)
        
        for trend_id in ids:
            try:
                pk = from_global_id(trend_id)[1]
                market_trend = MarketTrend.objects.get(pk=pk)
                
                market_trend.delete()
                deleted_ids.append(trend_id)
                success_count += 1
                
            except MarketTrend.DoesNotExist:
                errors[trend_id] = ['Market trend not found.']
                failure_count += 1
            except Exception as e:
                errors[trend_id] = [str(e)]
                failure_count += 1
        
        return cls(
            deleted_ids=deleted_ids,
            success_count=success_count,
            failure_count=failure_count,
            success=failure_count == 0,
            errors=errors if errors else {}
        )


class BulkUpdateMarketTrendsMutation(relay.ClientIDMutation):
    """
    Bulk update multiple market trend records.
    
    Allows updating common fields across multiple market trends at once.
    """
    
    class Input:
        ids = graphene.List(graphene.ID, required=True)
        neighborhood_id = graphene.ID(required=False)
        date = graphene.Date(required=False)
        median_price = graphene.Decimal(required=False)
        listings_count = graphene.Int(required=False)
        avg_days_on_market = graphene.Int(required=False)
        price_per_sqft = graphene.Decimal(required=False)
    
    updated_ids = graphene.List(graphene.ID)
    success_count = graphene.Int()
    failure_count = graphene.Int()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Bulk update market trends.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            ids: List of market trend IDs to update
            updates: Fields to update
        
        Returns:
            BulkUpdateMarketTrendsMutation instance
        """
        errors = {}
        updated_ids = []
        success_count = 0
        failure_count = 0
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Check permission
        if not user.is_staff:
            errors['permission'] = ['Only staff members can update market trends.']
            return cls(success=False, errors=errors)
        
        for trend_id in ids:
            try:
                pk = from_global_id(trend_id)[1]
                market_trend = MarketTrend.objects.get(pk=pk)
                
                # Apply updates
                if updates.get('median_price') is not None:
                    if updates['median_price'] <= 0:
                        errors[trend_id] = ['Median price must be greater than 0.']
                        failure_count += 1
                        continue
                    market_trend.median_price = updates['median_price']
                
                if updates.get('listings_count') is not None:
                    if updates['listings_count'] < 0:
                        errors[trend_id] = ['Listings count cannot be negative.']
                        failure_count += 1
                        continue
                    market_trend.listings_count = updates['listings_count']
                
                if updates.get('avg_days_on_market') is not None:
                    if updates['avg_days_on_market'] < 0:
                        errors[trend_id] = ['Average days on market cannot be negative.']
                        failure_count += 1
                        continue
                    market_trend.avg_days_on_market = updates['avg_days_on_market']
                
                if updates.get('price_per_sqft') is not None:
                    if updates['price_per_sqft'] < 0:
                        errors[trend_id] = ['Price per sqft cannot be negative.']
                        failure_count += 1
                        continue
                    market_trend.price_per_sqft = updates['price_per_sqft']
                
                market_trend.full_clean()
                market_trend.save()
                updated_ids.append(trend_id)
                success_count += 1
                
            except MarketTrend.DoesNotExist:
                errors[trend_id] = ['Market trend not found.']
                failure_count += 1
            except ValidationError as e:
                errors[trend_id] = e.message_dict
                failure_count += 1
            except Exception as e:
                errors[trend_id] = [str(e)]
                failure_count += 1
        
        return cls(
            updated_ids=updated_ids,
            success_count=success_count,
            failure_count=failure_count,
            success=failure_count == 0,
            errors=errors if errors else {}
        )


# =============================================================================
# Export Mutations
# =============================================================================

class MarketTrendMutations(graphene.ObjectType):
    """All market trend mutations."""
    
    # CRUD operations
    create_market_trend = CreateMarketTrendMutation.Field()
    update_market_trend = UpdateMarketTrendMutation.Field()
    delete_market_trend = DeleteMarketTrendMutation.Field()
    
    # Bulk operations
    bulk_create_market_trends = BulkCreateMarketTrendsMutation.Field()
    bulk_delete_market_trends = BulkDeleteMarketTrendsMutation.Field()
    bulk_update_market_trends = BulkUpdateMarketTrendsMutation.Field()