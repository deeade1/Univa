# apps/backend/realestate/mutations/subscription.py

"""
Property Subscription Mutations for Real Estate Relay GraphQL API.
"""

import graphene
from graphene import relay
from graphql_relay import from_global_id

from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from realestate.models.subscription import PropertySubscription
from realestate.models.listing import Listing
from realestate.constants import NOTIFICATION_FREQUENCY
from graphq.realestate.types.subscription import PropertySubscriptionNode
from graphq.realestate.types.listing import ListingNode
# =============================================================================
# Input Types
# =============================================================================

class PropertySubscriptionInput(graphene.InputObjectType):
    """Input for property subscription creation."""
    
    property_type = graphene.String(required=False)
    latitude = graphene.Float(required=False)
    longitude = graphene.Float(required=False)
    radius_km = graphene.Int(required=False, default_value=10)
    notification_frequency = graphene.String(required=False, default_value="instant")


class PropertySubscriptionUpdateInput(graphene.InputObjectType):
    """Input for property subscription update."""
    
    id = graphene.ID(required=True)
    property_type = graphene.String(required=False)
    latitude = graphene.Float(required=False)
    longitude = graphene.Float(required=False)
    radius_km = graphene.Int(required=False)
    is_active = graphene.Boolean(required=False)
    notification_frequency = graphene.String(required=False)


# =============================================================================
# Create Property Subscription Mutation
# =============================================================================

