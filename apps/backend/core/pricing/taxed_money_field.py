"""
Canonical Univa Django TaxedMoneyField.

This module owns the Django persistence representation of:

    core.pricing.taxed_money.TaxedMoney

A TaxedMoney value consists of:

    net
    gross

Tax is derived:

    tax = gross - net

The logical TaxedMoney value is persisted through existing Django
database fields.

Typical usage with a shared currency field:

    total = TaxedMoneyField(
        net_amount_field="total_net_amount",
        gross_amount_field="total_gross_amount",
        currency_field="currency",
    )

This produces the database columns:

    total_net_amount
    total_gross_amount
    currency

while Python code works with:

    instance.total
        -> TaxedMoney(
            net=Money(...),
            gross=Money(...),
        )

Separate currency fields are also supported:

    total = TaxedMoneyField(
        net_amount_field="total_net_amount",
        gross_amount_field="total_gross_amount",
        net_currency_field="total_net_currency",
        gross_currency_field="total_gross_currency",
    )

Architecture
------------

This field is part of Univa's canonical core.pricing layer.

It is intentionally independent of django-prices.

It does NOT:

    - import django_prices
    - import prices
    - create authentication/business logic
    - calculate tax rules
    - persist a third independent tax amount

Tax calculation belongs to the pricing/tax domain.

The field only represents and persists TaxedMoney.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from django.core import checks
from django.core.exceptions import ValidationError
from django.db import models

from .money import Money
from .taxed_money import TaxedMoney


class TaxedMoneyFieldDescriptor:
    """
    Descriptor exposing Django database fields as one TaxedMoney value.

    Shared currency example:

        net_amount_field="total_net_amount"
        gross_amount_field="total_gross_amount"
        currency_field="currency"

    Separate currency example:

        net_currency_field="total_net_currency"
        gross_currency_field="total_gross_currency"
    """

    def __init__(
        self,
        field: "TaxedMoneyField",
        net_amount_field: str,
        gross_amount_field: str,
        net_currency_field: str,
        gross_currency_field: str,
    ) -> None:
        self.field = field
        self.net_amount_field = net_amount_field
        self.gross_amount_field = gross_amount_field
        self.net_currency_field = net_currency_field
        self.gross_currency_field = gross_currency_field

    def __get__(
        self,
        instance: models.Model | None,
        owner: type[models.Model] | None = None,
    ) -> TaxedMoney | None:
        if instance is None:
            return self

        net_amount = getattr(
            instance,
            self.net_amount_field,
            None,
        )

        gross_amount = getattr(
            instance,
            self.gross_amount_field,
            None,
        )

        net_currency = getattr(
            instance,
            self.net_currency_field,
            None,
        )

        gross_currency = getattr(
            instance,
            self.gross_currency_field,
            None,
        )

        # Completely empty value.
        if (
            net_amount is None
            and gross_amount is None
            and net_currency in (None, "")
            and gross_currency in (None, "")
        ):
            return None

        # A partially populated TaxedMoney value is invalid.
        if net_amount is None or gross_amount is None:
            if self.field.null:
                return None

            raise ValueError(
                f"TaxedMoneyField '{self.field.name}' has incomplete "
                "amount data."
            )

        if not net_currency or not gross_currency:
            if self.field.null:
                return None

            raise ValueError(
                f"TaxedMoneyField '{self.field.name}' has amount data "
                "but missing currency data."
            )

        net_amount = self.field.normalize_amount(net_amount)
        gross_amount = self.field.normalize_amount(gross_amount)

        net_currency = self.field.normalize_currency(
            net_currency
        )
        gross_currency = self.field.normalize_currency(
            gross_currency
        )

        return TaxedMoney(
            net=Money(
                amount=net_amount,
                currency=net_currency,
            ),
            gross=Money(
                amount=gross_amount,
                currency=gross_currency,
            ),
        )

    def __set__(
        self,
        instance: models.Model,
        value: TaxedMoney | None,
    ) -> None:
        if value is None:
            setattr(
                instance,
                self.net_amount_field,
                None,
            )

            setattr(
                instance,
                self.gross_amount_field,
                None,
            )

            setattr(
                instance,
                self.net_currency_field,
                None,
            )

            # Do not unnecessarily write the same shared currency
            # field twice.
            if (
                self.gross_currency_field
                != self.net_currency_field
            ):
                setattr(
                    instance,
                    self.gross_currency_field,
                    None,
                )

            return

        if not isinstance(value, TaxedMoney):
            raise TypeError(
                (
                    f"Cannot assign {type(value).__name__} to "
                    f"TaxedMoneyField '{self.field.name}'. "
                    "Expected TaxedMoney or None."
                )
            )

        net = value.net
        gross = value.gross

        net_amount = self.field.normalize_amount(
            net.amount
        )

        gross_amount = self.field.normalize_amount(
            gross.amount
        )

        net_currency = self.field.normalize_currency(
            net.currency
        )

        gross_currency = self.field.normalize_currency(
            gross.currency
        )

        self.field.validate_taxed_money_parts(
            net_amount=net_amount,
            gross_amount=gross_amount,
            net_currency=net_currency,
            gross_currency=gross_currency,
        )

        setattr(
            instance,
            self.net_amount_field,
            net_amount,
        )

        setattr(
            instance,
            self.gross_amount_field,
            gross_amount,
        )

        setattr(
            instance,
            self.net_currency_field,
            net_currency,
        )

        if (
            self.gross_currency_field
            != self.net_currency_field
        ):
            setattr(
                instance,
                self.gross_currency_field,
                gross_currency,
            )


class TaxedMoneyField(models.Field):
    """
    Canonical Univa Django field representing TaxedMoney.

    The field is logical/compound.

    It does not own a database column directly.

    The underlying database representation consists of:

        net amount
        gross amount
        currency

    or, when separate currency fields are configured:

        net amount
        net currency
        gross amount
        gross currency

    Example
    -------

        total = TaxedMoneyField(
            net_amount_field="total_net_amount",
            gross_amount_field="total_gross_amount",
            currency_field="currency",
        )
    """

    description = (
        "A taxed monetary amount containing net and gross values."
    )

    empty_strings_allowed = False

    def __init__(
        self,
        *,
        net_amount_field: str,
        gross_amount_field: str,
        currency_field: str | None = None,
        net_currency_field: str | None = None,
        gross_currency_field: str | None = None,
        max_digits: int = 20,
        decimal_places: int = 2,
        currency_max_length: int = 3,
        default_currency: str | None = None,
        null: bool = False,
        blank: bool = False,
        default: Any = None,
        editable: bool = True,
        **kwargs: Any,
    ) -> None:
        self.net_amount_field_name = net_amount_field
        self.gross_amount_field_name = gross_amount_field

        self.currency_field_name = currency_field

        self.net_currency_field_name = (
            net_currency_field or currency_field
        )

        self.gross_currency_field_name = (
            gross_currency_field or currency_field
        )

        self.max_digits = max_digits
        self.decimal_places = decimal_places
        self.currency_max_length = currency_max_length
        self.default_currency = default_currency

        if not self.net_currency_field_name:
            raise ValueError(
                (
                    "TaxedMoneyField requires either 'currency_field' "
                    "or 'net_currency_field'."
                )
            )

        if not self.gross_currency_field_name:
            raise ValueError(
                (
                    "TaxedMoneyField requires either 'currency_field' "
                    "or 'gross_currency_field'."
                )
            )

        super().__init__(
            null=null,
            blank=blank,
            default=default,
            editable=editable,
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Django field metadata
    # ------------------------------------------------------------------

    def deconstruct(self):
        """
        Return the field definition used by Django migrations.
        """

        name, path, args, kwargs = super().deconstruct()

        kwargs["net_amount_field"] = (
            self.net_amount_field_name
        )

        kwargs["gross_amount_field"] = (
            self.gross_amount_field_name
        )

        if self.currency_field_name is not None:
            kwargs["currency_field"] = (
                self.currency_field_name
            )
        else:
            kwargs["net_currency_field"] = (
                self.net_currency_field_name
            )

            kwargs["gross_currency_field"] = (
                self.gross_currency_field_name
            )

        if self.max_digits != 20:
            kwargs["max_digits"] = self.max_digits

        if self.decimal_places != 2:
            kwargs["decimal_places"] = self.decimal_places

        if self.currency_max_length != 3:
            kwargs["currency_max_length"] = (
                self.currency_max_length
            )

        if self.default_currency is not None:
            kwargs["default_currency"] = (
                self.default_currency
            )

        return name, path, args, kwargs

    # ------------------------------------------------------------------
    # Django model integration
    # ------------------------------------------------------------------

    def contribute_to_class(
        self,
        cls: type[models.Model],
        name: str,
        **kwargs: Any,
    ) -> None:
        """
        Register the logical TaxedMoney field on the model.

        The actual amount/currency fields must already exist on
        the model.
        """

        super().contribute_to_class(
            cls,
            name,
            **kwargs,
        )

        setattr(
            cls,
            self.attname,
            TaxedMoneyFieldDescriptor(
                field=self,
                net_amount_field=(
                    self.net_amount_field_name
                ),
                gross_amount_field=(
                    self.gross_amount_field_name
                ),
                net_currency_field=(
                    self.net_currency_field_name
                ),
                gross_currency_field=(
                    self.gross_currency_field_name
                ),
            ),
        )

    # ------------------------------------------------------------------
    # Django system checks
    # ------------------------------------------------------------------

    def check(self, **kwargs: Any):
        errors = super().check(**kwargs)

        errors.extend(
            self._check_amount_field(
                self.net_amount_field_name,
                "net",
            )
        )

        errors.extend(
            self._check_amount_field(
                self.gross_amount_field_name,
                "gross",
            )
        )

        errors.extend(
            self._check_currency_field(
                self.net_currency_field_name,
                "net",
            )
        )

        if (
            self.gross_currency_field_name
            != self.net_currency_field_name
        ):
            errors.extend(
                self._check_currency_field(
                    self.gross_currency_field_name,
                    "gross",
                )
            )

        return errors

    def _check_amount_field(
        self,
        field_name: str,
        amount_type: str,
    ):
        model = self.model

        if model is None:
            return []

        try:
            field = model._meta.get_field(field_name)
        except models.FieldDoesNotExist:
            return [
                checks.Error(
                    (
                        f"TaxedMoneyField '{self.name}' references "
                        f"missing {amount_type} amount field "
                        f"'{field_name}'."
                    ),
                    obj=self,
                    id="pricing.E101",
                )
            ]

        if not isinstance(field, models.DecimalField):
            return [
                checks.Error(
                    (
                        f"TaxedMoneyField '{self.name}' {amount_type} "
                        f"amount field '{field_name}' must be a "
                        "DecimalField."
                    ),
                    obj=self,
                    id="pricing.E102",
                )
            ]

        return []

    def _check_currency_field(
        self,
        field_name: str,
        currency_type: str,
    ):
        model = self.model

        if model is None:
            return []

        try:
            field = model._meta.get_field(field_name)
        except models.FieldDoesNotExist:
            return [
                checks.Error(
                    (
                        f"TaxedMoneyField '{self.name}' references "
                        f"missing {currency_type} currency field "
                        f"'{field_name}'."
                    ),
                    obj=self,
                    id="pricing.E103",
                )
            ]

        if not isinstance(field, models.CharField):
            return [
                checks.Error(
                    (
                        f"TaxedMoneyField '{self.name}' "
                        f"{currency_type} currency field "
                        f"'{field_name}' must be a CharField."
                    ),
                    obj=self,
                    id="pricing.E104",
                )
            ]

        return []

    # ------------------------------------------------------------------
    # Normalization
    # ------------------------------------------------------------------

    def normalize_amount(
        self,
        value: Decimal | int | float | str,
    ) -> Decimal:
        """
        Normalize a monetary amount to the configured precision.
        """

        try:
            amount = Decimal(str(value))
        except (
            InvalidOperation,
            ValueError,
            TypeError,
        ) as exc:
            raise ValidationError(
                f"Invalid monetary amount: {value!r}"
            ) from exc

        if amount.is_nan() or amount.is_infinite():
            raise ValidationError(
                "Monetary amount must be finite."
            )

        return amount.quantize(
            Decimal("1").scaleb(
                -self.decimal_places
            )
        )

    def normalize_currency(
        self,
        currency: str,
    ) -> str:
        """
        Normalize and validate a currency code.
        """

        if currency is None:
            return currency

        currency = str(currency).strip().upper()

        if not currency:
            raise ValidationError(
                "Currency cannot be empty."
            )

        if len(currency) > self.currency_max_length:
            raise ValidationError(
                (
                    f"Currency '{currency}' exceeds the maximum "
                    f"length of {self.currency_max_length}."
                )
            )

        return currency

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_taxed_money_parts(
        self,
        *,
        net_amount: Decimal,
        gross_amount: Decimal,
        net_currency: str,
        gross_currency: str,
    ) -> None:
        """
        Validate the complete TaxedMoney representation.
        """

        if net_amount.is_nan() or net_amount.is_infinite():
            raise ValidationError(
                "Net monetary amount must be finite."
            )

        if gross_amount.is_nan() or gross_amount.is_infinite():
            raise ValidationError(
                "Gross monetary amount must be finite."
            )

        if not net_currency:
            raise ValidationError(
                "Net currency is required."
            )

        if not gross_currency:
            raise ValidationError(
                "Gross currency is required."
            )

        if net_currency != gross_currency:
            raise ValidationError(
                (
                    "TaxedMoney net and gross values must use the "
                    "same currency: "
                    f"{net_currency} != {gross_currency}."
                )
            )

    # ------------------------------------------------------------------
    # Defaults
    # ------------------------------------------------------------------

    def get_default(self):
        """
        Return a logical TaxedMoney default.

        A TaxedMoney instance may be supplied directly.

        Numeric defaults require default_currency and produce
        zero tax:

            net = default
            gross = default
        """

        default = self.default

        if callable(default):
            default = default()

        if default is None:
            return None

        if isinstance(default, TaxedMoney):
            return default

        if self.default_currency is None:
            raise ValueError(
                (
                    f"TaxedMoneyField '{self.name}' has a numeric "
                    "default but no default_currency."
                )
            )

        amount = self.normalize_amount(default)
        currency = self.normalize_currency(
            self.default_currency
        )

        money = Money(
            amount=amount,
            currency=currency,
        )

        return TaxedMoney(
            net=money,
            gross=money,
        )

    # ------------------------------------------------------------------
    # Python conversion
    # ------------------------------------------------------------------

    def to_python(self, value):
        """
        Convert supported Python representations into TaxedMoney.

        Database loading is handled by the descriptor because the
        actual database columns belong to the underlying fields.
        """

        if value is None:
            return None

        if isinstance(value, TaxedMoney):
            return value

        if isinstance(value, dict):
            net = value.get("net")
            gross = value.get("gross")

            if net is None or gross is None:
                raise ValidationError(
                    (
                        "TaxedMoney requires both 'net' and "
                        "'gross'."
                    )
                )

            net_money = self._money_from_value(net)
            gross_money = self._money_from_value(gross)

            return TaxedMoney(
                net=net_money,
                gross=gross_money,
            )

        return value

    def _money_from_value(
        self,
        value: Any,
    ) -> Money:
        """
        Convert a supported value into Money.
        """

        if isinstance(value, Money):
            return value

        if not isinstance(value, dict):
            raise ValidationError(
                "Money must be a Money instance or dictionary."
            )

        amount = value.get("amount")
        currency = value.get("currency")

        if amount is None or currency is None:
            raise ValidationError(
                "Money requires both amount and currency."
            )

        return Money(
            amount=self.normalize_amount(amount),
            currency=self.normalize_currency(currency),
        )

    # ------------------------------------------------------------------
    # Database preparation
    # ------------------------------------------------------------------

    def get_prep_value(self, value):
        """
        This logical field does not directly own a database column.

        The underlying DecimalField and CharField instances prepare
        their respective database values.
        """

        if value is None:
            return None

        if isinstance(value, TaxedMoney):
            return value.net.amount

        return value

    # ------------------------------------------------------------------
    # Form integration
    # ------------------------------------------------------------------

    def formfield(self, **kwargs):
        """
        Until a dedicated Univa Money/TaxedMoney form field exists,
        expose the net amount as the primary form representation.

        Model forms should normally expose the underlying amount and
        currency fields independently.
        """

        defaults = {
            "required": not self.blank,
        }

        defaults.update(kwargs)

        return models.DecimalField(
            max_digits=self.max_digits,
            decimal_places=self.decimal_places,
        ).formfield(**defaults)

    # ------------------------------------------------------------------
    # String representation
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        return (
            "TaxedMoneyField("
            f"net_amount_field="
            f"{self.net_amount_field_name!r}, "
            f"gross_amount_field="
            f"{self.gross_amount_field_name!r}, "
            f"net_currency_field="
            f"{self.net_currency_field_name!r}, "
            f"gross_currency_field="
            f"{self.gross_currency_field_name!r}"
            ")"
        )

