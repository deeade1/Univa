# apps/backend/core/pricing/serialization.py

"""
Serialization helpers for canonical pricing values.

These functions provide stable application-level representations that can
be consumed by GraphQL, REST, events, Celery tasks and persistence layers.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from .money import Money
from .money_range import MoneyRange
from .taxed_money import TaxedMoney


def money_to_dict(money: Money) -> dict[str, Any]:
    return {
        "amount": str(money.amount),
        "currency": money.currency,
    }


def money_from_dict(data: dict[str, Any]) -> Money:
    return Money(
        amount=Decimal(str(data["amount"])),
        currency=data["currency"],
    )


def taxed_money_to_dict(
    value: TaxedMoney,
) -> dict[str, Any]:
    return {
        "net": money_to_dict(value.net),
        "gross": money_to_dict(value.gross),
        "tax": money_to_dict(value.tax),
        "currency": value.currency,
    }


def taxed_money_from_dict(
    data: dict[str, Any],
) -> TaxedMoney:
    return TaxedMoney(
        net=money_from_dict(data["net"]),
        gross=money_from_dict(data["gross"]),
    )


def money_range_to_dict(
    value: MoneyRange,
) -> dict[str, Any]:
    return {
        "start": money_to_dict(value.start),
        "stop": money_to_dict(value.stop),
        "currency": value.currency,
    }