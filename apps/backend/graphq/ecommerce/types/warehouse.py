# graphql/ecommerce/types/warehouse.py

"""
GraphQL Nodes for Warehouse and ChannelWarehouse models.
"""

from graphene import Node, String, Boolean, Field, List, DateTime, Int, UUID, Float
from graphene_django_optimizer import OptimizedDjangoObjectType

from ecommerce.models.warehouse import Warehouse, ChannelWarehouse
from ecommerce.models.constants import WarehouseClickAndCollectOption




class ChannelWarehouseNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Channel Warehouse (through model).
    """
    class Meta:
        model = ChannelWarehouse
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            'id': ['exact'],
            'channel': ['exact'],
            'warehouse': ['exact'],
            'sort_order': ['exact', 'gte', 'lte'],
        }
        ordering = [
            'sort_order',
            'channel__name',
            'warehouse__name',
        ]
    
    def resolve_channel_details(self, info):
        """Resolve channel details."""
        return self.channel
    
    def resolve_warehouse_details(self, info):
        """Resolve warehouse details."""
        return self.warehouse


class WarehouseNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Warehouse with full warehouse management.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    # Capacity
    available_capacity = Int(description="Available storage capacity")
    capacity_utilization = Float(description="Capacity utilization percentage")
    countries = List(String, description="Countries served by this warehouse")
    country_count = Int(description="Number of countries served")
    channel_count = Int(description="Number of channels associated")
    shipping_zone_count = Int(description="Number of shipping zones associated")
    
    # Status
    is_click_and_collect_enabled = Boolean(description="Whether click and collect is enabled")
    click_and_collect_option_display = String(description="Human-readable click and collect option display")
    is_operating = Boolean(description="Whether warehouse is currently operating based on hours")
    is_private_status = Boolean(description="Whether warehouse is private")
    has_capacity = Boolean(description="Whether warehouse has any capacity")
    is_at_capacity = Boolean(description="Whether warehouse is at full capacity")
    
    class Meta:
        model = Warehouse
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            
            # String fields
            'name': ['exact', 'icontains', 'istartswith'],
            'slug': ['exact', 'icontains', 'istartswith'],
            'email': ['exact', 'icontains'],
            'timezone': ['exact'],
            'click_and_collect_option': ['exact'],
            
            # Boolean fields
            'is_private': ['exact'],
            
            # Numeric fields
            'capacity_total': ['exact', 'gte', 'lte'],
            'capacity_used': ['exact', 'gte', 'lte'],
            'max_daily_throughput': ['exact', 'gte', 'lte'],
            
            # Date fields
            'created_at': ['exact', 'gte', 'lte'],
            'updated_at': ['exact', 'gte', 'lte'],
            
            # Time fields
            'operating_hours_start': ['exact', 'gte', 'lte', 'isnull'],
            'operating_hours_end': ['exact', 'gte', 'lte', 'isnull'],
            
            # Foreign keys
            'address': ['exact'],
        }
        ordering = [
            'name',
            'slug',
            '-created_at',
        ]
    
    # ============================================================
    # Resolvers - Calculated Properties
    # ============================================================
    
    def resolve_available_capacity(self, info):
        """Resolve available storage capacity."""
        return self.available_capacity
    
    def resolve_capacity_utilization(self, info):
        """Resolve capacity utilization percentage."""
        return self.capacity_utilization
    
    def resolve_countries(self, info):
        """Resolve countries served by this warehouse."""
        return list(self.countries)
    
    def resolve_country_count(self, info):
        """Resolve number of countries served."""
        return len(self.countries)
    
    def resolve_channel_count(self, info):
        """Resolve number of channels associated."""
        return self.channels.count()
    
    def resolve_shipping_zone_count(self, info):
        """Resolve number of shipping zones associated."""
        return self.shipping_zones.count()
    
    def resolve_is_click_and_collect_enabled(self, info):
        """Resolve whether click and collect is enabled."""
        return self.click_and_collect_option in [
            WarehouseClickAndCollectOption.LOCAL_STOCK,
            WarehouseClickAndCollectOption.ALL_WAREHOUSES,
        ]
    
    def resolve_click_and_collect_option_display(self, info):
        """Resolve human-readable click and collect option display."""
        return dict(WarehouseClickAndCollectOption.CHOICES).get(
            self.click_and_collect_option, self.click_and_collect_option
        )
    
    def resolve_is_operating(self, info):
        """Resolve whether warehouse is currently operating based on hours."""
        if not self.operating_hours_start or not self.operating_hours_end:
            return True
        from django.utils import timezone
        now = timezone.now().time()
        if self.operating_hours_start <= self.operating_hours_end:
            return self.operating_hours_start <= now <= self.operating_hours_end
        # Crosses midnight
        return now >= self.operating_hours_start or now <= self.operating_hours_end
    
    def resolve_is_private_status(self, info):
        """Resolve whether warehouse is private."""
        return self.is_private
    
    def resolve_has_capacity(self, info):
        """Resolve whether warehouse has any capacity."""
        return self.capacity_total > 0
    
    def resolve_is_at_capacity(self, info):
        """Resolve whether warehouse is at full capacity."""
        return self.capacity_total > 0 and self.capacity_used >= self.capacity_total
    
    # ============================================================
    # Resolvers - Nested Fields
    # ============================================================
    
    def resolve_address_details(self, info):
        """Resolve address details."""
        return self.address


# =============================================================================
# Utility Resolvers
# =============================================================================

from django.db.models import Count, Q
from django.utils import timezone


def resolve_warehouses_by_channel(info, channel_id):
    """
    Utility resolver for getting warehouses by channel.
    
    Usage in schema:
        warehousesByChannel(channelId: ID!): [WarehouseNode!]!
    """
    return Warehouse.objects.for_channel(channel_id)


def resolve_warehouses_by_country(info, country_code, channel_id=None):
    """
    Utility resolver for getting warehouses by country.
    
    Usage in schema:
        warehousesByCountry(
            countryCode: String!,
            channelId: ID
        ): [WarehouseNode!]!
    """
    queryset = Warehouse.objects.filter(
        shipping_zones__countries__contains=country_code
    )
    if channel_id:
        queryset = queryset.filter(channelwarehouse__channel_id=channel_id)
    return queryset.distinct().order_by('name')


def resolve_click_and_collect_warehouses(info, channel_id):
    """
    Utility resolver for getting click and collect warehouses.
    
    Usage in schema:
        clickAndCollectWarehouses(channelId: ID!): [WarehouseNode!]!
    """
    return Warehouse.objects._for_channel_click_and_collect(channel_id)


def resolve_warehouse_stats(info):
    """
    Utility resolver for getting warehouse statistics.
    
    Usage in schema:
        warehouseStats: WarehouseStats!
    """
    total = Warehouse.objects.count()
    private = Warehouse.objects.filter(is_private=True).count()
    public = total - private
    
    cc_enabled = Warehouse.objects.filter(
        click_and_collect_option__in=[
            WarehouseClickAndCollectOption.LOCAL_STOCK,
            WarehouseClickAndCollectOption.ALL_WAREHOUSES,
        ]
    ).count()
    
    with_capacity = Warehouse.objects.filter(capacity_total__gt=0).count()
    at_capacity = Warehouse.objects.filter(
        capacity_total__gt=0,
        capacity_used__gte=models.F('capacity_total')
    ).count()
    
    total_capacity = Warehouse.objects.aggregate(
        total=models.Sum('capacity_total')
    )['total'] or 0
    
    used_capacity = Warehouse.objects.aggregate(
        total=models.Sum('capacity_used')
    )['total'] or 0
    
    return {
        'total_warehouses': total,
        'private_warehouses': private,
        'public_warehouses': public,
        'click_and_collect_enabled': cc_enabled,
        'warehouses_with_capacity': with_capacity,
        'warehouses_at_capacity': at_capacity,
        'total_capacity': total_capacity,
        'used_capacity': used_capacity,
        'available_capacity': total_capacity - used_capacity,
    }


# =============================================================================
# Supporting Types
# =============================================================================

class WarehouseStats:
    """Warehouse statistics object for GraphQL."""
    
    def __init__(self, stats_dict):
        self.total_warehouses = stats_dict.get('total_warehouses', 0)
        self.private_warehouses = stats_dict.get('private_warehouses', 0)
        self.public_warehouses = stats_dict.get('public_warehouses', 0)
        self.click_and_collect_enabled = stats_dict.get('click_and_collect_enabled', 0)
        self.warehouses_with_capacity = stats_dict.get('warehouses_with_capacity', 0)
        self.warehouses_at_capacity = stats_dict.get('warehouses_at_capacity', 0)
        self.total_capacity = stats_dict.get('total_capacity', 0)
        self.used_capacity = stats_dict.get('used_capacity', 0)
        self.available_capacity = stats_dict.get('available_capacity', 0)

