# apps/backend/graphq/core/types/money.py

"""
Univa GraphQL money and pricing types.

This module is the GraphQL representation layer for the canonical
Univa pricing domain.

Canonical pricing implementation:

    core.pricing
        ├── money.py
        ├── taxed_money.py
        ├── money_field.py
        └── taxed_money_field.py

This module MUST NOT depend on django-prices.

Supported conversions:

    core.pricing.MoneyField
        -> GraphQL Money

    core.pricing.TaxedMoneyField
        -> GraphQL TaxedMoney

    pgvector VectorField
        -> GraphQL VectorScalar

    PostgreSQL SearchVectorField
        -> GraphQL JSONString

    Django JSONField
        -> GraphQL JSONString / VectorScalar

Architecture
------------

    Django models
          │
          ▼
    core.pricing
          │
          ▼
    graphq.core.types.money
          │
          ▼
    GraphQL schema

GraphQL is an adapter.

It does not own:

    - pricing calculations
    - currency validation
    - tax calculation
    - money persistence
    - pricing business rules
"""

from __future__ import annotations

import json
import logging
from decimal import Decimal
from typing import Any

import graphene
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from graphene.types import Scalar
from graphene_django.converter import convert_django_field
from graphql.language import ast

from core.pricing.money import Money as PricingMoney
from core.pricing.money_field import MoneyField
from core.pricing.taxed_money import TaxedMoney as PricingTaxedMoney
from core.pricing.taxed_money_field import TaxedMoneyField


logger = logging.getLogger(__name__)


# ============================================================================
# Optional NumPy
# ============================================================================

try:
    import numpy as np
except ImportError:
    np = None


# ============================================================================
# Optional pgvector
# ============================================================================

try:
    from pgvector.django import VectorField
except ImportError:
    VectorField = None


# ============================================================================
# Money
# ============================================================================


class Money(graphene.ObjectType):
    """
    GraphQL representation of a canonical Univa Money value.

    Python source:

        core.pricing.money.Money

    GraphQL:

        {
            amount
            currency
        }
    """

    amount = graphene.Float(
        required=True,
        description="Monetary amount.",
    )

    currency = graphene.String(
        required=True,
        description="ISO 4217 currency code.",
    )

    localized = graphene.String(
        description="Localized monetary representation.",
    )

    class Meta:
        description = (
            "Represents a monetary amount in a specific currency."
        )

    @staticmethod
    def resolve_amount(
        root: PricingMoney | Any,
        info,
    ):
        amount = getattr(root, "amount", None)

        if amount is None:
            return None

        if isinstance(amount, Decimal):
            return float(amount)

        try:
            return float(amount)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def resolve_currency(
        root: PricingMoney | Any,
        info,
    ):
        return getattr(root, "currency", None)

    @staticmethod
    def resolve_localized(
        root: PricingMoney | Any,
        info,
    ):
        """
        Return a simple canonical string representation.

        Formatting remains deliberately lightweight here.

        Full locale-aware formatting belongs in:

            core.pricing.formatting
        """

        amount = getattr(root, "amount", None)
        currency = getattr(root, "currency", None)

        if amount is None or not currency:
            return None

        return f"{amount} {currency}"


# ============================================================================
# Money Range
# ============================================================================


class MoneyRange(graphene.ObjectType):
    """
    GraphQL representation of a monetary range.
    """

    start = graphene.Field(
        Money,
        description="Lower monetary bound.",
    )

    stop = graphene.Field(
        Money,
        description="Upper monetary bound.",
    )

    class Meta:
        description = (
            "Represents a range of monetary values."
        )


# ============================================================================
# Taxed Money
# ============================================================================


class TaxedMoney(graphene.ObjectType):
    """
    GraphQL representation of canonical Univa TaxedMoney.

    Python source:

        core.pricing.taxed_money.TaxedMoney

    Tax is derived by the canonical domain object:

        tax = gross - net
    """

    currency = graphene.String(
        required=True,
        description="ISO 4217 currency code.",
    )

    net = graphene.Field(
        Money,
        required=True,
        description="Amount excluding tax.",
    )

    gross = graphene.Field(
        Money,
        required=True,
        description="Amount including tax.",
    )

    tax = graphene.Field(
        Money,
        required=True,
        description="Derived tax amount.",
    )

    class Meta:
        description = (
            "Represents monetary values including and excluding tax."
        )

    @staticmethod
    def resolve_currency(
        root: PricingTaxedMoney | Any,
        info,
    ):
        currency = getattr(root, "currency", None)

        if currency:
            return currency

        net = getattr(root, "net", None)

        return getattr(net, "currency", None)

    @staticmethod
    def resolve_net(
        root: PricingTaxedMoney | Any,
        info,
    ):
        return getattr(root, "net", None)

    @staticmethod
    def resolve_gross(
        root: PricingTaxedMoney | Any,
        info,
    ):
        return getattr(root, "gross", None)

    @staticmethod
    def resolve_tax(
        root: PricingTaxedMoney | Any,
        info,
    ):
        tax = getattr(root, "tax", None)

        if tax is not None:
            return tax

        net = getattr(root, "net", None)
        gross = getattr(root, "gross", None)

        if net is None or gross is None:
            return None

        try:
            return gross - net
        except (TypeError, ValueError):
            return None


