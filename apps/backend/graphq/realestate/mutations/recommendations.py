# apps/backend/realestate/mutations/recommendations.py

"""
Recommendation Mutations for Real Estate Relay GraphQL API.
"""

import graphene
from graphene import relay
from graphql_relay import from_global_id

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from django.db.models import Q, F
from django.db.models.functions import Coalesce, Abs
from django.core.exceptions import ValidationError

from realestate.models.listing import Listing
from realestate.models.client import Client
from realestate.models.search import SearchProfile

from graphq.realestate.types.listing import ListingNode
# =============================================================================
# Helper Functions
# =============================================================================

def get_listing_node():
    """
    Lazy import of ListingNode to avoid circular imports.
    """
    from graphq.realestate.types import ListingNode
    return ListingNode


# =============================================================================
# Similar Properties Mutation
# =============================================================================

class GetSimilarPropertiesMutation(relay.ClientIDMutation):
    """
    Get similar properties based on a reference property.
    
    Finds properties with similar characteristics including:
    - Property type
    - Square footage (within 20%)
    - Bedrooms and bathrooms
    - Location (within 1.5km)
    - Price range (within 30%)
    """
    
    class Input:
        listing_id = graphene.ID(required=True)
        num_recommendations = graphene.Int(required=False, default_value=5)
        include_sold = graphene.Boolean(required=False, default_value=False)
        max_distance_km = graphene.Int(required=False, default_value=5)
    
    similar_properties = graphene.Field(ListingNode)
    total_count = graphene.Int()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    def mutate_and_get_payload(
        cls, 
        root, 
        info, 
        listing_id, 
        num_recommendations=5, 
        include_sold=False,
        max_distance_km=5
    ):
        """
        Get similar properties.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            listing_id: Reference listing ID
            num_recommendations: Number of properties to return
            include_sold: Include sold properties in results
            max_distance_km: Maximum distance in kilometers
        
        Returns:
            GetSimilarPropertiesMutation instance
        """
        errors = {}
        
        # Resolve listing
        try:
            pk = from_global_id(listing_id)[1]
            reference_listing = Listing.objects.get(pk=pk)
        except Listing.DoesNotExist:
            errors['listing_id'] = ['Property not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['listing_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        try:
            # Build query for similar properties
            queryset = Listing.objects.filter(is_published=True)
            
            # Exclude the reference property
            queryset = queryset.exclude(pk=reference_listing.pk)
            
            # Filter by property type (listing_type)
            if reference_listing.listing_type:
                queryset = queryset.filter(
                    listing_type=reference_listing.listing_type
                )
            
            # Filter by property area
            if reference_listing.property_area:
                queryset = queryset.filter(
                    property_area=reference_listing.property_area
                )
            
            # Filter by location (within max_distance_km)
            if reference_listing.location_point:
                queryset = queryset.filter(
                    location_point__distance_lte=(
                        reference_listing.location_point,
                        D(km=max_distance_km)
                    )
                )
            
            # Filter by square footage (within 20%)
            if reference_listing.square_feet:
                min_sqft = reference_listing.square_feet * 0.8
                max_sqft = reference_listing.square_feet * 1.2
                queryset = queryset.filter(
                    square_feet__gte=min_sqft,
                    square_feet__lte=max_sqft
                )
            
            # Filter by bedrooms (within 1)
            if reference_listing.bedrooms is not None:
                min_bedrooms = max(0, reference_listing.bedrooms - 1)
                max_bedrooms = reference_listing.bedrooms + 1
                queryset = queryset.filter(
                    bedrooms__gte=min_bedrooms,
                    bedrooms__lte=max_bedrooms
                )
            
            # Filter by bathrooms (within 1)
            if reference_listing.bathrooms is not None:
                min_bathrooms = max(0, reference_listing.bathrooms - 1)
                max_bathrooms = reference_listing.bathrooms + 1
                queryset = queryset.filter(
                    bathrooms__gte=min_bathrooms,
                    bathrooms__lte=max_bathrooms
                )
            
            # Filter by price (within 30%)
            if reference_listing.price:
                min_price = reference_listing.price * 0.7
                max_price = reference_listing.price * 1.3
                queryset = queryset.filter(
                    price__gte=min_price,
                    price__lte=max_price
                )
            
            # Include sold properties if requested
            if include_sold:
                queryset = queryset.filter(
                    Q(property_status='published') | 
                    Q(property_status='sold')
                )
            else:
                queryset = queryset.filter(property_status='published')
            
            # Annotate with distance if location available
            if reference_listing.location_point:
                queryset = queryset.annotate(
                    distance=Distance('location_point', reference_listing.location_point)
                ).order_by('distance')
            else:
                # Order by similarity score (closest match first)
                # Using a simple scoring system
                queryset = queryset.annotate(
                    similarity_score=(
                        Coalesce(F('square_feet'), 0) / 
                        (reference_listing.square_feet or 1) * 0.3 +
                        Coalesce(F('bedrooms'), 0) / 
                        (reference_listing.bedrooms or 1) * 0.2 +
                        Coalesce(F('bathrooms'), 0) / 
                        (reference_listing.bathrooms or 1) * 0.2 +
                        1.0 / (1 + Abs(F('price') - (reference_listing.price or 1)) / (reference_listing.price or 1) * 0.3)
                    )
                ).order_by('-similarity_score')
            
            # Get total count
            total_count = queryset.count()
            
            # Apply limit
            similar_properties = queryset[:num_recommendations]
            
            return cls(
                similar_properties=similar_properties,
                total_count=total_count,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Get Personalized Recommendations Mutation
# =============================================================================

class GetPersonalizedRecommendationsMutation(relay.ClientIDMutation):
    """
    Get personalized property recommendations for a user.
    
    Uses the user's client profile, location preferences, saved searches,
    and browsing history to generate personalized property recommendations.
    """
    
    class Input:
        max_results = graphene.Int(required=False, default_value=10)
        use_preferences = graphene.Boolean(required=False, default_value=True)
        use_saved_searches = graphene.Boolean(required=False, default_value=True)
    
    recommendations = graphene.Field(ListingNode)
    total_count = graphene.Int()
    recommendation_score = graphene.JSONString()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    def mutate_and_get_payload(
        cls, 
        root, 
        info, 
        max_results=10, 
        use_preferences=True,
        use_saved_searches=True
    ):
        """
        Get personalized recommendations.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            max_results: Maximum number of results
            use_preferences: Use location preferences
            use_saved_searches: Use saved searches
        
        Returns:
            GetPersonalizedRecommendationsMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        try:
            # Get client profile
            try:
                client = Client.objects.get(user=user)
            except Client.DoesNotExist:
                errors['client'] = ['Client profile not found. Please complete your client profile.']
                return cls(success=False, errors=errors)
            
            # Start with published listings
            queryset = Listing.objects.filter(is_published=True)
            
            # Build recommendation filters
            filters = Q()
            recommendation_score = {}
            
            # 1. Use client preferences
            if use_preferences:
                preference_filters = cls._build_preference_filters(client)
                if preference_filters:
                    filters |= preference_filters
                    recommendation_score['preferences'] = 1.0
                else:
                    recommendation_score['preferences'] = 0.0
            
            # 2. Use location preferences
            if use_preferences:
                location_filters = cls._build_location_filters(client)
                if location_filters:
                    filters |= location_filters
                    recommendation_score['location'] = 1.0
                else:
                    recommendation_score['location'] = 0.0
            
            # 3. Use saved searches
            if use_saved_searches:
                search_filters = cls._build_saved_search_filters(user)
                if search_filters:
                    filters |= search_filters
                    recommendation_score['saved_searches'] = 1.0
                else:
                    recommendation_score['saved_searches'] = 0.0
            
            # 4. Use property proximity
            proximity_filters = cls._build_proximity_filters(client)
            if proximity_filters:
                filters |= proximity_filters
                recommendation_score['proximity'] = 1.0
            else:
                recommendation_score['proximity'] = 0.0
            
            # Apply filters
            if filters:
                queryset = queryset.filter(filters)
            else:
                # If no filters, return recent listings
                queryset = queryset.order_by('-created_at')
            
            # Annotate with recommendation score
            queryset = queryset.annotate(
                relevance_score=(
                    # Prefer properties matching client preferences
                    Coalesce(F('price'), 0) * 0.1 +
                    Coalesce(F('bedrooms'), 0) * 0.2 +
                    Coalesce(F('bathrooms'), 0) * 0.2 +
                    Coalesce(F('square_feet'), 0) * 0.1
                )
            )
            
            # Order by relevance (newer properties first)
            queryset = queryset.order_by('-created_at', '-relevance_score')
            
            # Get total count
            total_count = queryset.count()
            
            # Apply limit
            recommendations = queryset[:max_results]
            
            # Calculate overall recommendation score
            total_score = sum(recommendation_score.values()) / max(1, len(recommendation_score))
            recommendation_score['overall'] = total_score
            
            return cls(
                recommendations=recommendations,
                total_count=total_count,
                recommendation_score=recommendation_score,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)
    
    @classmethod
    def _build_preference_filters(cls, client):
        """Build filters from client preferences."""
        filters = Q()
        
        # Price range
        if client.price_range_min and client.price_range_max:
            filters &= Q(
                price__gte=client.price_range_min,
                price__lte=client.price_range_max
            )
        elif client.price_range_min:
            filters &= Q(price__gte=client.price_range_min)
        elif client.price_range_max:
            filters &= Q(price__lte=client.price_range_max)
        
        # Property types
        if client.preferred_property_types:
            filters &= Q(listing_type__property_type__in=client.preferred_property_types)
        
        return filters
    
    @classmethod
    def _build_location_filters(cls, client):
        """Build filters from location preferences."""
        filters = Q()
        
        # Get location preferences
        location_prefs = LocationPreference.objects.filter(user=client.user)
        
        for pref in location_prefs:
            if pref.location_point:
                filters |= Q(
                    location_point__distance_lte=(
                        pref.location_point,
                        D(km=pref.radius_km or 10)
                    )
                )
        
        return filters
    
    @classmethod
    def _build_saved_search_filters(cls, user):
        """Build filters from saved searches."""
        filters = Q()
        
        saved_searches = SearchProfile.objects.filter(
            user=user,
            is_active=True
        )
        
        for search in saved_searches:
            search_filters = search.search_filters or {}
            
            # Price range
            if search_filters.get('min_price'):
                filters &= Q(price__gte=search_filters['min_price'])
            if search_filters.get('max_price'):
                filters &= Q(price__lte=search_filters['max_price'])
            
            # Property type
            if search_filters.get('property_types'):
                filters &= Q(listing_type__property_type__in=search_filters['property_types'])
            
            # Bedrooms
            if search_filters.get('bedrooms'):
                filters &= Q(bedrooms__gte=search_filters['bedrooms'])
            
            # Bathrooms
            if search_filters.get('bathrooms'):
                filters &= Q(bathrooms__gte=search_filters['bathrooms'])
        
        return filters
    
    @classmethod
    def _build_proximity_filters(cls, client):
        """Build filters from property proximity."""
        filters = Q()
        
        if hasattr(client, 'property_proximities'):
            proximities = client.property_proximities.filter(
                is_in_preferred_location=True
            )
            
            for prox in proximities:
                if prox.property and prox.property.location_point:
                    filters |= Q(
                        location_point__distance_lte=(
                            prox.property.location_point,
                            D(km=prox.distance_km or 5)
                        )
                    )
        
        return filters


# =============================================================================
# Get Property Recommendations by Location Mutation
# =============================================================================

class GetPropertyRecommendationsByLocationMutation(relay.ClientIDMutation):
    """
    Get property recommendations based on a location.
    
    Finds properties near a specific location point.
    """
    
    class Input:
        latitude = graphene.Float(required=True)
        longitude = graphene.Float(required=True)
        radius_km = graphene.Int(required=False, default_value=10)
        max_results = graphene.Int(required=False, default_value=20)
        min_price = graphene.Decimal(required=False)
        max_price = graphene.Decimal(required=False)
        property_type = graphene.String(required=False)
    
    properties = graphene.Field(ListingNode)
    total_count = graphene.Int()
    center_latitude = graphene.Float()
    center_longitude = graphene.Float()
    radius_km = graphene.Int()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    def mutate_and_get_payload(
        cls, 
        root, 
        info, 
        latitude, 
        longitude, 
        radius_km=10, 
        max_results=20,
        min_price=None,
        max_price=None,
        property_type=None
    ):
        """
        Get property recommendations by location.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            latitude: Center latitude
            longitude: Center longitude
            radius_km: Search radius in kilometers
            max_results: Maximum number of results
            min_price: Minimum price filter
            max_price: Maximum price filter
            property_type: Property type filter
        
        Returns:
            GetPropertyRecommendationsByLocationMutation instance
        """
        errors = {}
        
        # Validate coordinates
        if not (-90 <= latitude <= 90):
            errors['latitude'] = ['Latitude must be between -90 and 90.']
            return cls(success=False, errors=errors)
        
        if not (-180 <= longitude <= 180):
            errors['longitude'] = ['Longitude must be between -180 and 180.']
            return cls(success=False, errors=errors)
        
        # Validate radius
        if radius_km <= 0:
            errors['radius_km'] = ['Radius must be greater than 0.']
            return cls(success=False, errors=errors)
        
        try:
            from django.contrib.gis.geos import Point
            
            # Create location point
            location_point = Point(longitude, latitude, srid=4326)
            
            # Build query
            queryset = Listing.objects.filter(
                is_published=True,
                location_point__isnull=False,
                location_point__distance_lte=(
                    location_point,
                    D(km=radius_km)
                )
            )
            
            # Apply price filters
            if min_price is not None:
                queryset = queryset.filter(price__gte=min_price)
            if max_price is not None:
                queryset = queryset.filter(price__lte=max_price)
            
            # Apply property type filter
            if property_type:
                queryset = queryset.filter(listing_type__property_type=property_type)
            
            # Annotate with distance
            queryset = queryset.annotate(
                distance=Distance('location_point', location_point)
            ).order_by('distance')
            
            # Get total count
            total_count = queryset.count()
            
            # Apply limit
            properties = queryset[:max_results]
            
            return cls(
                properties=properties,
                total_count=total_count,
                center_latitude=latitude,
                center_longitude=longitude,
                radius_km=radius_km,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Get Trending Properties Mutation
# =============================================================================

class GetTrendingPropertiesMutation(relay.ClientIDMutation):
    """
    Get trending properties based on views, saves, and inquiries.
    
    Returns properties with the most engagement (views, bookmarks, inquiries).
    """
    
    class Input:
        max_results = graphene.Int(required=False, default_value=10)
        days = graphene.Int(required=False, default_value=30)
        min_price = graphene.Decimal(required=False)
        max_price = graphene.Decimal(required=False)
        property_type = graphene.String(required=False)
    
    properties = graphene.Field(ListingNode)
    total_count = graphene.Int()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    def mutate_and_get_payload(
        cls, 
        root, 
        info, 
        max_results=10, 
        days=30,
        min_price=None,
        max_price=None,
        property_type=None
    ):
        """
        Get trending properties.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            max_results: Maximum number of results
            days: Number of days to look back
            min_price: Minimum price filter
            max_price: Maximum price filter
            property_type: Property type filter
        
        Returns:
            GetTrendingPropertiesMutation instance
        """
        errors = {}
        
        try:
            # Build query
            queryset = Listing.objects.filter(is_published=True)
            
            # Apply price filters
            if min_price is not None:
                queryset = queryset.filter(price__gte=min_price)
            if max_price is not None:
                queryset = queryset.filter(price__lte=max_price)
            
            # Apply property type filter
            if property_type:
                queryset = queryset.filter(listing_type__property_type=property_type)
            
            # Note: If view_count, save_count, inquiry_count don't exist on Listing,
            # you'll need to add them or use related models.
            # For now, order by created_at as a fallback
            queryset = queryset.order_by('-created_at')
            
            # Get total count
            total_count = queryset.count()
            
            # Apply limit
            properties = queryset[:max_results]
            
            return cls(
                properties=properties,
                total_count=total_count,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Export Mutations
# =============================================================================

class RecommendationMutations(graphene.ObjectType):
    """All recommendation mutations."""
    
    get_similar_properties = GetSimilarPropertiesMutation.Field()
    get_personalized_recommendations = GetPersonalizedRecommendationsMutation.Field()
    get_property_recommendations_by_location = GetPropertyRecommendationsByLocationMutation.Field()
    get_trending_properties = GetTrendingPropertiesMutation.Field()