# apps/backend/ecommerce/models/attribute.py
# Complete rewritten attribute system - scalable and optimized

import logging
from typing import TYPE_CHECKING, TypeVar, Union

from django.contrib.postgres.indexes import BTreeIndex, GinIndex
from django.db import models, transaction
from django.db.models import (
    Case, Exists, F, Max, OrderBy, OuterRef, Q, Value, When, Count
)
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError

from core.models.metadata import ModelWithExternalReference, ModelWithMetadata
from core.models.sortable import SortableModel
from core.units import MeasurementUnits
from accounts.models.user import User
from ecommerce.models.product import (
    Product, ProductType, ProductVariant)

from .constants import (
    AttributeType,
    AttributeInputType,
    AttributeEntityType
)
logger = logging.getLogger(__name__)
T = TypeVar("T", bound=models.Model)



# =============================================================================
# QUERYSETS & MANAGERS
# =============================================================================

class BaseAttributeQuerySet(models.QuerySet[T]):
    """Base queryset for attribute models."""
    
    def get_public_attributes(self):
        return self.filter(visible_in_storefront=True)
    
    def get_visible_to_user(self, requestor: Union["User", None]):
        return self.get_public_attributes()
    
    def active(self):
        return self.filter(is_active=True)
    
    def by_type(self, attribute_type):
        return self.filter(type=attribute_type)
    
    def by_input_type(self, input_type):
        return self.filter(input_type=input_type)
    
    def search(self, query):
        if not query:
            return self
        return self.filter(
            Q(name__icontains=query) |
            Q(slug__icontains=query) |
            Q(external_reference__icontains=query)
        )


class AttributeQuerySet(BaseAttributeQuerySet[T]):
    """Custom queryset for Attribute model."""
    
    def get_unassigned_product_type_attributes(self, product_type_pk: int):
        return self.product_type_attributes().exclude(
            Q(attributeproduct__product_type_id=product_type_pk) |
            Q(attributevariant__product_type_id=product_type_pk)
        )
    
    def get_assigned_product_type_attributes(self, product_type_pk: int):
        return self.product_type_attributes().filter(
            Q(attributeproduct__product_type_id=product_type_pk) |
            Q(attributevariant__product_type_id=product_type_pk)
        )
    
    def product_type_attributes(self):
        return self.filter(type=AttributeType.PRODUCT_TYPE)
    
    def variant_attributes(self):
        return self.filter(type=AttributeType.VARIANT)
    
    def product_attributes(self):
        return self.filter(type=AttributeType.PRODUCT)
    
    def with_values_count(self):
        return self.annotate(values_count=Count('values'))
    
    def with_product_count(self):
        return self.annotate(product_count=Count('attributeproduct__product_type__product'))
    
    def _get_sorted_m2m_field(self, m2m_field_name: str, asc: bool):
        sort_order_field = F(f"{m2m_field_name}__sort_order")
        id_field = F(f"{m2m_field_name}__id")
        if asc:
            sort_method = sort_order_field.asc(nulls_last=True)
            id_sort: Union[OrderBy, F] = id_field
        else:
            sort_method = sort_order_field.desc(nulls_first=True)
            id_sort = id_field.desc()
        return self.order_by(sort_method, id_sort)
    
    def product_attributes_sorted(self, asc=True):
        return self._get_sorted_m2m_field("attributeproduct", asc)
    
    def variant_attributes_sorted(self, asc=True):
        return self._get_sorted_m2m_field("attributevariant", asc)


class AssociatedAttributeQuerySet(BaseAttributeQuerySet[T]):
    """Queryset for associated attributes."""
    
    def get_public_attributes(self):
        attributes = Attribute.objects.filter(visible_in_storefront=True)
        return self.filter(Exists(attributes.filter(id=OuterRef("attribute_id"))))


class AttributeManager(models.Manager):
    """Custom manager for Attribute model."""
    
    def get_queryset(self):
        return AttributeQuerySet(self.model, using=self._db)
    
    def public(self):
        return self.get_queryset().get_public_attributes()
    
    def active(self):
        return self.get_queryset().active()
    
    def by_type(self, attribute_type):
        return self.get_queryset().by_type(attribute_type)
    
    def search(self, query):
        return self.get_queryset().search(query)


