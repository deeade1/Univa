# apps/backend/core/tests/test_quantity_unit.py

from decimal import Decimal

from django.test import SimpleTestCase

from core.pricing.quantity_unit import (
    CONTINUOUS_UNITS,
    DISCRETE_UNITS,
    QuantityUnit,
    abbreviation,
    decimal_places,
    is_continuous,
    is_discrete,
    label,
    quantize_quantity,
)


class TestPartition(SimpleTestCase):
    def test_partition_is_total(self):
        self.assertEqual(
            CONTINUOUS_UNITS | DISCRETE_UNITS,
            set(QuantityUnit),
        )

    def test_partition_is_disjoint(self):
        self.assertEqual(CONTINUOUS_UNITS & DISCRETE_UNITS, set())


class TestContinuous(SimpleTestCase):
    def test_kg_is_continuous(self):
        self.assertTrue(is_continuous(QuantityUnit.KG))

    def test_unit_is_not_continuous(self):
        self.assertFalse(is_continuous(QuantityUnit.UNIT))


class TestDiscrete(SimpleTestCase):
    def test_piece_is_discrete(self):
        self.assertTrue(is_discrete(QuantityUnit.PIECE))

    def test_l_is_not_discrete(self):
        self.assertFalse(is_discrete(QuantityUnit.L))


class TestDecimalPlaces(SimpleTestCase):
    def test_kg(self):
        self.assertEqual(decimal_places(QuantityUnit.KG), 3)

    def test_g(self):
        self.assertEqual(decimal_places(QuantityUnit.G), 0)

    def test_l(self):
        self.assertEqual(decimal_places(QuantityUnit.L), 3)

    def test_ml(self):
        self.assertEqual(decimal_places(QuantityUnit.ML), 0)

    def test_unit(self):
        self.assertEqual(decimal_places(QuantityUnit.UNIT), 0)

    def test_piece(self):
        self.assertEqual(decimal_places(QuantityUnit.PIECE), 0)


class TestQuantize(SimpleTestCase):
    def test_continuous_quantizes_to_precision(self):
        self.assertEqual(
            quantize_quantity(Decimal("2.5"), QuantityUnit.KG),
            Decimal("2.500"),
        )

    def test_discrete_accepts_whole(self):
        self.assertEqual(
            quantize_quantity(Decimal("3"), QuantityUnit.UNIT),
            Decimal("3"),
        )

    def test_discrete_rejects_fractional(self):
        with self.assertRaises(ValueError):
            quantize_quantity(Decimal("2.5"), QuantityUnit.UNIT)


class TestLabels(SimpleTestCase):
    def test_label(self):
        self.assertEqual(label(QuantityUnit.KG), "Kilogram")

    def test_abbreviation(self):
        self.assertEqual(abbreviation(QuantityUnit.KG), "kg")