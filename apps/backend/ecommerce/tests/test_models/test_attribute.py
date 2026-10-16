# apps/backend/ecommerce/tests/test_models/test_attribute.py

"""
Tests for AssignedAttribute ownership validation.

Focus:

    - clean() rejects an attribute_value that belongs to a different
      attribute
    - clean() accepts an attribute_value that belongs to the right
      attribute
    - assign() rejects the same mismatch without touching the database
    - assign() is equivalent to objects.create() when the value is
      valid
    - the raw_value path is not affected by the ownership check
    - the exactly-one-of CheckConstraints still fire
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from ecommerce.models.attribute import (
    AssignedAttribute,
    Attribute,
    AttributeValue,
)
from ecommerce.models.enums.attribute import (
    AttributeDataType,
    AttributeScope,
    AttributeWidget,
)
from ecommerce.models.product import Product, ProductType, ProductVariant


class AttributeTestFixture(TestCase):
    """
    Shared fixture for AssignedAttribute tests.
    """

    @classmethod
    def setUpTestData(cls):
        cls.color = Attribute.objects.create(
            name="Color",
            slug="color",
            scope=AttributeScope.VARIANT,
            data_type=AttributeDataType.TEXT,
            widget=AttributeWidget.SWATCH,
        )
        cls.size = Attribute.objects.create(
            name="Size",
            slug="size",
            scope=AttributeScope.VARIANT,
            data_type=AttributeDataType.TEXT,
            widget=AttributeWidget.DROPDOWN,
        )
        cls.weight = Attribute.objects.create(
            name="Weight",
            slug="weight",
            scope=AttributeScope.PRODUCT_AND_VARIANT,
            data_type=AttributeDataType.NUMBER,
            widget=AttributeWidget.TEXT_INPUT,
        )

        cls.red = AttributeValue.objects.create(
            attribute=cls.color,
            name="Red",
            slug="red",
            value="red",
        )
        cls.small = AttributeValue.objects.create(
            attribute=cls.size,
            name="Small",
            slug="small",
            value="small",
        )

        cls.product_type = ProductType.objects.create(
            name="Test Type",
            slug="attr-test-type",
            has_variants=True,
            is_shipping_required=True,
            is_digital=False,
        )

    def make_product(self, slug="attr-product"):
        return Product.objects.create(
            product_type=self.product_type,
            name=slug.title(),
            slug=slug,
        )

    def make_variant(self, product, name="Default"):
        return ProductVariant.objects.create(
            product=product,
            name=name,
        )


# ----------------------------------------------------------------------
# clean()
# ----------------------------------------------------------------------


class AssignedAttributeCleanTests(AttributeTestFixture):

    def test_clean_accepts_matching_attribute_value(self):
        product = self.make_product("clean-accept")

        assignment = AssignedAttribute(
            product=product,
            attribute=self.color,
            attribute_value=self.red,
        )

        # Should not raise.
        assignment.clean()

    def test_clean_rejects_mismatched_attribute_value(self):
        product = self.make_product("clean-reject")

        assignment = AssignedAttribute(
            product=product,
            attribute=self.color,
            attribute_value=self.small,   # Small belongs to Size, not Color
        )

        with self.assertRaises(ValidationError) as ctx:
            assignment.clean()

        self.assertIn(
            "attribute_value",
            ctx.exception.message_dict,
        )

    def test_clean_does_not_run_ownership_check_when_attribute_value_is_none(self):
        product = self.make_product("clean-raw")

        assignment = AssignedAttribute(
            product=product,
            attribute=self.weight,
            raw_value={"amount": 2.5, "unit": "kg"},
        )

        # Should not raise — raw_value path bypasses the ownership
        # check entirely.
        assignment.clean()

    def test_clean_does_not_run_ownership_check_for_unsaved_row(self):
        """
        When both FKs are set but the row hasn't been saved, we can
        still check. This test confirms the check runs on
        unsaved-but-populated instances.
        """
        product = self.make_product("clean-unsaved")

        assignment = AssignedAttribute(
            product=product,
            attribute=self.color,
            attribute_value=self.small,
        )

        # attribute_id and attribute_value_id are both set because
        # the FKs are assigned, so the check runs.
        with self.assertRaises(ValidationError):
            assignment.clean()


# ----------------------------------------------------------------------
# assign()
# ----------------------------------------------------------------------


class AssignedAttributeAssignTests(AttributeTestFixture):

    def test_assign_creates_row_when_value_matches(self):
        product = self.make_product("assign-ok")

        assignment = AssignedAttribute.assign(
            product=product,
            attribute=self.color,
            attribute_value=self.red,
        )

        self.assertIsNotNone(assignment.pk)
        self.assertEqual(assignment.attribute_id, self.color.pk)
        self.assertEqual(assignment.attribute_value_id, self.red.pk)

    def test_assign_raises_when_value_does_not_match(self):
        product = self.make_product("assign-mismatch")

        with self.assertRaises(ValidationError):
            AssignedAttribute.assign(
                product=product,
                attribute=self.color,
                attribute_value=self.small,
            )

        # No row should have been created.
        self.assertFalse(
            AssignedAttribute.objects.filter(
                product=product,
                attribute=self.color,
            ).exists()
        )

    def test_assign_creates_row_when_value_is_none(self):
        product = self.make_product("assign-raw")

        assignment = AssignedAttribute.assign(
            product=product,
            attribute=self.weight,
            raw_value={"amount": 2.5, "unit": "kg"},
        )

        self.assertIsNotNone(assignment.pk)
        self.assertIsNone(assignment.attribute_value_id)
        self.assertEqual(
            assignment.raw_value,
            {"amount": 2.5, "unit": "kg"},
        )

    def test_assign_to_variant(self):
        product = self.make_product("assign-variant")
        variant = self.make_variant(product)

        assignment = AssignedAttribute.assign(
            variant=variant,
            attribute=self.color,
            attribute_value=self.red,
        )

        self.assertIsNotNone(assignment.pk)
        self.assertEqual(assignment.variant_id, variant.pk)
        self.assertIsNone(assignment.product_id)

    def test_assign_honors_sort_order(self):
        product = self.make_product("assign-sort")

        assignment = AssignedAttribute.assign(
            product=product,
            attribute=self.color,
            attribute_value=self.red,
            sort_order=42,
        )

        self.assertEqual(assignment.sort_order, 42)


# ----------------------------------------------------------------------
# Database-level CheckConstraints still work
# ----------------------------------------------------------------------


class AssignedAttributeConstraintTests(AttributeTestFixture):

    def test_both_product_and_variant_set_is_rejected(self):
        product = self.make_product("both-targets")
        variant = self.make_variant(product)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                AssignedAttribute.objects.create(
                    product=product,
                    variant=variant,
                    attribute=self.color,
                    attribute_value=self.red,
                )

    def test_neither_product_nor_variant_set_is_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                AssignedAttribute.objects.create(
                    attribute=self.color,
                    attribute_value=self.red,
                )

    def test_both_value_and_raw_value_set_is_rejected(self):
        product = self.make_product("both-values")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                AssignedAttribute.objects.create(
                    product=product,
                    attribute=self.color,
                    attribute_value=self.red,
                    raw_value="also-set",
                )

    def test_neither_value_nor_raw_value_set_is_rejected(self):
        product = self.make_product("no-values")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                AssignedAttribute.objects.create(
                    product=product,
                    attribute=self.color,
                )

    def test_objects_create_bypasses_ownership_check(self):
        """
        Regression test documenting the gap that `assign()` exists
        to close.

        The database cannot enforce cross-row ownership, and
        `objects.create()` does not call `clean()`. So this pattern
        silently succeeds — which is exactly why production code
        should use `assign()`.

        If this test ever starts failing (i.e. because someone added
        a database trigger enforcing ownership), that's a signal
        worth knowing about, and the test should be updated to
        reflect the new invariant.
        """
        product = self.make_product("bypass-check")

        # This is the bug. It should NOT be used in production code.
        assignment = AssignedAttribute.objects.create(
            product=product,
            attribute=self.color,
            attribute_value=self.small,   # Small is a Size value
        )

        self.assertIsNotNone(assignment.pk)
        self.assertEqual(assignment.attribute_id, self.color.pk)
        self.assertEqual(assignment.attribute_value_id, self.small.pk)
        # The row is inconsistent but persisted.
        self.assertNotEqual(
            assignment.attribute_value.attribute_id,
            assignment.attribute_id,
        )