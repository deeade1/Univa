# apps/backend/ecommerce/models/attribute.py

"""
Attribute system for Univa.

Design
------

An attribute is a *property* of a product or variant: "Color", "Size",
"Weight", "Material", "Origin". An attribute has zero or more values
("Red", "Blue", "Small", "Large").

Attributes are scoped:

    - PRODUCT  — describes the product as a whole (Material, Origin)
    - VARIANT  — distinguishes variants (Color, Size)
    - PRODUCT_AND_VARIANT — either

Attributes are typed. Two orthogonal concepts:

    - data_type — what kind of value it holds
      TEXT, NUMBER, BOOLEAN, DATE, DATETIME, REFERENCE, FILE, JSON

    - widget — how the UI presents the input
      DROPDOWN, MULTISELECT, RADIO, SWATCH, SLIDER, TEXT_INPUT, ...

Value storage
-------------

AttributeValue carries a *hybrid* value:

    - attribute_value = FK(AttributeValue)  — for preset types
    - raw_value = JSONField()               — for arbitrary types

An AssignedAttribute row sets exactly one of the two, matching the
attribute's data_type.

Assignment
----------

A single `AssignedAttribute` model handles both products and variants.
A CheckConstraint enforces that exactly one of `product` / `variant`
is set.

Translation
-----------

Attribute and AttributeValue both support translations via
`AttributeTranslation` and `AttributeValueTranslation`.
"""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models.metadata import (
    ModelWithExternalReference,
    ModelWithMetadata,
)
from core.models.sortable import SortableModel
from ecommerce.models.enums.attribute import (
    AttributeDataType,
    AttributeReferenceType,
    AttributeScope,
    AttributeWidget,
)


# =====================================================================
# ATTRIBUTE
# =====================================================================


class Attribute(ModelWithMetadata, ModelWithExternalReference):
    """
    Definition of an attribute.

    Examples:

        Attribute(
            name="Color",
            slug="color",
            scope=AttributeScope.VARIANT,
            data_type=AttributeDataType.TEXT,
            widget=AttributeWidget.SWATCH,
        )

        Attribute(
            name="Weight",
            slug="weight",
            scope=AttributeScope.PRODUCT_AND_VARIANT,
            data_type=AttributeDataType.NUMBER,
            widget=AttributeWidget.TEXT_INPUT,
        )
    """

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    name = models.CharField(
        max_length=255,
        help_text=_("Display name of the attribute."),
    )
    slug = models.SlugField(
        max_length=250,
        unique=True,
        allow_unicode=True,
        help_text=_("URL-safe identifier for the attribute."),
    )
    description = models.TextField(
        blank=True,
        help_text=_("Long-form description."),
    )

    # ------------------------------------------------------------------
    # Type configuration
    # ------------------------------------------------------------------

    scope = models.CharField(
        max_length=32,
        choices=AttributeScope.CHOICES,
        default=AttributeScope.PRODUCT,
        db_index=True,
        help_text=_(
            "Whether the attribute describes a product, a variant, or both."
        ),
    )
    data_type = models.CharField(
        max_length=32,
        choices=AttributeDataType.CHOICES,
        default=AttributeDataType.TEXT,
        db_index=True,
        help_text=_("Kind of value the attribute stores."),
    )
    widget = models.CharField(
        max_length=32,
        choices=AttributeWidget.CHOICES,
        default=AttributeWidget.DROPDOWN,
        help_text=_("How the input is presented in the UI."),
    )
    reference_type = models.CharField(
        max_length=32,
        choices=AttributeReferenceType.CHOICES,
        blank=True,
        help_text=_(
            "For data_type=REFERENCE, what kind of object the value "
            "points to."
        ),
    )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    is_required = models.BooleanField(
        default=False,
        help_text=_(
            "Whether a value must be set when the attribute is assigned."
        ),
    )
    min_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("For NUMBER attributes: minimum allowed value."),
    )
    max_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("For NUMBER attributes: maximum allowed value."),
    )
    max_length = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("For TEXT attributes: maximum character count."),
    )

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    is_variant_only = models.BooleanField(
        default=False,
        help_text=_(
            "If True, the attribute is only assignable to variants, "
            "regardless of scope."
        ),
    )
    visible_in_storefront = models.BooleanField(
        default=True,
        db_index=True,
        help_text=_("Whether the attribute is visible on the storefront."),
    )
    filterable_in_storefront = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Whether the attribute can be used as a filter."),
    )
    filterable_in_dashboard = models.BooleanField(
        default=False,
        help_text=_(
            "Whether the attribute can be used as a filter in the admin."
        ),
    )
    available_in_grid = models.BooleanField(
        default=False,
        help_text=_("Whether the attribute is shown in product grids."),
    )
    storefront_search_position = models.IntegerField(
        default=0,
        help_text=_("Ordering position for storefront search filters."),
    )

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text=_(
            "Inactive attributes are hidden from the UI but remain "
            "referenced by historical data."
        ),
    )

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_attributes",
    )

    class Meta:
        ordering = ("storefront_search_position", "slug")
        indexes = [
            *ModelWithMetadata.Meta.indexes,
            models.Index(fields=["scope", "is_active"]),
            models.Index(fields=["data_type", "is_active"]),
            models.Index(fields=["filterable_in_storefront", "is_active"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(min_value__isnull=True)
                    | models.Q(min_value__gte=0)
                ),
                name="attribute_min_value_non_negative",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(max_value__isnull=True)
                    | models.Q(max_value__gte=0)
                ),
                name="attribute_max_value_non_negative",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(min_value__isnull=True)
                    | models.Q(max_value__isnull=True)
                    | models.Q(min_value__lte=models.F("max_value"))
                ),
                name="attribute_min_le_max",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def has_values(self) -> bool:
        return self.values.exists()

    def get_value_count(self) -> int:
        return self.values.count()


