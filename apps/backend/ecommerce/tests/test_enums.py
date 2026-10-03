# apps/backend/ecommerce/tests/test_enums.py

from decimal import Decimal

from django.test import SimpleTestCase

from ecommerce.models.enums import (
    AttributeDataType,
    AttributeScope,
    AttributeWidget,
    FulfillmentLineData,
    OrderStatus,
    ProductTypeKind,
    QuantityUnit,
)


class TestProductTypeKind(SimpleTestCase):
    def test_market_item_exists(self):
        self.assertEqual(ProductTypeKind.MARKET_ITEM, "market_item")

    def test_existing_kinds_preserved(self):
        self.assertEqual(ProductTypeKind.NORMAL, "normal")
        self.assertEqual(ProductTypeKind.GIFT_CARD, "gift_card")


class TestOrderStatus(SimpleTestCase):
    def test_partially_fulfilled_has_no_space(self):
        self.assertEqual(
            OrderStatus.PARTIALLY_FULFILLED,
            "partially_fulfilled",
        )

    def test_no_status_value_contains_spaces(self):
        # CHOICES is [(value, label), ...]; iterate values only.
        for value, label in OrderStatus.CHOICES:
            self.assertNotIn(
                " ",
                value,
                msg=f"OrderStatus value {value!r} (label {label!r}) has a space",
            )


class TestFulfillmentLineData(SimpleTestCase):
    def test_quantity_accepts_decimal(self):
        d = FulfillmentLineData(line=None, quantity=Decimal("2.5"))
        self.assertIsInstance(d.quantity, Decimal)

    def test_replace_defaults_false(self):
        d = FulfillmentLineData(line=None, quantity=Decimal("1"))
        self.assertFalse(d.replace)


class TestAttributeDecomposition(SimpleTestCase):
    def test_scope_values(self):
        expected = {"product", "variant", "product_and_variant"}
        actual = {value for value, _ in AttributeScope.CHOICES}
        self.assertEqual(actual, expected)

    def test_data_type_values(self):
        expected = {
            "text", "number", "boolean", "date",
            "datetime", "reference", "file", "json",
        }
        actual = {value for value, _ in AttributeDataType.CHOICES}
        self.assertEqual(actual, expected)

    def test_widget_values(self):
        expected = {
            "dropdown", "multiselect", "radio", "swatch", "slider",
            "text_input", "textarea", "rich_text", "checkbox",
            "date_picker", "datetime_picker", "file_upload",
            "reference_picker",
        }
        actual = {value for value, _ in AttributeWidget.CHOICES}
        self.assertEqual(actual, expected)


class TestBackwardCompat(SimpleTestCase):
    def test_old_import_path(self):
        from ecommerce.models.constants import ProductTypeKind as old
        self.assertEqual(old.MARKET_ITEM, "market_item")

    def test_quantity_unit_reexport(self):
        from ecommerce.models.constants import QuantityUnit as q
        self.assertEqual(q.KG, "kg")