"""
graphq.core.types
=================

Centralized type registry for all custom GraphQL type converters
and base scalars (Money, TaxedMoney, Vector, GIS, JSON, etc.).
"""

import logging

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------
# Register all type converters automatically
# -------------------------------------------------------------------

try:
    from . import gis

    logger.debug(
        "GIS converters registered successfully."
    )
except Exception as e:
    logger.warning(
        "Failed to register GIS converters: %s",
        e,
    )


try:
    from . import money

    logger.debug(
        "Money converters registered successfully."
    )
except Exception as e:
    logger.warning(
        "Failed to register money converters: %s",
        e,
    )


# -------------------------------------------------------------------
# Re-export common GraphQL types for convenience
# -------------------------------------------------------------------

from .common import (
    TYPES_WITH_DOUBLE_ID_AVAILABLE,
    Job,
    LanguageDisplay,
    NonNullList,
    PriceInput,
    PriceRangeInput,
    SeoInput,
    TaxType,
    ThumbnailField,
    TimePeriod,
    TimePeriodInputType,
    Weight,
)

from .money import (
    VAT,
    Money,
    MoneyRange,
    MoneyRangeType,
    MoneyType,
    ReducedRate,
    TaxedMoney,
    TaxedMoneyRange,
    TaxedMoneyRangeType,
    TaxedMoneyType,
    VectorScalar,
)


__all__ = [
    "TYPES_WITH_DOUBLE_ID_AVAILABLE",
    "Job",
    "LanguageDisplay",
    "NonNullList",
    "PriceInput",
    "PriceRangeInput",
    "SeoInput",
    "TaxType",
    "ThumbnailField",
    "TimePeriod",
    "TimePeriodInputType",
    "Weight",
    "Money",
    "MoneyRange",
    "TaxedMoney",
    "TaxedMoneyRange",
    "VAT",
    "ReducedRate",
    "VectorScalar",
    "MoneyType",
    "MoneyRangeType",
    "TaxedMoneyType",
    "TaxedMoneyRangeType",
]