# =====================================================================
# ATTRIBUTE TRANSLATION
# =====================================================================


class AttributeTranslation(models.Model):
    """Localized name and description for an Attribute."""

    attribute = models.ForeignKey(
        Attribute,
        related_name="translations",
        on_delete=models.CASCADE,
    )
    language_code = models.CharField(max_length=35, db_index=True)
    name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["language_code", "attribute"],
                name="uniq_lang_attr_attributetransl",
            ),
        ]
        ordering = ("attribute_id", "language_code")

    def __str__(self) -> str:
        return f"{self.attribute.name} ({self.language_code})"


# =====================================================================
# ATTRIBUTE VALUE
# =====================================================================


class AttributeValue(ModelWithExternalReference):
    """
    A value an Attribute can take.

    Examples: "Red" for Color; "Small" for Size; "2.5" for Weight.

    The `value` JSONField holds the canonical typed representation.
    For DROPDOWN-style attributes it holds a string; for NUMBER it
    holds a number; for DATE it holds an ISO date string; etc.

    A `sort_order` controls presentation order within the attribute.
    """

    attribute = models.ForeignKey(
        Attribute,
        related_name="values",
        on_delete=models.CASCADE,
        db_index=True,
    )
    name = models.CharField(
        max_length=250,
        help_text=_("Human-readable label."),
    )
    slug = models.SlugField(
        max_length=255,
        allow_unicode=True,
        help_text=_("URL-safe identifier, unique within the attribute."),
    )
    value = models.JSONField(
        blank=True,
        null=True,
        help_text=_(
            "Canonical machine-readable value. Type determined by "
            "attribute.data_type."
        ),
    )
    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.IntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("sort_order", "pk", "name")
        constraints = [
            models.UniqueConstraint(
                fields=["attribute", "slug"],
                name="uniq_attribute_slug",
            ),
        ]
        indexes = [
            models.Index(
                fields=["attribute", "sort_order"],
                name="attrval_attr_sort_idx",
            ),
            models.Index(
                fields=["attribute", "is_active"],
                name="attrval_attr_active_idx",
            ),
        ]

    def __str__(self) -> str:
        return self.name


# =====================================================================
# ATTRIBUTE VALUE TRANSLATION
# =====================================================================


class AttributeValueTranslation(models.Model):
    """Localized name for an AttributeValue."""

    attribute_value = models.ForeignKey(
        AttributeValue,
        related_name="translations",
        on_delete=models.CASCADE,
    )
    language_code = models.CharField(max_length=35, db_index=True)
    name = models.CharField(max_length=250, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["language_code", "attribute_value"],
                name="uniq_lang_attrval_attrvaltransl",
            ),
        ]
        ordering = ("attribute_value_id", "language_code")

    def __str__(self) -> str:
        return f"{self.attribute_value.name} ({self.language_code})"


# =====================================================================
# ATTRIBUTE SCOPE LINK
# =====================================================================


