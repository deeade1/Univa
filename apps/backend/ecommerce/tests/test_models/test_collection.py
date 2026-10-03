# ecommerce/tests/test_models/test_collection.py

from django.test import SimpleTestCase, TestCase

from ecommerce.models.collection import (
    Collection,
    CollectionChannelListing,
    CollectionProduct,
    CollectionTranslation,
    CollectionType,
)


class TestCollectionModel(SimpleTestCase):
    def test_expected_fields(self):
        names = {f.name for f in Collection._meta.get_fields()}
        for field in (
            "name", "slug", "description",
            "background_image", "background_image_alt",
            "collection_type", "rule_definition", "products",
            "is_active", "created_at", "updated_at",
        ):
            self.assertIn(field, names, f"missing Collection.{field}")

    def test_collection_type_default(self):
        field = Collection._meta.get_field("collection_type")
        self.assertEqual(field.default, CollectionType.MANUAL)

    def test_is_active_present(self):
        field = Collection._meta.get_field("is_active")
        self.assertTrue(field.default)

    def test_description_no_null(self):
        field = Collection._meta.get_field("description")
        self.assertFalse(field.null)


class TestCollectionProduct(SimpleTestCase):
    def test_unique_constraint(self):
        names = {c.name for c in CollectionProduct._meta.constraints}
        self.assertIn("unique_collection_product", names)

    def test_deterministic_ordering(self):
        self.assertEqual(
            CollectionProduct._meta.ordering,
            ("sort_order", "pk"),
        )


class TestCollectionChannelListing(SimpleTestCase):
    def test_is_active_present(self):
        names = {
            f.name for f in CollectionChannelListing._meta.get_fields()
        }
        self.assertIn("is_active", names)

    def test_unique_constraint(self):
        names = {
            c.name for c in CollectionChannelListing._meta.constraints
        }
        self.assertIn("unique_collection_channel_listing", names)


class TestCollectionTranslation(SimpleTestCase):
    def test_unique_constraints(self):
        names = {
            c.name for c in CollectionTranslation._meta.constraints
        }
        self.assertIn("uniq_lang_slug_collectiontransl", names)
        self.assertIn("uniq_lang_collection_collectiontransl", names)


class TestCollectionTypeEnum(SimpleTestCase):
    def test_values(self):
        expected = {"manual", "rule_based"}
        actual = {v for v, _ in CollectionType.choices}
        self.assertEqual(actual, expected)