class AssociatedAttributeManager(models.Manager):
    """Manager for associated attributes."""
    
    def get_queryset(self):
        return AssociatedAttributeQuerySet(self.model, using=self._db)
    
    def public(self):
        return self.get_queryset().get_public_attributes()


class AttributeValueQuerySet(models.QuerySet):
    """Queryset for AttributeValue."""
    
    def active(self):
        return self.filter(is_active=True)
    
    def by_attribute(self, attribute_id):
        return self.filter(attribute_id=attribute_id)
    
    def search(self, query):
        if not query:
            return self
        return self.filter(
            Q(name__icontains=query) |
            Q(slug__icontains=query) |
            Q(value__icontains=query)
        )
    
    def with_usage_count(self):
        return self.annotate(usage_count=Count('productvalueassignment'))


class AttributeValueManager(models.Manager):
    """Custom manager for AttributeValue."""
    
    def get_queryset(self):
        return AttributeValueQuerySet(self.model, using=self._db)
    
    def active(self):
        return self.get_queryset().active()
    
    def by_attribute(self, attribute_id):
        return self.get_queryset().by_attribute(attribute_id)
    
    def search(self, query):
        return self.get_queryset().search(query)
    
    def _prepare_query_for_bulk_operation(self, objects_data):
        query_params = Q()
        for obj in objects_data:
            defaults = obj.pop("defaults")
            query_params |= Q(**obj)
            obj["defaults"] = defaults
        return self.filter(query_params)
    
    def _is_correct_record(self, record, obj):
        return all(
            getattr(record, field_name) == field_value
            for field_name, field_value in obj.items()
            if field_name != "defaults"
        )
    
    def bulk_get_or_create(self, objects_data):
        """Bulk get or create attribute values."""
        results = []
        objects_not_in_db = []
        objects_enumerated = list(enumerate(objects_data))
        query = self._prepare_query_for_bulk_operation(objects_data)
        
        for record in query.iterator():
            for index, obj in objects_enumerated[:]:
                if self._is_correct_record(record, obj):
                    results.append((index, record))
                    objects_enumerated.remove((index, obj))
                    break
        
        self._add_new_records(objects_enumerated, objects_not_in_db, results)
        results.sort()
        results = [obj for index, obj in results]
        
        if objects_not_in_db:
            self.bulk_create(objects_not_in_db, ignore_conflicts=True)
        
        return results
    
    def _add_new_records(self, objects_enumerated, objects_not_in_db, results):
        for index, obj in objects_enumerated:
            defaults = obj.pop("defaults")
            obj.update(defaults)
            record = self.model(**obj)
            objects_not_in_db.append(record)
            results.append((index, record))


# =============================================================================
# CORE MODELS
# =============================================================================

