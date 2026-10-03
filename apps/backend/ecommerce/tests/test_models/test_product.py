# apps/backend/ecommerce/tests/test_product.py

from django.db import models as dj_models
from django.test import SimpleTestCase

from ecommerce.models.enums import ProductTypeKind, QuantityUnit
from ecommerce.models.product import (
    DigitalContentUrl,
    Product,
    ProductChannelListing,
    ProductReview,
    ProductType,
    ProductVariant,
    ProductVariantChannelListing,
)


class TestProductType(SimpleTestCase):
    def test_constraint_present(self):
        names = {c.name for c in ProductType._meta.constraints}
        self.assertIn("product_type_digital_not_shipped", names)

    def test_kind_is_indexed(self):
        field = ProductType._meta.get_field("kind")
        self.assertTrue(field.db_index)


class TestProduct(SimpleTestCase):
    def test_removed_fields_are_gone(self):
        names = {f.name for f in Product._meta.get_fields()}
        for removed in (
            "rating",
            "is_featured",
            "is_flash_sale",
            "flash_sale_price",
        ):
            self.assertNotIn(removed, names)

    def test_is_active_present(self):
        names = {f.name for f in Product._meta.get_fields()}
        self.assertIn("is_active", names)

    def test_category_on_delete_is_protect(self):
        field = Product._meta.get_field("category")
        self.assertEqual(field.remote_field.on_delete, dj_models.PROTECT)

    def test_no_graphene_import(self):
        import ecommerce.models.product as module
        self.assertFalse(hasattr(module, "graphene"))


class TestProductReview(SimpleTestCase):
    def test_unique_constraint(self):
        names = {c.name for c in ProductReview._meta.constraints}
        self.assertIn("unique_user_product_review", names)

    def test_rating_range_constraint(self):
        names = {c.name for c in ProductReview._meta.constraints}
        self.assertIn("review_rating_1_to_5", names)

    def test_rating_validators(self):
        field = ProductReview._meta.get_field("rating")
        validator_types = {type(v).__name__ for v in field.validators}
        self.assertIn("MinValueValidator", validator_types)
        self.assertIn("MaxValueValidator", validator_types)

    def test_new_fields_present(self):
        names = {f.name for f in ProductReview._meta.get_fields()}
        for expected in (
            "title",
            "is_verified_purchase",
            "is_published",
            "helpful_count",
            "updated_at",
        ):
            self.assertIn(expected, names)


class TestProductChannelListing(SimpleTestCase):
    def test_price_amount_required(self):
        field = ProductChannelListing._meta.get_field("price_amount")
        self.assertFalse(field.null)
        self.assertFalse(field.blank)

    def test_is_featured_present(self):
        names = {f.name for f in ProductChannelListing._meta.get_fields()}
        self.assertIn("is_featured", names)


class TestProductVariant(SimpleTestCase):
    def test_quantity_unit_present(self):
        names = {f.name for f in ProductVariant._meta.get_fields()}
        self.assertIn("quantity_unit", names)

    def test_quantity_unit_default(self):
        field = ProductVariant._meta.get_field("quantity_unit")
        self.assertEqual(field.default, QuantityUnit.UNIT.value)

    def test_get_global_id_removed(self):
        self.assertFalse(hasattr(ProductVariant, "get_global_id"))

    def test_quantity_limit_has_max_validator(self):
        field = ProductVariant._meta.get_field("quantity_limit_per_customer")
        validator_types = {type(v).__name__ for v in field.validators}
        self.assertIn("MaxValueValidator", validator_types)


class TestProductVariantChannelListing(SimpleTestCase):
    def test_price_amount_required(self):
        field = ProductVariantChannelListing._meta.get_field("price_amount")
        self.assertFalse(field.null)

    def test_is_featured_present(self):
        names = {
            f.name for f in ProductVariantChannelListing._meta.get_fields()
        }
        self.assertIn("is_featured", names)

    def test_discounted_price_dirty_present(self):
        names = {
            f.name for f in ProductVariantChannelListing._meta.get_fields()
        }
        self.assertIn("discounted_price_dirty", names)


class TestDigitalContentUrl(SimpleTestCase):
    def test_token_is_charfield(self):
        field = DigitalContentUrl._meta.get_field("token")
        self.assertIsInstance(field, dj_models.CharField)
        self.assertEqual(field.max_length, 32)

    def test_line_is_foreignkey(self):
        field = DigitalContentUrl._meta.get_field("line")
        self.assertIsInstance(field, dj_models.ForeignKey)

    def test_is_revoked_present(self):
        names = {f.name for f in DigitalContentUrl._meta.get_fields()}
        self.assertIn("is_revoked", names)