# apps/backend/ecommerce/mutations/category.py

"""
Category Mutations for Relay GraphQL API.
"""

import graphene


from graphql_relay import from_global_id
from graphene import relay
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.text import slugify

from ecommerce.models.category import Category, CategoryTranslation


from graphq.ecommerce.types.category import (
    CategoryNode, 
    CategoryTranslationNode,
    CategoryTreeNode
)


# =============================================================================
# Create Category Mutation
# =============================================================================

class CreateCategoryMutation(relay.ClientIDMutation):
    """Create a new category."""
    
    class Input:
        name = graphene.String(required=True)
        slug = graphene.String(required=False)
        description = graphene.JSONString(required=False)
        description_plaintext = graphene.String(required=False)
        background_image = graphene.String(required=False)
        background_image_alt = graphene.String(required=False)
        parent_id = graphene.ID(required=False)
        translations = graphene.String(required=False)

    
    category = graphene.Field(CategoryTreeNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, input):
        """
        Create a new category with optional translations.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: CategoryInput data
        
        Returns:
            CreateCategoryMutation instance
        """
        errors = {}
        data = {}
        
        # Extract input data
        name = input.get('name')
        slug = input.get('slug')
        description = input.get('description')
        description_plaintext = input.get('description_plaintext')
        background_image = input.get('background_image')
        background_image_alt = input.get('background_image_alt')
        parent_id = input.get('parent_id')
        translations_data = input.get('translations', [])
        
        # Validate required fields
        if not name:
            errors['name'] = ['This field is required.']
            return cls(success=False, errors=errors)
        
        # Auto-generate slug if not provided
        if not slug:
            slug = slugify(name)
        
        # Check slug uniqueness
        if Category.objects.filter(slug=slug).exists():
            errors['slug'] = ['Category with this slug already exists.']
            return cls(success=False, errors=errors)
        
        # Resolve parent if provided
        parent = None
        if parent_id:
            try: 
                parent = Category.objects.get(pk=from_global_id(parent_id)[1])
                if not parent:
                    errors['parent_id'] = ['Parent category not found.']
                    return cls(success=False, errors=errors)
            except Exception as e:
                errors['parent_id'] = [str(e)]
                return cls(success=False, errors=errors)
        
        try:
            # Create category
            category = Category.objects.create(
                name=name,
                slug=slug,
                description=description or {},
                description_plaintext=description_plaintext or '',
                background_image=background_image,
                background_image_alt=background_image_alt,
                parent=parent,
            )
            
            # Create translations
            for translation_data in translations_data:
                language_code = translation_data.get('language_code')
                trans_name = translation_data.get('name')
                trans_description = translation_data.get('description')
                trans_slug = translation_data.get('slug')
                
                # Auto-generate translation slug if not provided
                if not trans_slug and trans_name:
                    trans_slug = slugify(trans_name)
                
                # Validate required fields for translation
                if not language_code:
                    continue  # Skip invalid translation data
                
                CategoryTranslation.objects.create(
                    category=category,
                    language_code=language_code,
                    name=trans_name or name,
                    description=trans_description or description,
                    slug=trans_slug or slug,
                )
            
            # Return success response
            return cls(
                category=category,
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
# Update Category Mutation
# =============================================================================

class UpdateCategoryMutation(relay.ClientIDMutation):
    """Update an existing category."""
    
    class Input:
        language_code = graphene.String(required=True)
        name = graphene.String(required=False)
        description = graphene.JSONString(required=False)
        slug = graphene.String(required=False)
    
    category = graphene.Field(CategoryNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, input):
        """
        Update an existing category.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: UpdateCategoryInput data
        
        Returns:
            UpdateCategoryMutation instance
        """
        errors = {}
        data = {}
        
        # Extract input
        category_id = input.get('id')
        name = input.get('name')
        slug = input.get('slug')
        description = input.get('description')
        description_plaintext = input.get('description_plaintext')
        background_image = input.get('background_image')
        background_image_alt = input.get('background_image_alt')
        parent_id = input.get('parent_id')
        translations_data = input.get('translations', [])
        
        # Resolve category ID
        try:
            pk = from_global_id(category_id)[1]
            category = Category.objects.get(pk=pk)
        except Category.DoesNotExist:
            errors['id'] = ['Category not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Validate slug uniqueness (if changed)
        if slug and slug != category.slug:
            if Category.objects.filter(slug=slug).exclude(pk=pk).exists():
                errors['slug'] = ['Category with this slug already exists.']
                return cls(success=False, errors=errors)
        
        # Resolve parent if provided
        parent = None
        if parent_id:
            try:
                parent = graphene.Node.get_node_from_global_id(
                    info, parent_id, only_type=CategoryType
                )
                if not parent:
                    errors['parent_id'] = ['Parent category not found.']
                    return cls(success=False, errors=errors)
                
                # Prevent setting parent to itself or descendant
                if parent.pk == category.pk:
                    errors['parent_id'] = ['Cannot set category as its own parent.']
                    return cls(success=False, errors=errors)
                
                if category.get_descendants().filter(pk=parent.pk).exists():
                    errors['parent_id'] = ['Cannot set a descendant as parent.']
                    return cls(success=False, errors=errors)
                    
            except Exception as e:
                errors['parent_id'] = [str(e)]
                return cls(success=False, errors=errors)
        
        try:
            # Update category fields
            if name is not None:
                category.name = name
            if slug is not None:
                category.slug = slug
            if description is not None:
                category.description = description
            if description_plaintext is not None:
                category.description_plaintext = description_plaintext
            if background_image is not None:
                category.background_image = background_image
            if background_image_alt is not None:
                category.background_image_alt = background_image_alt
            if parent_id is not None:
                category.parent = parent
            
            category.save()
            
            # Update translations
            # Strategy: Replace all existing translations with the provided ones
            # This is simpler and avoids partial update complexities
            if translations_data is not None:
                # Delete existing translations if we're sending new ones
                if translations_data:
                    category.translations.all().delete()
                    
                    # Create new translations
                    for translation_data in translations_data:
                        language_code = translation_data.get('language_code')
                        trans_name = translation_data.get('name')
                        trans_description = translation_data.get('description')
                        trans_slug = translation_data.get('slug')
                        
                        if not language_code:
                            continue  # Skip invalid translation data
                        
                        # Auto-generate translation slug if not provided
                        if not trans_slug and trans_name:
                            trans_slug = slugify(trans_name)
                        
                        CategoryTranslation.objects.create(
                            category=category,
                            language_code=language_code,
                            name=trans_name or category.name,
                            description=trans_description or category.description,
                            slug=trans_slug or category.slug,
                        )
            
            # Return success response
            return cls(
                category=category,
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
# Delete Category Mutation
# =============================================================================

class DeleteCategoryMutation(relay.ClientIDMutation):
    """Delete a category."""
    
    class Input:
        id = graphene.ID(required=True)
        force_cascade = graphene.Boolean(
            required=False,
            default_value=False,
            description="If True, delete all child categories as well"
        )
    
    deleted_id = graphene.ID()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id, force_cascade=False):
        """
        Delete a category.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Category ID to delete
            force_cascade: Whether to delete child categories
        
        Returns:
            DeleteCategoryMutation instance
        """
        errors = {}
        
        # Resolve category ID
        try:
            pk = from_global_id(id)[1]
            category = Category.objects.get(pk=pk)
        except Category.DoesNotExist:
            errors['id'] = ['Category not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check for child categories
        children_count = category.children.count()
        if children_count > 0 and not force_cascade:
            errors['children'] = [
                f'Cannot delete category with {children_count} child categories. '
                'Use force_cascade=True to delete all children.'
            ]
            return cls(success=False, errors=errors)
        
        # Check for products using this category
        # Note: You'll need to import Product model dynamically or use a generic check
        # This prevents category deletion if products reference it
        try:
            from ..models.product import Product
            
            product_count = Product.objects.filter(
                category=category
            ).count()
            
            if product_count > 0:
                errors['products'] = [
                    f'Cannot delete category with {product_count} products. '
                    'Move or delete the products first.'
                ]
                return cls(success=False, errors=errors)
                
        except ImportError:
            # Product model might be in a different location
            # Skip product check if model is not available
            pass
        
        try:
            # Delete the category
            deleted_id = id
            category.delete()
            
            return cls(
                deleted_id=deleted_id,
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
# Move Category Mutation (Re-parent)
# =============================================================================

class MoveCategoryMutation(relay.ClientIDMutation):
    """Move a category to a new parent."""
    
    class Input:
        id = graphene.ID(required=True)
        new_parent_id = graphene.ID(required=True)
    
    category = graphene.Field(CategoryNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id, new_parent_id):
        """
        Move a category to a new parent.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Category ID to move
            new_parent_id: New parent category ID
        
        Returns:
            MoveCategoryMutation instance
        """
        errors = {}
        
        # Resolve category
        try:
            pk = from_global_id(id)[1]
            category = Category.objects.get(pk=pk)
        except Category.DoesNotExist:
            errors['id'] = ['Category not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Resolve new parent
        try:
            new_parent = Category.objects.get(pk=from_global_id(new_parent_id)[1])
            if not new_parent:
                errors['new_parent_id'] = ['Parent category not found.']
                return cls(success=False, errors=errors)
        except Exception as e:
            errors['new_parent_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Validate move
        if new_parent.pk == category.pk:
            errors['new_parent_id'] = ['Cannot set category as its own parent.']
            return cls(success=False, errors=errors)
        
        if category.get_descendants().filter(pk=new_parent.pk).exists():
            errors['new_parent_id'] = ['Cannot set a descendant as parent.']
            return cls(success=False, errors=errors)
        
        try:
            # Move the category
            category.parent = new_parent
            category.save()
            
            return cls(
                category=category,
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
# Batch Operations
# =============================================================================

class BulkDeleteCategoriesMutation(graphene.relay.ClientIDMutation):
    """Bulk delete multiple categories."""
    
    class Input:
        ids = graphene.List(graphene.ID, required=True)
        force_cascade = graphene.Boolean(default_value=False)
    
    deleted_ids = graphene.List(graphene.ID)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, ids, force_cascade=False):
        """
        Delete multiple categories in bulk.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            ids: List of category IDs to delete
            force_cascade: Whether to delete child categories
        
        Returns:
            BulkDeleteCategoriesMutation instance
        """
        errors = {}
        deleted_ids = []
        failed_ids = []
        
        for category_id in ids:
            try:
                pk = from_global_id(category_id)[1]
                category = Category.objects.get(pk=pk)
                
                # Check for children
                if category.children.exists() and not force_cascade:
                    failed_ids.append(category_id)
                    errors[category_id] = ['Category has children. Use force_cascade=True.']
                    continue
                
                # Delete the category
                deleted_ids.append(category_id)
                category.delete()
                
            except Category.DoesNotExist:
                failed_ids.append(category_id)
                errors[category_id] = ['Category not found.']
            except Exception as e:
                failed_ids.append(category_id)
                errors[category_id] = [str(e)]
        
        success = len(failed_ids) == 0
        
        return cls(
            deleted_ids=deleted_ids,
            success=success,
            errors=errors if not success else {}
        )


# =============================================================================
# Export Mutations
# =============================================================================

class CategoryMutations(graphene.ObjectType):
    """All category mutations."""
    
    create_category = CreateCategoryMutation.Field()
    update_category = UpdateCategoryMutation.Field()
    delete_category = DeleteCategoryMutation.Field()
    move_category = MoveCategoryMutation.Field()
    bulk_delete_categories = BulkDeleteCategoriesMutation.Field()