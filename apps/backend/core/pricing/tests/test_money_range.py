import pytest

from core.pricing import (
    CurrencyMismatchError,
    Money,
    MoneyRange,
)


def test_money_range():
    price_range = MoneyRange(
        start=Money("1000", "NGN"),
        stop=Money("5000", "NGN"),
    )

    assert price_range.contains(
        Money("3000", "NGN")
    )


def test_money_range_excludes_value_outside_range():
    price_range = MoneyRange(
        start=Money("1000", "NGN"),
        stop=Money("5000", "NGN"),
    )

    assert not price_range.contains(
        Money("6000", "NGN")
    )


def test_money_range_currency_mismatch():
    price_range = MoneyRange(
        start=Money("1000", "NGN"),
        stop=Money("5000", "NGN"),
    )

    with pytest.raises(CurrencyMismatchError):
        price_range.contains(
            Money("3000", "USD")
        )