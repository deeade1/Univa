# apps/backend/ecommerce/tests/test_models/test_inventory_services.py

"""
Tests for Stock mutation services.

Focus:

    - increase_stock and decrease_stock raise ValidationError, not
      ValueError, on invalid input
    - decrease_stock respects available_quantity (which reads from
      Allocation rows)
    - increase_stock and decrease_stock create StockHistory rows
    - StockHistory.create_from_stock_change raises rather than
      silently clamping negative previous_quantity
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from ecommerce.models.inventory import Stock, StockHistory
from ecommerce.models.product import Product, ProductType, ProductVariant
from ecommerce.models.warehouse import Warehouse


# These tests reuse the same fixture pattern as test_warehouse.py.
# If the fixture below conflicts with anything you already have,
# merge rather than duplicate.


class InventoryTestFixture(TestCase):

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth import get_user_model

        User = get_user_model()

        cls.user = User.objects.create_user(
            email="inventory-fixture@example.com",
            password="test-password",
        )

    def make_warehouse(self, slug):
        from accounts.models.address import Address

        address = Address.objects.create(
            user=self.user,
            first_name="Test",
            last_name="Warehouse",
            street_address_1=f"{slug} address",
            city="Lagos",
            country="NG",
        )

        return Warehouse.objects.create(
            name=slug.title(),
            slug=slug,
            address=address,
        )

    def make_product_variant(self, slug):
        product_type = ProductType.objects.create(
            name=slug.title(),
            slug=f"{slug}-type",
            has_variants=True,
            is_shipping_required=True,
            is_digital=False,
        )
        product = Product.objects.create(
            product_type=product_type,
            name=slug.title(),
            slug=slug,
        )
        return ProductVariant.objects.create(
            product=product,
            name="Default",
        )

    def make_stock(self, *, warehouse_slug, variant_slug, quantity):
        warehouse = self.make_warehouse(warehouse_slug)
        variant = self.make_product_variant(variant_slug)

        return Stock.objects.create(
            warehouse=warehouse,
            product_variant=variant,
            quantity=quantity,
        )


class StockIncreaseTests(InventoryTestFixture):

    def test_increase_stock_adds_quantity(self):
        stock = self.make_stock(
            warehouse_slug="inc-wh",
            variant_slug="inc-var",
            quantity=Decimal("10"),
        )

        stock.increase_stock(Decimal("5"))

        stock.refresh_from_db()
        self.assertEqual(stock.quantity, Decimal("15"))

    def test_increase_stock_records_history(self):
        stock = self.make_stock(
            warehouse_slug="inc-hist-wh",
            variant_slug="inc-hist-var",
            quantity=Decimal("10"),
        )

        stock.increase_stock(Decimal("5"), reason="Restock")

        history = StockHistory.objects.filter(stock=stock).latest("created_at")
        self.assertEqual(history.quantity_change, Decimal("5"))
        self.assertEqual(history.previous_quantity, Decimal("10"))
        self.assertEqual(history.new_quantity, Decimal("15"))

    def test_increase_stock_raises_validation_error_for_zero(self):
        stock = self.make_stock(
            warehouse_slug="inc-zero-wh",
            variant_slug="inc-zero-var",
            quantity=Decimal("10"),
        )

        with self.assertRaises(ValidationError):
            stock.increase_stock(Decimal("0"))

    def test_increase_stock_raises_validation_error_for_negative(self):
        stock = self.make_stock(
            warehouse_slug="inc-neg-wh",
            variant_slug="inc-neg-var",
            quantity=Decimal("10"),
        )

        with self.assertRaises(ValidationError):
            stock.increase_stock(Decimal("-5"))


class StockDecreaseTests(InventoryTestFixture):

    def test_decrease_stock_removes_quantity(self):
        stock = self.make_stock(
            warehouse_slug="dec-wh",
            variant_slug="dec-var",
            quantity=Decimal("10"),
        )

        stock.decrease_stock(Decimal("3"))

        stock.refresh_from_db()
        self.assertEqual(stock.quantity, Decimal("7"))

    def test_decrease_stock_raises_validation_error_when_insufficient(self):
        stock = self.make_stock(
            warehouse_slug="dec-insuf-wh",
            variant_slug="dec-insuf-var",
            quantity=Decimal("3"),
        )

        with self.assertRaises(ValidationError):
            stock.decrease_stock(Decimal("10"))

        stock.refresh_from_db()
        self.assertEqual(stock.quantity, Decimal("3"))

    def test_decrease_stock_raises_validation_error_for_zero(self):
        stock = self.make_stock(
            warehouse_slug="dec-zero-wh",
            variant_slug="dec-zero-var",
            quantity=Decimal("10"),
        )

        with self.assertRaises(ValidationError):
            stock.decrease_stock(Decimal("0"))


class StockHistoryTests(InventoryTestFixture):

    def test_create_from_stock_change_computes_previous_quantity(self):
        stock = self.make_stock(
            warehouse_slug="hist-wh",
            variant_slug="hist-var",
            quantity=Decimal("15"),
        )

        history = StockHistory.create_from_stock_change(
            stock=stock,
            quantity_change=Decimal("5"),
            change_type=StockHistory.ChangeType.RESTOCK,
        )

        self.assertEqual(history.previous_quantity, Decimal("10"))
        self.assertEqual(history.new_quantity, Decimal("15"))

    def test_create_from_stock_change_raises_on_negative_previous(self):
        """
        Regression test: the previous implementation used
        max(previous_quantity, 0), which silently clamped a
        nonsensical input to zero. Now it raises.
        """
        stock = self.make_stock(
            warehouse_slug="hist-neg-wh",
            variant_slug="hist-neg-var",
            quantity=Decimal("3"),
        )

        with self.assertRaises(ValidationError):
            StockHistory.create_from_stock_change(
                stock=stock,
                quantity_change=Decimal("10"),  # implies previous = -7
                change_type=StockHistory.ChangeType.REMOVAL,
            )