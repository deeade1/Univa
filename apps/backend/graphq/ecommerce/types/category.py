# apps/backend/graphq/ecommerce/types/category.py

"""
GraphQL Types for Ecommerce Product Module
Compatible with graphene-django 3.x
"""

import graphene
from graphene import relay
from graphene_django_optimizer import OptimizedDjangoObjectType
from django.db import models

from ecommerce.models.category import Category, CategoryTranslation


# =============================================================================
# CATEGORY TRANSLATION NODE
# =============================================================================

class CategoryTranslationNode(OptimizedDjangoObjectType):
    """
    CategoryTranslation GraphQL Node.
    
    Represents localized category data with Relay support.
    """
    
    class Meta:
        model = CategoryTranslation
        fields = "__all__"
        interfaces = (relay.Node,)
        filter_fields = {
            'language_code': ['exact'],
            'name': ['exact', 'icontains', 'istartswith'],
            'slug': ['exact', 'icontains'],
            'category': ['exact'],
        }
        


# =============================================================================
# CATEGORY NODE
# =============================================================================

class CategoryNode(OptimizedDjangoObjectType):
    """
    Category GraphQL Node.
    
    Represents a product category with hierarchical tree structure.
    Uses MPTT for tree operations.
    """
    
    # Computed fields
    level = graphene.Int()
    has_children = graphene.Boolean()
    children_count = graphene.Int()
    
    # Self-referencing fields using lambdas for lazy evaluation
    # The lambda should return the class, not an instance
    children = graphene.List(lambda: CategoryNode)
    parent = graphene.Field(lambda: CategoryNode)
    descendants = graphene.List(lambda: CategoryNode)
    ancestors = graphene.List(lambda: CategoryNode)
    siblings = graphene.List(lambda: CategoryNode)
    
    class Meta:
        model = Category
        fields = "__all__"
        interfaces = (relay.Node,)
        filter_fields = {
            'name': ['exact', 'icontains', 'istartswith'],
            'slug': ['exact', 'icontains'],
            'parent': ['exact', 'isnull'],
            'level': ['exact', 'gte', 'lte'],
        }
    
    def resolve_level(self, info):
        """Get the tree level of the category."""
        return self.level if hasattr(self, 'level') else None
    
    def resolve_has_children(self, info):
        """Check if category has children."""
        return self.children.exists()
    
    def resolve_children_count(self, info):
        """Get count of direct children."""
        return self.children.count()
    
    def resolve_children(self, info, **kwargs):
        """Get child categories."""
        return self.children.all()
    
    def resolve_parent(self, info):
        """Get parent category."""
        return self.parent
    
    def resolve_descendants(self, info):
        """Get all descendants of this category."""
        return self.get_descendants()
    
    def resolve_ancestors(self, info):
        """Get all ancestors of this category."""
        return self.get_ancestors()
    
    def resolve_siblings(self, info):
        """Get sibling categories."""
        return Category.objects.filter(
            parent=self.parent
        ).exclude(pk=self.pk)
    
    def resolve_translations(self, info, **kwargs):
        """Get translations."""
        return self.translations.all()


# =============================================================================
# CATEGORY TREE NODE (Extended - for full tree display)
# =============================================================================

class CategoryTreeNode(CategoryNode):
    """
    Extended Category Node with full tree data.
    
    Use this for hierarchical displays where you need
    the complete tree structure.
    """
    descendants = graphene.List(lambda: CategoryTreeNode)
    children = graphene.List(lambda: CategoryTreeNode)
    
    class Meta:
        model = Category
        fields = "__all__"
        interfaces = (relay.Node,)
    
    def resolve_descendants(self, info):
        """Get all descendants as tree nodes."""
        return Category.objects.filter(
            tree_id=self.tree_id,
            lft__gt=self.lft,
            rght__lt=self.rght
        ).order_by('lft')
    
    def resolve_children(self, info):
        """Get direct children as tree nodes."""
        return self.children.all().order_by('lft')




