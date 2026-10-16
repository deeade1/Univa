# ecommerce/tests/test_models/test_inventory.py

from decimal import Decimal

from django.db import models as dj
from django.test import SimpleTestCase

from ecommerce.models.inventory import (
    Allocation,
    PreorderAllocation,
    PreorderReservation,
    Reservation,
    Stock,
    StockHistory,
)


class TestStockModel(SimpleTestCase):
    def test_quantity_is_decimal(self):
        field = Stock._meta.get_field("quantity")
        self.assertIsInstance(field, dj.DecimalField)
        self.assertEqual(field.max_digits, 12)
        self.assertEqual(field.decimal_places, 3)

    def test_low_stock_threshold_is_decimal(self):
        field = Stock._meta.get_field("low_stock_threshold")
        self.assertIsInstance(field, dj.DecimalField)

    def test_constraints_present(self):
        names = {c.name for c in Stock._meta.constraints}
        self.assertIn("stock_quantity_non_negative", names)
        self.assertIn("unique_warehouse_product_variant", names)

    def test_quantity_allocated_field_removed(self):
        """
        Regression test: Stock.quantity_allocated was a write-only
        cache maintained by allocation.py but never read for any
        decision. It was removed; availability is computed from
        Allocation rows.
        """
        field_names = {f.name for f in Stock._meta.get_fields()}
        self.assertNotIn("quantity_allocated", field_names)


class TestStockHistoryModel(SimpleTestCase):
    def test_quantity_fields_are_decimal(self):
        for field_name in (
            "quantity_change",
            "previous_quantity",
            "new_quantity",
            "reserved_change",
            "previous_reserved",
            "new_reserved",
        ):
            field = StockHistory._meta.get_field(field_name)
            self.assertIsInstance(field, dj.DecimalField, field_name)
            self.assertEqual(field.max_digits, 12)
            self.assertEqual(field.decimal_places, 3)

    def test_change_type_choices(self):
        field = StockHistory._meta.get_field("change_type")
        names = {v for v, _ in field.choices}
        self.assertIn("restock", names)
        self.assertIn("removal", names)


class TestAllocationModel(SimpleTestCase):
    def test_quantity_allocated_is_decimal(self):
        field = Allocation._meta.get_field("quantity_allocated")
        self.assertIsInstance(field, dj.DecimalField)
        self.assertEqual(field.max_digits, 12)
        self.assertEqual(field.decimal_places, 3)


class TestReservationModel(SimpleTestCase):
    def test_quantity_reserved_is_decimal(self):
        field = Reservation._meta.get_field("quantity_reserved")
        self.assertIsInstance(field, dj.DecimalField)


class TestPreorderModels(SimpleTestCase):
    def test_preorder_allocation_quantity_is_decimal(self):
        field = PreorderAllocation._meta.get_field("quantity")
        self.assertIsInstance(field, dj.DecimalField)

    def test_preorder_reservation_quantity_is_decimal(self):
        field = PreorderReservation._meta.get_field("quantity_reserved")
        self.assertIsInstance(field, dj.DecimalField)


class TestDeletedSatellites(SimpleTestCase):
    DELETED = (
        "ReturnsManagement",
        "InventoryPrediction",
        "InventoryHealthMetrics",
        "InterWarehouseTransfer",
        "WarehousePerformance",
        "WarehouseTask",
    )

    def test_satellites_removed(self):
        import ecommerce.models as models_module
        for name in self.DELETED:
            self.assertFalse(
                hasattr(models_module, name),
                f"{name} should have been deleted",
            )