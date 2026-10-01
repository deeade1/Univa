import graphene
from graphene import Node
from graphene_django.filter import DjangoFilterConnectionField
from graphq.ecommerce.types.attribute import ( 
    AttributeNode,
    AttributeValueNode,
    AttributeProductNode,
    AttributeVariantNode,
    AssignedProductAttributeValueNode,
    AssignedVariantAttributeValueNode,
    AssignedVariantAttributeNode
)
# =============================================================================
# Schema Registration
# =============================================================================

# In your schema.py, you would register these nodes:
#
class AttributeQuery(graphene.ObjectType):
    # Single Node queries
    attribute = Node.Field(AttributeNode)
    attribute_value = Node.Field(AttributeValueNode)
    attribute_product = Node.Field(AttributeProductNode)
    attribute_variant = Node.Field(AttributeVariantNode)
    assigned_product_attribute_value = Node.Field(AssignedProductAttributeValueNode)
    assigned_variant_attribute_value  = Node.Field(AssignedVariantAttributeValueNode)
    assigned_variant_attribute = Node.Field(AssignedVariantAttributeNode)
    #  All Node queries
    all_attributes = DjangoFilterConnectionField(AttributeNode)
    all_attribute_values = DjangoFilterConnectionField(AttributeValueNode)
    all_attribute_product = DjangoFilterConnectionField(AttributeProductNode)
    all_attribute_variant = DjangoFilterConnectionField(AttributeVariantNode)
    all_assigned_product_attribute_value = DjangoFilterConnectionField(AssignedProductAttributeValueNode)
    all_assigned_variant_attribute_value  = DjangoFilterConnectionField(AssignedVariantAttributeValueNode)
    all_assigned_variant_attribute = DjangoFilterConnectionField(AssignedVariantAttributeNode)
  
    