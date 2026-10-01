# graphql/transport/types/rating.py

"""
GraphQL Nodes for Ratings including Provider, Customer, and Shared Trip Ratings.
"""

from graphene import Node, Float, Int, Boolean, String, Field, List, Decimal, DateTime
from graphene_django_optimizer import OptimizedDjangoObjectType

from transport.models.rating.ratings import Rating, ProviderRating, CustomerRating
from transport.models.core.service_provider import ServiceProviderProfile
from transport.models.core.service_request import ServiceRequest


class RatingNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for legacy Rating (shared trips).
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    rating_display = String(description="Human-readable rating display")
    is_high_rating = Boolean(description="Whether rating is 4 or above")
    is_low_rating = Boolean(description="Whether rating is 2 or below")
    
    class Meta:
        model = Rating
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Primary key
            'id': ['exact'],
            
            # Foreign keys
            'rater': ['exact'],
            'rater__email': ['exact', 'icontains'],
            'rated_user': ['exact'],
            'rated_user__email': ['exact', 'icontains'],
            'trip': ['exact'],
            'trip__id': ['exact'],
            
            # Numeric fields
            'score': ['exact', 'gte', 'lte'],
            
            # String fields
            'comment': ['exact', 'icontains'],
            
            # Date fields
            'created_at': ['exact', 'gte', 'lte'],
        }
       
    
    def resolve_rating_display(self, info):
        """Resolve human-readable rating display."""
        return self.rating_display
    
    def resolve_is_high_rating(self, info):
        """Resolve whether rating is 4 or above."""
        return self.score >= 4
    
    def resolve_is_low_rating(self, info):
        """Resolve whether rating is 2 or below."""
        return self.score <= 2
    
    def resolve_rater_details(self, info):
        """Resolve user giving the rating."""
        return self.rater
    
    def resolve_rated_user_details(self, info):
        """Resolve user being rated."""
        return self.rated_user
    
    def resolve_trip_details(self, info):
        """Resolve trip being rated."""
        return self.trip


class ProviderRatingNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Provider Rating with comprehensive rating criteria.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    average_score = Float(description="Average of all rating categories")
    is_high_rating = Boolean(description="Whether rating is 4 or above")
    is_low_rating = Boolean(description="Whether rating is 2 or below")
    has_response = Boolean(description="Whether provider has responded")
    rating_summary = String(description="JSON summary of the rating")
    
    # Display fields
    overall_rating_display = String(description="Display star rating")
    
    class Meta:
        model = ProviderRating
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Primary key
            'id': ['exact'],
            
            # Foreign keys
            'provider': ['exact'],
            'provider__user__email': ['exact', 'icontains'],
            'customer': ['exact'],
            'customer__email': ['exact', 'icontains'],
            'service_request': ['exact'],
            'service_request__id': ['exact'],
            
            # Numeric fields
            'overall_rating': ['exact', 'gte', 'lte'],
            'punctuality': ['exact', 'gte', 'lte', 'isnull'],
            'professionalism': ['exact', 'gte', 'lte', 'isnull'],
            'communication': ['exact', 'gte', 'lte', 'isnull'],
            'service_quality': ['exact', 'gte', 'lte', 'isnull'],
            'value_for_money': ['exact', 'gte', 'lte', 'isnull'],
            'vehicle_condition': ['exact', 'gte', 'lte', 'isnull'],
            'safety': ['exact', 'gte', 'lte', 'isnull'],
            
            # String fields
            'review': ['exact', 'icontains'],
            'provider_response': ['exact', 'icontains'],
            
            # Boolean fields
            'is_verified': ['exact'],
            'is_public': ['exact'],
            'is_edited': ['exact'],
            
            # Date fields
            'created_at': ['exact', 'gte', 'lte'],
            'updated_at': ['exact', 'gte', 'lte'],
            'provider_response_at': ['exact', 'gte', 'lte', 'isnull'],
        }
        
    
    # ============================================================
    # Resolvers - Calculated Properties
    # ============================================================
    
    def resolve_average_score(self, info):
        """Resolve average of all rating categories."""
        return self.average_score
    
    def resolve_is_high_rating(self, info):
        """Resolve whether rating is 4 or above."""
        return self.is_high_rating
    
    def resolve_is_low_rating(self, info):
        """Resolve whether rating is 2 or below."""
        return self.is_low_rating
    
    def resolve_has_response(self, info):
        """Resolve whether provider has responded."""
        return bool(self.provider_response)
    
    def resolve_rating_summary(self, info):
        """Resolve JSON summary of the rating."""
        import json
        return json.dumps(self.rating_summary)
    
    def resolve_overall_rating_display(self, info):
        """Resolve display star rating."""
        return f"{'⭐' * self.overall_rating} ({self.overall_rating}/5)"
    
    # ============================================================
    # Resolvers - Nested Fields
    # ============================================================
    
    def resolve_provider_details(self, info):
        """Resolve provider being rated."""
        return self.provider
    
    def resolve_customer_details(self, info):
        """Resolve customer giving the rating."""
        return self.customer
    
    def resolve_service_request_details(self, info):
        """Resolve service request being rated."""
        return self.service_request


class CustomerRatingNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Customer Rating (providers rating customers).
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    average_score = Float(description="Average of all rating categories")
    is_high_rating = Boolean(description="Whether rating is 4 or above")
    is_low_rating = Boolean(description="Whether rating is 2 or below")
    overall_rating_display = String(description="Display star rating")
    
  
    class Meta:
        model = CustomerRating
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Primary key
            'id': ['exact'],
            
            # Foreign keys
            'customer': ['exact'],
            'customer__email': ['exact', 'icontains'],
            'provider': ['exact'],
            'provider__user__email': ['exact', 'icontains'],
            'service_request': ['exact'],
            'service_request__id': ['exact'],
            
            # Numeric fields
            'overall_rating': ['exact', 'gte', 'lte'],
            'punctuality': ['exact', 'gte', 'lte', 'isnull'],
            'communication': ['exact', 'gte', 'lte', 'isnull'],
            'behavior': ['exact', 'gte', 'lte', 'isnull'],
            'respect': ['exact', 'gte', 'lte', 'isnull'],
            
            # String fields
            'review': ['exact', 'icontains'],
            
            # Boolean fields
            'is_public': ['exact'],
            'is_edited': ['exact'],
            
            # Date fields
            'created_at': ['exact', 'gte', 'lte'],
            'updated_at': ['exact', 'gte', 'lte'],
        }
        
    
    # ============================================================
    # Resolvers - Calculated Properties
    # ============================================================
    
    def resolve_average_score(self, info):
        """Resolve average of all rating categories."""
        return self.average_score
    
    def resolve_is_high_rating(self, info):
        """Resolve whether rating is 4 or above."""
        return self.is_high_rating
    
    def resolve_is_low_rating(self, info):
        """Resolve whether rating is 2 or below."""
        return self.is_low_rating
    
    def resolve_overall_rating_display(self, info):
        """Resolve display star rating."""
        return f"{'⭐' * self.overall_rating} ({self.overall_rating}/5)"
    
    # ============================================================
    # Resolvers - Nested Fields
    # ============================================================
    
    def resolve_customer_details(self, info):
        """Resolve customer being rated."""
        return self.customer
    
    def resolve_provider_details(self, info):
        """Resolve provider giving the rating."""
        return self.provider
    
    def resolve_service_request_details(self, info):
        """Resolve service request being rated."""
        return self.service_request

