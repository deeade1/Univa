# ecommerce/services/product/utils/variants.py

"""
Variant utility helpers.

Rebuilt on the unified AssignedAttribute model. See
`ecommerce.models.attribute` for the design of attributes,
scope links, and assignments.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Optional

from django.conf import settings
from django.db.models import QuerySet

from discount.models import PromotionRule
from discount.utils.promotion import update_rule_variant_relation

from ...models import ProductVariant

if TYPE_CHECKING:
    from ecommerce.models.attribute import AssignedAttribute, Attribute


def generate_and_set_variant_name(
    variant: "ProductVariant",
    sku: Optional[str],
    save: bool = True,
) -> "ProductVariant":
    """
    Generate a ProductVariant's name from its variant-selection
    attributes.

    Variant-selection attributes are those whose scope link on the
    variant's product type has `variant_selection=True`. Values are
    ordered, joined, and set as the variant name.

    Falls back to the SKU (or a placeholder) when no selection
    attributes exist.
    """
    attributes_display: list[str] = []

    variant_selection_attrs = (
        variant.assigned_attributes
        .filter(
            attribute__scope_links__product_type=variant.product.product_type,
            attribute__scope_links__variant_selection=True,
        )
        .select_related("attribute", "attribute_value")
    )

    assigned: "AssignedAttribute"
    for assigned in variant_selection_attrs.iterator():
        value_repr = _assigned_value_repr(assigned)
        if value_repr:
            attributes_display.append(value_repr)

    name = " / ".join(sorted(attributes_display))
    if not name:
        name = sku or f"Variant {variant.pk}"

    variant.name = name
    if save:
        variant.save(update_fields=["name", "updated_at"])
    return variant


def get_variant_selection_attributes(
    attributes: Iterable[tuple["Attribute", bool]],
) -> list[tuple["Attribute", bool]]:
    """
    Filter (Attribute, variant_selection) pairs down to those eligible
    for variant selection.

    An attribute is eligible when:
        - variant_selection is True, and
        - its scope is VARIANT or PRODUCT_AND_VARIANT.
    """
    return [
        (attribute, variant_selection)
        for attribute, variant_selection in attributes
        if variant_selection
        and attribute.scope in ("variant", "product_and_variant")
    ]


def fetch_variants_for_promotion_rules(
    rules: QuerySet[PromotionRule],
):
    """Rebuild the PromotionRule ↔ ProductVariant relation for a set of rules."""
    from graphq.discount.utils import get_variants_for_catalogue_predicate

    PromotionRuleVariant = PromotionRule.variants.through
    new_rules_variants = []
    for rule in rules.iterator():
        variants = get_variants_for_catalogue_predicate(
            rule.catalogue_predicate,
        )
        new_rules_variants.extend(
            [
                PromotionRuleVariant(
                    promotionrule_id=rule.pk,
                    productvariant_id=variant_id,
                )
                for variant_id in set(
                    variants.values_list("pk", flat=True)
                )
            ]
        )
    return update_rule_variant_relation(rules, new_rules_variants)


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------


def _assigned_value_repr(assigned: "AssignedAttribute") -> str:
    """
    Human-readable representation of an AssignedAttribute's value.

    Preset values use `attribute_value.name`. Raw values are stringified
    from JSON.
    """
    if assigned.attribute_value_id is not None:
        return assigned.attribute_value.name

    raw = assigned.raw_value
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    if isinstance(raw, bool):
        return "Yes" if raw else "No"
    return str(raw)