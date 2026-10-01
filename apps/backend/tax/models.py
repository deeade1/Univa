# apps/backend/tax/models.py
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django_countries.fields import CountryField

from core.models.metadata import ModelWithMetadata

# Flexible import for Channel - try ecommerce first, fallback to legacy
try:
    from ecommerce.models.channel import Channel
    CHANNEL_AVAILABLE = True
except ImportError:
    try:
        from channel.models import Channel
        CHANNEL_AVAILABLE = True
    except ImportError:
        Channel = None
        CHANNEL_AVAILABLE = False

from . import TaxCalculationStrategy


class TaxClass(ModelWithMetadata):
    """Tax class model for categorizing products with different tax rates."""
    
    name = models.CharField(max_length=255, help_text="Name of the tax class")
    description = models.TextField(
        blank=True, 
        help_text="Description of the tax class"
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this tax class is active"
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tax_classes_created',
        help_text="User who created this tax class"
    )
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tax_classes_modified',
        help_text="User who last modified this tax class"
    )

    class Meta:
        ordering = ("name", "pk")
        indexes = [
            models.Index(fields=["name"], name="tax_class_name_idx"),
            models.Index(fields=["is_active"], name="tax_class_active_idx"),
        ]
        verbose_name = "Tax Class"
        verbose_name_plural = "Tax Classes"

    def __str__(self):
        return self.name

    def get_default_rate(self, country_code=None):
        """Get the default tax rate for this class."""
        if country_code:
            try:
                rate = self.country_rates.get(country=country_code)
                return rate.rate
            except TaxClassCountryRate.DoesNotExist:
                pass
        # Return default rate (could be 0 or a fallback)
        return Decimal('0.00')


