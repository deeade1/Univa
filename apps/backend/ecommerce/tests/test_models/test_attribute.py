# ecommerce/tests/test_attribute.py

from django.test import SimpleTestCase

from ecommerce.models.attribute import (
    AssignedAttribute,
    Attribute,
    AttributeScopeLink,
    AttributeTranslation,
    AttributeValue,
    AttributeValueTranslation,
)
from ecommerce.models.enums.attribute import (
    AttributeDataType,
    AttributeReferenceType,
    AttributeScope,
    AttributeWidget,
)


class TestAttributeModel(SimpleTestCase):
    def test_expected_fields(self):
        names = {f.name for f in Attribute._meta.get_fields()}
        for field in (
            "name", "slug", "description",
            "scope", "data_type", "widget", "reference_type",
            "is_required", "min_value", "max_value", "max_length",
            "is_variant_only", "visible_in_storefront",
            "filterable_in_storefront", "filterable_in_dashboard",
            "available_in_grid", "storefront_search_position",
            "is_active", "created_at", "updated_at", "created_by",
        ):
            self.assertIn(field, names, f"missing Attribute.{field}")

    def test_old_fields_removed(self):
        names = {f.name for f in Attribute._meta.get_fields()}
        for removed in ("type", "input_type", "entity_type", "unit"):
            self.assertNotIn(removed, names)

    def test_constraints_present(self):
        names = {c.name for c in Attribute._meta.constraints}
        self.assertIn("attribute_min_value_non_negative", names)
        self.assertIn("attribute_max_value_non_negative", names)
        self.assertIn("attribute_min_le_max", names)

    def test_no_full_clean_in_save(self):
        import inspect

        from django.db import models as dj_models

        # If Attribute doesn't override save(), it can't call full_clean().
        if Attribute.save is dj_models.Model.save:
            return

        # If it does override, ensure full_clean is not invoked.
        src = inspect.getsource(Attribute.save)
        self.assertNotIn("full_clean", src)


class TestAttributeValue(SimpleTestCase):
    def test_expected_fields(self):
        names = {f.name for f in AttributeValue._meta.get_fields()}
        for field in (
            "attribute", "name", "slug", "value",
            "is_active", "sort_order", "created_at", "updated_at",
        ):
            self.assertIn(field, names)

    def test_old_sparse_columns_removed(self):
        names = {f.name for f in AttributeValue._meta.get_fields()}
        for removed in (
            "file_url", "content_type", "rich_text", "plain_text",
            "boolean", "date_time", "reference_product",
            "reference_variant",
        ):
            self.assertNotIn(removed, names)

    def test_unique_constraint(self):
        names = {c.name for c in AttributeValue._meta.constraints}
        self.assertIn("uniq_attribute_slug", names)
        
    def test_no_full_clean_in_save(self):
        import inspect

        from django.db import models as dj_models

        if AttributeValue.save is dj_models.Model.save:
            return

        src = inspect.getsource(AttributeValue.save)
        self.assertNotIn("full_clean", src)


class TestAttributeScopeLink(SimpleTestCase):
    def test_expected_fields(self):
        names = {f.name for f in AttributeScopeLink._meta.get_fields()}
        for field in (
            "attribute", "product_type", "scope",
            "variant_selection", "sort_order",
        ):
            self.assertIn(field, names)

    def test_unique_constraint(self):
        names = {c.name for c in AttributeScopeLink._meta.constraints}
        self.assertIn("uniq_attr_scope_link", names)


class TestAssignedAttribute(SimpleTestCase):
    def test_expected_fields(self):
        names = {f.name for f in AssignedAttribute._meta.get_fields()}
        for field in (
            "attribute", "product", "variant",
            "attribute_value", "raw_value",
            "sort_order", "created_at", "updated_at",
        ):
            self.assertIn(field, names)

    def test_target_constraint(self):
        names = {c.name for c in AssignedAttribute._meta.constraints}
        self.assertIn("assigned_attr_one_target", names)

    def test_value_constraint(self):
        names = {c.name for c in AssignedAttribute._meta.constraints}
        self.assertIn("assigned_attr_one_value", names)


class TestTranslations(SimpleTestCase):
    def test_attribute_translation_fields(self):
        names = {f.name for f in AttributeTranslation._meta.get_fields()}
        for field in ("attribute", "language_code", "name", "description"):
            self.assertIn(field, names)

    def test_attribute_value_translation_fields(self):
        names = {f.name for f in AttributeValueTranslation._meta.get_fields()}
        for field in ("attribute_value", "language_code", "name"):
            self.assertIn(field, names)


class TestEnums(SimpleTestCase):
    def test_scope_values(self):
        self.assertEqual(AttributeScope.PRODUCT, "product")
        self.assertEqual(AttributeScope.VARIANT, "variant")
        self.assertEqual(AttributeScope.PRODUCT_AND_VARIANT, "product_and_variant")

    def test_data_type_values(self):
        self.assertEqual(AttributeDataType.TEXT, "text")
        self.assertEqual(AttributeDataType.REFERENCE, "reference")

    def test_widget_values(self):
        self.assertEqual(AttributeWidget.DROPDOWN, "dropdown")
        self.assertEqual(AttributeWidget.RICH_TEXT, "rich_text")