# apps/backend/realestate/models/listing.py

"""
Listing model for the real estate domain.

A Listing belongs to the real-estate domain, but user identity belongs
directly to the central accounts.User model.

Architecture:

    accounts.User
        │
        ├── owner
        └── reviewer

    realestate.Agent
        │
        └── listings

UserProfile is intentionally NOT used for application relationships.
UserProfile is reserved for profile-specific information.
"""

import logging

from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.contrib.postgres.indexes import GinIndex
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_resized import ResizedImageField

from accounts.models import Address
from core.models.location import LocationModel
from core.models.metadata import ModelWithMetadata
from seo.models import SeoModel

from .agent import Agent
from .base import TimeStampedModel, listing_dir_path
from realestate.constants import (
    LAND_UNITS,
    PRICE_METRICS,
    PROPERTY_AREAS,
    PROPERTY_CONDITION,
    PROPERTY_FOR,
    PROPERTY_STATUS,
    PROPERTY_TYPES,
    CURRENCY_CHOICES,
)
from .listing_category import ListingCategory
from .listing_type import ListingType
from .managers import ListingManager


logger = logging.getLogger(__name__)


class Listing(TimeStampedModel, LocationModel):
    """
    Real-estate property listing.

    The central User model owns the application-level identity.
    Real-estate-specific agent information belongs to Agent.

    Relationships:

        Listing.owner
            -> accounts.User

        Listing.reviewer
            -> accounts.User

        Listing.agent
            -> realestate.Agent
    """

    VERIFY_ADDRESS = True

    # ------------------------------------------------------------------
    # Basic Information
    # ------------------------------------------------------------------

    property_area = models.CharField(
        max_length=20,
        choices=PROPERTY_AREAS,
    )

    listing_type = models.ForeignKey(
        "realestate.ListingType",
        on_delete=models.CASCADE,
        verbose_name=_("Listing type"),
        related_name="listing"
    )

    property_location = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    property_category = models.ForeignKey(
        ListingCategory,
        related_name="products",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    # ------------------------------------------------------------------
    # International Location (Replaces Nigerian Location)
    # ------------------------------------------------------------------

    # Country field - supports all countries
    country = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_("Country"),
        help_text=_("Country where the property is located"),
    )

    # Country code for easy filtering (e.g., US, NG, UK, etc.)
    country_code = models.CharField(
        max_length=3,
        blank=True,
        null=True,
        verbose_name=_("Country Code"),
        help_text=_("ISO country code (e.g., US, NG, UK, CA)"),
    )

    # State/Province/Region - generic for all countries
    state_province = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_("State/Province"),
        help_text=_("State, province, or region"),
    )

    # City/LGA - works for all countries
    city = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_("City"),
        help_text=_("City or municipality"),
    )

    # Local area/neighborhood - generic
    local_area = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_("Local Area"),
        help_text=_("Neighborhood, district, or local area"),
    )

    # Postal/ZIP code
    postal_code = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_("Postal/ZIP Code"),
    )

    # Estate/Community name
    estate_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text=_("Name of estate, community, or development if applicable"),
    )

    # Full address as text
    full_address = models.TextField(
        blank=True,
        null=True,
        help_text=_("Full formatted address"),
    )

    # ------------------------------------------------------------------
    # Property Details
    # ------------------------------------------------------------------

    title = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    slug = models.SlugField(
        max_length=255,
        unique=True,
        allow_unicode=True,
    )

    description = models.TextField(
        blank=True,
    )

    address = models.ForeignKey(
        Address,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="listings_address",
    )

    # ------------------------------------------------------------------
    # Property Condition (NEW)
    # ------------------------------------------------------------------

    property_condition = models.CharField(
        max_length=20,
        choices=PROPERTY_CONDITION,
        default="good",
        blank=True,
        null=True,
        verbose_name=_("Property Condition"),
        help_text=_("Current condition of the property"),
    )

    # ------------------------------------------------------------------
    # Land Details
    # ------------------------------------------------------------------

    land_size = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
        ],
        help_text=_("Size of the land"),
    )

    land_unit = models.CharField(
        max_length=20,
        choices=LAND_UNITS,
        default="square_meter",
        null=True,
        blank=True,
    )

    total_plots = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Total number of plots available"),
    )

    plots_available = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Number of plots still available"),
    )

    # ------------------------------------------------------------------
    # Building Details
    # ------------------------------------------------------------------

    bedrooms = models.PositiveIntegerField(
        blank=True,
        null=True,
    )

    bathrooms = models.PositiveIntegerField(
        blank=True,
        null=True,
    )

    garage = models.IntegerField(
        default=0,
    )

    square_feet = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
        ],
    )

    ceiling_height = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[
            MinValueValidator(0),
        ],
    )

    # ------------------------------------------------------------------
    # Pricing
    # ------------------------------------------------------------------

    price_metric = models.CharField(
        max_length=20,
        choices=PRICE_METRICS,
        default="total_price",
    )

    price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[
            MinValueValidator(0),
        ],
        help_text=_("Price based on selected metric"),
    )

    price_per_plot = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
        ],
        help_text=_("Price per individual plot"),
    )

    # Currency field for international support
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default="USD",
        help_text=_("Currency for the listing price"),
    )

    # ------------------------------------------------------------------
    # Additional Property Information
    # ------------------------------------------------------------------

    lot_size = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
        ],
    )

    image = ResizedImageField(
        size=[1200, 630],
        upload_to=listing_dir_path,
    )

    property_status = models.CharField(
        max_length=40,
        choices=PROPERTY_STATUS,
        default="draft",
    )

    property_for = models.CharField(
        max_length=5,
        choices=PROPERTY_FOR,
        default="S",
    )

    is_published = models.BooleanField(
        default=False,
    )

    year_built = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    # ------------------------------------------------------------------
    # Property Features (International Friendly)
    # ------------------------------------------------------------------

    # Document-related fields
    has_legal_documents = models.BooleanField(
        default=False,
        verbose_name=_("Has Legal Documents"),
        help_text=_("Property has proper legal documentation"),
    )

    # Generic feature flags
    is_gated_community = models.BooleanField(
        default=False,
        help_text=_("Property is in a gated community or estate"),
    )

    has_road_access = models.BooleanField(
        default=True,
        help_text=_("Property has good road access"),
    )

    # Nigerian-specific features (optional, can be conditionally shown)
    has_c_of_o = models.BooleanField(
        default=False,
        verbose_name=_("Has Certificate of Occupancy"),
        help_text=_("Nigerian-specific: Has Certificate of Occupancy"),
    )

    has_governors_consent = models.BooleanField(
        default=False,
        help_text=_("Nigerian-specific: Governor's Consent obtained"),
    )

    # ------------------------------------------------------------------
    # Real Estate Relationships
    # ------------------------------------------------------------------

    agent = models.ForeignKey(
        "realestate.Agent",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="listings_agent",
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="realestate_owned_listings",
    )

    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="realestate_reviewed_listings",
    )

    free_from = models.DateField(
        default=timezone.now,
        blank=True,
    )

    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # ------------------------------------------------------------------
    # Manager
    # ------------------------------------------------------------------

    objects = ListingManager()

    # ------------------------------------------------------------------
    # Meta
    # ------------------------------------------------------------------

    class Meta:
        ordering = ["-created"]

        permissions = [
            (
                "can_create_update_listing",
                "Can create and update listing",
            ),
            (
                "can_publish_listing",
                "Can publish listing",
            ),
        ]

        indexes = [
            GinIndex(
                fields=["description"],
                name="listing_desc_gin",
                opclasses=["gin_trgm_ops"],
            ),
            GinIndex(
                fields=["title"],
                name="listing_title_gin",
                opclasses=["gin_trgm_ops"],
            ),
            models.Index(
                fields=["address"],
                name="listing_address_idx",
            ),
            gis_models.Index(
                fields=["location_point"],
                name="listing_location_point_idx",
            ),
            models.Index(
                fields=["price", "property_status"],
                name="listing_price_status_idx",
            ),
            # Updated indexes for international locations
            models.Index(
                fields=["country", "state_province"],
                name="listing_country_state_idx",
            ),
            models.Index(
                fields=["city"],
                name="listing_city_idx",
            ),
            models.Index(
                fields=["postal_code"],
                name="listing_postal_code_idx",
            ),
            models.Index(
                fields=["estate_name"],
                name="listing_estate_name_idx",
            ),
            models.Index(
                fields=["land_unit", "land_size"],
                name="listing_land_details_idx",
            ),
            models.Index(
                fields=["is_published"],
                condition=Q(is_published=True),
                name="published_listings_idx",
            ),
            models.Index(
                fields=["property_status"],
                name="listing_status_idx",
            ),
            models.Index(
                fields=["property_for"],
                name="listing_property_for_idx",
            ),
            models.Index(
                fields=["property_area"],
                name="listing_property_area_idx",
            ),
            models.Index(
                fields=["listing_type"],
                name="listing_type_idx",
            ),
            models.Index(
                fields=["agent"],
                name="listing_agent_idx",
            ),
            models.Index(
                fields=["owner"],
                name="listing_owner_idx",
            ),
            models.Index(
                fields=["currency"],
                name="listing_currency_idx",
            ),
            models.Index(
                fields=["property_condition"],
                name="listing_condition_idx",
            ),
        ]
        
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(plots_available__isnull=True)
                    | Q(total_plots__isnull=True)
                    | Q(plots_available__lte=F("total_plots"))
                ),
                name="listing_plots_available_lte_total",
            ),
        ]

    # ------------------------------------------------------------------
    # String Representation
    # ------------------------------------------------------------------

    def __str__(self):
        return (
            f"{self.title or 'No Title'} - "
            f"{self.property_status}"
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def clean(self):
        super().clean()

        if self.price is not None and self.price < 0:
            raise ValidationError(
                {
                    "price": "Price cannot be negative",
                }
            )

        if (
            self.listing_type
            and self.listing_type.requires_land_details
        ):
            if not self.land_size or self.land_size <= 0:
                raise ValidationError(
                    {
                        "land_size": (
                            "Land size is required for land properties"
                        ),
                    }
                )

        if (
            self.listing_type
            and self.listing_type.requires_building_details
        ):
            if not self.square_feet or self.square_feet <= 0:
                raise ValidationError(
                    {
                        "square_feet": (
                            "Square footage is required for building properties"
                        ),
                    }
                )

        if (
            self.total_plots
            and self.plots_available
            and self.plots_available > self.total_plots
        ):
            raise ValidationError(
                {
                    "plots_available": (
                        "Available plots cannot exceed total plots"
                    ),
                }
            )

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def save(self, *args, **kwargs):
        """
        Save the listing.

        Computes `price_per_plot` for plot-sale listings that
        have a price and total plot count.

        Note: `self.clean()` runs to enforce cross-field
        invariants (land_size required for land types, etc.).
        `self.full_clean()` is deliberately NOT called — DB
        constraints catch what they can, and callers see
        IntegrityError rather than ValidationError for those.
        """
        if (
            self.listing_type
            and self.listing_type.supports_plot_sales
            and self.price
            and self.total_plots
            and not self.price_per_plot
        ):
            self.price_per_plot = (
                self.price / self.total_plots
            )

        self.clean()

        super().save(*args, **kwargs)

    # ------------------------------------------------------------------
    # Display Helpers
    # ------------------------------------------------------------------

    @property
    def display_price(self):
        if not self.price:
            return "Price on request"

        currency_symbols = {
            "NGN": "₦",
            "USD": "$",
            "EUR": "€",
            "GBP": "£",
            "CAD": "C$",
            "AUD": "A$",
            "JPY": "¥",
            "CNY": "¥",
            "INR": "₹",
            "ZAR": "R",
            "KES": "KSh",
            "GHS": "GH₵",
        }
        
        currency_symbol = currency_symbols.get(self.currency, "$")
        price_formatted = f"{currency_symbol}{self.price:,.2f}"

        metric_labels = {
            "total_price": price_formatted,
            "price_per_plot": (
                f"{price_formatted} per plot"
            ),
            "price_per_acre": (
                f"{price_formatted} per acre"
            ),
            "price_per_hectare": (
                f"{price_formatted} per hectare"
            ),
            "price_per_sqm": (
                f"{price_formatted} per sqm"
            ),
            "price_per_sqft": (
                f"{price_formatted} per sqft"
            ),
            "annual_rent": (
                f"{price_formatted} per year"
            ),
            "monthly_rent": (
                f"{price_formatted} per month"
            ),
        }

        return metric_labels.get(
            self.price_metric,
            price_formatted,
        )

    @property
    def location_string(self):
        """Generate a formatted location string for international addresses"""
        parts = []

        if self.estate_name:
            parts.append(self.estate_name)

        if self.local_area:
            parts.append(self.local_area)

        if self.city:
            parts.append(self.city)

        if self.state_province:
            parts.append(self.state_province)

        if self.country:
            parts.append(self.country)

        return (
            ", ".join(parts)
            if parts
            else "Location not specified"
        )

    @property
    def full_location(self):
        """Generate a complete address string with postal code"""
        parts = []

        if self.full_address:
            return self.full_address

        if self.estate_name:
            parts.append(self.estate_name)

        if self.local_area:
            parts.append(self.local_area)

        if self.city:
            parts.append(self.city)

        if self.state_province:
            parts.append(self.state_province)

        if self.postal_code:
            parts.append(self.postal_code)

        if self.country:
            parts.append(self.country)

        return ", ".join(parts) if parts else ""

    @property
    def condition_label(self):
        """Get the human-readable label for property condition"""
        return dict(PROPERTY_CONDITION).get(self.property_condition, self.property_condition)

    @property
    def is_new_construction(self):
        """Check if property is new construction"""
        return self.property_condition == "new"

    @property
    def needs_renovation(self):
        """Check if property needs renovation"""
        return self.property_condition == "needs_renovation"