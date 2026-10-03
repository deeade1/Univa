# apps/backend/ecommerce/models/enums/attribute.py

"""
Attribute enums.

This module contains BOTH the legacy Saleor-style enums (kept for
backward compatibility while the attribute system is refactored)
AND the new, decomposed enums that the refactored attribute system
will use.

Legacy (to be deleted once attribute.py is rewritten):
    - AttributeType
    - AttributeInputType
    - AttributeEntityType

New (target):
    - AttributeScope
    - AttributeDataType
    - AttributeWidget
    - AttributeReferenceType
"""

from __future__ import annotations


# =====================================================================
# LEGACY — DEPRECATED
# =====================================================================


class AttributeType:
    """DEPRECATED. Use AttributeScope instead."""

    PRODUCT_TYPE = "product-type"
    PRODUCT = "product"
    VARIANT = "variant"

    CHOICES = [
        (PRODUCT_TYPE, "Product Type"),
        (PRODUCT, "Product"),
        (VARIANT, "Variant"),
    ]


class AttributeInputType:
    """DEPRECATED. Split into AttributeDataType + AttributeWidget."""

    DROPDOWN = "dropdown"
    MULTISELECT = "multiselect"
    TEXT = "text"
    TEXTAREA = "textarea"
    RICH_TEXT = "rich-text"
    NUMERIC = "numeric"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    FILE = "file"
    REFERENCE = "reference"

    CHOICES = [
        (DROPDOWN, "Dropdown"),
        (MULTISELECT, "Multi-select"),
        (TEXT, "Text"),
        (TEXTAREA, "Text Area"),
        (RICH_TEXT, "Rich Text"),
        (NUMERIC, "Numeric"),
        (BOOLEAN, "Boolean"),
        (DATE, "Date"),
        (DATETIME, "Date Time"),
        (FILE, "File"),
        (REFERENCE, "Reference"),
    ]

    MULTI_VALUE_TYPES = [MULTISELECT]
    REQUIRES_VALUE = [
        DROPDOWN, MULTISELECT, TEXT, TEXTAREA,
        RICH_TEXT, NUMERIC, DATE, DATETIME,
    ]
    RICH_TEXT_TYPES = [RICH_TEXT]


class AttributeEntityType:
    """DEPRECATED. Use AttributeReferenceType instead."""

    PRODUCT = "product"
    PRODUCT_VARIANT = "product-variant"
    PAGE = "page"
    BLOG = "blog"

    CHOICES = [
        (PRODUCT, "Product"),
        (PRODUCT_VARIANT, "Product Variant"),
        (PAGE, "Page"),
        (BLOG, "Blog"),
    ]


# =====================================================================
# NEW — TARGET API
# =====================================================================


class AttributeScope:
    """What an attribute describes."""
    PRODUCT = "product"
    VARIANT = "variant"
    PRODUCT_AND_VARIANT = "product_and_variant"

    CHOICES = [
        (PRODUCT, "Product"),
        (VARIANT, "Variant"),
        (PRODUCT_AND_VARIANT, "Product and variant"),
    ]


class AttributeDataType:
    """The kind of value an attribute stores."""
    TEXT = "text"
    NUMBER = "number"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    REFERENCE = "reference"
    FILE = "file"
    JSON = "json"

    CHOICES = [
        (TEXT, "Text"),
        (NUMBER, "Number"),
        (BOOLEAN, "Boolean"),
        (DATE, "Date"),
        (DATETIME, "Date and time"),
        (REFERENCE, "Reference to another object"),
        (FILE, "File"),
        (JSON, "Structured JSON"),
    ]


class AttributeWidget:
    """How the attribute is presented in the UI."""
    DROPDOWN = "dropdown"
    MULTISELECT = "multiselect"
    RADIO = "radio"
    SWATCH = "swatch"
    SLIDER = "slider"
    TEXT_INPUT = "text_input"
    TEXTAREA = "textarea"
    RICH_TEXT = "rich_text"
    CHECKBOX = "checkbox"
    DATE_PICKER = "date_picker"
    DATETIME_PICKER = "datetime_picker"
    FILE_UPLOAD = "file_upload"
    REFERENCE_PICKER = "reference_picker"

    CHOICES = [
        (DROPDOWN, "Dropdown"),
        (MULTISELECT, "Multi-select"),
        (RADIO, "Radio"),
        (SWATCH, "Swatch"),
        (SLIDER, "Slider"),
        (TEXT_INPUT, "Text input"),
        (TEXTAREA, "Text area"),
        (RICH_TEXT, "Rich text"),
        (CHECKBOX, "Checkbox"),
        (DATE_PICKER, "Date picker"),
        (DATETIME_PICKER, "Date and time picker"),
        (FILE_UPLOAD, "File upload"),
        (REFERENCE_PICKER, "Reference picker"),
    ]


class AttributeReferenceType:
    """What a reference attribute can point to."""
    PRODUCT = "product"
    PRODUCT_VARIANT = "product_variant"
    CATEGORY = "category"
    COLLECTION = "collection"

    CHOICES = [
        (PRODUCT, "Product"),
        (PRODUCT_VARIANT, "Product variant"),
        (CATEGORY, "Category"),
        (COLLECTION, "Collection"),
    ]