# ============================================================================
# Taxed Money Range
# ============================================================================


class TaxedMoneyRange(graphene.ObjectType):
    """
    GraphQL representation of a taxed-money range.
    """

    start = graphene.Field(
        TaxedMoney,
        description="Lower taxed-money bound.",
    )

    stop = graphene.Field(
        TaxedMoney,
        description="Upper taxed-money bound.",
    )

    class Meta:
        description = (
            "Represents a range of taxed monetary values."
        )


# ============================================================================
# VAT
# ============================================================================


class ReducedRate(graphene.ObjectType):
    """
    Reduced VAT rate.
    """

    rate = graphene.Float(
        required=True,
        description="Reduced VAT rate in percent.",
    )

    rate_type = graphene.String(
        required=True,
        description="Type of goods or service.",
    )


class VAT(graphene.ObjectType):
    """
    VAT configuration for a country.
    """

    country_code = graphene.String(
        required=True,
        description="ISO country code.",
    )

    standard_rate = graphene.Float(
        description="Standard VAT rate in percent.",
    )

    reduced_rates = graphene.List(
        graphene.NonNull(ReducedRate),
        required=True,
        description="Reduced VAT rates.",
    )

    class Meta:
        description = (
            "VAT rate configuration."
        )


# ============================================================================
# VAT Resolvers
# ============================================================================


def _resolve_vat_data(
    root,
) -> dict[str, Any]:
    """
    Resolve VAT data from either an object or dictionary.
    """

    data = getattr(
        root,
        "data",
        None,
    )

    if isinstance(data, dict):
        return data

    if isinstance(root, dict):
        return root

    return {}


def _resolve_vat_country_code(root):
    value = getattr(
        root,
        "country_code",
        None,
    )

    if value:
        return value

    data = _resolve_vat_data(root)

    return data.get("country_code")


def _resolve_vat_standard_rate(root):
    data = _resolve_vat_data(root)

    return data.get("standard_rate")


def _resolve_vat_reduced_rates(root):
    data = _resolve_vat_data(root)

    reduced = data.get(
        "reduced_rates"
    ) or {}

    if not isinstance(
        reduced,
        dict,
    ):
        return []

    return [
        ReducedRate(
            rate=rate,
            rate_type=rate_type,
        )
        for rate_type, rate in reduced.items()
    ]


VAT.resolve_country_code = staticmethod(
    _resolve_vat_country_code
)

VAT.resolve_standard_rate = staticmethod(
    _resolve_vat_standard_rate
)

VAT.resolve_reduced_rates = staticmethod(
    _resolve_vat_reduced_rates
)


# ============================================================================
# Vector Scalar
# ============================================================================


class VectorScalar(Scalar):
    """
    GraphQL scalar for vector / embedding values.

    Supports:

        - Python lists
        - tuples
        - NumPy arrays
        - JSON strings
    """

    class Meta:
        description = (
            "Vector or embedding value represented as "
            "JSON-compatible data."
        )

    @staticmethod
    def serialize(value):
        if value is None:
            return None

        if (
            np is not None
            and isinstance(value, np.ndarray)
        ):
            return value.tolist()

        if isinstance(
            value,
            tuple,
        ):
            return list(value)

        if isinstance(
            value,
            list,
        ):
            return value

        if isinstance(
            value,
            str,
        ):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value

        return value

    @staticmethod
    def parse_value(value):
        if value is None:
            return None

        if (
            np is not None
            and isinstance(value, np.ndarray)
        ):
            return value.tolist()

        if isinstance(
            value,
            (list, tuple),
        ):
            return list(value)

        if isinstance(
            value,
            str,
        ):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value

        return value

    @staticmethod
    def parse_literal(node):
        if isinstance(
            node,
            ast.ListValue,
        ):
            values = []

            for item in node.values:
                if isinstance(
                    item,
                    (
                        ast.FloatValue,
                        ast.IntValue,
                    ),
                ):
                    values.append(
                        float(item.value)
                    )
                else:
                    return None

            return values

        if isinstance(
            node,
            ast.StringValue,
        ):
            try:
                return json.loads(
                    node.value
                )
            except json.JSONDecodeError:
                return node.value

        return None


