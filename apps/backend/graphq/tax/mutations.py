import graphene
from graphene import relay
from graphql import GraphQLError

from tax import models

from .types import (
    TaxClassCountryRateNode, 
    TaxClassNode,
    TaxConfigurationPerCountryNode, 
    TaxConfigurationNode
)


# ---------- Helper ----------
def get_object(model, id):
    try:
        return model.objects.get(pk=id)
    except model.DoesNotExist:
        raise GraphQLError(f"{model.__name__} with ID {id} does not exist.")


# ---------- TAX CLASS ----------
class CreateTaxClass(relay.ClientIDMutation):
    class Input:
        name = graphene.String(required=True)

    tax_class = graphene.Field(TaxClassNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, name):
        obj = models.TaxClass.objects.create(name=name)
        return CreateTaxClass(tax_class=obj)


class UpdateTaxClass(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        name = graphene.String(required=False)

    tax_class = graphene.Field(TaxClassNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, id, **kwargs):
        obj = get_object(models.TaxClass, id)
        for k, v in kwargs.items():
            setattr(obj, k, v)
        obj.save()
        return UpdateTaxClass(tax_class=obj)


class DeleteTaxClass(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, id):
        obj = get_object(models.TaxClass, id)
        obj.delete()
        return DeleteTaxClass(ok=True)


# ---------- TAX CLASS COUNTRY RATE ----------
class CreateTaxClassCountryRate(relay.ClientIDMutation):
    class Input:
        tax_class_id = graphene.ID(required=False)
        country = graphene.String(required=True)
        rate = graphene.Decimal(required=True)

    tax_class_country_rate = graphene.Field(TaxClassCountryRateNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, country, rate, tax_class_id=None):
        tax_class = get_object(models.TaxClass, tax_class_id) if tax_class_id else None
        obj = models.TaxClassCountryRate.objects.create(
            tax_class=tax_class, country=country, rate=rate
        )
        return CreateTaxClassCountryRate(tax_class_country_rate=obj)


class DeleteTaxClassCountryRate(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, id):
        obj = get_object(models.TaxClassCountryRate, id)
        obj.delete()
        return DeleteTaxClassCountryRate(ok=True)


# ---------- TAX CONFIGURATION ----------
class CreateTaxConfiguration(relay.ClientIDMutation):
    class Input:
        channel_id = graphene.ID(required=True)
        charge_taxes = graphene.Boolean(required=False)
        tax_calculation_strategy = graphene.String(required=False)
        display_gross_prices = graphene.Boolean(required=False)
        prices_entered_with_tax = graphene.Boolean(required=False)
        tax_app_id = graphene.String(required=False)

    tax_configuration = graphene.Field(TaxConfigurationNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, channel_id, **kwargs):
        from channel.models import Channel

        channel = get_object(Channel, channel_id)
        obj = models.TaxConfiguration.objects.create(channel=channel, **kwargs)
        return CreateTaxConfiguration(tax_configuration=obj)


class UpdateTaxConfiguration(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        charge_taxes = graphene.Boolean(required=False)
        display_gross_prices = graphene.Boolean(required=False)
        prices_entered_with_tax = graphene.Boolean(required=False)
        tax_calculation_strategy = graphene.String(required=False)
        tax_app_id = graphene.String(required=False)

    tax_configuration = graphene.Field(TaxConfigurationNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, id, **kwargs):
        obj = get_object(models.TaxConfiguration, id)
        for k, v in kwargs.items():
            setattr(obj, k, v)
        obj.save()
        return UpdateTaxConfiguration(tax_configuration=obj)


class DeleteTaxConfiguration(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, id):
        obj = get_object(models.TaxConfiguration, id)
        obj.delete()
        return DeleteTaxConfiguration(ok=True)


# ---------- TAX CONFIG PER COUNTRY ----------
class CreateTaxConfigurationPerCountry(relay.ClientIDMutation):
    class Input:
        tax_configuration_id = graphene.ID(required=True)
        country = graphene.String(required=True)
        charge_taxes = graphene.Boolean(required=False)
        tax_calculation_strategy = graphene.String(required=False)
        display_gross_prices = graphene.Boolean(required=False)
        tax_app_id = graphene.String(required=False)

    tax_configuration_per_country = graphene.Field(TaxConfigurationPerCountryNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, tax_configuration_id, country, **kwargs):
        config = get_object(models.TaxConfiguration, tax_configuration_id)
        obj = models.TaxConfigurationPerCountry.objects.create(
            tax_configuration=config, country=country, **kwargs
        )
        return CreateTaxConfigurationPerCountry(
            tax_configuration_per_country=obj
        )


class DeleteTaxConfigurationPerCountry(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, id):
        obj = get_object(models.TaxConfigurationPerCountry, id)
        obj.delete()
        return DeleteTaxConfigurationPerCountry(ok=True)


# ---------- ROOT ----------
class TaxMutations(graphene.ObjectType):
    create_tax_class = CreateTaxClass.Field()
    update_tax_class = UpdateTaxClass.Field()
    delete_tax_class = DeleteTaxClass.Field()

    create_tax_class_country_rate = CreateTaxClassCountryRate.Field()
    delete_tax_class_country_rate = DeleteTaxClassCountryRate.Field()

    create_tax_configuration = CreateTaxConfiguration.Field()
    update_tax_configuration = UpdateTaxConfiguration.Field()
    delete_tax_configuration = DeleteTaxConfiguration.Field()

    create_tax_configuration_per_country = CreateTaxConfigurationPerCountry.Field()
    delete_tax_configuration_per_country = DeleteTaxConfigurationPerCountry.Field()