class AttributeScopeLink(SortableModel):
    """
    Through-table connecting Attribute and ProductType.

    Replaces the previous two through-tables (AttributeProduct,
    AttributeVariant) with one, disambiguated by `scope`.

    `variant_selection` is meaningful only for scope=VARIANT: when
    True, the attribute is used to select variants on the product
    detail page (color picker, size chips).

    `sort_order` controls the order in which attributes appear on the
    product detail page.
    """

    attribute = models.ForeignKey(
        Attribute,
        related_name="scope_links",
        on_delete=models.CASCADE,
    )
    product_type = models.ForeignKey(
        "ecommerce.ProductType",
        related_name="attribute_scope_links",
        on_delete=models.CASCADE,
    )
    scope = models.CharField(
        max_length=32,
        choices=AttributeScope.CHOICES,
        default=AttributeScope.PRODUCT,
        db_index=True,
        help_text=_(
            "How the attribute applies to this product type. "
            "Usually matches Attribute.scope but can be narrowed."
        ),
    )
    variant_selection = models.BooleanField(
        default=False,
        help_text=_(
            "For scope=VARIANT: whether this attribute selects variants."
        ),
    )
    sort_order = models.IntegerField(default=0, db_index=True)

    class Meta:
        ordering = ("product_type", "sort_order", "attribute__name")
        constraints = [
            models.UniqueConstraint(
                fields=["attribute", "product_type", "scope"],
                name="uniq_attr_scope_link",
            ),
        ]
        indexes = [
            models.Index(
                fields=["product_type", "scope"],
                name="attrscopelink_pt_scope_idx",
            ),
            models.Index(
                fields=["attribute"],
                name="attrscopelink_attr_idx",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.product_type.name} ↔ {self.attribute.name} "
            f"({self.scope})"
        )

    def get_ordering_queryset(self):
        return self.product_type.attribute_scope_links.all()


# =====================================================================
# ASSIGNED ATTRIBUTE
# =====================================================================


class AssignedAttribute(ModelWithMetadata):
    """
    A single attribute assignment to a product or a variant.

    Exactly one of `product` / `variant` is set.
    Exactly one of `attribute_value` / `raw_value` is set.

    Hybrid storage:
      - `attribute_value` — preset value (FK to AttributeValue)
        Used for DROPDOWN, MULTISELECT, SWATCH.
      - `raw_value` — freeform value stored inline
        Used for TEXT, NUMBER, BOOLEAN, DATE, DATETIME, FILE, JSON.

    Which one is required depends on the parent attribute's data_type.
    The database enforces the exactly-one constraint; the service
    layer enforces the data_type match.
    """

    attribute = models.ForeignKey(
        Attribute,
        related_name="assignments",
        on_delete=models.PROTECT,
        help_text=_(
            "Deleting an attribute is prevented while it has "
            "assignments. Deactivate it instead."
        ),
    )
    product = models.ForeignKey(
        "ecommerce.Product",
        related_name="assigned_attributes",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    variant = models.ForeignKey(
        "ecommerce.ProductVariant",
        related_name="assigned_attributes",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    attribute_value = models.ForeignKey(
        AttributeValue,
        related_name="assignments",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    raw_value = models.JSONField(
        blank=True,
        null=True,
        help_text=_(
            "For attributes with data_type other than preset types. "
            "Value shape matches the attribute's data_type."
        ),
    )

    sort_order = models.IntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("attribute", "sort_order", "pk")
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(product__isnull=False, variant__isnull=True)
                    | models.Q(product__isnull=True, variant__isnull=False)
                ),
                name="assigned_attr_one_target",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        attribute_value__isnull=False,
                        raw_value__isnull=True,
                    )
                    | models.Q(
                        attribute_value__isnull=True,
                        raw_value__isnull=False,
                    )
                ),
                name="assigned_attr_one_value",
            ),
        ]
        indexes = [
            *ModelWithMetadata.Meta.indexes,
            models.Index(
                fields=["product", "attribute"],
                name="assignedattr_product_attr_idx",
            ),
            models.Index(
                fields=["variant", "attribute"],
                name="assignedattr_variant_attr_idx",
            ),
            models.Index(
                fields=["attribute_value"],
                name="assignedattr_value_idx",
            ),
        ]

    def __str__(self) -> str:
        target = self.product or self.variant
        return f"{target} — {self.attribute.name}"

    @property
    def target(self):
        """The product or variant this attribute is attached to."""
        return self.product or self.variant