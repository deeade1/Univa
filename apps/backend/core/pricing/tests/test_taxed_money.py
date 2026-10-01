import pytest

from core.pricing import (
    InvalidTaxedMoneyError,
    Money,
    TaxedMoney,
)


def test_taxed_money():
    value = TaxedMoney(
        net=Money("1000", "NGN"),
        gross=Money("1075", "NGN"),
    )

    assert value.tax == Money("75", "NGN")


def test_taxed_money_from_net_and_tax():
    value = TaxedMoney.from_net_and_tax(
        net=Money("1000", "NGN"),
        tax=Money("75", "NGN"),
    )

    assert value.net == Money("1000", "NGN")
    assert value.gross == Money("1075", "NGN")


def test_taxed_money_requires_same_currency():
    with pytest.raises(InvalidTaxedMoneyError):
        TaxedMoney(
            net=Money("1000", "NGN"),
            gross=Money("1075", "USD"),
        )


def test_gross_cannot_be_less_than_net():
    with pytest.raises(InvalidTaxedMoneyError):
        TaxedMoney(
            net=Money("1000", "NGN"),
            gross=Money("900", "NGN"),
        )


def test_taxed_money_addition():
    first = TaxedMoney(
        net=Money("1000", "NGN"),
        gross=Money("1075", "NGN"),
    )

    second = TaxedMoney(
        net=Money("500", "NGN"),
        gross=Money("537.50", "NGN"),
    )

    result = first + second

    assert result.net == Money("1500", "NGN")
    assert result.gross == Money("1612.50", "NGN")