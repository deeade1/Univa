# apps/backend/graphq/tax/types.py
"""
Graphene node types for the tax domain.

Each node is aligned against `tax/models.py`. The `filter_fields` maps
use Graphene-Django's dict form so exact and lookup filters (icontains,
range comparisons, isnull) are both available.

Note on `TaxConfiguration.channel`: the model conditionally defines the
`channel` FK based on whether the Channel model imported successfully at
module load time. We mirror that decision here so filtering on `channel`
never references a field that doesn't exist in the DB.
"""

import graphene
from graphene import relay
from graphene_django import DjangoObjectType

from tax import models

# Mirror the model's module-level detection. Import the flag from the
# model module rather than re-detecting here so both stay in sync.
CHANNEL_AVAILABLE = getattr(models, "CHANNEL_AVAILABLE", False)


# =============================================================================
# TaxClass
# =============================================================================

class TaxClassNode(DjangoObjectType):
    """
    Tax class — categorises products under a shared tax rate scheme.
    """

    class Meta:
        model = models.TaxClass
        interfaces = (relay.Node,)
        fields = "__all__"
        filter_fields = {
            "id": ["exact"],
            "name": ["exact", "icontains", "istartswith"],
            "is_active": ["exact"],
            "created_at": ["exact", "lt", "gt"],
            "updated_at": ["exact", "lt", "gt"],
            "created_by": ["exact"],
            "modified_by": ["exact"],
        }


# =============================================================================
# TaxClassCountryRate
# =============================================================================

class TaxClassCountryRateNode(DjangoObjectType):
    """
    Country-specific rate within a tax class.

    `tax_class=None` denotes the default rate for the country.
    """

    class Meta:
        model = models.TaxClassCountryRate
        interfaces = (relay.Node,)
        fields = "__all__"
        filter_fields = {
            "id": ["exact"],
            "country": ["exact", "in"],
            "tax_class": ["exact", "isnull"],
            "rate": ["exact", "gte", "lte"],
            "description": ["exact", "icontains"],
            "created_at": ["exact", "lt", "gt"],
            "updated_at": ["exact", "lt", "gt"],
            "created_by": ["exact"],
        }


# =============================================================================
# TaxConfiguration
# =============================================================================

class TaxConfigurationNode(DjangoObjectType):
    """
    Per-channel tax configuration.

    The `channel` FK is only present when `CHANNEL_AVAILABLE` — the
    filter map reflects that.
    """

    class Meta:
        model = models.TaxConfiguration
        interfaces = (relay.Node,)
        fields = "__all__"

        filter_fields = {
            "id": ["exact"],
            "charge_taxes": ["exact"],
            "tax_calculation_strategy": ["exact", "in"],
            "display_gross_prices": ["exact"],
            "prices_entered_with_tax": ["exact"],
            "tax_app_id": ["exact", "icontains", "isnull"],
            "created_at": ["exact", "lt", "gt"],
            "updated_at": ["exact", "lt", "gt"],
            "created_by": ["exact"],
            "modified_by": ["exact"],
            #"channel": ["exact"],
        }
       


# =============================================================================
# TaxConfigurationPerCountry
# =============================================================================

class TaxConfigurationPerCountryNode(DjangoObjectType):
    """
    Country override for a channel's tax configuration.
    """

    class Meta:
        model = models.TaxConfigurationPerCountry
        interfaces = (relay.Node,)
        fields = "__all__"
        filter_fields = {
            "id": ["exact"],
            "tax_configuration": ["exact"],
            "country": ["exact", "in"],
            "charge_taxes": ["exact"],
            "tax_calculation_strategy": ["exact", "in"],
            "display_gross_prices": ["exact"],
            "tax_app_id": ["exact", "icontains", "isnull"],
            "created_at": ["exact", "lt", "gt"],
            "updated_at": ["exact", "lt", "gt"],
            "created_by": ["exact"],
        }