# ecommerce/tests/test_seed_categories.py

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from ecommerce.models.category import Category
from ecommerce.management.commands.seed_categories import TAXONOMY


class TestSeedCategories(TestCase):
    def _run(self, *args):
        out = StringIO()
        call_command("seed_categories", *args, stdout=out)
        return out.getvalue()

    def test_creates_base_tree(self):
        self._run()

        # Top-level categories created
        for top_name in TAXONOMY:
            self.assertTrue(
                Category.objects.filter(name=top_name, parent__isnull=True).exists(),
                f"Top-level {top_name!r} not created",
            )

    def test_creates_full_depth(self):
        self._run()

        # A specific leaf should exist under its parent chain
        beef = Category.objects.filter(slug="beef").first()
        self.assertIsNotNone(beef)
        self.assertEqual(beef.parent.slug, "meat-poultry")
        self.assertEqual(beef.parent.parent.slug, "food-groceries")

    def test_idempotent(self):
        self._run()
        first_count = Category.objects.count()

        self._run()
        second_count = Category.objects.count()

        self.assertEqual(first_count, second_count)

    def test_dry_run_creates_nothing(self):
        self._run("--dry-run")
        self.assertEqual(Category.objects.count(), 0)

    def test_flush_deletes_existing(self):
        self._run()
        initial = Category.objects.count()
        self.assertGreater(initial, 0)

        # Flush then re-seed in one command
        self._run("--flush")

        # Same number as before (deleted then re-created)
        self.assertEqual(Category.objects.count(), initial)

    def test_categories_are_active(self):
        self._run()
        inactive = Category.objects.filter(is_active=False).count()
        self.assertEqual(inactive, 0)

    def test_slugs_are_unique(self):
        self._run()
        slugs = list(Category.objects.values_list("slug", flat=True))
        self.assertEqual(len(slugs), len(set(slugs)))