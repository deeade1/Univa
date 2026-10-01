# graphql/ecommerce/types/gotomarket.py

"""
GraphQL Nodes for GoToMarket - MarketItem, Purchase, PurchaseItem.
"""

from graphene import Node, String, Boolean, Field, List, DateTime, Int, Decimal, UUID, JSONString
from graphene_django_optimizer import OptimizedDjangoObjectType
from graphene_django import DjangoObjectType
from django.db.models import F
from ecommerce.models.gotomarket import (
    MarketItem,
    Purchase,
    PurchaseItem,
    PurchaseCounter,
)



class MarketItemNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Market Item with full product management.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    quantity_available = Int()
    is_in_stock = Boolean(description="Whether item is in stock")
    is_low_stock = Boolean(description="Whether stock is below threshold")
    is_out_of_stock = Boolean(description="Whether item is out of stock")
    category_display = String(description="Human-readable category display")
    subcategory_display = String(description="Human-readable subcategory display")
    unit_display = String(description="Human-readable unit display")
    price_display = String(description="Formatted price")
    stock_status = String(description="Stock status (in_stock, low_stock, out_of_stock)")
    available_quantity = Int(description="Available quantity (on hand - committed)")
    
    
    class Meta:
        model = MarketItem
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # String fields
            'name': ['exact', 'icontains', 'istartswith'],
            'description': ['exact', 'icontains'],
            'category': ['exact'],
            'subcategory': ['exact'],
            'unit': ['exact'],
            'supplier': ['exact', 'icontains'],
            'supplier_contact': ['exact', 'icontains'],
            'origin_region': ['exact', 'icontains'],
            
            # Numeric fields
            'price_per_unit': ['exact', 'gte', 'lte'],
            'stock': ['exact', 'gte', 'lte'],
            'quantity_on_hand': ['exact', 'gte', 'lte'],
            'quantity_committed': ['exact', 'gte', 'lte'],
            'restock_threshold': ['exact', 'gte', 'lte'],
            'lead_time_days': ['exact', 'gte', 'lte'],
            
            # Boolean fields
            'is_available': ['exact'],
            'is_featured': ['exact'],
            'is_bestseller': ['exact'],
            'is_seasonal': ['exact'],
            'is_organic': ['exact'],
            'is_locally_sourced': ['exact'],
            
            # Date fields
            'season_start': ['exact', 'gte', 'lte', 'isnull'],
            'season_end': ['exact', 'gte', 'lte', 'isnull'],
            'created_at': ['exact', 'gte', 'lte'],
            'updated_at': ['exact', 'gte', 'lte'],
            
            # Foreign keys
            'created_by': ['exact'],
        }
       
    
    # ============================================================
    # Resolvers - Calculated Properties
    # ============================================================
    
    def resolve_is_in_stock(self, info):
        """Resolve whether item is in stock."""
        return self.is_in_stock
    
    def resolve_is_low_stock(self, info):
        """Resolve whether stock is below threshold."""
        return self.is_low_stock
    
    def resolve_is_out_of_stock(self, info):
        """Resolve whether item is out of stock."""
        return self.is_out_of_stock
    
    def resolve_category_display(self, info):
        """Resolve human-readable category display."""
        return self.get_category_display() if hasattr(self, 'get_category_display') else self.category
    
    def resolve_subcategory_display(self, info):
        """Resolve human-readable subcategory display."""
        if self.subcategory:
            return dict(MarketItem.ALL_SUBCATEGORIES).get(self.subcategory, self.subcategory)
        return None
    
    def resolve_unit_display(self, info):
        """Resolve human-readable unit display."""
        if self.unit:
            return dict(MarketItem.UNIT_CHOICES).get(self.unit, self.unit)
        return None
    
    def resolve_price_display(self, info):
        """Resolve formatted price."""
        return f"₦{self.price_per_unit:,.2f} per {self.unit_display or 'unit'}"
    
    def resolve_stock_status(self, info):
        """Resolve stock status (in_stock, low_stock, out_of_stock)."""
        if self.is_out_of_stock:
            return "out_of_stock"
        if self.is_low_stock:
            return "low_stock"
        if self.is_in_stock:
            return "in_stock"
        return "unknown"
    
    def resolve_quantity_available(self, info):
        """Resolve quantity_available from property."""
        return self.quantity_available
    
    @classmethod
    def get_queryset(cls, queryset, info):
        """Optimize queryset by annotating if needed."""
        return queryset.annotate(
            quantity_available=F('quantity_on_hand') - F('quantity_committed')
        )
    # ============================================================
    # Resolvers - Nested Fields
    # ============================================================
    
    def resolve_created_by_details(self, info):
        """Resolve user who created this item."""
        return self.created_by
    
    def resolve_purchase_items(self, info):
        """Resolve purchase items for this market item."""
        return self.purchase_items.all()


class PurchaseItemNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Purchase Item.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    line_total_display = String(description="Formatted line total")
    unit_price_display = String(description="Formatted unit price")
    
    class Meta:
        model = PurchaseItem
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = { 
            # Foreign keys
            'purchase': ['exact'],
            'market_item': ['exact'],
            
            # String fields
            'product_name': ['exact', 'icontains'],
            
            # Numeric fields
            'unit_price': ['exact', 'gte', 'lte'],
            'quantity': ['exact', 'gte', 'lte'],
            'line_total': ['exact', 'gte', 'lte'],
        }
    
    def resolve_line_total_display(self, info):
        """Resolve formatted line total."""
        return f"₦{self.line_total:,.2f}"
    
    def resolve_unit_price_display(self, info):
        """Resolve formatted unit price."""
        return f"₦{self.unit_price:,.2f}"
    
    


class PurchaseNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Purchase with full purchase management.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    status_display = String(description="Human-readable status display")
    subtotal_display = String(description="Formatted subtotal")
    vat_amount_display = String(description="Formatted VAT amount")
    discount_display = String(description="Formatted discount")
    total_display = String(description="Formatted total")
    item_count = Int(description="Number of items in purchase")
    total_quantity = Int(description="Total quantity of items")
    vat_rate_display = String(description="Formatted VAT rate")
    receipt_html = String(description="HTML receipt")
    receipt_text = String(description="Text receipt")
    
    
    class Meta:
        model = Purchase
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Foreign keys
            'user': ['exact'],
            'invoice': ['exact'],
            
            # String fields
            'purchase_number': ['exact', 'icontains'],
            'status': ['exact'],
            'delivery_address': ['exact', 'icontains'],
            'delivery_instructions': ['exact', 'icontains'],
            
            # Numeric fields
            'subtotal': ['exact', 'gte', 'lte'],
            'vat_rate': ['exact', 'gte', 'lte'],
            'vat_amount': ['exact', 'gte', 'lte'],
            'discount': ['exact', 'gte', 'lte'],
            'total': ['exact', 'gte', 'lte'],
            
            # Date fields
            'created_at': ['exact', 'gte', 'lte'],
            'updated_at': ['exact', 'gte', 'lte'],
            'delivery_date': ['exact', 'gte', 'lte', 'isnull'],
        }
    
    # ============================================================
    # Resolvers - Calculated Properties
    # ============================================================
    
    def resolve_status_display(self, info):
        """Resolve human-readable status display."""
        return dict(Purchase.PURCHASE_STATUS).get(self.status, self.status)
    
    def resolve_subtotal_display(self, info):
        """Resolve formatted subtotal."""
        return f"₦{self.subtotal:,.2f}"
    
    def resolve_vat_amount_display(self, info):
        """Resolve formatted VAT amount."""
        return f"₦{self.vat_amount:,.2f}"
    
    def resolve_discount_display(self, info):
        """Resolve formatted discount."""
        return f"₦{self.discount:,.2f}"
    
    def resolve_total_display(self, info):
        """Resolve formatted total."""
        return f"₦{self.total:,.2f}"
    
    def resolve_item_count(self, info):
        """Resolve number of items in purchase."""
        return self.items.count()
    
    def resolve_total_quantity(self, info):
        """Resolve total quantity of items."""
        return self.items.aggregate(total=models.Sum('quantity'))['total'] or 0
    
    def resolve_vat_rate_display(self, info):
        """Resolve formatted VAT rate."""
        return f"{float(self.vat_rate) * 100:.1f}%"
    
    def resolve_receipt_html(self, info):
        """Resolve HTML receipt."""
        return self.receipt_html
    
    def resolve_receipt_text(self, info):
        """Resolve text receipt."""
        return self.receipt_text
    
    # ============================================================
    # Resolvers - Nested Fields
    # ============================================================
    
    def resolve_user_details(self, info):
        """Resolve user who made the purchase."""
        return self.user
    
    def resolve_items(self, info):
        """Resolve purchase items."""
        return self.items.all()
    
    def resolve_invoice_details(self, info):
        """Resolve invoice details."""
        return self.invoice

class PurchaseCounterNode(DjangoObjectType):
    class Meta:
        model = Purchase
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Numeric fields
            'year': ['exact', 'gte', 'lte'],
            'counter': ['exact', 'gte', 'lte'],   
        }
    
