# ecommerce/tests/test_models/test_category.py

from django.test import SimpleTestCase, TestCase

from ecommerce.models.category import Category, CategoryTranslation


class TestCategoryModel(SimpleTestCase):
    def test_expected_fields(self):
        names = {f.name for f in Category._meta.get_fields()}
        for field in (
            "name", "slug", "description", "description_plaintext",
            "background_image", "background_image_alt",
            "parent", "region", "search_vector",
            "is_active", "updated_at",
        ):
            self.assertIn(field, names, f"missing Category.{field}")

    def test_mptt_fields(self):
        names = {f.name for f in Category._meta.get_fields()}
        for field in ("lft", "rght", "tree_id", "level"):
            self.assertIn(field, names)

    def test_objects_is_mptt_manager(self):
        from mptt.managers import TreeManager
        self.assertIsInstance(Category.objects, TreeManager)

    def test_no_tree_attribute(self):
        # We removed the second `tree` manager.
        self.assertFalse(hasattr(Category, "tree"))

    def test_region_is_nullable_protect(self):
        from django.db import models as dj
        field = Category._meta.get_field("region")
        self.assertIsInstance(field, dj.ForeignKey)
        self.assertTrue(field.null)
        self.assertEqual(field.remote_field.on_delete, dj.PROTECT)

    def test_is_active_present(self):
        field = Category._meta.get_field("is_active")
        self.assertTrue(field.default)

    def test_self_parent_constraint(self):
        names = {c.name for c in Category._meta.constraints}
        self.assertIn("category_not_own_parent", names)


class TestCategoryTree(TestCase):
    def setUp(self):
        self.root = Category.objects.create(name="Root", slug="root")
        self.child = Category.objects.create(
            name="Child", slug="child", parent=self.root
        )

    def test_descendants(self):
        self.assertEqual(
            self.root.get_descendants(include_self=True).count(), 2
        )

    def test_ancestors(self):
        self.assertEqual(
            self.child.get_ancestors(include_self=False).count(), 1
        )

    def test_top_level_queryset(self):
        self.assertIn(self.root, Category.objects.top_level())
        self.assertNotIn(self.child, Category.objects.top_level())

    def test_active_queryset(self):
        self.root.is_active = False
        self.root.save(update_fields=["is_active"])
        self.assertNotIn(
            self.root, Category.objects.active()
        )


class TestCategoryTranslation(SimpleTestCase):
    def test_expected_fields(self):
        names = {f.name for f in CategoryTranslation._meta.get_fields()}
        for field in ("category", "language_code", "name", "description"):
            self.assertIn(field, names)

    def test_unique_constraints(self):
        names = {c.name for c in CategoryTranslation._meta.constraints}
        self.assertIn("uniq_lang_slug_categorytransl", names)
        self.assertIn("uniq_lang_category_categorytransl", names)