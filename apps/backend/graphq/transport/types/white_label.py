# graphql/transport/types/white_label.py

"""
GraphQL Nodes for White-label Clients and Configurations.
"""

from graphene import Node, Boolean, String, Field, List, DateTime, JSONString, Int
from graphene_django_optimizer import OptimizedDjangoObjectType

from transport.models.white_label import WhiteLabelClient, WhiteLabelConfiguration


class WhiteLabelClientNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for White-label Client with full client configuration.
    """
     
    class Meta:
        model = WhiteLabelClient
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Primary key
            'id': ['exact'],
            
            # String fields
            'name': ['exact', 'icontains', 'istartswith'],
            'domain': ['exact', 'icontains'],
            'company_name': ['exact', 'icontains'],
            'support_email': ['exact', 'icontains'],
            'support_phone': ['exact', 'icontains'],
            'api_key': ['exact', 'icontains'],
            'webhook_url': ['exact', 'icontains'],
            'primary_color': ['exact'],
            'secondary_color': ['exact'],
            'font_family': ['exact', 'icontains'],
            
            # Boolean fields
            'is_active': ['exact'],
            
            # Date fields
            'created_at': ['exact', 'gte', 'lte'],
            'updated_at': ['exact', 'gte', 'lte'],
        }
       
    


class WhiteLabelConfigurationNode(OptimizedDjangoObjectType):
    
    class Meta:
        model = WhiteLabelConfiguration
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Primary key
            'id': ['exact'],
            
            # Foreign keys
            'client': ['exact'],
            'client__name': ['exact', 'icontains'],
            'client__company_name': ['exact', 'icontains'],
            
            # String fields
            'theme_mode': ['exact'],
            'payment_gateway': ['exact'],
            'google_analytics_id': ['exact', 'icontains'],
            'facebook_pixel_id': ['exact', 'icontains'],
            
            # Boolean fields
            'enable_ride_sharing': ['exact'],
            'enable_sustainability_tracking': ['exact'],
            'enable_accessibility_features': ['exact'],
            'enable_analytics_dashboard': ['exact'],
        }
        ordering = [
            'client__name',
            '-client__created_at',
        ]
    