class Attribute(ModelWithMetadata, ModelWithExternalReference):
    """
    Attribute definition model.
    
    Attributes define the characteristics of products, product types, and variants.
    """
    
    # Basic Info
    slug = models.SlugField(
        max_length=250,
        unique=True,
        allow_unicode=True,
        db_index=True,
        help_text="Unique identifier for the attribute"
    )
    name = models.CharField(
        max_length=255,
        help_text="Display name of the attribute"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of the attribute"
    )
    
    # Type Configuration
    type = models.CharField(
        max_length=50,
        choices=AttributeType.CHOICES,
        default=AttributeType.PRODUCT,
        db_index=True,
        help_text="Type of attribute"
    )
    input_type = models.CharField(
        max_length=50,
        choices=AttributeInputType.CHOICES,
        default=AttributeInputType.DROPDOWN,
        db_index=True,
        help_text="Input type for the attribute"
    )
    entity_type = models.CharField(
        max_length=50,
        choices=AttributeEntityType.CHOICES,
        blank=True,
        null=True,
        help_text="Entity type for reference attributes"
    )
    
    # Unit
    unit = models.CharField(
        max_length=100,
        choices=MeasurementUnits.CHOICES if hasattr(MeasurementUnits, 'CHOICES') else [],
        blank=True,
        null=True,
        help_text="Unit of measurement for numeric attributes"
    )
    
    # Validation
    value_required = models.BooleanField(
        default=False,
        help_text="Whether a value is required"
    )
    min_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Minimum value for numeric attributes"
    )
    max_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Maximum value for numeric attributes"
    )
    max_length = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum length for text attributes"
    )
    
    # Display Settings
    is_variant_only = models.BooleanField(
        default=False,
        help_text="Whether this attribute is only for variants"
    )
    visible_in_storefront = models.BooleanField(
        default=True,
        help_text="Whether to show in storefront"
    )
    filterable_in_storefront = models.BooleanField(
        default=False,
        help_text="Whether to allow filtering in storefront"
    )
    filterable_in_dashboard = models.BooleanField(
        default=False,
        help_text="Whether to allow filtering in dashboard"
    )
    storefront_search_position = models.IntegerField(
        default=0,
        help_text="Position in storefront search"
    )
    available_in_grid = models.BooleanField(
        default=False,
        help_text="Whether to show in product grid"
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this attribute is active"
    )
    
    # Relationships
    product_types = models.ManyToManyField(
        "ecommerce.ProductType",
        blank=True,
        related_name="product_attributes",
        through="ecommerce.AttributeProduct",
        help_text="Product types this attribute belongs to"
    )
    product_variant_types = models.ManyToManyField(
        "ecommerce.ProductType",
        blank=True,
        related_name="variant_attributes",
        through="ecommerce.AttributeVariant",
        help_text="Variant types this attribute belongs to"
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_attributes"
    )
    
    objects = AttributeManager()

    class Meta:
        ordering = ("storefront_search_position", "slug")
        indexes = [
            BTreeIndex(fields=["type"], name="attr_type_idx"),
            BTreeIndex(fields=["input_type"], name="attr_input_type_idx"),
            BTreeIndex(fields=["is_active"], name="attr_active_idx"),
            BTreeIndex(fields=["created_at"], name="attr_created_idx"),
            GinIndex(
                name="attr_search_gin",
                fields=["slug", "name", "description"],
                opclasses=["gin_trgm_ops"] * 3,
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(min_value__isnull=True) | Q(min_value__gte=0),
                name="attr_min_value_positive"
            ),
            models.CheckConstraint(
                condition=Q(max_value__isnull=True) | Q(max_value__gte=0),
                name="attr_max_value_positive"
            ),
            models.CheckConstraint(
                condition=(
                    Q(min_value__isnull=True) |
                    Q(max_value__isnull=True) |
                    Q(min_value__lte=F("max_value"))
                ),
                name="attr_min_less_than_max"
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def clean(self):
        """Validate attribute data."""
        # Validate numeric range
        if self.input_type == AttributeInputType.NUMERIC:
            if self.min_value is not None and self.max_value is not None:
                if self.min_value > self.max_value:
                    raise ValidationError({
                        "min_value": "Minimum value cannot be greater than maximum value."
                    })
        
        # Validate rich text input
        if self.input_type == AttributeInputType.RICH_TEXT:
            if self.input_type not in AttributeInputType.RICH_TEXT_TYPES:
                raise ValidationError({
                    "input_type": "Rich text input type is not supported for this attribute."
                })
        
        # Validate reference attributes
        if self.input_type == AttributeInputType.REFERENCE:
            if not self.entity_type:
                raise ValidationError({
                    "entity_type": "Entity type is required for reference attributes."
                })
        
        # Validate file attributes
        if self.input_type == AttributeInputType.FILE:
            if self.entity_type not in [AttributeEntityType.PRODUCT, AttributeEntityType.PRODUCT_VARIANT]:
                raise ValidationError({
                    "entity_type": "Invalid entity type for file attribute."
                })

    def save(self, *args, **kwargs):
        """Save attribute with validation."""
        self.full_clean()
        super().save(*args, **kwargs)

    def has_values(self) -> bool:
        """Check if attribute has values."""
        return self.values.exists()
    
    def get_value_count(self) -> int:
        """Get count of values."""
        return self.values.count()
    
    def get_usage_count(self) -> int:
        """Get count of attribute usage across products."""
        return self.values.aggregate(
            total=Count('productvalueassignment')
        )['total'] or 0


class AttributeValue(ModelWithExternalReference):
    """
    Attribute value model.
    
    Values for attributes (e.g., "Red", "Large", "10kg").
    """
    
    # Basic Info
    name = models.CharField(
        max_length=250,
        help_text="Display name of the value"
    )
    slug = models.SlugField(
        max_length=255,
        allow_unicode=True,
        help_text="Unique slug for the value"
    )
    value = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Actual value (for non-dropdown attributes)"
    )
    
    # Type-specific fields
    file_url = models.URLField(
        null=True,
        blank=True,
        help_text="URL for file attributes"
    )
    content_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Content type for file attributes"
    )
    rich_text = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        help_text="Rich text content"
    )
    plain_text = models.TextField(
        blank=True,
        null=True,
        help_text="Plain text version of rich text"
    )
    boolean = models.BooleanField(
        blank=True,
        null=True,
        help_text="Boolean value"
    )
    date_time = models.DateTimeField(
        blank=True,
        null=True,
        help_text="DateTime value"
    )
    
    # Reference fields
    reference_product = models.ForeignKey(
        "ecommerce.Product",
        related_name="attribute_references",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Product reference"
    )
    reference_variant = models.ForeignKey(
        "ecommerce.ProductVariant",
        related_name="attribute_references",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Variant reference"
    )
    
    # Relationships
    attribute = models.ForeignKey(
        Attribute,
        related_name="values",
        on_delete=models.CASCADE,
        db_index=True,
        help_text="Parent attribute"
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this value is active"
    )
    
    # Ordering
    sort_order = models.IntegerField(
        editable=False,
        db_index=True,
        null=True,
        help_text="Sort order within attribute"
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = AttributeValueManager()

    class Meta:
        ordering = ("sort_order", "pk", "name")
        constraints = [
            models.UniqueConstraint(
                fields=["attribute", "slug"],
                name="unique_attribute_slug"
            ),
        ]
        indexes = [
            BTreeIndex(fields=["attribute", "sort_order"], name="attrval_attr_sort_idx"),
            BTreeIndex(fields=["is_active"], name="attrval_active_idx"),
            GinIndex(
                name="attrval_search_gin",
                fields=["name", "slug", "value"],
                opclasses=["gin_trgm_ops"] * 3,
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def clean(self):
        """Validate attribute value."""
        # Validate based on attribute input type
        if self.attribute.input_type == AttributeInputType.BOOLEAN:
            if self.boolean is None:
                raise ValidationError({
                    "boolean": "Boolean value is required for boolean attributes."
                })
        
        if self.attribute.input_type == AttributeInputType.FILE:
            if not self.file_url:
                raise ValidationError({
                    "file_url": "File URL is required for file attributes."
                })
        
        if self.attribute.input_type == AttributeInputType.REFERENCE:
            if not self.reference_product and not self.reference_variant:
                raise ValidationError({
                    "reference_product": "Product or variant reference is required."
                })
        
        # Validate date time
        if self.attribute.input_type == AttributeInputType.DATETIME:
            if not self.date_time:
                raise ValidationError({
                    "date_time": "DateTime is required for datetime attributes."
                })

    def save(self, *args, **kwargs):
        """Save attribute value with validation."""
        self.full_clean()
        super().save(*args, **kwargs)


# =============================================================================
# ASSIGNMENT MODELS
# =============================================================================

class BaseAssignedAttribute(models.Model):
    """Base abstract model for assigned attributes."""
    
    class Meta:
        abstract = True
    
    @property
    def attribute(self):
        return self.assignment.attribute


class AttributeProduct(SortableModel):
    """Through model for ProductType -> Attribute relationship."""
    
    attribute = models.ForeignKey(
        Attribute,
        related_name="attributeproduct",
        on_delete=models.CASCADE,
        help_text="Attribute"
    )
    product_type = models.ForeignKey(
        "ecommerce.ProductType",
        related_name="attributeproduct",
        on_delete=models.CASCADE,
        help_text="Product type"
    )
    sort_order = models.IntegerField(
        editable=False,
        db_index=True,
        null=True,
        help_text="Sort order"
    )
    
    objects = AssociatedAttributeManager()
    
    class Meta:
        ordering = ("product_type", "attribute__name")
        constraints = [
            models.UniqueConstraint(
                fields=["attribute", "product_type"],
                name="unique_attribute_product_type"
            ),
        ]
        indexes = [
            BTreeIndex(fields=["product_type"], name="attrprod_prodtype_idx"),
            BTreeIndex(fields=["attribute"], name="attrprod_attr_idx"),
        ]
    
    def __str__(self) -> str:
        return f"{self.product_type.name} - {self.attribute.name}"
    
    def get_ordering_queryset(self):
        return self.product_type.attributeproduct.all()


class AttributeVariant(SortableModel):
    """Through model for ProductType -> Variant Attribute relationship."""
    
    attribute = models.ForeignKey(
        Attribute,
        related_name="attributevariant",
        on_delete=models.CASCADE,
        help_text="Attribute"
    )
    product_type = models.ForeignKey(
        "ecommerce.ProductType",
        related_name="attributevariant",
        on_delete=models.CASCADE,
        help_text="Product type"
    )
    variant_selection = models.BooleanField(
        default=False,
        help_text="Whether this attribute is used for variant selection"
    )
    sort_order = models.IntegerField(
        editable=False,
        db_index=True,
        null=True,
        help_text="Sort order"
    )
    
    objects = AssociatedAttributeManager()
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["attribute", "product_type"],
                name="unique_attribute_variant_type"
            ),
        ]
        ordering = ("sort_order", "pk")
        indexes = [
            BTreeIndex(fields=["product_type"], name="attrvar_prodtype_idx"),
            BTreeIndex(fields=["attribute"], name="attrvar_attr_idx"),
            BTreeIndex(fields=["variant_selection"], name="attrvar_selection_idx"),
        ]
    
    def __str__(self) -> str:
        return f"{self.product_type.name} - {self.attribute.name}"
    
    def get_ordering_queryset(self):
        return self.product_type.attributevariant.all()


class AssignedProductAttributeValue(models.Model):
    """Assignment of attribute values to products."""
    
    value = models.ForeignKey(
        AttributeValue,
        on_delete=models.CASCADE,
        related_name="productvalueassignment",
        help_text="Attribute value"
    )
    product = models.ForeignKey(
        "ecommerce.Product",
        related_name="attributevalues",
        on_delete=models.CASCADE,
        help_text="Product"
    )
    
    class Meta:
        ordering = ("product", "value__sort_order", "value__name")
        constraints = [
            models.UniqueConstraint(
                fields=["value", "product"],
                name="unique_product_attribute_value"
            ),
        ]
        indexes = [
            BTreeIndex(fields=["product"], name="assignedprodattrval_product_idx"),
            BTreeIndex(fields=["value"], name="assignedprodattrval_value_idx"),
        ]
    
    def __str__(self) -> str:
        return f"{self.product.name} - {self.value.name}"


class AssignedVariantAttributeValue(SortableModel):
    """Assignment of attribute values to variants."""
    
    value = models.ForeignKey(
        AttributeValue,
        on_delete=models.CASCADE,
        related_name="variantvalueassignment",
        help_text="Attribute value"
    )
    assignment = models.ForeignKey(
        "AssignedVariantAttribute",
        on_delete=models.CASCADE,
        related_name="variantvalueassignment",
        help_text="Variant attribute assignment"
    )
    sort_order = models.IntegerField(
        editable=False,
        db_index=True,
        null=True,
        help_text="Sort order"
    )
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["value", "assignment"],
                name="unique_variant_attribute_value"
            ),
        ]
        ordering = ("sort_order", "pk")
        indexes = [
            BTreeIndex(fields=["assignment"], name="avarval_assign_idx"),
            BTreeIndex(fields=["value"], name="assignedvarattrval_value_idx"),
        ]
    
    def __str__(self) -> str:
        return f"{self.assignment.variant.name} - {self.value.name}"
    
    def get_ordering_queryset(self):
        return self.assignment.variantvalueassignment.all()


class AssignedVariantAttribute(BaseAssignedAttribute):
    """Assignment of attributes to variants."""
    
    variant = models.ForeignKey(
        "ecommerce.ProductVariant",
        related_name="attributes",
        on_delete=models.CASCADE,
        help_text="Product variant"
    )
    assignment = models.ForeignKey(
        AttributeVariant,
        on_delete=models.CASCADE,
        related_name="variantassignments",
        help_text="Attribute variant assignment"
    )
    values = models.ManyToManyField(
        AttributeValue,
        blank=True,
        related_name="variantassignments",
        through=AssignedVariantAttributeValue,
        help_text="Assigned values"
    )
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["variant", "assignment"],
                name="unique_variant_attribute_assignment"
            ),
        ]
        ordering = ("assignment__sort_order", "pk")
        indexes = [
            BTreeIndex(fields=["variant"], name="assignedvarattr_variant_idx"),
            BTreeIndex(fields=["assignment"], name="assignedvarattr_assignment_idx"),
        ]
    
    def __str__(self) -> str:
        return f"{self.variant.name} - {self.assignment.attribute.name}"

