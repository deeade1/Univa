# ecommerce/management/commands/seed_categories.py

"""
Seed the base product category tree.

Creates a region-agnostic taxonomy that any Univa vertical can extend
later with region-specific subcategories.

Structure:

    Food & Groceries
    ├── Meat & Poultry
    │   ├── Beef
    │   ├── Goat
    │   └── ...
    ├── Fish & Seafood
    ├── Vegetables & Leafy Greens
    ├── Fruits
    ├── Grains & Cereals
    ├── Tubers & Root Vegetables
    ├── Legumes & Beans
    ├── Spices & Seasonings
    ├── Oils & Fats
    ├── Dairy & Alternatives
    ├── Beverages
    ├── Snacks & Pastries
    └── Condiments & Sauces

Usage:

    python manage.py seed_categories
    python manage.py seed_categories --dry-run
    python manage.py seed_categories --flush

Idempotent:

    Re-running creates missing categories and leaves existing ones
    untouched. Safe to run multiple times.

--flush:

    Deletes all existing categories first. Use with caution — this
    cascades to Product.category assignments. Intended for dev only.
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from ecommerce.models.category import Category


# =====================================================================
# TAXONOMY DEFINITION
# =====================================================================


TAXONOMY: dict[str, dict[str, list[str]]] = {
    "Food & Groceries": {
        "Meat & Poultry": [
            "Beef",
            "Goat Meat",
            "Lamb Meat",
            "Pork",
            "Chicken",
            "Turkey",
            "Duck",
            "Guinea Fowl",
            "Quail",
            "Eggs",
            "Offal",
        ],
        "Fish & Seafood": [
            "Tilapia",
            "Catfish",
            "Mackerel",
            "Sardine",
            "Tuna",
            "Pangasius",
            "Stockfish",
            "Smoked Fish",
            "Dried Fish",
            "Shrimp & Prawns",
            "Crayfish",
            "Periwinkle",
            "Octopus",
        ],
        "Vegetables & Leafy Greens": [
            "Spinach",
            "Tomatoes",
            "Peppers",
            "Onions",
            "Garlic",
            "Ginger",
            "Okra",
            "Bitter Leaf",
            "Waterleaf",
            "Cabbage",
            "Lettuce",
            "Cucumber",
            "Carrots",
            "Broccoli",
            "Cauliflower",
            "Mushrooms",
            "Spring Onions",
        ],
        "Fruits": [
            "Oranges",
            "Bananas",
            "Plantain",
            "Pineapples",
            "Mangoes",
            "Avocado",
            "Papaya",
            "Watermelon",
            "Guava",
            "Apples",
            "Grapes",
            "Tiger Nut",
            "Lemons & Limes",
        ],
        "Grains & Cereals": [
            "Rice",
            "Ofada Rice",
            "Basmati Rice",
            "Maize",
            "Millet",
            "Sorghum",
            "Wheat",
            "Barley",
            "Oats",
            "Garri",
            "Semolina",
            "Wheat Flour",
            "Pasta",
            "Noodles",
        ],
        "Tubers & Root Vegetables": [
            "Yam",
            "White Yam",
            "Water Yam",
            "Cassava",
            "Sweet Potato",
            "Cocoyam",
            "Irish Potato",
            "Cocoyam Leaves",
        ],
        "Legumes & Beans": [
            "Beans",
            "Cowpea",
            "Honey Beans",
            "Kidney Beans",
            "Lima Beans",
            "Green Peas",
            "Pigeon Pea",
            "Groundnuts",
            "Soybeans",
            "Moi Moi Mix",
        ],
        "Spices & Seasonings": [
            "Chili Peppers",
            "Scotch Bonnet",
            "Bell Peppers",
            "Dried Peppers",
            "Black Pepper",
            "Onion Powder",
            "Garlic Powder",
            "Ginger Powder",
            "Thyme",
            "Curry Powder",
            "Nutmeg",
            "Cloves",
            "Cinnamon",
            "Paprika",
            "Cumin",
            "Coriander",
            "Bay Leaves",
            "Stock Cubes",
            "Suya Spice",
            "Dawadawa",
            "Iru",
        ],
        "Oils & Fats": [
            "Palm Oil",
            "Vegetable Oil",
            "Olive Oil",
            "Coconut Oil",
            "Groundnut Oil",
            "Sesame Oil",
            "Butter",
            "Margarine",
            "Shea Butter",
        ],
        "Dairy & Alternatives": [
            "Fresh Milk",
            "Powdered Milk",
            "Evaporated Milk",
            "Yogurt",
            "Cheese",
            "Wara (Local Cheese)",
            "Ice Cream",
            "Buttermilk",
        ],
        "Beverages": [
            "Tea",
            "Coffee",
            "Chocolate Drink",
            "Zobo",
            "Palm Wine",
            "Kunu",
            "Fura",
            "Sobo",
            "Ginger Drink",
            "Lemon Drink",
            "Fresh Fruit Juice",
            "Coconut Water",
            "Bottled Water",
            "Soft Drinks",
        ],
        "Snacks & Pastries": [
            "Bread",
            "Agele",
            "Akara",
            "Moi Moi",
            "Meat Pie",
            "Scotch Egg",
            "Samosa",
            "Spring Roll",
            "Puff Puff",
            "Buns",
            "Chin Chin",
            "Kulikuli",
            "Pankasu",
            "Cassava Chips",
            "Plantain Chips",
            "Coconut Balls",
            "Groundnut Balls",
        ],
        "Condiments & Sauces": [
            "Tomato Paste",
            "Pepper Paste",
            "Pepper Sauce",
            "Oyo",
            "Ogiri",
            "Ogbono",
            "Egusi",
            "Palm Nut",
            "Banga Nut",
            "Soy Sauce",
            "Vinegar",
            "Ketchup",
            "Mayonnaise",
            "Mustard",
        ],
    },
}


# =====================================================================
# COMMAND
# =====================================================================


class Command(BaseCommand):
    help = (
        "Seed the base product category tree. Idempotent — safe to "
        "re-run."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be created without writing.",
        )
        parser.add_argument(
            "--flush",
            action="store_true",
            help=(
                "Delete all existing categories before seeding. "
                "DEV ONLY — cascades to Product.category assignments."
            ),
        )

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        dry_run = options["dry_run"]
        flush = options["flush"]

        if flush:
            existing_count = Category.objects.count()
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f"[dry-run] Would delete {existing_count} categories."
                    )
                )
            else:
                Category.objects.all().delete()
                self.stdout.write(
                    self.style.WARNING(
                        f"Flushed {existing_count} categories."
                    )
                )

        created = 0
        skipped = 0

        for top_name, subs in TAXONOMY.items():
            top_category, was_created = self._ensure_category(
                name=top_name,
                parent=None,
                dry_run=dry_run,
            )
            if was_created:
                created += 1
            else:
                skipped += 1

            for sub_name, leaves in subs.items():
                sub_category, was_created = self._ensure_category(
                    name=sub_name,
                    parent=top_category,
                    dry_run=dry_run,
                )
                if was_created:
                    created += 1
                else:
                    skipped += 1

                for leaf_name in leaves:
                    _, was_created = self._ensure_category(
                        name=leaf_name,
                        parent=sub_category,
                        dry_run=dry_run,
                    )
                    if was_created:
                        created += 1
                    else:
                        skipped += 1

        prefix = "[dry-run] " if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix}Done. Created: {created}, Skipped (already existed): {skipped}"
            )
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ensure_category(
        self,
        *,
        name: str,
        parent: Category | None,
        dry_run: bool,
    ) -> tuple[Category | None, bool]:
        """
        Return (category, was_created).

        Idempotent: if a category with the derived slug already exists
        under the same parent, return it without modification.
        """
        slug = slugify(name, allow_unicode=True)

        existing = Category.objects.filter(slug=slug).first()
        if existing is not None:
            return existing, False

        if dry_run:
            self.stdout.write(
                f"[dry-run] Would create: {name!r} "
                f"(slug={slug!r}, "
                f"parent={parent.name if parent else None!r})"
            )
            return None, True

        created = Category.objects.create(
            name=name,
            slug=slug,
            parent=parent,
            is_active=True,
        )
        self.stdout.write(f"  Created: {name}")
        return created, True