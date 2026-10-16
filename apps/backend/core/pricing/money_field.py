# apps/backend/core/pricing/money_field.py

"""
Canonical Univa Django MoneyField.

This module owns the Django-facing representation of
core.pricing.money.Money.

A Money value consists of:

    amount + currency

Django persists those values as two database columns:

    <amount_field>
    <currency_field>

Example:

    price_amount = models.DecimalField(...)
    currency = models.CharField(...)

    price = MoneyField(
        amount_field="price_amount",
        currency_field="currency",
    )

Python code can work with:

    product.price
        -> Money(amount=..., currency=...)

Design note
-----------

MoneyField is a *virtual* field. It has no database column of its
own. It installs a descriptor that reads/writes the two real columns
(amount and currency).

For this reason, `contribute_to_class` deliberately does NOT call
`super().contribute_to_class()`. Doing so would register MoneyField
as a real Django field, which makes the ORM look for a column that
doesn't exist.

The amount and currency columns must be declared separately on the
model as real `DecimalField` and `CharField`.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from django.core import checks
from django.core.exceptions import ValidationError
from django.db import models

from .money import Money


class MoneyFieldDescriptor:
    """
    Descriptor exposing two Django database fields as one Money value.
    """

    def __init__(
        self,
        field: "MoneyField",
        amount_field: str,
        currency_field: str,
    ) -> None:
        self.field = field
        self.amount_field = amount_field
        self.currency_field = currency_field

    def __get__(
        self,
        instance: models.Model | None,
        owner: type[models.Model] | None = None,
    ) -> Money | None:
        if instance is None:
            return self

        amount = getattr(instance, self.amount_field, None)
        currency = getattr(instance, self.currency_field, None)

        # No amount stored → the Money value is unset.
        # Do NOT coerce to Money(0); that conflates "unset" with "zero"
        # and breaks optional Money fields (e.g. discounted_price).
        if amount is None:
            return None

        if not currency:
            if self.field.null:
                return None

            raise ValidationError(
                f"MoneyField '{self.field.name}' has an amount "
                "but no currency."
            )

        return Money(amount=amount, currency=currency)

    def __set__(
        self,
        instance: models.Model,
        value: Money | Decimal | int | float | str | None,
    ) -> None:
        if value is None:
            setattr(instance, self.amount_field, None)
            setattr(instance, self.currency_field, None)
            return

        if isinstance(value, Money):
            amount = value.amount
            currency = value.currency
        else:
            amount = value

            currency = getattr(
                instance,
                self.currency_field,
                None,
            )

            if not currency:
                currency = self.field.default_currency

            if not currency:
                raise ValidationError(
                    f"Cannot assign a numeric value to MoneyField "
                    f"'{self.field.name}' without a currency."
                )

        amount = self.field.normalize_amount(amount)
        currency = self.field.normalize_currency(currency)

        self.field.validate_money_parts(
            amount=amount,
            currency=currency,
        )

        setattr(instance, self.amount_field, amount)
        setattr(instance, self.currency_field, currency)


class MoneyField(models.Field):
    """
    Canonical Univa Django MoneyField.

    The actual persistence columns must exist separately on the model
    as `DecimalField` and `CharField`.

    MoneyField itself is a virtual field and creates no column.
    """

    description = "A monetary amount paired with an ISO currency code."

    empty_strings_allowed = False

    def __init__(
        self,
        *,
        amount_field: str,
        currency_field: str,
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
        self.amount_field_name = amount_field
        self.currency_field_name = currency_field
        self.max_digits = max_digits
        self.decimal_places = decimal_places
        self.currency_max_length = currency_max_length
        self.default_currency = default_currency

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
        name, path, args, kwargs = super().deconstruct()

        kwargs["amount_field"] = self.amount_field_name
        kwargs["currency_field"] = self.currency_field_name

        if self.max_digits != 20:
            kwargs["max_digits"] = self.max_digits

        if self.decimal_places != 2:
            kwargs["decimal_places"] = self.decimal_places

        if self.currency_max_length != 3:
            kwargs["currency_max_length"] = self.currency_max_length

        if self.default_currency is not None:
            kwargs["default_currency"] = self.default_currency

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
        Install a descriptor that reads/writes two real columns:
        the amount field and the currency field.

        Deliberately does NOT call super().contribute_to_class().
        MoneyField is a virtual field with no column of its own, so
        registering it with the model's _meta.fields would make the
        ORM look for a column that doesn't exist.

        Populates enough Django-internal state for deconstruct()
        and admin/introspection to work.
        """
        self.set_attributes_from_name(name)
        self.model = cls
        self.name = name
        self.attname = name

        setattr(
            cls,
            name,
            MoneyFieldDescriptor(
                field=self,
                amount_field=self.amount_field_name,
                currency_field=self.currency_field_name,
            ),
        )

    # ------------------------------------------------------------------
    # Django checks
    # ------------------------------------------------------------------

    def check(self, **kwargs: Any):
        errors = super().check(**kwargs)

        errors.extend(self._check_amount_field(**kwargs))
        errors.extend(self._check_currency_field(**kwargs))

        return errors

    def _check_amount_field(self, **kwargs: Any):
        model = self.model

        if model is None:
            return []

        try:
            field = model._meta.get_field(self.amount_field_name)
        except models.FieldDoesNotExist:
            return [
                checks.Error(
                    (
                        f"MoneyField '{self.name}' references missing "
                        f"amount field '{self.amount_field_name}'."
                    ),
                    obj=self,
                    id="pricing.E001",
                )
            ]

        if not isinstance(field, models.DecimalField):
            return [
                checks.Error(
                    (
                        f"MoneyField '{self.name}' amount field "
                        f"'{self.amount_field_name}' must be a "
                        "DecimalField."
                    ),
                    obj=self,
                    id="pricing.E002",
                )
            ]

        return []

    def _check_currency_field(self, **kwargs: Any):
        model = self.model

        if model is None:
            return []

        try:
            field = model._meta.get_field(self.currency_field_name)
        except models.FieldDoesNotExist:
            return [
                checks.Error(
                    (
                        f"MoneyField '{self.name}' references missing "
                        f"currency field '{self.currency_field_name}'."
                    ),
                    obj=self,
                    id="pricing.E003",
                )
            ]

        if not isinstance(field, models.CharField):
            return [
                checks.Error(
                    (
                        f"MoneyField '{self.name}' currency field "
                        f"'{self.currency_field_name}' must be a "
                        "CharField."
                    ),
                    obj=self,
                    id="pricing.E004",
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
        try:
            amount = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise ValidationError(
                f"Invalid monetary amount: {value!r}"
            ) from exc

        if amount.is_nan() or amount.is_infinite():
            raise ValidationError("Monetary amount must be finite.")

        quantizer = Decimal("1").scaleb(-self.decimal_places)
        return amount.quantize(quantizer)

    def normalize_currency(self, currency: str) -> str:
        if currency is None:
            return currency

        currency = str(currency).strip().upper()

        if not currency:
            raise ValidationError("Currency cannot be empty.")

        if len(currency) > self.currency_max_length:
            raise ValidationError(
                f"Currency '{currency}' exceeds the maximum "
                f"length of {self.currency_max_length}."
            )

        return currency

    def validate_money_parts(
        self,
        *,
        amount: Decimal,
        currency: str,
    ) -> None:
        if amount.is_nan() or amount.is_infinite():
            raise ValidationError("Monetary amount must be finite.")

        if not currency:
            raise ValidationError("Currency is required.")

        if len(currency) > self.currency_max_length:
            raise ValidationError(
                f"Currency '{currency}' exceeds the maximum "
                f"length of {self.currency_max_length}."
            )

    # ------------------------------------------------------------------
    # Defaults
    # ------------------------------------------------------------------

    def get_default(self):
        default = self.default

        if callable(default):
            default = default()

        if default is None:
            return None

        if isinstance(default, Money):
            return default

        if self.default_currency is None:
            raise ValidationError(
                f"MoneyField '{self.name}' has a numeric default "
                "but no default_currency."
            )

        return Money(
            amount=self.normalize_amount(default),
            currency=self.normalize_currency(self.default_currency),
        )

    # ------------------------------------------------------------------
    # Python conversion
    # ------------------------------------------------------------------

    def to_python(self, value):
        if value is None:
            return None

        if isinstance(value, Money):
            return value

        if isinstance(value, dict):
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

        return value

    # ------------------------------------------------------------------
    # Database preparation
    # ------------------------------------------------------------------

    def get_prep_value(self, value):
        if value is None:
            return None

        if isinstance(value, Money):
            return value.amount

        return self.normalize_amount(value)

    # ------------------------------------------------------------------
    # Form integration
    # ------------------------------------------------------------------

    def formfield(self, **kwargs):
        defaults = {"required": not self.blank}
        defaults.update(kwargs)

        return models.DecimalField(
            max_digits=self.max_digits,
            decimal_places=self.decimal_places,
        ).formfield(**defaults)

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        return (
            "MoneyField("
            f"amount_field={self.amount_field_name!r}, "
            f"currency_field={self.currency_field_name!r}"
            ")"
        )