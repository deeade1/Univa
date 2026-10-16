# tax/models.py

"""
Tax models.

    TaxClass                       — a category of goods with shared
                                     tax treatment ("Standard VAT").
    TaxClassCountryRate           — a country-specific rate for a
                                     TaxClass. NULL tax_class = default
                                     rate for that country.
    TaxConfiguration              — per-channel tax behavior.
    TaxConfigurationPerCountry    — country-specific overrides for a
                                     channel's tax configuration.

Rates are stored as percentages (7.5 = 7.5%), not fractions.
"""

from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField

from core.models.metadata import ModelWithMetadata


# =====================================================================
# ENUMS
# =====================================================================


class TaxCalculationStrategy:
    """Strategy used to compute tax for a channel."""

    FLAT_RATES = "FLAT_RATES"
    TAX_APP = "TAX_APP"

    CHOICES = [
        (FLAT_RATES, _("Flat rates")),
        (TAX_APP, _("Tax app")),
    ]


# =====================================================================
# TAX CLASS
# =====================================================================


class TaxClass(ModelWithMetadata):
    """
    A category of goods with shared tax treatment.

    Examples:

        TaxClass(name="Standard VAT")
        TaxClass(name="Food — Exempt")
        TaxClass(name="Books — Exempt")

    Products and ProductTypes link to a TaxClass. When calculating
    tax, the TaxClass is resolved to a country-specific
    `TaxClassCountryRate`.
    """

    name = models.CharField(
        max_length=255,
        help_text=_("Name of the tax class"),
    )
    description = models.TextField(
        blank=True,
        help_text=_("Description of the tax class"),
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text=_("Whether this tax class is active"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tax_classes_created",
        help_text=_("User who created this tax class"),
    )
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tax_classes_modified",
        help_text=_("User who last modified this tax class"),
    )

    class Meta(ModelWithMetadata.Meta):
        verbose_name = _("Tax Class")
        verbose_name_plural = _("Tax Classes")
        ordering = ("name", "pk")
        indexes = [
            *ModelWithMetadata.Meta.indexes,
            models.Index(fields=["name"], name="tax_class_name_idx"),
            models.Index(fields=["is_active"], name="tax_class_active_idx"),
        ]

    def __str__(self) -> str:
        return self.name


# =====================================================================
# TAX CLASS COUNTRY RATE
# =====================================================================


