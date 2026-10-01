import graphene
from graphene import relay
from graphene_django.filter import DjangoFilterConnectionField

from .mutations import TaxMutations
from .types import (
    TaxClassCountryRateNode, 
    TaxClassNode,
    TaxConfigurationPerCountryNode, 
    TaxConfigurationNode
)


class TaxQueries(graphene.ObjectType):
    # TaxClass
    tax_class = relay.Node.Field(TaxClassNode)
    all_tax_classes = DjangoFilterConnectionField(TaxClassNode)

    # TaxClassCountryRate
    tax_class_country_rate = relay.Node.Field(TaxClassCountryRateNode)
    all_tax_class_country_rates = DjangoFilterConnectionField(TaxClassCountryRateNode)

    # TaxConfiguration
    tax_configuration = relay.Node.Field(TaxConfigurationNode)
    all_tax_configurations = DjangoFilterConnectionField(TaxConfigurationNode)

    # TaxConfigurationPerCountry
    tax_configuration_per_country = relay.Node.Field(TaxConfigurationPerCountryNode)
    all_tax_configuration_per_countries = DjangoFilterConnectionField(
        TaxConfigurationPerCountryNode
    )