# ============================================================================
# Django -> GraphQL: MoneyField
# ============================================================================


@convert_django_field.register(
    MoneyField
)
def convert_money_field(
    field,
    registry=None,
):
    """
    Convert the canonical Univa MoneyField to GraphQL Money.

    Important:

        MoneyField is a logical/compound field.

    The actual database values live in:

        amount_field
        currency_field
    """

    logger.debug(
        "Registering GraphQL MoneyField converter for %s",
        getattr(
            field,
            "name",
            "<unknown>",
        ),
    )

    return graphene.Field(
        Money,
        required=not getattr(
            field,
            "null",
            False,
        ),
        description=(
            getattr(
                field,
                "help_text",
                None,
            )
            or "Monetary amount with currency."
        ),
    )


# ============================================================================
# Django -> GraphQL: TaxedMoneyField
# ============================================================================


@convert_django_field.register(
    TaxedMoneyField
)
def convert_taxed_money_field(
    field,
    registry=None,
):
    """
    Convert the canonical Univa TaxedMoneyField to GraphQL TaxedMoney.
    """

    logger.debug(
        "Registering GraphQL TaxedMoneyField converter for %s",
        getattr(
            field,
            "name",
            "<unknown>",
        ),
    )

    return graphene.Field(
        TaxedMoney,
        required=not getattr(
            field,
            "null",
            False,
        ),
        description=(
            getattr(
                field,
                "help_text",
                None,
            )
            or (
                "Monetary amount including "
                "and excluding tax."
            )
        ),
    )


# ============================================================================
# pgvector converter
# ============================================================================


if VectorField is not None:

    @convert_django_field.register(
        VectorField
    )
    def convert_vector_field(
        field,
        registry=None,
    ):
        """
        Convert pgvector VectorField to VectorScalar.
        """

        logger.debug(
            "Registering GraphQL VectorField converter for %s",
            getattr(
                field,
                "name",
                "<unknown>",
            ),
        )

        return graphene.Field(
            VectorScalar,
            required=not getattr(
                field,
                "null",
                False,
            ),
            description=(
                getattr(
                    field,
                    "help_text",
                    None,
                )
                or "Vector embedding."
            ),
        )


# ============================================================================
# JSONField converter
# ============================================================================


@convert_django_field.register(
    models.JSONField
)
def convert_json_field(
    field,
    registry=None,
):
    """
    Convert Django JSONField.

    Fields whose names indicate vector/embedding data use
    VectorScalar.

    Other JSON fields use Graphene JSONString.
    """

    field_name = (
        getattr(
            field,
            "name",
            "",
        )
        or ""
    ).lower()

    description = (
        getattr(
            field,
            "help_text",
            None,
        )
        or "JSON data."
    )

    if (
        "vector" in field_name
        or "embedding" in field_name
    ):
        return graphene.Field(
            VectorScalar,
            required=not getattr(
                field,
                "null",
                False,
            ),
            description=description,
        )

    return graphene.JSONString(
        required=not getattr(
            field,
            "null",
            False,
        ),
        description=description,
    )


# ============================================================================
# PostgreSQL SearchVectorField
# ============================================================================


@convert_django_field.register(
    SearchVectorField
)
def convert_search_vector_field(
    field,
    registry=None,
):
    """
    Convert PostgreSQL SearchVectorField.

    Search vectors are database implementation details and are
    represented as JSON-compatible data at the GraphQL boundary.
    """

    return graphene.JSONString(
        required=not getattr(
            field,
            "null",
            False,
        ),
        description=(
            getattr(
                field,
                "help_text",
                None,
            )
            or "PostgreSQL search vector."
        ),
    )


# ============================================================================
# Backwards-compatible aliases
# ============================================================================

MoneyType = Money
MoneyRangeType = MoneyRange
TaxedMoneyType = TaxedMoney
TaxedMoneyRangeType = TaxedMoneyRange


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "Money",
    "MoneyRange",
    "TaxedMoney",
    "TaxedMoneyRange",
    "ReducedRate",
    "VAT",
    "VectorScalar",
    "MoneyType",
    "MoneyRangeType",
    "TaxedMoneyType",
    "TaxedMoneyRangeType",
]