class TaxClassCountryRate(ModelWithMetadata):
    """
    A country-specific tax rate for a TaxClass.

    If `tax_class` is NULL, this rate is the **default rate** for the
    country — used when a product has no tax class assigned.

    Examples:

        TaxClassCountryRate(country="NG", rate=7.5,  tax_class=standard)
        TaxClassCountryRate(country="GB", rate=20.0, tax_class=standard)
        TaxClassCountryRate(country="NG", rate=0.0,  tax_class=None)   # default

    Rate is a percentage: 7.5 = 7.5%.
    """

    country = CountryField(
        db_index=True,
        help_text=_("Country code"),
    )
    rate = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
        help_text=_("Tax rate percentage (0-100)"),
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Description of this tax rate"),
    )
    tax_class = models.ForeignKey(
        TaxClass,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="country_rates",
        help_text=_(
            "Tax class this rate applies to "
            "(null = default rate for country)"
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tax_rates_created",
        help_text=_("User who created this tax rate"),
    )

    class Meta(ModelWithMetadata.Meta):
        verbose_name = _("Tax Class Country Rate")
        verbose_name_plural = _("Tax Class Country Rates")
        ordering = (
            "country",
            models.OrderBy(models.F("tax_class_id"), nulls_first=True),
            "pk",
        )
        indexes = [
            *ModelWithMetadata.Meta.indexes,
            models.Index(
                fields=["country", "tax_class"],
                name="tax_rate_country_class_idx",
            ),
            models.Index(fields=["rate"], name="tax_rate_value_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["country", "tax_class"],
                name="unique_country_tax_class",
            ),
            models.UniqueConstraint(
                condition=models.Q(tax_class__isnull=True),
                fields=["country"],
                name="unique_country_without_tax_class",
            ),
        ]

    def __str__(self) -> str:
        if self.tax_class:
            return f"{self.tax_class.name} — {self.country.code} @ {self.rate}%"
        return f"Default — {self.country.code} @ {self.rate}%"

    @property
    def is_default(self) -> bool:
        """True when this is the default rate for the country."""
        return self.tax_class_id is None

    @classmethod
    def resolve(
        cls,
        tax_class: "TaxClass | None",
        country_code: str,
    ) -> "TaxClassCountryRate | None":
        """
        Resolve the applicable rate for a tax class + country.

        Order:
            1. The specific (tax_class, country) rate.
            2. The default rate for the country (tax_class IS NULL).

        Returns None if no rate can be resolved.
        """
        if tax_class is not None:
            rate = cls.objects.filter(
                tax_class=tax_class,
                country=country_code,
            ).first()
            if rate is not None:
                return rate

        # Fall back to the country default.
        return cls.objects.filter(
            tax_class__isnull=True,
            country=country_code,
        ).first()

    @property
    def rate_fraction(self) -> Decimal:
        """Rate as a decimal fraction for tax math: 7.5 → 0.075."""
        return self.rate / Decimal("100")


# =====================================================================
# TAX CONFIGURATION
# =====================================================================


class TaxConfiguration(ModelWithMetadata):
    """
    Per-channel tax behavior.

    Controls whether a channel charges tax, how tax is calculated
    (flat rates vs. external tax app), and how prices are displayed.
    """

    channel = models.OneToOneField(
        "ecommerce.Channel",
        on_delete=models.CASCADE,
        related_name="tax_configuration",
        null=True,
        blank=True,
        help_text=_("Channel this configuration applies to"),
    )
    charge_taxes = models.BooleanField(
        default=True,
        help_text=_("Whether to charge taxes"),
    )
    tax_calculation_strategy = models.CharField(
        max_length=20,
        choices=TaxCalculationStrategy.CHOICES,
        default=TaxCalculationStrategy.FLAT_RATES,
        null=True,
        blank=True,
        help_text=_("Tax calculation strategy"),
    )
    display_gross_prices = models.BooleanField(
        default=True,
        help_text=_("Whether to display gross prices (including tax)"),
    )
    prices_entered_with_tax = models.BooleanField(
        default=True,
        help_text=_("Whether prices are entered with tax included"),
    )
    tax_app_id = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        help_text=_("External tax app identifier"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tax_configs_created",
        help_text=_("User who created this tax configuration"),
    )
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tax_configs_modified",
        help_text=_("User who last modified this tax configuration"),
    )

    class Meta(ModelWithMetadata.Meta):
        verbose_name = _("Tax Configuration")
        verbose_name_plural = _("Tax Configurations")
        ordering = ("pk",)
        indexes = [
            *ModelWithMetadata.Meta.indexes,
            models.Index(
                fields=["tax_app_id"],
                name="tax_taxconf_tax_app_299dc3_idx",
            ),
            models.Index(
                fields=["tax_calculation_strategy"],
                name="tax_taxconf_tax_cal_0d395d_idx",
            ),
        ]

    def __str__(self) -> str:
        if self.channel_id:
            return f"TaxConfiguration({self.channel})"
        return f"TaxConfiguration #{self.pk}"


# =====================================================================
# TAX CONFIGURATION PER COUNTRY
# =====================================================================


class TaxConfigurationPerCountry(models.Model):
    """
    Country-specific override for a channel's tax configuration.
    """

    country = CountryField(
        db_index=True,
        help_text=_("Country code"),
    )
    charge_taxes = models.BooleanField(
        default=True,
        help_text=_("Whether to charge taxes for this country"),
    )
    tax_calculation_strategy = models.CharField(
        max_length=20,
        choices=TaxCalculationStrategy.CHOICES,
        null=True,
        blank=True,
        help_text=_("Override tax calculation strategy for this country"),
    )
    display_gross_prices = models.BooleanField(
        default=True,
        help_text=_("Whether to display gross prices for this country"),
    )
    tax_app_id = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Override tax app ID for this country"),
    )
    tax_configuration = models.ForeignKey(
        TaxConfiguration,
        on_delete=models.CASCADE,
        related_name="country_exceptions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tax_country_configs_created",
        help_text=_("User who created this country configuration"),
    )

    class Meta:
        verbose_name = _("Tax Configuration Per Country")
        verbose_name_plural = _("Tax Configurations Per Country")
        ordering = ("country", "pk")
        indexes = [
            models.Index(
                fields=["tax_configuration", "country"],
                name="tax_country_config_idx",
            ),
            models.Index(
                fields=["country", "charge_taxes"],
                name="tax_country_charge_idx",
            ),
            models.Index(
                fields=["tax_app_id"],
                name="tax_country_app_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tax_configuration", "country"],
                name="unique_tax_configuration_country",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.tax_configuration} — {self.country.code}"