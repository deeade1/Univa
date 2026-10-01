from typing import TYPE_CHECKING
from urllib.parse import urlparse

import graphene

# -------------------------------------------------------------------
# Lazy import helper
# -------------------------------------------------------------------
def import_build_absolute_uri():
    """Lazy import to avoid AppRegistryNotReady errors."""
    from core.utils import build_absolute_uri
    return build_absolute_uri

# -------------------------------------------------------------------
# GraphQL Types
# -------------------------------------------------------------------

# Money is safe to import at top-level if it doesn't import models
from .money import VAT

TYPES_WITH_DOUBLE_ID_AVAILABLE = [
    "Order", 
    "OrderLine", 
    "OrderDiscount", 
    "CheckoutLine"
]

# Re-export GraphQL Enums lazily if needed
from ..enums import (
    IconThumbnailFormatEnum,
    JobStatusEnum,
    LanguageCodeEnum,
    ThumbnailFormatEnum,
    TimePeriodTypeEnum,
    WeightUnitsEnum,
)


class LanguageDisplay(graphene.ObjectType):
    code = LanguageCodeEnum(
        description="ISO 639 representation of the language name.", required=True
    )
    language = graphene.String(description="Full name of the language.", required=True)


class NonNullList(graphene.List):
    """A list type that automatically adds non-null constraint on contained items."""

    def __init__(self, of_type, *args, **kwargs):
        of_type = graphene.NonNull(of_type)
        super().__init__(of_type, *args, **kwargs)


class CountryDisplay(graphene.ObjectType):
    code = graphene.String(description="Country code.", required=True)
    country = graphene.String(description="Country name.", required=True)
    vat = graphene.Field(
        VAT,
        description="Country tax.",
        deprecation_reason=(
            f"Always returns `null`. Use `TaxClassCountryRate`"
            " type to manage tax rates per country."
        ),
    )


class SeoInput(graphene.InputObjectType):
    title = graphene.String(description="SEO title.")
    description = graphene.String(description="SEO description.")


class Weight(graphene.ObjectType):
    unit = WeightUnitsEnum(description="Weight unit.", required=True)
    value = graphene.Float(
        description="Weight value. Returns a value with maximal three decimal places",
        required=True,
    )

    class Meta:
        description = "Represents weight value in a specific weight unit."

    @staticmethod
    def resolve_value(root, _info):
        return round(root.value, 3)


class PriceInput(graphene.InputObjectType):
    currency = graphene.String(description="Currency code.", required=True)
    amount = graphene.Decimal(description="Amount of money.", required=True)


class PriceRangeInput(graphene.InputObjectType):
    gte = graphene.Float(description="Price greater than or equal to.", required=False)
    lte = graphene.Float(description="Price less than or equal to.", required=False)


class IntRangeInput(graphene.InputObjectType):
    gte = graphene.Int(description="Value greater than or equal to.", required=False)
    lte = graphene.Int(description="Value less than or equal to.", required=False)


class TimePeriodInputType(graphene.InputObjectType):
    amount = graphene.Int(description="The length of the period.", required=True)
    type = TimePeriodTypeEnum(description="The type of the period.", required=True)


class TaxType(graphene.ObjectType):
    """Representation of tax types fetched from tax gateway."""
    description = graphene.String(description="Description of the tax type.")
    tax_code = graphene.String(description="External tax code used to identify given tax group.")


class Image(graphene.ObjectType):
    url = graphene.String(required=True, description="The URL of the image.")
    alt = graphene.String(description="Alt text for an image.")

    class Meta:
        description = "Represents an image."

    def resolve_url(root, _info: "ResolveInfo"):
        build_absolute_uri = import_build_absolute_uri()  # lazy import
        if urlparse(root.url).netloc:
            return root.url
        return build_absolute_uri(root.url)


class ThumbnailField(graphene.Field):
    size = graphene.Int(
        description=(
            "Desired longest side the image in pixels. Defaults to 4096. "
            "Images are never cropped. "
            "Pass 0 to retrieve the original size (not recommended)."
        ),
    )
    format = ThumbnailFormatEnum(
        default_value="ORIGINAL",
        description=(
            "The format of the image. When not provided, format of the original "
            "image will be used."
        ),
    )

    def __init__(self, of_type=Image, *args, **kwargs):
        kwargs["size"] = self.size
        kwargs["format"] = self.format
        super().__init__(of_type, *args, **kwargs)


class IconThumbnailField(ThumbnailField):
    format = IconThumbnailFormatEnum(
        default_value="ORIGINAL",
        description=(
            "The format of the image. When not provided, format of the original "
            "image will be used."
        ),
    )


class Job(graphene.Interface):
    status = JobStatusEnum(description="Job status.", required=True)
    created_at = graphene.DateTime(
        description="Created date time of job in ISO 8601 format.", required=True
    )
    updated_at = graphene.DateTime(
        description="Date time of job last update in ISO 8601 format.", required=True
    )
    message = graphene.String(description="Job message.")

    @classmethod
    def resolve_type(cls, instance, _info: "ResolveInfo"):
        return None


class TimePeriod(graphene.ObjectType):
    amount = graphene.Int(description="The length of the period.", required=True)
    type = TimePeriodTypeEnum(description="The type of the period.", required=True)