class TaxClassCountryRate(models.Model):
    """Country-specific tax rates for tax classes."""
    
    tax_class = models.ForeignKey(
        TaxClass, 
        related_name="country_rates", 
        on_delete=models.CASCADE, 
        null=True,
        blank=True,
        help_text="Tax class this rate applies to (null = default rate for country)"
    )
    country = CountryField(
        db_index=True,
        help_text="Country code"
    )
    rate = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        validators=[
            MinValueValidator(Decimal('0.00')),
            MaxValueValidator(Decimal('100.00'))
        ],
        help_text="Tax rate percentage (0-100)"
    )
    
    # Description
    description = models.CharField(
        max_length=255,
        blank=True,
        help_text="Description of this tax rate"
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tax_rates_created',
        help_text="User who created this tax rate"
    )

    class Meta:
        ordering = ("country", models.F("tax_class_id").asc(nulls_first=True), "pk")
        constraints = [
            models.UniqueConstraint(
                fields=("country", "tax_class"), 
                name="unique_country_tax_class"
            ),
            models.UniqueConstraint(
                fields=("country",),
                condition=models.Q(tax_class=None),
                name="unique_country_without_tax_class",
            ),
        ]
        indexes = [
            models.Index(fields=["country", "tax_class"], name="tax_rate_country_class_idx"),
            models.Index(fields=["rate"], name="tax_rate_value_idx"),
        ]
        verbose_name = "Tax Class Country Rate"
        verbose_name_plural = "Tax Class Country Rates"

    def __str__(self):
        return f"{self.country}: {self.rate}%"

    def clean(self):
        """Validate tax rate."""
        if self.rate < 0 or self.rate > 100:
            raise ValidationError({
                "rate": "Tax rate must be between 0 and 100."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class TaxConfiguration(ModelWithMetadata):
    """Tax configuration for a channel."""
    
    # Only create ForeignKey if Channel is available
    channel = models.OneToOneField(
        Channel, 
        related_name="tax_configuration", 
        on_delete=models.CASCADE,
        help_text="Channel this tax configuration applies to"
    ) if CHANNEL_AVAILABLE else None
    
    # Tax settings
    charge_taxes = models.BooleanField(
        default=True,
        help_text="Whether to charge taxes"
    )
    tax_calculation_strategy = models.CharField(
        max_length=20,
        choices=TaxCalculationStrategy.CHOICES,
        blank=True,
        null=True,
        default=TaxCalculationStrategy.FLAT_RATES,
        help_text="Tax calculation strategy"
    )
    display_gross_prices = models.BooleanField(
        default=True,
        help_text="Whether to display gross prices (including tax)"
    )
    prices_entered_with_tax = models.BooleanField(
        default=True,
        help_text="Whether prices are entered with tax included"
    )
    tax_app_id = models.CharField(
        blank=True, 
        null=True, 
        max_length=256,
        help_text="External tax app identifier"
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tax_configs_created',
        help_text="User who created this tax configuration"
    )
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tax_configs_modified',
        help_text="User who last modified this tax configuration"
    )

    class Meta:
        ordering = ("pk",)
        indexes = [
            models.Index(fields=["tax_app_id"]),
            models.Index(fields=["tax_calculation_strategy"]),
        ]
        if CHANNEL_AVAILABLE:
            indexes.append(models.Index(fields=["channel"]))
        verbose_name = "Tax Configuration"
        verbose_name_plural = "Tax Configurations"

    def __str__(self):
        if CHANNEL_AVAILABLE and self.channel:
            return f"Tax Config for {self.channel.name}"
        return f"Tax Config {self.pk}"

    def clean(self):
        """Validate tax configuration."""
        if self.tax_calculation_strategy and self.tax_calculation_strategy not in dict(TaxCalculationStrategy.CHOICES):
            raise ValidationError({
                "tax_calculation_strategy": "Invalid tax calculation strategy."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def get_country_config(self, country_code):
        """Get tax configuration for a specific country."""
        try:
            return self.country_exceptions.get(country=country_code)
        except TaxConfigurationPerCountry.DoesNotExist:
            return None

    def get_tax_rate(self, country_code, tax_class=None):
        """Get tax rate for a specific country and tax class."""
        # Check for country-specific configuration first
        country_config = self.get_country_config(country_code)
        if country_config:
            # Use the country's charge_taxes setting
            if not country_config.charge_taxes:
                return Decimal('0.00')
        
        # Get rate from tax class
        if tax_class:
            try:
                rate = tax_class.country_rates.get(country=country_code)
                return rate.rate
            except TaxClassCountryRate.DoesNotExist:
                pass
        
        # Check for default rate for country
        try:
            default_rate = TaxClassCountryRate.objects.get(
                country=country_code,
                tax_class=None
            )
            return default_rate.rate
        except TaxClassCountryRate.DoesNotExist:
            pass
        
        return Decimal('0.00')


class TaxConfigurationPerCountry(models.Model):
    """Country-specific tax configuration overrides."""
    
    tax_configuration = models.ForeignKey(
        TaxConfiguration, 
        related_name="country_exceptions", 
        on_delete=models.CASCADE,
        db_index=True
    )
    country = CountryField(
        db_index=True,
        help_text="Country code"
    )
    charge_taxes = models.BooleanField(
        default=True,
        help_text="Whether to charge taxes for this country"
    )
    tax_calculation_strategy = models.CharField(
        max_length=20, 
        choices=TaxCalculationStrategy.CHOICES, 
        blank=True, 
        null=True,
        help_text="Override tax calculation strategy for this country"
    )
    display_gross_prices = models.BooleanField(
        default=True,
        help_text="Whether to display gross prices for this country"
    )
    tax_app_id = models.CharField(
        blank=True, 
        null=True, 
        max_length=256,
        db_index=True,
        help_text="Override tax app ID for this country"
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tax_country_configs_created',
        help_text="User who created this country configuration"
    )

    class Meta:
        ordering = ("country", "pk")
        indexes = [
            models.Index(fields=["tax_configuration", "country"], name="tax_country_config_idx"),
            models.Index(fields=["country", "charge_taxes"], name="tax_country_charge_idx"),
            models.Index(fields=["tax_app_id"], name="tax_country_app_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tax_configuration", "country"],
                name="unique_tax_configuration_country"
            ),
        ]
        verbose_name = "Tax Configuration Per Country"
        verbose_name_plural = "Tax Configurations Per Country"

    def __str__(self):
        config_name = f"Tax Config {self.tax_configuration.pk}"
        if CHANNEL_AVAILABLE and self.tax_configuration.channel:
            config_name = self.tax_configuration.channel.name
        return f"{self.country} - {config_name}"

    def clean(self):
        """Validate tax configuration per country."""
        # Validate tax calculation strategy
        if self.tax_calculation_strategy and self.tax_calculation_strategy not in dict(TaxCalculationStrategy.CHOICES):
            raise ValidationError({
                "tax_calculation_strategy": "Invalid tax calculation strategy."
            })
        
        # Validate tax_app_id format (if needed)
        if self.tax_app_id and len(self.tax_app_id) > 256:
            raise ValidationError({
                "tax_app_id": "Tax App ID cannot exceed 256 characters."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @classmethod
    def get_for_country(cls, tax_configuration, country_code):
        """Get tax configuration for a specific country."""
        try:
            return cls.objects.get(
                tax_configuration=tax_configuration,
                country=country_code
            )
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_active_countries(cls, tax_configuration):
        """Get all countries with tax configuration."""
        return cls.objects.filter(
            tax_configuration=tax_configuration
        ).values_list('country', flat=True)


# Default tax calculation strategy if not provided
class TaxCalculationStrategy:
    """Tax calculation strategy constants."""
    
    FLAT_RATES = "flat_rates"
    TAX_APP = "tax_app"
    
    CHOICES = [
        (FLAT_RATES, "Flat Rates"),
        (TAX_APP, "Tax App"),
    ]


# Add a helper function to get tax rates
def get_tax_rate_for_product(product, country_code, tax_config=None):
    """
    Get the appropriate tax rate for a product.
    
    Args:
        product: The product instance
        country_code: The country code
        tax_config: Optional tax configuration
    
    Returns:
        Decimal: The tax rate as a percentage
    """
    # Get the product's tax class
    tax_class = getattr(product, 'tax_class', None)
    
    if tax_config and CHANNEL_AVAILABLE and tax_config.channel:
        # Use the channel's tax configuration
        return tax_config.get_tax_rate(country_code, tax_class)
    
    # Fallback: get from tax class directly
    if tax_class:
        try:
            rate = tax_class.country_rates.get(country=country_code)
            return rate.rate
        except TaxClassCountryRate.DoesNotExist:
            pass
    
    # Check for default rate
    try:
        default_rate = TaxClassCountryRate.objects.get(
            country=country_code,
            tax_class=None
        )
        return default_rate.rate
    except TaxClassCountryRate.DoesNotExist:
        pass
    
    return Decimal('0.00')


# Helper function to calculate tax amount
def calculate_tax_amount(price, tax_rate):
    """
    Calculate tax amount for a given price and tax rate.
    
    Args:
        price: The price (Decimal)
        tax_rate: The tax rate as a percentage (Decimal)
    
    Returns:
        Decimal: The tax amount
    """
    return price * (tax_rate / Decimal('100.00'))


# Helper function to calculate total with tax
def calculate_total_with_tax(price, tax_rate):
    """
    Calculate total including tax.
    
    Args:
        price: The price (Decimal)
        tax_rate: The tax rate as a percentage (Decimal)
    
    Returns:
        Decimal: The total including tax
    """
    return price + calculate_tax_amount(price, tax_rate)