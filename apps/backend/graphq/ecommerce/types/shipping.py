# graphql/ecommerce/types/shipping.py

"""
GraphQL Nodes for Shipping Zone, Shipping Method, ShippingMethodChannelListing,
ShippingMethodPostalCodeRule, and ShippingMethodTranslation.
"""

from graphene import Node, String, Boolean, Field, List, DateTime, Int, Decimal, UUID, JSONString, Float
from graphene_django_optimizer import OptimizedDjangoObjectType

from ecommerce.models.shipping import (
    ShippingZone,
    ShippingMethod,
    ShippingMethodChannelListing,
    ShippingMethodPostalCodeRule,
    ShippingMethodTranslation,
)


class ShippingMethodTranslationNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Shipping Method Translation.
    """
    
    class Meta:
        model = ShippingMethodTranslation
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            'id': ['exact'],
            'shipping_method': ['exact'],
            'language_code': ['exact'],
            'name': ['exact', 'icontains'],
        }
        ordering = [
            'language_code',
            'name',
        ]
    
    def resolve_shipping_method_details(self, info):
        """Resolve shipping method details."""
        return self.shipping_method


class ShippingMethodPostalCodeRuleNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Shipping Method Postal Code Rule.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    inclusion_type_display = String(description="Human-readable inclusion type display")
    range_display = String(description="Postal code range display")
    is_exclusion = Boolean(description="Whether this is an exclusion rule")
    is_inclusion = Boolean(description="Whether this is an inclusion rule")
    
    class Meta:
        model = ShippingMethodPostalCodeRule
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            'id': ['exact'],
            'shipping_method': ['exact'],
            'start': ['exact', 'icontains'],
            'end': ['exact', 'icontains', 'isnull'],
            'inclusion_type': ['exact'],
            'is_active': ['exact'],
            'created_at': ['exact', 'gte', 'lte'],
            'updated_at': ['exact', 'gte', 'lte'],
        }
        ordering = [
            'shipping_method__name',
            'start',
        ]
    
    def resolve_inclusion_type_display(self, info):
        """Resolve human-readable inclusion type display."""
        return dict(PostalCodeRuleInclusionType.CHOICES).get(self.inclusion_type, self.inclusion_type)
    
    def resolve_range_display(self, info):
        """Resolve postal code range display."""
        if self.end:
            return f"{self.start} - {self.end}"
        return self.start
    
    def resolve_is_exclusion(self, info):
        """Resolve whether this is an exclusion rule."""
        return self.inclusion_type == PostalCodeRuleInclusionType.EXCLUDE
    
    def resolve_is_inclusion(self, info):
        """Resolve whether this is an inclusion rule."""
        return self.inclusion_type == PostalCodeRuleInclusionType.INCLUDE
    
    def resolve_shipping_method_details(self, info):
        """Resolve shipping method details."""
        return self.shipping_method


class ShippingMethodChannelListingNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Shipping Method Channel Listing.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    price_display = String(description="Formatted price")
    minimum_order_price_display = String(description="Formatted minimum order price")
    maximum_order_price_display = String(description="Formatted maximum order price")
    price_range = String(description="Price range display")
    is_applicable = Boolean(description="Whether listing is active and valid")
    
    class Meta:
        model = ShippingMethodChannelListing
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            'id': ['exact'],
            'shipping_method': ['exact'],
            'channel': ['exact'],
            'currency': ['exact'],
            'price_amount': ['exact', 'gte', 'lte'],
            'minimum_order_price_amount': ['exact', 'gte', 'lte', 'isnull'],
            'maximum_order_price_amount': ['exact', 'gte', 'lte', 'isnull'],
            'is_active': ['exact'],
            'created_at': ['exact', 'gte', 'lte'],
            'updated_at': ['exact', 'gte', 'lte'],
        }
        ordering = [
            'channel__name',
            'price_amount',
        ]
    
    def resolve_price_display(self, info):
        """Resolve formatted price."""
        if self.price_amount:
            return f"{self.price_amount:.2f} {self.currency}"
        return None
    
    def resolve_minimum_order_price_display(self, info):
        """Resolve formatted minimum order price."""
        if self.minimum_order_price_amount:
            return f"{self.minimum_order_price_amount:.2f} {self.currency}"
        return None
    
    def resolve_maximum_order_price_display(self, info):
        """Resolve formatted maximum order price."""
        if self.maximum_order_price_amount:
            return f"{self.maximum_order_price_amount:.2f} {self.currency}"
        return None
    
    def resolve_price_range(self, info):
        """Resolve price range display."""
        min_price = self.minimum_order_price_display
        max_price = self.maximum_order_price_display
        if min_price and max_price:
            return f"{min_price} - {max_price}"
        elif min_price:
            return f"From {min_price}"
        elif max_price:
            return f"Up to {max_price}"
        return None
    
    def resolve_is_applicable(self, info):
        """Resolve whether listing is active and valid."""
        return self.is_active
    
    def resolve_shipping_method_details(self, info):
        """Resolve shipping method details."""
        return self.shipping_method
    
    def resolve_channel_details(self, info):
        """Resolve channel details."""
        return self.channel


class ShippingMethodNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Shipping Method with full shipping method management.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    # Status checks
    is_active_status = Boolean(description="Whether shipping method is active")
    type_display = String(description="Human-readable type display")
    status_display = String(description="Human-readable status display")
    has_weight_restrictions = Boolean(description="Whether method has weight restrictions")
    has_delivery_time_estimate = Boolean(description="Whether method has delivery time estimate")
    delivery_time_display = String(description="Delivery time range display")
    weight_range_display = String(description="Weight range display")
    is_price_based = Boolean(description="Whether method is price-based")
    is_weight_based = Boolean(description="Whether method is weight-based")
    
    class Meta:
        model = ShippingMethod
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Primary key
            'id': ['exact'],
            
            # Foreign keys
            'shipping_zone': ['exact'],
            'tax_class': ['exact'],
            'created_by': ['exact'],
            
            # String fields
            'name': ['exact', 'icontains', 'istartswith'],
            'type': ['exact'],
            'status': ['exact'],
            'description': ['exact', 'icontains'],
            
            # Boolean fields
            'is_active': ['exact'],
            
            # Numeric fields
            'delivery_time_min': ['exact', 'gte', 'lte', 'isnull'],
            'delivery_time_max': ['exact', 'gte', 'lte', 'isnull'],
            
            # Date fields
            'created_at': ['exact', 'gte', 'lte'],
            'updated_at': ['exact', 'gte', 'lte'],
            
            # Time fields
            'cutoff_time': ['exact', 'gte', 'lte', 'isnull'],
        }
        ordering = [
            'name',
            '-created_at',
        ]
    
    # ============================================================
    # Resolvers - Status Checks
    # ============================================================
    
    def resolve_is_active_status(self, info):
        """Resolve whether shipping method is active."""
        return self.is_active and self.status == ShippingMethodStatus.ACTIVE
    
    def resolve_type_display(self, info):
        """Resolve human-readable type display."""
        return dict(ShippingMethodType.CHOICES).get(self.type, self.type)
    
    def resolve_status_display(self, info):
        """Resolve human-readable status display."""
        return dict(ShippingMethodStatus.CHOICES).get(self.status, self.status)
    
    def resolve_has_weight_restrictions(self, info):
        """Resolve whether method has weight restrictions."""
        return self.minimum_order_weight is not None or self.maximum_order_weight is not None
    
    def resolve_has_delivery_time_estimate(self, info):
        """Resolve whether method has delivery time estimate."""
        return self.delivery_time_min is not None or self.delivery_time_max is not None
    
    def resolve_delivery_time_display(self, info):
        """Resolve delivery time range display."""
        if self.delivery_time_min and self.delivery_time_max:
            return f"{self.delivery_time_min} - {self.delivery_time_max} days"
        elif self.delivery_time_min:
            return f"{self.delivery_time_min}+ days"
        elif self.delivery_time_max:
            return f"Up to {self.delivery_time_max} days"
        return None
    
    def resolve_weight_range_display(self, info):
        """Resolve weight range display."""
        min_weight = self.minimum_order_weight
        max_weight = self.maximum_order_weight
        if min_weight and max_weight:
            return f"{min_weight.value} {min_weight.unit} - {max_weight.value} {max_weight.unit}"
        elif min_weight:
            return f"From {min_weight.value} {min_weight.unit}"
        elif max_weight:
            return f"Up to {max_weight.value} {max_weight.unit}"
        return None
    
    def resolve_is_price_based(self, info):
        """Resolve whether method is price-based."""
        return self.type == ShippingMethodType.PRICE_BASED
    
    def resolve_is_weight_based(self, info):
        """Resolve whether method is weight-based."""
        return self.type == ShippingMethodType.WEIGHT_BASED
    
    # ============================================================
    # Resolvers - Nested Fields
    # ============================================================
    
    def resolve_shipping_zone_details(self, info):
        """Resolve shipping zone details."""
        return self.shipping_zone
    
    def resolve_tax_class_details(self, info):
        """Resolve tax class details."""
        return self.tax_class
    
    def resolve_created_by_details(self, info):
        """Resolve user who created this shipping method."""
        return self.created_by
    
    def resolve_channel_listings(self, info):
        """Resolve channel listings."""
        return self.channel_listings.all()
    
    def resolve_postal_code_rules(self, info):
        """Resolve postal code rules."""
        return self.postal_code_rules.filter(is_active=True)
    
    def resolve_translations(self, info):
        """Resolve method translations."""
        return self.translations.all()
    
    def resolve_translation(self, info, language_code):
        """Resolve method translation for a specific language."""
        return self.translations.filter(language_code=language_code).first()
    
    def resolve_excluded_products(self, info):
        """Resolve excluded products."""
        return self.excluded_products.all()


class ShippingZoneNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Shipping Zone with full shipping zone management.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    countries_list = List(String, description="List of country codes")
    country_count = Int(description="Number of countries in zone")
    method_count = Int(description="Number of shipping methods in zone")
    is_active_status = Boolean(description="Whether shipping zone is active")
    is_default_status = Boolean(description="Whether this is the default zone")
    channels_list = List(String, description="List of channel names")
    channel_count = Int(description="Number of channels in zone")
    
    class Meta:
        model = ShippingZone
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Primary key
            'id': ['exact'],
            
            # String fields
            'name': ['exact', 'icontains', 'istartswith'],
            'description': ['exact', 'icontains'],
            
            # Boolean fields
            'default': ['exact'],
            'is_active': ['exact'],
            
            # Date fields
            'created_at': ['exact', 'gte', 'lte'],
            'updated_at': ['exact', 'gte', 'lte'],
        }
        ordering = [
            'name',
            '-created_at',
        ]
    
    # ============================================================
    # Resolvers - Calculated Properties
    # ============================================================
    
    def resolve_countries_list(self, info):
        """Resolve list of country codes."""
        return list(self.countries) if self.countries else []
    
    def resolve_country_count(self, info):
        """Resolve number of countries in zone."""
        return len(self.countries) if self.countries else 0
    
    def resolve_method_count(self, info):
        """Resolve number of shipping methods in zone."""
        return self.shipping_methods.count()
    
    def resolve_is_active_status(self, info):
        """Resolve whether shipping zone is active."""
        return self.is_active
    
    def resolve_is_default_status(self, info):
        """Resolve whether this is the default zone."""
        return self.default
    
    def resolve_channels_list(self, info):
        """Resolve list of channel names."""
        return list(self.channels.values_list('name', flat=True))
    
    def resolve_channel_count(self, info):
        """Resolve number of channels in zone."""
        return self.channels.count()
    
    # ============================================================
    # Resolvers - Nested Fields
    # ============================================================
    
    def resolve_shipping_methods(self, info):
        """Resolve shipping methods in this zone."""
        return self.shipping_methods.filter(is_active=True)
    
    def resolve_channels(self, info):
        """Resolve channels this zone applies to."""
        return self.channels.all()