class CreatePropertySubscriptionMutation(relay.ClientIDMutation):
    """
    Create a new property subscription.
    
    Allows users to subscribe to property notifications based on
    location, property type, and radius.
    """
    
    class Input:
        id = graphene.ID(required=True)
        property_type = graphene.String(required=False)
        latitude = graphene.Float(required=False)
        longitude = graphene.Float(required=False)
        radius_km = graphene.Int(required=False)
        is_active = graphene.Boolean(required=False)
        notification_frequency = graphene.String(required=False)
    
    subscription = graphene.Field(PropertySubscriptionNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Create a new property subscription.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: PropertySubscriptionInput data
        
        Returns:
            CreatePropertySubscriptionMutation instance
        """
        errors = {}
        
        # Extract input
        property_type = input.get('property_type', '')
        latitude = input.get('latitude')
        longitude = input.get('longitude')
        radius_km = input.get('radius_km', 10)
        notification_frequency = input.get('notification_frequency', 'instant')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Validate radius
        if radius_km <= 0:
            errors['radius_km'] = ['Radius must be greater than 0.']
            return cls(success=False, errors=errors)
        
        # Validate notification frequency
        valid_frequencies = [choice[0] for choice in NOTIFICATION_FREQUENCY]
        if notification_frequency not in valid_frequencies:
            errors['notification_frequency'] = [
                f'Invalid frequency. Must be one of: {", ".join(valid_frequencies)}'
            ]
            return cls(success=False, errors=errors)
        
        # Create location point if coordinates provided
        location_point = None
        if latitude is not None and longitude is not None:
            if not (-90 <= latitude <= 90):
                errors['latitude'] = ['Latitude must be between -90 and 90.']
                return cls(success=False, errors=errors)
            
            if not (-180 <= longitude <= 180):
                errors['longitude'] = ['Longitude must be between -180 and 180.']
                return cls(success=False, errors=errors)
            
            location_point = Point(longitude, latitude, srid=4326)
        else:
            # If no location provided, subscription is global
            location_point = None
        
        try:
            # Create subscription
            subscription = PropertySubscription.objects.create(
                user=user,
                property_type=property_type,
                location_point=location_point,
                radius_km=radius_km,
                is_active=True,
                notification_frequency=notification_frequency,
                last_notified=None,
            )
            
            return cls(
                subscription=subscription,
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
# Update Property Subscription Mutation
# =============================================================================

class UpdatePropertySubscriptionMutation(relay.ClientIDMutation):
    """
    Update an existing property subscription.
    
    Allows updating the property type, location, radius, active status,
    and notification frequency.
    """
    
    class Input:
        id = graphene.ID(required=True)
        property_type = graphene.String(required=False)
        latitude = graphene.Float(required=False)
        longitude = graphene.Float(required=False)
        radius_km = graphene.Int(required=False)
        is_active = graphene.Boolean(required=False)
        notification_frequency = graphene.String(required=False)
    
    subscription = graphene.Field(PropertySubscriptionNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Update an existing property subscription.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: PropertySubscriptionUpdateInput data
        
        Returns:
            UpdatePropertySubscriptionMutation instance
        """
        errors = {}
        
        # Extract input
        subscription_id = input.get('id')
        property_type = input.get('property_type')
        latitude = input.get('latitude')
        longitude = input.get('longitude')
        radius_km = input.get('radius_km')
        is_active = input.get('is_active')
        notification_frequency = input.get('notification_frequency')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve subscription
        try:
            pk = from_global_id(subscription_id)[1]
            subscription = PropertySubscription.objects.get(pk=pk)
        except PropertySubscription.DoesNotExist:
            errors['id'] = ['Property subscription not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only the owner can update
        if subscription.user != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to update this subscription.']
            return cls(success=False, errors=errors)
        
        # Validate radius if provided
        if radius_km is not None and radius_km <= 0:
            errors['radius_km'] = ['Radius must be greater than 0.']
            return cls(success=False, errors=errors)
        
        # Validate notification frequency if provided
        if notification_frequency is not None:
            valid_frequencies = [choice[0] for choice in NOTIFICATION_FREQUENCY]
            if notification_frequency not in valid_frequencies:
                errors['notification_frequency'] = [
                    f'Invalid frequency. Must be one of: {", ".join(valid_frequencies)}'
                ]
                return cls(success=False, errors=errors)
        
        # Update location if coordinates provided
        if latitude is not None and longitude is not None:
            if not (-90 <= latitude <= 90):
                errors['latitude'] = ['Latitude must be between -90 and 90.']
                return cls(success=False, errors=errors)
            
            if not (-180 <= longitude <= 180):
                errors['longitude'] = ['Longitude must be between -180 and 180.']
                return cls(success=False, errors=errors)
            
            subscription.location_point = Point(longitude, latitude, srid=4326)
        elif latitude is not None or longitude is not None:
            errors['location'] = ['Both latitude and longitude are required to update location.']
            return cls(success=False, errors=errors)
        
        try:
            # Update fields
            if property_type is not None:
                subscription.property_type = property_type
            if radius_km is not None:
                subscription.radius_km = radius_km
            if is_active is not None:
                subscription.is_active = is_active
            if notification_frequency is not None:
                subscription.notification_frequency = notification_frequency
            
            subscription.full_clean()
            subscription.save()
            
            return cls(
                subscription=subscription,
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
# Delete Property Subscription Mutation
# =============================================================================

class DeletePropertySubscriptionMutation(relay.ClientIDMutation):
    """
    Delete a property subscription.
    
    Removes a subscription from the user's account.
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
        Delete a property subscription.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Subscription ID to delete
        
        Returns:
            DeletePropertySubscriptionMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve subscription
        try:
            pk = from_global_id(id)[1]
            subscription = PropertySubscription.objects.get(pk=pk)
        except PropertySubscription.DoesNotExist:
            errors['id'] = ['Property subscription not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only the owner can delete
        if subscription.user != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to delete this subscription.']
            return cls(success=False, errors=errors)
        
        try:
            deleted_id = id
            subscription.delete()
            
            return cls(
                deleted_id=deleted_id,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Toggle Subscription Status Mutation
# =============================================================================

class ToggleSubscriptionStatusMutation(relay.ClientIDMutation):
    """
    Toggle the active status of a property subscription.
    
    This is a convenience mutation for enabling/disabling a subscription.
    """
    
    class Input:
        id = graphene.ID(required=True)
        is_active = graphene.Boolean(required=True)
    
    subscription = graphene.Field(PropertySubscriptionNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id, is_active):
        """
        Toggle subscription active status.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Subscription ID
            is_active: New active status
        
        Returns:
            ToggleSubscriptionStatusMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve subscription
        try:
            pk = from_global_id(id)[1]
            subscription = PropertySubscription.objects.get(pk=pk)
        except PropertySubscription.DoesNotExist:
            errors['id'] = ['Property subscription not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission
        if subscription.user != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to update this subscription.']
            return cls(success=False, errors=errors)
        
        try:
            subscription.is_active = is_active
            subscription.save()
            
            return cls(
                subscription=subscription,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Get Properties for Subscription Mutation
# =============================================================================

class GetPropertiesForSubscriptionMutation(relay.ClientIDMutation):
    """
    Get properties matching a subscription.
    
    Returns properties within the subscription's radius and property type.
    """
    
    class Input:
        subscription_id = graphene.ID(required=True)
        limit = graphene.Int(required=False, default_value=20)
        offset = graphene.Int(required=False, default_value=0)
    
    properties = graphene.Field(ListingNode)
    total_count = graphene.Int()
    distance = graphene.Float()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    def mutate_and_get_payload(cls, root, info, subscription_id, limit=20, offset=0):
        """
        Get properties for a subscription.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            subscription_id: Subscription ID
            limit: Number of results to return
            offset: Results offset for pagination
        
        Returns:
            GetPropertiesForSubscriptionMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve subscription
        try:
            pk = from_global_id(subscription_id)[1]
            subscription = PropertySubscription.objects.get(pk=pk)
        except PropertySubscription.DoesNotExist:
            errors['subscription_id'] = ['Property subscription not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['subscription_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only the owner or staff can view
        if subscription.user != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to view this subscription.']
            return cls(success=False, errors=errors)
        
        try:
            # Get properties
            queryset = subscription.get_properties_in_radius()
            
            # Apply pagination
            total_count = queryset.count()
            properties = queryset[offset:offset + limit] if limit else queryset
            
            # Get distance for first result if available
            first_property = properties.first() if properties else None
            distance = None
            if first_property and hasattr(first_property, 'distance'):
                distance = first_property.distance.km
            
            return cls(
                properties=properties,
                total_count=total_count,
                distance=distance,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Bulk Operations
# =============================================================================

class BulkCreateSubscriptionsMutation(relay.ClientIDMutation):
    """
    Bulk create multiple property subscriptions.
    
    Allows creating multiple subscriptions at once.
    """
    
    class Input:
        id = graphene.ID(required=True)
        property_type = graphene.String(required=False)
        latitude = graphene.Float(required=False)
        longitude = graphene.Float(required=False)
        radius_km = graphene.Int(required=False)
        is_active = graphene.Boolean(required=False)
        notification_frequency = graphene.String(required=False)
    
    success_count = graphene.Int()
    failure_count = graphene.Int()
    results = graphene.JSONString()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Bulk create subscriptions.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            subscriptions: List of subscription inputs
        
        Returns:
            BulkCreateSubscriptionsMutation instance
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
        
        for idx, subscription_input in enumerate(subscriptions):
            try:
                # Use the create mutation for each subscription
                result = CreatePropertySubscriptionMutation.mutate_and_get_payload(
                    root, info, subscription_input
                )
                
                if result.success:
                    success_count += 1
                    results.append({
                        'index': idx,
                        'status': 'success',
                        'subscription_id': result.subscription.id if result.subscription else None,
                    })
                else:
                    failure_count += 1
                    errors[f'subscription_{idx}'] = result.errors
                    results.append({
                        'index': idx,
                        'status': 'failed',
                        'errors': result.errors,
                    })
                    
            except Exception as e:
                failure_count += 1
                errors[f'subscription_{idx}'] = [str(e)]
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


class BulkDeleteSubscriptionsMutation(relay.ClientIDMutation):
    """
    Bulk delete multiple property subscriptions.
    
    Allows deleting multiple subscriptions at once.
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
        Bulk delete subscriptions.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            ids: List of subscription IDs to delete
        
        Returns:
            BulkDeleteSubscriptionsMutation instance
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
        
        for subscription_id in ids:
            try:
                pk = from_global_id(subscription_id)[1]
                subscription = PropertySubscription.objects.get(pk=pk)
                
                # Check permission
                if subscription.user != user and not user.is_staff:
                    errors[subscription_id] = ['Permission denied.']
                    failure_count += 1
                    continue
                
                subscription.delete()
                deleted_ids.append(subscription_id)
                success_count += 1
                
            except PropertySubscription.DoesNotExist:
                errors[subscription_id] = ['Property subscription not found.']
                failure_count += 1
            except Exception as e:
                errors[subscription_id] = [str(e)]
                failure_count += 1
        
        return cls(
            deleted_ids=deleted_ids,
            success_count=success_count,
            failure_count=failure_count,
            success=failure_count == 0,
            errors=errors if errors else {}
        )


# =============================================================================
# Export Mutations
# =============================================================================

class PropertySubscriptionMutations(graphene.ObjectType):
    """All property subscription mutations."""
    
    # CRUD operations
    create_property_subscription = CreatePropertySubscriptionMutation.Field()
    update_property_subscription = UpdatePropertySubscriptionMutation.Field()
    delete_property_subscription = DeletePropertySubscriptionMutation.Field()
    
    # Status management
    toggle_subscription_status = ToggleSubscriptionStatusMutation.Field()
    
    # Property lookup
    get_properties_for_subscription = GetPropertiesForSubscriptionMutation.Field()
    
    # Bulk operations
    bulk_create_subscriptions = BulkCreateSubscriptionsMutation.Field()
    bulk_delete_subscriptions = BulkDeleteSubscriptionsMutation.Field()