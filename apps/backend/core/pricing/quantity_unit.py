# apps/backend/core/pricing/quantity_unit.py

"""
Canonical Univa quantity units.

Quantity is a first-class domain concept, sibling to Money and Weight:

    line_total = unit_price × quantity

Quantity is expressed as:

    (amount: Decimal, unit: QuantityUnit)

The unit answers "of what?" — pieces, kilograms, litres, bunches,
cups, tablespoons.

This module defines the canonical set of units and the metadata
each one carries. It has no Django dependency and no pricing
dependency (though pricing depends on it).

Domain applications should import from here, not redefine their
own unit lists.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum


class QuantityUnit(StrEnum):
    """
    Canonical quantity units.

    Grouped by family so that consumers can make decisions like
    "is this a decimal-quantity unit?" or "is this a count unit?"
    without a lookup table.

    Codes are lowercase to match ISO-ish conventions; display
    labels are handled by the presentation layer.
    """

    # ------------------------------------------------------------------
    # Discrete / count units  (integer quantity only)
    # ------------------------------------------------------------------
    UNIT = "unit"
    PIECE = "piece"
    BUNCH = "bunch"
    BAG = "bag"
    CUP = "cup"
    TABLESPOON = "tablespoon"
    TEASPOON = "teaspoon"
    PACK = "pack"
    BOX = "box"
    CARTON = "carton"
    DOZEN = "dozen"
    SACHET = "sachet"
    BOTTLE = "bottle"
    CAN = "can"
    TUBER = "tuber"
    HEAD = "head"
    BUNCH_OF = "bunch_of"  # e.g. bunch_of ugu
    STICK = "stick"

    # ------------------------------------------------------------------
    # Continuous / measured units  (decimal quantity allowed)
    # ------------------------------------------------------------------
    KG = "kg"
    G = "g"
    L = "l"
    ML = "ml"
    M = "m"
    CM = "cm"

    # ------------------------------------------------------------------
    # Weight aliases (optional; kept for market vernacular)
    # ------------------------------------------------------------------
    GRAM = "gram"
    KILOGRAM = "kilogram"
    LITRE = "litre"
    MILLILITRE = "millilitre"
    
    @classmethod
    def choices(cls) -> list[tuple[str, str]]:
        """
        Django `choices=` compatible list.

        Returns:
            [(value, label), ...] sorted by label for stable admin
            ordering.
        """
        return sorted(
            ((unit.value, label(unit)) for unit in cls),
            key=lambda pair: pair[1],
        )

# ======================================================================
# Unit metadata
# ======================================================================


#: Units that allow fractional quantity (2.5 kg, 0.75 l).
#: Everything else must be ordered in whole numbers.
CONTINUOUS_UNITS: frozenset[QuantityUnit] = frozenset({
    QuantityUnit.KG,
    QuantityUnit.G,
    QuantityUnit.L,
    QuantityUnit.ML,
    QuantityUnit.M,
    QuantityUnit.CM,
    QuantityUnit.GRAM,
    QuantityUnit.KILOGRAM,
    QuantityUnit.LITRE,
    QuantityUnit.MILLILITRE,
})


#: Units that represent discrete, countable things.
#: Derived from CONTINUOUS_UNITS to guarantee the partition is total.
DISCRETE_UNITS: frozenset[QuantityUnit] = frozenset(
    QuantityUnit
) - CONTINUOUS_UNITS


#: Decimal precision appropriate for each continuous unit.
#: Discrete units always use 0 decimal places.
#:
#: Values:
#:   KG       -> 3   (2.500 kg)
#:   G        -> 0   (250 g)
#:   L        -> 3   (0.750 l)
#:   ML       -> 0   (500 ml)
#:   M        -> 3   (1.250 m)
#:   CM       -> 0   (75 cm)
DECIMAL_PLACES_BY_UNIT: dict[QuantityUnit, int] = {
    QuantityUnit.KG: 3,
    QuantityUnit.GRAM: 3,
    QuantityUnit.KILOGRAM: 3,
    QuantityUnit.G: 0,
    QuantityUnit.L: 3,
    QuantityUnit.LITRE: 3,
    QuantityUnit.MILLILITRE: 3,
    QuantityUnit.ML: 0,
    QuantityUnit.M: 3,
    QuantityUnit.CM: 0,
}


#: Human-readable labels. Useful for admin, invoices, receipts.
#:
#: Note: real presentation should go through translations
#: (gettext) — these are English fallbacks.
LABELS: dict[QuantityUnit, str] = {
    # Discrete
    QuantityUnit.UNIT: "Unit",
    QuantityUnit.PIECE: "Piece",
    QuantityUnit.BUNCH: "Bunch",
    QuantityUnit.BAG: "Bag",
    QuantityUnit.CUP: "Cup",
    QuantityUnit.TABLESPOON: "Tablespoon",
    QuantityUnit.TEASPOON: "Teaspoon",
    QuantityUnit.PACK: "Pack",
    QuantityUnit.BOX: "Box",
    QuantityUnit.CARTON: "Carton",
    QuantityUnit.DOZEN: "Dozen",
    QuantityUnit.SACHET: "Sachet",
    QuantityUnit.BOTTLE: "Bottle",
    QuantityUnit.CAN: "Can",
    QuantityUnit.TUBER: "Tuber",
    QuantityUnit.HEAD: "Head",
    QuantityUnit.BUNCH_OF: "Bunch",
    QuantityUnit.STICK: "Stick",

    # Continuous
    QuantityUnit.KG: "Kilogram",
    QuantityUnit.G: "Gram",
    QuantityUnit.L: "Litre",
    QuantityUnit.ML: "Millilitre",
    QuantityUnit.M: "Metre",
    QuantityUnit.CM: "Centimetre",

    # Weight aliases
    QuantityUnit.GRAM: "Gram",
    QuantityUnit.KILOGRAM: "Kilogram",
    QuantityUnit.LITRE: "Litre",
    QuantityUnit.MILLILITRE: "Millilitre",
}


#: Abbreviations for compact UI (receipts, chips, filters).
ABBREVIATIONS: dict[QuantityUnit, str] = {
    QuantityUnit.UNIT: "unit",
    QuantityUnit.PIECE: "pc",
    QuantityUnit.BUNCH: "bch",
    QuantityUnit.BAG: "bag",
    QuantityUnit.CUP: "cup",
    QuantityUnit.TABLESPOON: "tbsp",
    QuantityUnit.TEASPOON: "tsp",
    QuantityUnit.PACK: "pk",
    QuantityUnit.BOX: "box",
    QuantityUnit.CARTON: "ctn",
    QuantityUnit.DOZEN: "dz",
    QuantityUnit.SACHET: "sch",
    QuantityUnit.BOTTLE: "btl",
    QuantityUnit.CAN: "can",
    QuantityUnit.TUBER: "tbr",
    QuantityUnit.HEAD: "hd",
    QuantityUnit.BUNCH_OF: "bch",
    QuantityUnit.STICK: "stk",
    QuantityUnit.KG: "kg",
    QuantityUnit.G: "g",
    QuantityUnit.L: "l",
    QuantityUnit.ML: "ml",
    QuantityUnit.M: "m",
    QuantityUnit.CM: "cm",
    QuantityUnit.GRAM: "g",
    QuantityUnit.KILOGRAM: "kg",
    QuantityUnit.LITRE: "l",
    QuantityUnit.MILLILITRE: "ml",
}


# ======================================================================
# Helpers
# ======================================================================


def is_continuous(unit: QuantityUnit) -> bool:
    """True if the unit allows fractional quantities."""
    return unit in CONTINUOUS_UNITS


def is_discrete(unit: QuantityUnit) -> bool:
    """True if the unit must be ordered in whole numbers."""
    return unit in DISCRETE_UNITS


def decimal_places(unit: QuantityUnit) -> int:
    """
    Decimal places appropriate for storing a quantity in this unit.

    Discrete units return 0. Continuous units return their
    unit-specific precision (see DECIMAL_PLACES_BY_UNIT).
    """
    return DECIMAL_PLACES_BY_UNIT.get(unit, 0)


def quantize_quantity(quantity: Decimal, unit: QuantityUnit) -> Decimal:
    """
    Snap a Decimal quantity to the correct precision for its unit.

    Raises ValueError if a discrete unit receives a non-integer
    quantity — callers should validate before persisting.
    """
    if is_discrete(unit) and quantity != quantity.to_integral_value():
        raise ValueError(
            f"Unit {unit!r} is discrete; got fractional quantity "
            f"{quantity!r}"
        )

    exponent = Decimal(1).scaleb(-decimal_places(unit))
    return quantity.quantize(exponent)


def label(unit: QuantityUnit) -> str:
    """Full display label."""
    return LABELS.get(unit, str(unit))


def abbreviation(unit: QuantityUnit) -> str:
    """Compact display abbreviation."""
    return ABBREVIATIONS.get(unit, str(unit))


def choices() -> list[tuple[str, str]]:
    """
    Django `choices=` compatible list.

    Returns:
        [(value, label), ...] sorted by label for stable admin ordering.
    """
    return sorted(
        ((unit.value, label(unit)) for unit in QuantityUnit),
        key=lambda pair: pair[1],
    )