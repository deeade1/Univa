# ecommerce/services/product/search.py

"""
Product full-text search indexing.

Uses Django's built-in SearchVector primitives. The previous
implementation depended on custom FlatConcatSearchVector /
NoValidationSearchVector classes that no longer exist.

Rebuilt on the unified AssignedAttribute model.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Union

from django.conf import settings
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db.models import F, Q, Value, prefetch_related_objects

from core.utils.editorjs import clean_editor_js
from ecommerce.models.attribute import AssignedAttribute, Attribute
from ecommerce.models.product import Product

if TYPE_CHECKING:
    from django.db.models import QuerySet


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PRODUCT_SEARCH_FIELDS = ["name", "description_plaintext"]

PRODUCT_FIELDS_TO_PREFETCH = [
    "variants__assigned_attributes__attribute",
    "variants__assigned_attributes__attribute_value",
    "assigned_attributes__attribute",
    "assigned_attributes__attribute_value",
    "product_type__attribute_scope_links__attribute",
]

PRODUCTS_BATCH_SIZE = 100


# ---------------------------------------------------------------------------
# Batch driver
# ---------------------------------------------------------------------------


def update_products_search_vector(product_ids: Iterable[int]) -> None:
    """Recompute the search vector for the given product IDs."""
    product_ids = list(product_ids)
    products = Product.objects.filter(pk__in=product_ids).order_by("pk")

    for product_pks in queryset_in_batches(products):
        batch = list(Product.objects.filter(pk__in=product_pks))
        _prep_product_search_vector_index(batch)


def queryset_in_batches(queryset: "QuerySet") -> Iterable[list[int]]:
    """Yield batches of PKs from a queryset, ordered by PK."""
    start_pk = 0
    while True:
        qs = queryset.filter(pk__gt=start_pk)[:PRODUCTS_BATCH_SIZE]
        pks = list(qs.values_list("pk", flat=True))
        if not pks:
            break
        yield pks
        start_pk = pks[-1]


# ---------------------------------------------------------------------------
# Per-product vector build
# ---------------------------------------------------------------------------


def _prep_product_search_vector_index(products: list[Product]) -> None:
    """Compute and persist the search vector for a batch of products."""
    prefetch_related_objects(products, *PRODUCT_FIELDS_TO_PREFETCH)

    for product in products:
        product.search_vector = _build_search_vector(product)
        product.search_index_dirty = False

    Product.objects.bulk_update(
        products,
        ["search_vector", "updated_at", "search_index_dirty"],
    )


def _build_search_vector(product: Product) -> SearchVector:
    """
    Build the complete search vector for a product by combining:

        - product name (weight A)
        - product description plaintext (weight C)
        - product attribute values (weight B)
        - variant SKU + name + variant attribute values (weight B)
    """
    vector = (
        SearchVector(Value(product.name), weight="A", config="simple")
        + SearchVector(
            Value(product.description_plaintext or ""),
            weight="C",
            config="simple",
        )
    )

    for text in _product_attribute_texts(product):
        vector = vector + SearchVector(Value(text), weight="B", config="simple")

    for text in _variant_texts(product):
        vector = vector + SearchVector(Value(text), weight="B", config="simple")

    return vector


# ---------------------------------------------------------------------------
# Attribute value extraction
# ---------------------------------------------------------------------------


def _product_attribute_texts(product: Product) -> list[str]:
    """
    Values for product-scoped attributes applicable to this product's
    type, capped at PRODUCT_MAX_INDEXED_ATTRIBUTES.
    """
    applicable_ids = {
        link.attribute_id
        for link in product.product_type.attribute_scope_links.all()
    }

    assignments = [
        a
        for a in product.assigned_attributes.all()
        if a.attribute_id in applicable_ids
    ][: settings.PRODUCT_MAX_INDEXED_ATTRIBUTES]

    return _texts_from_assignments(assignments)


def _variant_texts(product: Product) -> list[str]:
    """SKU, name, and attribute values for the first N variants."""
    variants = list(
        product.variants.all()[: settings.PRODUCT_MAX_INDEXED_VARIANTS]
    )

    texts: list[str] = []

    for variant in variants:
        if variant.sku:
            texts.append(variant.sku)
        if variant.name:
            texts.append(variant.name)

        variant_assignments = list(
            variant.assigned_attributes.all()[
                : settings.PRODUCT_MAX_INDEXED_ATTRIBUTES
            ]
        )
        texts.extend(_texts_from_assignments(variant_assignments))

    return texts


def _texts_from_assignments(
    assignments: list[AssignedAttribute],
) -> list[str]:
    """
    Extract searchable text from a list of AssignedAttribute rows.

    Handles preset values (dropdown, multiselect, swatch) and raw
    values (text, number, date, etc.).
    """
    texts: list[str] = []
    for assigned in assignments:
        text = _assigned_search_text(assigned)
        if text:
            texts.append(text)
    return texts


def _assigned_search_text(assigned: AssignedAttribute) -> str:
    attribute = assigned.attribute

    # Preset value (dropdown / multiselect / swatch)
    if assigned.attribute_value_id is not None:
        return assigned.attribute_value.name

    raw = assigned.raw_value
    if raw is None:
        return ""

    if isinstance(raw, str):
        # Rich text stored as JSON
        if attribute.data_type == "json" and isinstance(raw, dict):
            return clean_editor_js(raw, to_string=True)
        return raw

    if isinstance(raw, bool):
        return "Yes" if raw else "No"

    return str(raw)


# ---------------------------------------------------------------------------
# Query-time
# ---------------------------------------------------------------------------


def search_products(qs: "QuerySet", value: str) -> "QuerySet":
    """Filter a Product queryset by a websearch-style query."""
    if not value:
        return qs

    query = SearchQuery(value, search_type="websearch", config="simple")
    return qs.filter(search_vector=query).annotate(
        search_rank=SearchRank(F("search_vector"), query)
    )