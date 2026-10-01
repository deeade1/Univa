from decimal import Decimal

import pytest

from core.pricing import (
    CurrencyMismatchError,
    InvalidCurrencyError,
    InvalidMoneyError,
    Money,
)


def test_money_creation():
    money = Money("1500.00", "NGN")

    assert money.amount == Decimal("1500.00")
    assert money.currency == "NGN"


def test_currency_is_normalized():
    money = Money("100", "ngn")

    assert money.currency == "NGN"


def test_money_addition():
    result = Money("1000", "NGN") + Money("500", "NGN")

    assert result == Money("1500", "NGN")


def test_money_subtraction():
    result = Money("1000", "NGN") - Money("300", "NGN")

    assert result == Money("700", "NGN")


def test_money_multiplication():
    result = Money("1000", "NGN") * Decimal("1.5")

    assert result == Money("1500", "NGN")


def test_money_division():
    result = Money("1000", "NGN") / 2

    assert result == Money("500", "NGN")


def test_different_currencies_cannot_be_added():
    with pytest.raises(CurrencyMismatchError):
        Money("100", "NGN") + Money("100", "USD")


def test_different_currencies_cannot_be_compared():
    with pytest.raises(CurrencyMismatchError):
        Money("100", "NGN") < Money("100", "USD")


def test_invalid_currency():
    with pytest.raises(InvalidCurrencyError):
        Money("100", "INVALID")


def test_invalid_amount():
    with pytest.raises(InvalidMoneyError):
        Money("not-a-number", "NGN")


def test_money_is_immutable():
    money = Money("100", "NGN")

    with pytest.raises(AttributeError):
        money.amount = Decimal("200")