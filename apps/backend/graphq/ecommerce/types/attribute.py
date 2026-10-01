# graphql/ecommerce/types/attribute.py

"""
GraphQL Nodes for Attribute, AttributeValue, and related assignment models.
"""

from graphene import Node, Float, Int, Boolean, String, Field, List, Decimal, DateTime, JSONString
from graphene_django_optimizer import OptimizedDjangoObjectType

from ecommerce.models.attribute import (
    Attribute,
    AttributeValue,
    AttributeProduct,
    AttributeVariant,
    AssignedProductAttributeValue,
    AssignedVariantAttributeValue,
    AssignedVariantAttribute,
)


class AttributeNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Attribute with full attribute configuration.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    type_display = String(description="Human-readable type display")
    input_type_display = String(description="Human-readable input type display")
    entity_type_display = String(description="Human-readable entity type display")
    unit_display = String(description="Human-readable unit display")
    has_values = Boolean(description="Whether attribute has values")
    value_count = Int(description="Number of values")
    usage_count = Int(description="Number of attribute usage across products")
    is_numeric = Boolean(description="Whether attribute is numeric type")
    is_required = Boolean(description="Whether value is required")
    is_filterable = Boolean(description="Whether attribute is filterable")
    
    
    class Meta:
        model = Attribute
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Primary key
            'id': ['exact'],
            
            # String fields
            'slug': ['exact', 'icontains', 'istartswith'],
            'name': ['exact', 'icontains', 'istartswith'],
            'description': ['exact', 'icontains'],
            'unit': ['exact', 'icontains'],
            
            # Choice fields
            'type': ['exact'],
            'input_type': ['exact'],
            'entity_type': ['exact'],
            
            # Boolean fields
            'value_required': ['exact'],
            'is_variant_only': ['exact'],
            'visible_in_storefront': ['exact'],
            'filterable_in_storefront': ['exact'],
            'filterable_in_dashboard': ['exact'],
            'available_in_grid': ['exact'],
            'is_active': ['exact'],
            
            # Numeric fields
            'min_value': ['exact', 'gte', 'lte', 'isnull'],
            'max_value': ['exact', 'gte', 'lte', 'isnull'],
            'max_length': ['exact', 'gte', 'lte', 'isnull'],
            'storefront_search_position': ['exact', 'gte', 'lte'],
            
            # Date fields
            'created_at': ['exact', 'gte', 'lte'],
            'updated_at': ['exact', 'gte', 'lte'],
            
            # Foreign keys
            'created_by': ['exact'],
            'created_by__email': ['exact', 'icontains'],
        }
        
    
    # ============================================================
    # Resolvers - Calculated Properties
    # ============================================================
    
    def resolve_type_display(self, info):
        """Resolve human-readable type display."""
        return dict(AttributeType.CHOICES).get(self.type, self.type)
    
    def resolve_input_type_display(self, info):
        """Resolve human-readable input type display."""
        return dict(AttributeInputType.CHOICES).get(self.input_type, self.input_type)
    
    def resolve_entity_type_display(self, info):
        """Resolve human-readable entity type display."""
        if self.entity_type:
            return dict(AttributeEntityType.CHOICES).get(self.entity_type, self.entity_type)
        return None
    
    def resolve_unit_display(self, info):
        """Resolve human-readable unit display."""
        if self.unit and hasattr(MeasurementUnits, 'CHOICES'):
            return dict(MeasurementUnits.CHOICES).get(self.unit, self.unit)
        return self.unit
    
    def resolve_has_values(self, info):
        """Resolve whether attribute has values."""
        return self.has_values()
    
    def resolve_value_count(self, info):
        """Resolve number of values."""
        return self.get_value_count()
    
    def resolve_usage_count(self, info):
        """Resolve number of attribute usage across products."""
        return self.get_usage_count()
    
    def resolve_is_numeric(self, info):
        """Resolve whether attribute is numeric type."""
        return self.input_type == AttributeInputType.NUMERIC
    
    def resolve_is_required(self, info):
        """Resolve whether value is required."""
        return self.value_required
    
    def resolve_is_filterable(self, info):
        """Resolve whether attribute is filterable."""
        return self.filterable_in_storefront or self.filterable_in_dashboard
    
    # ============================================================
    # Resolvers - Nested Fields
    # ============================================================
    
    def resolve_created_by_details(self, info):
        """Resolve user who created this attribute."""
        return self.created_by
    
    def resolve_values(self, info):
        """Resolve attribute values."""
        return self.values.all().order_by('sort_order', 'name')
    
    def resolve_product_types(self, info):
        """Resolve product types this attribute belongs to."""
        return self.product_types.all()
    
    def resolve_variant_types(self, info):
        """Resolve variant types this attribute belongs to."""
        return self.product_variant_types.all()

class AttributeValueNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Attribute Value with full value configuration.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    value_type = String(description="Type of value (based on attribute input type)")
    display_value = String(description="Display-friendly value")
    is_boolean = Boolean(description="Whether value is boolean")
    is_file = Boolean(description="Whether value is file")
    is_reference = Boolean(description="Whether value is reference")
    is_rich_text = Boolean(description="Whether value is rich text")
    
    class Meta:
        model = AttributeValue
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # String fields
            'name': ['exact', 'icontains', 'istartswith'],
            'slug': ['exact', 'icontains', 'istartswith'],
            'value': ['exact', 'icontains'],
            'file_url': ['exact', 'icontains'],
            'content_type': ['exact', 'icontains'],
            
            # Boolean fields
            'boolean': ['exact'],
            'is_active': ['exact'],
            
            # Numeric fields
            'sort_order': ['exact', 'gte', 'lte'],
            
            # Date fields
            'date_time': ['exact', 'gte', 'lte', 'isnull'],
            'created_at': ['exact', 'gte', 'lte'],
            'updated_at': ['exact', 'gte', 'lte'],
            
            # Foreign keys
            'attribute': ['exact'],
            'reference_product': ['exact'],
            'reference_variant': ['exact'],
        }
        
    
    # ============================================================
    # Resolvers - Calculated Properties
    # ============================================================
    
    def resolve_value_type(self, info):
        """Resolve type of value (based on attribute input type)."""
        if self.attribute:
            return self.attribute.input_type
        return None
    
    def resolve_display_value(self, info):
        """Resolve display-friendly value."""
        if self.attribute:
            if self.attribute.input_type == AttributeInputType.BOOLEAN:
                return "Yes" if self.boolean else "No"
            elif self.attribute.input_type == AttributeInputType.DATETIME:
                return self.date_time.strftime("%Y-%m-%d %H:%M") if self.date_time else None
            elif self.attribute.input_type == AttributeInputType.FILE:
                return self.file_url
            elif self.attribute.input_type == AttributeInputType.REFERENCE:
                if self.reference_product:
                    return str(self.reference_product)
                if self.reference_variant:
                    return str(self.reference_variant)
            elif self.attribute.input_type == AttributeInputType.RICH_TEXT:
                return self.plain_text or "Rich content"
        return self.value or self.name
    
    def resolve_is_boolean(self, info):
        """Resolve whether value is boolean."""
        return self.attribute and self.attribute.input_type == AttributeInputType.BOOLEAN
    
    def resolve_is_file(self, info):
        """Resolve whether value is file."""
        return self.attribute and self.attribute.input_type == AttributeInputType.FILE
    
    def resolve_is_reference(self, info):
        """Resolve whether value is reference."""
        return self.attribute and self.attribute.input_type == AttributeInputType.REFERENCE
    
    def resolve_is_rich_text(self, info):
        """Resolve whether value is rich text."""
        return self.attribute and self.attribute.input_type == AttributeInputType.RICH_TEXT
    
    # ============================================================
    # Resolvers - Nested Fields
    # ============================================================
    
    def resolve_attribute_details(self, info):
        """Resolve parent attribute."""
        return self.attribute
    
    def resolve_reference_product_details(self, info):
        """Resolve referenced product."""
        return self.reference_product
    
    def resolve_reference_variant_details(self, info):
        """Resolve referenced variant."""
        return self.reference_variant
    
    def resolve_product_assignments(self, info):
        """Resolve product assignments."""
        return self.productvalueassignment.all()
    
    def resolve_variant_assignments(self, info):
        """Resolve variant assignments."""
        return self.variantvalueassignment.all()

class AttributeProductNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for AttributeProduct (ProductType -> Attribute relationship).
    """

    class Meta:
        model = AttributeProduct
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            'attribute': ['exact'],
            'product_type': ['exact'],
            'sort_order': ['exact', 'gte', 'lte'],
        }
        
    
    def resolve_attribute_details(self, info):
        """Resolve attribute details."""
        return self.attribute
    
    def resolve_product_type_details(self, info):
        """Resolve product type details."""
        return self.product_type

class AttributeVariantNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for AttributeVariant (ProductType -> Variant Attribute relationship).
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    is_selection_attribute = Boolean(description="Whether this is used for variant selection")
    
  
    class Meta:
        model = AttributeVariant
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            'attribute': ['exact'],
            'product_type': ['exact'],
            'variant_selection': ['exact'],
            'sort_order': ['exact', 'gte', 'lte'],
        }
        
    
    def resolve_is_selection_attribute(self, info):
        """Resolve whether this is used for variant selection."""
        return self.variant_selection
    
    def resolve_attribute_details(self, info):
        """Resolve attribute details."""
        return self.attribute
    
    def resolve_product_type_details(self, info):
        """Resolve product type details."""
        return self.product_type


class AssignedProductAttributeValueNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for AssignedProductAttributeValue (Product -> Attribute Value assignment).
    """
    
    
    class Meta:
        model = AssignedProductAttributeValue
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            'value': ['exact'],
            'product': ['exact'],
        }
        
    
    def resolve_value_details(self, info):
        """Resolve attribute value details."""
        return self.value
    
    def resolve_product_details(self, info):
        """Resolve product details."""
        return self.product

class AssignedVariantAttributeValueNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for AssignedVariantAttributeValue (Variant -> Attribute Value assignment).
    """

    class Meta:
        model = AssignedVariantAttributeValue
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            'value': ['exact'],
            'assignment': ['exact'],
            'sort_order': ['exact', 'gte', 'lte'],
        }
       
    
    


class AssignedVariantAttributeNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for AssignedVariantAttribute (Variant -> Attribute assignment).
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    attribute_name = String(description="Name of the attribute")
    attribute_slug = String(description="Slug of the attribute")
    value_count = Int(description="Number of assigned values")
    
    class Meta:
        model = AssignedVariantAttribute
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            'variant': ['exact'],
            'assignment': ['exact'],
        }
        
    
    def resolve_attribute_name(self, info):
        """Resolve name of the attribute."""
        return self.assignment.attribute.name if self.assignment else None
    
    def resolve_attribute_slug(self, info):
        """Resolve slug of the attribute."""
        return self.assignment.attribute.slug if self.assignment else None
    
    def resolve_value_count(self, info):
        """Resolve number of assigned values."""
        return self.values.count()
    
    def resolve_variant_details(self, info):
        """Resolve variant details."""
        return self.variant
    
    def resolve_assignment_details(self, info):
        """Resolve attribute variant assignment details."""
        return self.assignment
    
    def resolve_values_details(self, info):
        """Resolve assigned values."""
        return self.values.all()
    
    def resolve_value_assignments(self, info):
        """Resolve value assignments."""
        return self.variantvalueassignment.all()

