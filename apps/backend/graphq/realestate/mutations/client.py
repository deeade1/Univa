# apps/backend/realestate/mutations/client.py

"""
Client Mutations for Real Estate Relay GraphQL API.
"""

import graphene
from graphene_django import DjangoObjectType
from graphql_relay import from_global_id
from graphene  import relay
from django.conf import settings
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, F

from realestate.models.client import Client
from realestate.models.listing import Listing
from core.models.location import LocationModel

from graphq.realestate.types.client import ClientNode
from graphq.realestate.types.listing import ListingNode



# =============================================================================
# Create Client Mutation
# =============================================================================

class CreateClientMutation(relay.ClientIDMutation):
    """Create a new real estate client."""
    
    class Input:
        search_radius_km = graphene.Int(required=False, default_value=10)
        price_range_min = graphene.Decimal(required=False)
        price_range_max = graphene.Decimal(required=False)
        preferred_property_types = graphene.List(graphene.String, required=False)
        notification_frequency = graphene.String(required=False, default_value="instant")
        
        # Location fields (from LocationModel)
        location_point_lat = graphene.Float(required=False)
        location_point_lng = graphene.Float(required=False)
        location_address = graphene.String(required=False)
        location_city = graphene.String(required=False)
        location_state = graphene.String(required=False)
        location_country = graphene.String(required=False)
        location_postal_code = graphene.String(required=False)
    
    client = graphene.Field(ClientNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Create a new real estate client.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: ClientInput data
        
        Returns:
            CreateClientMutation instance
        """
        errors = {}
        
        # Extract input
        search_radius_km = input.get('search_radius_km', 10)
        price_range_min = input.get('price_range_min')
        price_range_max = input.get('price_range_max')
        preferred_property_types = input.get('preferred_property_types', [])
        notification_frequency = input.get('notification_frequency', 'instant')
        
        # Location fields
        location_point_lat = input.get('location_point_lat')
        location_point_lng = input.get('location_point_lng')
        location_address = input.get('location_address', '')
        location_city = input.get('location_city', '')
        location_state = input.get('location_state', '')
        location_country = input.get('location_country', '')
        location_postal_code = input.get('location_postal_code', '')
        
        # Get user
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['user'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Check if client already exists
        if Client.objects.filter(user=user).exists():
            errors['user'] = ['Client already exists for this user.']
            return cls(success=False, errors=errors)
        
        # Validate price range
        if price_range_min is not None and price_range_max is not None:
            if price_range_min > price_range_max:
                errors['price_range'] = ['Maximum price must be greater than minimum price.']
                return cls(success=False, errors=errors)
        
        # Validate search radius
        if search_radius_km > 100:
            errors['search_radius_km'] = ['Search radius cannot exceed 100 km.']
            return cls(success=False, errors=errors)
        
        # Validate notification frequency
        valid_frequencies = ['instant', 'daily', 'weekly']
        if notification_frequency not in valid_frequencies:
            errors['notification_frequency'] = [
                f'Invalid frequency. Must be one of: {", ".join(valid_frequencies)}'
            ]
            return cls(success=False, errors=errors)
        
        try:
            # Create location point
            location_point = None
            if location_point_lat is not None and location_point_lng is not None:
                location_point = Point(location_point_lng, location_point_lat, srid=4326)
            
            # Create client
            client = Client.objects.create(
                user=user,
                search_radius_km=search_radius_km,
                price_range_min=price_range_min,
                price_range_max=price_range_max,
                preferred_property_types=preferred_property_types,
                notification_frequency=notification_frequency,
                location_point=location_point,
                location_address=location_address,
                location_city=location_city,
                location_state=location_state,
                location_country=location_country,
                location_postal_code=location_postal_code,
            )
            
            return cls(
                client=client,
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
# Update Client Mutation
# =============================================================================

class UpdateClientMutation(relay.ClientIDMutation):
    """Update an existing real estate client."""
    
    class Input:
        search_radius_km = graphene.Int(required=False, default_value=10)
        price_range_min = graphene.Decimal(required=False)
        price_range_max = graphene.Decimal(required=False)
        preferred_property_types = graphene.List(graphene.String, required=False)
        notification_frequency = graphene.String(required=False, default_value="instant")
        
        # Location fields (from LocationModel)
        location_point_lat = graphene.Float(required=False)
        location_point_lng = graphene.Float(required=False)
        location_address = graphene.String(required=False)
        location_city = graphene.String(required=False)
        location_state = graphene.String(required=False)
        location_country = graphene.String(required=False)
        location_postal_code = graphene.String(required=False)
        
    client = graphene.Field(ClientNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Update an existing real estate client.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: UpdateClientInput data
        
        Returns:
            UpdateClientMutation instance
        """
        errors = {}
        
        # Extract input
        client_id = input.get('id')
        search_radius_km = input.get('search_radius_km')
        price_range_min = input.get('price_range_min')
        price_range_max = input.get('price_range_max')
        preferred_property_types = input.get('preferred_property_types')
        notification_frequency = input.get('notification_frequency')
        
        # Location fields
        location_point_lat = input.get('location_point_lat')
        location_point_lng = input.get('location_point_lng')
        location_address = input.get('location_address')
        location_city = input.get('location_city')
        location_state = input.get('location_state')
        location_country = input.get('location_country')
        location_postal_code = input.get('location_postal_code')
        
        # Resolve client
        try:
            pk = from_global_id(client_id)[1]
            client = Client.objects.get(pk=pk)
        except Client.DoesNotExist:
            errors['id'] = ['Client not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only the owner or admin can update
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['user'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        if client.user != user and not user.is_staff:
            errors['user'] = ['You do not have permission to update this client.']
            return cls(success=False, errors=errors)
        
        # Validate price range
        if price_range_min is not None and price_range_max is not None:
            if price_range_min > price_range_max:
                errors['price_range'] = ['Maximum price must be greater than minimum price.']
                return cls(success=False, errors=errors)
        
        # Validate search radius
        if search_radius_km is not None and search_radius_km > 100:
            errors['search_radius_km'] = ['Search radius cannot exceed 100 km.']
            return cls(success=False, errors=errors)
        
        # Validate notification frequency
        if notification_frequency is not None:
            valid_frequencies = ['instant', 'daily', 'weekly']
            if notification_frequency not in valid_frequencies:
                errors['notification_frequency'] = [
                    f'Invalid frequency. Must be one of: {", ".join(valid_frequencies)}'
                ]
                return cls(success=False, errors=errors)
        
        try:
            # Update location point
            if location_point_lat is not None and location_point_lng is not None:
                client.location_point = Point(location_point_lng, location_point_lat, srid=4326)
            
            # Update fields
            if search_radius_km is not None:
                client.search_radius_km = search_radius_km
            if price_range_min is not None:
                client.price_range_min = price_range_min
            if price_range_max is not None:
                client.price_range_max = price_range_max
            if preferred_property_types is not None:
                client.preferred_property_types = preferred_property_types
            if notification_frequency is not None:
                client.notification_frequency = notification_frequency
            if location_address is not None:
                client.location_address = location_address
            if location_city is not None:
                client.location_city = location_city
            if location_state is not None:
                client.location_state = location_state
            if location_country is not None:
                client.location_country = location_country
            if location_postal_code is not None:
                client.location_postal_code = location_postal_code
            
            client.full_clean()
            client.save()
            
            return cls(
                client=client,
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
# Update Client Preferences Mutation
# =============================================================================

class UpdateClientPreferencesMutation(relay.ClientIDMutation):
    """Update client preferences only."""
    
    class Input:
        search_radius_km = graphene.Int(required=False)
        price_range_min = graphene.Decimal(required=False)
        price_range_max = graphene.Decimal(required=False)
        preferred_property_types = graphene.List(graphene.String, required=False)
        notification_frequency = graphene.String(required=False)
    
    client = graphene.Field(ClientNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Update client preferences only (no location changes).
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: UpdateClientPreferencesInput data
        
        Returns:
            UpdateClientPreferencesMutation instance
        """
        errors = {}
        
        # Extract input
        client_id = input.get('id')
        search_radius_km = input.get('search_radius_km')
        price_range_min = input.get('price_range_min')
        price_range_max = input.get('price_range_max')
        preferred_property_types = input.get('preferred_property_types')
        notification_frequency = input.get('notification_frequency')
        
        # Resolve client
        try:
            pk = from_global_id(client_id)[1]
            client = Client.objects.get(pk=pk)
        except Client.DoesNotExist:
            errors['id'] = ['Client not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['user'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        if client.user != user and not user.is_staff:
            errors['user'] = ['You do not have permission to update this client.']
            return cls(success=False, errors=errors)
        
        # Validate price range
        price_min = price_range_min if price_range_min is not None else client.price_range_min
        price_max = price_range_max if price_range_max is not None else client.price_range_max
        if price_min is not None and price_max is not None:
            if price_min > price_max:
                errors['price_range'] = ['Maximum price must be greater than minimum price.']
                return cls(success=False, errors=errors)
        
        # Validate search radius
        if search_radius_km is not None and search_radius_km > 100:
            errors['search_radius_km'] = ['Search radius cannot exceed 100 km.']
            return cls(success=False, errors=errors)
        
        # Validate notification frequency
        if notification_frequency is not None:
            valid_frequencies = ['instant', 'daily', 'weekly']
            if notification_frequency not in valid_frequencies:
                errors['notification_frequency'] = [
                    f'Invalid frequency. Must be one of: {", ".join(valid_frequencies)}'
                ]
                return cls(success=False, errors=errors)
        
        try:
            # Update fields
            if search_radius_km is not None:
                client.search_radius_km = search_radius_km
            if price_range_min is not None:
                client.price_range_min = price_range_min
            if price_range_max is not None:
                client.price_range_max = price_range_max
            if preferred_property_types is not None:
                client.preferred_property_types = preferred_property_types
            if notification_frequency is not None:
                client.notification_frequency = notification_frequency
            
            client.full_clean()
            client.save()
            
            return cls(
                client=client,
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
# Update Client Location Mutation
# =============================================================================

class UpdateClientLocationMutation(relay.ClientIDMutation):
    """Update client location only."""
    
    class Input:
        search_radius_km = graphene.Int(required=False, default_value=10)
        price_range_min = graphene.Decimal(required=False)
        price_range_max = graphene.Decimal(required=False)
        preferred_property_types = graphene.List(graphene.String, required=False)
        notification_frequency = graphene.String(required=False, default_value="instant")
        
        # Location fields (from LocationModel)
        location_point_lat = graphene.Float(required=False)
        location_point_lng = graphene.Float(required=False)
        location_address = graphene.String(required=False)
        location_city = graphene.String(required=False)
        location_state = graphene.String(required=False)
        location_country = graphene.String(required=False)
        location_postal_code = graphene.String(required=False)
    client = graphene.Field(ClientNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Update client location only.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: UpdateClientLocationInput data
        
        Returns:
            UpdateClientLocationMutation instance
        """
        errors = {}
        
        # Extract input
        client_id = input.get('id')
        location_point_lat = input.get('location_point_lat')
        location_point_lng = input.get('location_point_lng')
        location_address = input.get('location_address')
        location_city = input.get('location_city')
        location_state = input.get('location_state')
        location_country = input.get('location_country')
        location_postal_code = input.get('location_postal_code')
        
        # Validate coordinates
        if location_point_lat is None or location_point_lng is None:
            errors['location_point'] = ['Both latitude and longitude are required.']
            return cls(success=False, errors=errors)
        
        if not (-90 <= location_point_lat <= 90):
            errors['location_point_lat'] = ['Latitude must be between -90 and 90.']
            return cls(success=False, errors=errors)
        
        if not (-180 <= location_point_lng <= 180):
            errors['location_point_lng'] = ['Longitude must be between -180 and 180.']
            return cls(success=False, errors=errors)
        
        # Resolve client
        try:
            pk = from_global_id(client_id)[1]
            client = Client.objects.get(pk=pk)
        except Client.DoesNotExist:
            errors['id'] = ['Client not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['user'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        if client.user != user and not user.is_staff:
            errors['user'] = ['You do not have permission to update this client.']
            return cls(success=False, errors=errors)
        
        try:
            # Update location
            client.location_point = Point(location_point_lng, location_point_lat, srid=4326)
            
            if location_address is not None:
                client.location_address = location_address
            if location_city is not None:
                client.location_city = location_city
            if location_state is not None:
                client.location_state = location_state
            if location_country is not None:
                client.location_country = location_country
            if location_postal_code is not None:
                client.location_postal_code = location_postal_code
            
            client.full_clean()
            client.save()
            
            return cls(
                client=client,
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
# Get Nearby Properties Mutation (for Client)
# =============================================================================

class GetNearbyPropertiesMutation(relay.ClientIDMutation):
    """Get nearby properties for a client."""
    
    class Input:
        client_id = graphene.ID(required=True)
        max_results = graphene.Int(required=False, default_value=20)
        override_radius_km = graphene.Int(required=False)
    
    properties = graphene.Field(ListingNode)
    total_count = graphene.Int()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    def mutate_and_get_payload(cls, root, info, client_id, max_results=20, override_radius_km=None):
        """
        Get nearby properties for a client.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            client_id: Client ID
            max_results: Maximum number of results
            override_radius_km: Override client's search radius
        
        Returns:
            GetNearbyPropertiesMutation instance
        """
        errors = {}
        
        # Resolve client
        try:
            pk = from_global_id(client_id)[1]
            client = Client.objects.get(pk=pk)
        except Client.DoesNotExist:
            errors['client_id'] = ['Client not found.']
            return cls(
                properties=[],
                total_count=0,
                success=False,
                errors=errors
            )
        except Exception as e:
            errors['client_id'] = [str(e)]
            return cls(
                properties=[],
                total_count=0,
                success=False,
                errors=errors
            )
        
        # Check permission
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['user'] = ['Authentication required.']
            return cls(
                properties=[],
                total_count=0,
                success=False,
                errors=errors
            )
        
        if client.user != user and not user.is_staff:
            errors['user'] = ['You do not have permission to view this client\'s properties.']
            return cls(
                properties=[],
                total_count=0,
                success=False,
                errors=errors
            )
        
        try:
            # Get nearby properties
            radius = override_radius_km or client.search_radius_km
            
            if not client.location_point:
                return cls(
                    properties=[],
                    total_count=0,
                    success=True,
                    errors={'location': ['Client location not set.']}
                )
            
            properties = client.find_nearby_properties(max_results)
            
            # Import ListingType dynamically to avoid circular import
            from .listing import ListingType
            
            return cls(
                properties=properties,
                total_count=properties.count() if hasattr(properties, 'count') else len(properties),
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(
                properties=[],
                total_count=0,
                success=False,
                errors=errors
            )


# =============================================================================
# Get Personalized Recommendations Mutation
# =============================================================================

class GetPersonalizedRecommendationsMutation(relay.ClientIDMutation):
    """Get personalized property recommendations for a client."""
    
    class Input:
        client_id = graphene.ID(required=True)
        max_results = graphene.Int(required=False, default_value=10)
    
    properties = graphene.Field(ListingNode)
    total_count = graphene.Int()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Get personalized recommendations for a client.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            client_id: Client ID
            max_results: Maximum number of results
        
        Returns:
            GetPersonalizedRecommendationsMutation instance
        """
        errors = {}
        
        # Resolve client
        try:
            pk = from_global_id(client_id)[1]
            client = Client.objects.get(pk=pk)
        except Client.DoesNotExist:
            errors['client_id'] = ['Client not found.']
            return cls(
                properties=[],
                total_count=0,
                success=False,
                errors=errors
            )
        except Exception as e:
            errors['client_id'] = [str(e)]
            return cls(
                properties=[],
                total_count=0,
                success=False,
                errors=errors
            )
        
        # Check permission
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['user'] = ['Authentication required.']
            return cls(
                properties=[],
                total_count=0,
                success=False,
                errors=errors
            )
        
        if client.user != user and not user.is_staff:
            errors['user'] = ['You do not have permission to view this client\'s recommendations.']
            return cls(
                properties=[],
                total_count=0,
                success=False,
                errors=errors
            )
        
        try:
            # Get personalized recommendations
            properties = client.get_personalized_recommendations(max_results)
            
            from .listing import ListingType
            
            return cls(
                properties=properties,
                total_count=properties.count() if hasattr(properties, 'count') else len(properties),
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(
                properties=[],
                total_count=0,
                success=False,
                errors=errors
            )


# =============================================================================
# Delete Client Mutation
# =============================================================================

class DeleteClientMutation(relay.ClientIDMutation):
    """Delete a real estate client."""
    
    class Input:
        id = graphene.ID(required=True)
    
    deleted_id = graphene.ID()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Delete a real estate client.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Client ID to delete
        
        Returns:
            DeleteClientMutation instance
        """
        errors = {}
        
        # Resolve client
        try:
            pk = from_global_id(id)[1]
            client = Client.objects.get(pk=pk)
        except Client.DoesNotExist:
            errors['id'] = ['Client not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['user'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        if client.user != user and not user.is_staff:
            errors['user'] = ['You do not have permission to delete this client.']
            return cls(success=False, errors=errors)
        
        try:
            deleted_id = id
            client.delete()
            
            return cls(
                deleted_id=deleted_id,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Bulk Update Client Preferences Mutation
# =============================================================================

class BulkUpdateClientPreferencesMutation(relay.ClientIDMutation):
    """Bulk update preferences for multiple clients."""
    
    class Input:
        client_ids = graphene.List(graphene.ID, required=True)
        search_radius_km = graphene.Int(required=False)
        price_range_min = graphene.Decimal(required=False)
        price_range_max = graphene.Decimal(required=False)
        preferred_property_types = graphene.List(graphene.String, required=False)
        notification_frequency = graphene.String(required=False)
        updated_count = graphene.Int()
        success = graphene.Boolean()
        errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Bulk update preferences for multiple clients.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            client_ids: List of client IDs
            preferences: Preferences to apply
        
        Returns:
            BulkUpdateClientPreferencesMutation instance
        """
        errors = {}
        updated_count = 0
        failed_ids = []
        
        # Get user for permission check
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['user'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        for client_id in client_ids:
            try:
                pk = from_global_id(client_id)[1]
                client = Client.objects.get(pk=pk)
                
                # Check permission
                if client.user != user and not user.is_staff:
                    failed_ids.append(client_id)
                    errors[client_id] = ['Permission denied.']
                    continue
                
                # Apply preferences
                if preferences.get('search_radius_km') is not None:
                    if preferences['search_radius_km'] > 100:
                        errors[client_id] = ['Search radius cannot exceed 100 km.']
                        failed_ids.append(client_id)
                        continue
                    client.search_radius_km = preferences['search_radius_km']
                
                if preferences.get('price_range_min') is not None:
                    client.price_range_min = preferences['price_range_min']
                
                if preferences.get('price_range_max') is not None:
                    client.price_range_max = preferences['price_range_max']
                
                # Validate price range
                if client.price_range_min is not None and client.price_range_max is not None:
                    if client.price_range_min > client.price_range_max:
                        errors[client_id] = ['Maximum price must be greater than minimum price.']
                        failed_ids.append(client_id)
                        continue
                
                if preferences.get('preferred_property_types') is not None:
                    client.preferred_property_types = preferences['preferred_property_types']
                
                if preferences.get('notification_frequency') is not None:
                    valid_frequencies = ['instant', 'daily', 'weekly']
                    if preferences['notification_frequency'] not in valid_frequencies:
                        errors[client_id] = [
                            f'Invalid frequency. Must be one of: {", ".join(valid_frequencies)}'
                        ]
                        failed_ids.append(client_id)
                        continue
                    client.notification_frequency = preferences['notification_frequency']
                
                client.full_clean()
                client.save()
                updated_count += 1
                
            except Client.DoesNotExist:
                failed_ids.append(client_id)
                errors[client_id] = ['Client not found.']
            except ValidationError as e:
                failed_ids.append(client_id)
                errors[client_id] = e.message_dict
            except Exception as e:
                failed_ids.append(client_id)
                errors[client_id] = [str(e)]
        
        return cls(
            updated_count=updated_count,
            success=len(failed_ids) == 0,
            errors=errors if errors else {}
        )


# =============================================================================
# Export Mutations
# =============================================================================

class ClientMutations(graphene.ObjectType):
    """All real estate client mutations."""
    
    # Client CRUD
    create_client = CreateClientMutation.Field()
    update_client = UpdateClientMutation.Field()
    delete_client = DeleteClientMutation.Field()
    
    # Client preferences
    update_client_preferences = UpdateClientPreferencesMutation.Field()
    update_client_location = UpdateClientLocationMutation.Field()
    bulk_update_client_preferences = BulkUpdateClientPreferencesMutation.Field()
    
    # Client queries (as mutations for Relay)
    get_nearby_properties = GetNearbyPropertiesMutation.Field()
    get_personalized_recommendations = GetPersonalizedRecommendationsMutation.Field()
    
