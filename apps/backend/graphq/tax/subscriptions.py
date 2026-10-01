'''import graphene
from django.db.models import Q
from django.utils import timezone
from graphql.accounts.types import UserNode
from graphql.channel.types import ChannelNode
from graphql.subscriptions.subscription import Subscription
from graphql.tax.types import (TaxClassCountryRateNode, TaxClassNode,
                               TaxConfigurationNode,
                               TaxConfigurationPerCountryNode)
from graphql_relay import from_global_id

from channel.models import Channel
from tax.models import (TaxClass, TaxClassCountryRate, TaxConfiguration,
                        TaxConfigurationPerCountry)

from . import TaxCalculationStrategy

# ----------------------------------------------------------------------
# 🏷️ TAX CLASS SUBSCRIPTIONS
# ----------------------------------------------------------------------

class OnTaxClassCreated(Subscription):
    tax_class = graphene.Field(TaxClassNode)
    name = graphene.String()
    created_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        if user.has_perm('tax.manage_taxes'):
            return [f"all_tax_classes_created"]
        else:
            raise Exception("Not authorized")

    @staticmethod
    def publish(payload, info):
        return OnTaxClassCreated(
            tax_class=payload["tax_class"],
            name=payload["name"],
            created_at=payload["created_at"]
        )

    @classmethod
    def broadcast(cls, tax_class):
        cls.broadcast_group(
            group="all_tax_classes_created",
            payload={
                "tax_class": tax_class,
                "name": tax_class.name,
                "created_at": timezone.now().isoformat()
            }
        )

class OnTaxClassUpdated(Subscription):
    class Arguments:
        tax_class_id = graphene.ID(required=True)

    tax_class = graphene.Field(TaxClassNode)
    old_name = graphene.String()
    new_name = graphene.String()
    updated_fields = graphene.List(graphene.String)
    updated_by = graphene.Field(UserNode)
    updated_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info, tax_class_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(tax_class_id)[1]
        try:
            tax_class = TaxClass.objects.get(id=real_id)
            if user.has_perm('tax.manage_taxes'):
                return [f"tax_class_updates_{real_id}"]
            else:
                raise Exception("Not authorized")
        except TaxClass.DoesNotExist:
            raise Exception("Tax class not found")

    @staticmethod
    def publish(payload, info, tax_class_id):
        return OnTaxClassUpdated(
            tax_class=payload["tax_class"],
            old_name=payload["old_name"],
            new_name=payload["new_name"],
            updated_fields=payload["updated_fields"],
            updated_by=payload["updated_by"],
            updated_at=payload["updated_at"]
        )

    @classmethod
    def broadcast(cls, tax_class, old_name, new_name, updated_fields, updated_by):
        cls.broadcast_group(
            group=f"tax_class_updates_{tax_class.id}",
            payload={
                "tax_class": tax_class,
                "old_name": old_name,
                "new_name": new_name,
                "updated_fields": updated_fields,
                "updated_by": updated_by,
                "updated_at": timezone.now().isoformat()
            }
        )

class OnTaxClassDeleted(Subscription):
    class Arguments:
        tax_class_id = graphene.ID(required=True)

    tax_class_id = graphene.ID()
    tax_class_name = graphene.String()
    deleted_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info, tax_class_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        if user.has_perm('tax.manage_taxes'):
            return [f"tax_class_deletions"]
        else:
            raise Exception("Not authorized")

    @staticmethod
    def publish(payload, info, tax_class_id):
        return OnTaxClassDeleted(
            tax_class_id=payload["tax_class_id"],
            tax_class_name=payload["tax_class_name"],
            deleted_at=payload["deleted_at"]
        )

    @classmethod
    def broadcast(cls, tax_class_id, tax_class_name):
        cls.broadcast_group(
            group="tax_class_deletions",
            payload={
                "tax_class_id": tax_class_id,
                "tax_class_name": tax_class_name,
                "deleted_at": timezone.now().isoformat()
            }
        )

# ----------------------------------------------------------------------
# 🌍 TAX COUNTRY RATE SUBSCRIPTIONS
# ----------------------------------------------------------------------

class OnTaxCountryRateCreated(Subscription):
    class Arguments:
        tax_class_id = graphene.ID(required=False)

    tax_country_rate = graphene.Field(TaxClassCountryRateNode)
    tax_class = graphene.Field(TaxClassNode)
    country = graphene.String()
    rate = graphene.Float()
    is_default = graphene.Boolean()
    created_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info, tax_class_id=None):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        if user.has_perm('tax.manage_taxes'):
            if tax_class_id:
                real_id = from_global_id(tax_class_id)[1]
                return [f"tax_class_rates_{real_id}"]
            else:
                return [f"all_tax_country_rates_created"]
        else:
            raise Exception("Not authorized")

    @staticmethod
    def publish(payload, info, tax_class_id=None):
        return OnTaxCountryRateCreated(
            tax_country_rate=payload["tax_country_rate"],
            tax_class=payload["tax_class"],
            country=payload["country"],
            rate=payload["rate"],
            is_default=payload["is_default"],
            created_at=payload["created_at"]
        )

    @classmethod
    def broadcast_for_tax_class(cls, tax_class, tax_country_rate):
        cls.broadcast_group(
            group=f"tax_class_rates_{tax_class.id}",
            payload={
                "tax_country_rate": tax_country_rate,
                "tax_class": tax_class,
                "country": tax_country_rate.country.code,
                "rate": float(tax_country_rate.rate),
                "is_default": tax_country_rate.tax_class is None,
                "created_at": timezone.now().isoformat()
            }
        )

    @classmethod
    def broadcast_to_all(cls, tax_country_rate):
        cls.broadcast_group(
            group="all_tax_country_rates_created",
            payload={
                "tax_country_rate": tax_country_rate,
                "tax_class": tax_country_rate.tax_class,
                "country": tax_country_rate.country.code,
                "rate": float(tax_country_rate.rate),
                "is_default": tax_country_rate.tax_class is None,
                "created_at": timezone.now().isoformat()
            }
        )

class OnTaxCountryRateUpdated(Subscription):
    class Arguments:
        tax_country_rate_id = graphene.ID(required=True)

    tax_country_rate = graphene.Field(TaxClassCountryRateNode)
    tax_class = graphene.Field(TaxClassNode)
    country = graphene.String()
    old_rate = graphene.Float()
    new_rate = graphene.Float()
    rate_change = graphene.Float()
    updated_by = graphene.Field(UserNode)
    updated_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info, tax_country_rate_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(tax_country_rate_id)[1]
        try:
            tax_country_rate = TaxClassCountryRate.objects.get(id=real_id)
            if user.has_perm('tax.manage_taxes'):
                return [f"tax_country_rate_updates_{real_id}"]
            else:
                raise Exception("Not authorized")
        except TaxClassCountryRate.DoesNotExist:
            raise Exception("Tax country rate not found")

    @staticmethod
    def publish(payload, info, tax_country_rate_id):
        return OnTaxCountryRateUpdated(
            tax_country_rate=payload["tax_country_rate"],
            tax_class=payload["tax_class"],
            country=payload["country"],
            old_rate=payload["old_rate"],
            new_rate=payload["new_rate"],
            rate_change=payload["rate_change"],
            updated_by=payload["updated_by"],
            updated_at=payload["updated_at"]
        )

    @classmethod
    def broadcast(cls, tax_country_rate, old_rate, new_rate, updated_by):
        rate_change = float(new_rate) - float(old_rate)
        cls.broadcast_group(
            group=f"tax_country_rate_updates_{tax_country_rate.id}",
            payload={
                "tax_country_rate": tax_country_rate,
                "tax_class": tax_country_rate.tax_class,
                "country": tax_country_rate.country.code,
                "old_rate": float(old_rate),
                "new_rate": float(new_rate),
                "rate_change": rate_change,
                "updated_by": updated_by,
                "updated_at": timezone.now().isoformat()
            }
        )

class OnTaxCountryRateDeleted(Subscription):
    class Arguments:
        tax_class_id = graphene.ID(required=False)

    tax_country_rate_id = graphene.ID()
    country = graphene.String()
    tax_class_name = graphene.String()
    rate = graphene.Float()
    deleted_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info, tax_class_id=None):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        if user.has_perm('tax.manage_taxes'):
            if tax_class_id:
                real_id = from_global_id(tax_class_id)[1]
                return [f"tax_class_rate_deletions_{real_id}"]
            else:
                return [f"all_tax_country_rate_deletions"]
        else:
            raise Exception("Not authorized")

    @staticmethod
    def publish(payload, info, tax_class_id=None):
        return OnTaxCountryRateDeleted(
            tax_country_rate_id=payload["tax_country_rate_id"],
            country=payload["country"],
            tax_class_name=payload["tax_class_name"],
            rate=payload["rate"],
            deleted_at=payload["deleted_at"]
        )

    @classmethod
    def broadcast_for_tax_class(cls, tax_class, tax_country_rate):
        cls.broadcast_group(
            group=f"tax_class_rate_deletions_{tax_class.id}",
            payload={
                "tax_country_rate_id": str(tax_country_rate.id),
                "country": tax_country_rate.country.code,
                "tax_class_name": tax_class.name if tax_class else "Default",
                "rate": float(tax_country_rate.rate),
                "deleted_at": timezone.now().isoformat()
            }
        )

    @classmethod
    def broadcast_to_all(cls, tax_country_rate):
        tax_class_name = tax_country_rate.tax_class.name if tax_country_rate.tax_class else "Default"
        cls.broadcast_group(
            group="all_tax_country_rate_deletions",
            payload={
                "tax_country_rate_id": str(tax_country_rate.id),
                "country": tax_country_rate.country.code,
                "tax_class_name": tax_class_name,
                "rate": float(tax_country_rate.rate),
                "deleted_at": timezone.now().isoformat()
            }
        )

# ----------------------------------------------------------------------
# ⚙️ TAX CONFIGURATION SUBSCRIPTIONS
# ----------------------------------------------------------------------

class OnTaxConfigurationCreated(Subscription):
    class Arguments:
        channel_id = graphene.ID(required=False)

    tax_configuration = graphene.Field(TaxConfigurationNode)
    channel = graphene.Field(ChannelNode)
    charge_taxes = graphene.Boolean()
    tax_calculation_strategy = graphene.String()
    display_gross_prices = graphene.Boolean()
    prices_entered_with_tax = graphene.Boolean()
    created_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info, channel_id=None):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        if user.has_perm('tax.manage_taxes'):
            if channel_id:
                real_id = from_global_id(channel_id)[1]
                return [f"channel_tax_config_{real_id}"]
            else:
                return [f"all_tax_configurations_created"]
        else:
            raise Exception("Not authorized")

    @staticmethod
    def publish(payload, info, channel_id=None):
        return OnTaxConfigurationCreated(
            tax_configuration=payload["tax_configuration"],
            channel=payload["channel"],
            charge_taxes=payload["charge_taxes"],
            tax_calculation_strategy=payload["tax_calculation_strategy"],
            display_gross_prices=payload["display_gross_prices"],
            prices_entered_with_tax=payload["prices_entered_with_tax"],
            created_at=payload["created_at"]
        )

    @classmethod
    def broadcast_for_channel(cls, channel, tax_configuration):
        cls.broadcast_group(
            group=f"channel_tax_config_{channel.id}",
            payload={
                "tax_configuration": tax_configuration,
                "channel": channel,
                "charge_taxes": tax_configuration.charge_taxes,
                "tax_calculation_strategy": tax_configuration.tax_calculation_strategy,
                "display_gross_prices": tax_configuration.display_gross_prices,
                "prices_entered_with_tax": tax_configuration.prices_entered_with_tax,
                "created_at": timezone.now().isoformat()
            }
        )

    @classmethod
    def broadcast_to_all(cls, tax_configuration):
        cls.broadcast_group(
            group="all_tax_configurations_created",
            payload={
                "tax_configuration": tax_configuration,
                "channel": tax_configuration.channel,
                "charge_taxes": tax_configuration.charge_taxes,
                "tax_calculation_strategy": tax_configuration.tax_calculation_strategy,
                "display_gross_prices": tax_configuration.display_gross_prices,
                "prices_entered_with_tax": tax_configuration.prices_entered_with_tax,
                "created_at": timezone.now().isoformat()
            }
        )

class OnTaxConfigurationUpdated(Subscription):
    class Arguments:
        tax_configuration_id = graphene.ID(required=True)

    tax_configuration = graphene.Field(TaxConfigurationNode)
    channel = graphene.Field(ChannelNode)
    updated_fields = graphene.List(graphene.String)
    old_charge_taxes = graphene.Boolean()
    new_charge_taxes = graphene.Boolean()
    old_tax_calculation_strategy = graphene.String()
    new_tax_calculation_strategy = graphene.String()
    old_display_gross_prices = graphene.Boolean()
    new_display_gross_prices = graphene.Boolean()
    updated_by = graphene.Field(UserNode)
    updated_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info, tax_configuration_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(tax_configuration_id)[1]
        try:
            tax_configuration = TaxConfiguration.objects.get(id=real_id)
            if user.has_perm('tax.manage_taxes'):
                return [f"tax_configuration_updates_{real_id}"]
            else:
                raise Exception("Not authorized")
        except TaxConfiguration.DoesNotExist:
            raise Exception("Tax configuration not found")

    @staticmethod
    def publish(payload, info, tax_configuration_id):
        return OnTaxConfigurationUpdated(
            tax_configuration=payload["tax_configuration"],
            channel=payload["channel"],
            updated_fields=payload["updated_fields"],
            old_charge_taxes=payload["old_charge_taxes"],
            new_charge_taxes=payload["new_charge_taxes"],
            old_tax_calculation_strategy=payload["old_tax_calculation_strategy"],
            new_tax_calculation_strategy=payload["new_tax_calculation_strategy"],
            old_display_gross_prices=payload["old_display_gross_prices"],
            new_display_gross_prices=payload["new_display_gross_prices"],
            updated_by=payload["updated_by"],
            updated_at=payload["updated_at"]
        )

    @classmethod
    def broadcast(cls, tax_configuration, updated_fields, old_charge_taxes, new_charge_taxes, 
                  old_tax_strategy, new_tax_strategy, old_display_gross, new_display_gross, updated_by):
        cls.broadcast_group(
            group=f"tax_configuration_updates_{tax_configuration.id}",
            payload={
                "tax_configuration": tax_configuration,
                "channel": tax_configuration.channel,
                "updated_fields": updated_fields,
                "old_charge_taxes": old_charge_taxes,
                "new_charge_taxes": new_charge_taxes,
                "old_tax_calculation_strategy": old_tax_strategy,
                "new_tax_calculation_strategy": new_tax_strategy,
                "old_display_gross_prices": old_display_gross,
                "new_display_gross_prices": new_display_gross,
                "updated_by": updated_by,
                "updated_at": timezone.now().isoformat()
            }
        )

# ----------------------------------------------------------------------
# 🇺🇸 TAX CONFIGURATION PER COUNTRY SUBSCRIPTIONS
# ----------------------------------------------------------------------

class OnTaxCountryConfigurationCreated(Subscription):
    class Arguments:
        tax_configuration_id = graphene.ID(required=True)

    country_configuration = graphene.Field(TaxConfigurationPerCountryNode)
    tax_configuration = graphene.Field(TaxConfigurationNode)
    channel = graphene.Field(ChannelNode)
    country = graphene.String()
    charge_taxes = graphene.Boolean()
    tax_calculation_strategy = graphene.String()
    display_gross_prices = graphene.Boolean()
    created_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info, tax_configuration_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(tax_configuration_id)[1]
        try:
            tax_configuration = TaxConfiguration.objects.get(id=real_id)
            if user.has_perm('tax.manage_taxes'):
                return [f"tax_config_country_rules_{real_id}"]
            else:
                raise Exception("Not authorized")
        except TaxConfiguration.DoesNotExist:
            raise Exception("Tax configuration not found")

    @staticmethod
    def publish(payload, info, tax_configuration_id):
        return OnTaxCountryConfigurationCreated(
            country_configuration=payload["country_configuration"],
            tax_configuration=payload["tax_configuration"],
            channel=payload["channel"],
            country=payload["country"],
            charge_taxes=payload["charge_taxes"],
            tax_calculation_strategy=payload["tax_calculation_strategy"],
            display_gross_prices=payload["display_gross_prices"],
            created_at=payload["created_at"]
        )

    @classmethod
    def broadcast(cls, tax_configuration, country_configuration):
        cls.broadcast_group(
            group=f"tax_config_country_rules_{tax_configuration.id}",
            payload={
                "country_configuration": country_configuration,
                "tax_configuration": tax_configuration,
                "channel": tax_configuration.channel,
                "country": country_configuration.country.code,
                "charge_taxes": country_configuration.charge_taxes,
                "tax_calculation_strategy": country_configuration.tax_calculation_strategy,
                "display_gross_prices": country_configuration.display_gross_prices,
                "created_at": timezone.now().isoformat()
            }
        )

class OnTaxCountryConfigurationUpdated(Subscription):
    class Arguments:
        country_configuration_id = graphene.ID(required=True)

    country_configuration = graphene.Field(TaxConfigurationPerCountryNode)
    tax_configuration = graphene.Field(TaxConfigurationNode)
    channel = graphene.Field(ChannelNode)
    country = graphene.String()
    updated_fields = graphene.List(graphene.String)
    old_charge_taxes = graphene.Boolean()
    new_charge_taxes = graphene.Boolean()
    old_tax_calculation_strategy = graphene.String()
    new_tax_calculation_strategy = graphene.String()
    updated_by = graphene.Field(UserNode)
    updated_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info, country_configuration_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(country_configuration_id)[1]
        try:
            country_configuration = TaxConfigurationPerCountry.objects.get(id=real_id)
            if user.has_perm('tax.manage_taxes'):
                return [f"tax_country_config_updates_{real_id}"]
            else:
                raise Exception("Not authorized")
        except TaxConfigurationPerCountry.DoesNotExist:
            raise Exception("Country tax configuration not found")

    @staticmethod
    def publish(payload, info, country_configuration_id):
        return OnTaxCountryConfigurationUpdated(
            country_configuration=payload["country_configuration"],
            tax_configuration=payload["tax_configuration"],
            channel=payload["channel"],
            country=payload["country"],
            updated_fields=payload["updated_fields"],
            old_charge_taxes=payload["old_charge_taxes"],
            new_charge_taxes=payload["new_charge_taxes"],
            old_tax_calculation_strategy=payload["old_tax_calculation_strategy"],
            new_tax_calculation_strategy=payload["new_tax_calculation_strategy"],
            updated_by=payload["updated_by"],
            updated_at=payload["updated_at"]
        )

    @classmethod
    def broadcast(cls, country_configuration, updated_fields, old_charge_taxes, new_charge_taxes, 
                  old_tax_strategy, new_tax_strategy, updated_by):
        cls.broadcast_group(
            group=f"tax_country_config_updates_{country_configuration.id}",
            payload={
                "country_configuration": country_configuration,
                "tax_configuration": country_configuration.tax_configuration,
                "channel": country_configuration.tax_configuration.channel,
                "country": country_configuration.country.code,
                "updated_fields": updated_fields,
                "old_charge_taxes": old_charge_taxes,
                "new_charge_taxes": new_charge_taxes,
                "old_tax_calculation_strategy": old_tax_strategy,
                "new_tax_calculation_strategy": new_tax_strategy,
                "updated_by": updated_by,
                "updated_at": timezone.now().isoformat()
            }
        )

class OnTaxCountryConfigurationDeleted(Subscription):
    class Arguments:
        tax_configuration_id = graphene.ID(required=True)

    country_configuration_id = graphene.ID()
    tax_configuration = graphene.Field(TaxConfigurationNode)
    channel = graphene.Field(ChannelNode)
    country = graphene.String()
    deleted_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info, tax_configuration_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(tax_configuration_id)[1]
        try:
            tax_configuration = TaxConfiguration.objects.get(id=real_id)
            if user.has_perm('tax.manage_taxes'):
                return [f"tax_country_config_deletions_{real_id}"]
            else:
                raise Exception("Not authorized")
        except TaxConfiguration.DoesNotExist:
            raise Exception("Tax configuration not found")

    @staticmethod
    def publish(payload, info, tax_configuration_id):
        return OnTaxCountryConfigurationDeleted(
            country_configuration_id=payload["country_configuration_id"],
            tax_configuration=payload["tax_configuration"],
            channel=payload["channel"],
            country=payload["country"],
            deleted_at=payload["deleted_at"]
        )

    @classmethod
    def broadcast(cls, tax_configuration, country_configuration):
        cls.broadcast_group(
            group=f"tax_country_config_deletions_{tax_configuration.id}",
            payload={
                "country_configuration_id": str(country_configuration.id),
                "tax_configuration": tax_configuration,
                "channel": tax_configuration.channel,
                "country": country_configuration.country.code,
                "deleted_at": timezone.now().isoformat()
            }
        )

# ----------------------------------------------------------------------
# 📊 TAX ANALYTICS SUBSCRIPTIONS
# ----------------------------------------------------------------------

class OnTaxRatesUpdated(Subscription):
    class Arguments:
        channel_id = graphene.ID(required=False)

    channel = graphene.Field(ChannelNode)
    updated_countries = graphene.List(graphene.String)
    average_tax_rate = graphene.Float()
    highest_tax_rate = graphene.Float()
    lowest_tax_rate = graphene.Float()
    countries_count = graphene.Int()
    updated_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info, channel_id=None):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        if user.has_perm('tax.manage_taxes'):
            if channel_id:
                real_id = from_global_id(channel_id)[1]
                return [f"tax_rates_updates_{real_id}"]
            else:
                return [f"all_tax_rates_updates"]
        else:
            raise Exception("Not authorized")

    @staticmethod
    def publish(payload, info, channel_id=None):
        return OnTaxRatesUpdated(
            channel=payload["channel"],
            updated_countries=payload["updated_countries"],
            average_tax_rate=payload["average_tax_rate"],
            highest_tax_rate=payload["highest_tax_rate"],
            lowest_tax_rate=payload["lowest_tax_rate"],
            countries_count=payload["countries_count"],
            updated_at=payload["updated_at"]
        )

    @classmethod
    def broadcast_for_channel(cls, channel, updated_countries, average_rate, highest_rate, lowest_rate, countries_count):
        cls.broadcast_group(
            group=f"tax_rates_updates_{channel.id}",
            payload={
                "channel": channel,
                "updated_countries": updated_countries,
                "average_tax_rate": float(average_rate),
                "highest_tax_rate": float(highest_rate),
                "lowest_tax_rate": float(lowest_rate),
                "countries_count": countries_count,
                "updated_at": timezone.now().isoformat()
            }
        )

    @classmethod
    def broadcast_to_all(cls, updated_countries, average_rate, highest_rate, lowest_rate, countries_count):
        cls.broadcast_group(
            group="all_tax_rates_updates",
            payload={
                "channel": None,
                "updated_countries": updated_countries,
                "average_tax_rate": float(average_rate),
                "highest_tax_rate": float(highest_rate),
                "lowest_tax_rate": float(lowest_rate),
                "countries_count": countries_count,
                "updated_at": timezone.now().isoformat()
            }
        )

class OnTaxCalculationStrategyChanged(Subscription):
    class Arguments:
        channel_id = graphene.ID(required=False)

    tax_configuration = graphene.Field(TaxConfigurationNode)
    channel = graphene.Field(ChannelNode)
    old_strategy = graphene.String()
    new_strategy = graphene.String()
    changed_by = graphene.Field(UserNode)
    changed_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info, channel_id=None):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        if user.has_perm('tax.manage_taxes'):
            if channel_id:
                real_id = from_global_id(channel_id)[1]
                return [f"tax_strategy_changes_{real_id}"]
            else:
                return [f"all_tax_strategy_changes"]
        else:
            raise Exception("Not authorized")

    @staticmethod
    def publish(payload, info, channel_id=None):
        return OnTaxCalculationStrategyChanged(
            tax_configuration=payload["tax_configuration"],
            channel=payload["channel"],
            old_strategy=payload["old_strategy"],
            new_strategy=payload["new_strategy"],
            changed_by=payload["changed_by"],
            changed_at=payload["changed_at"]
        )

    @classmethod
    def broadcast_for_channel(cls, channel, tax_configuration, old_strategy, new_strategy, changed_by):
        cls.broadcast_group(
            group=f"tax_strategy_changes_{channel.id}",
            payload={
                "tax_configuration": tax_configuration,
                "channel": channel,
                "old_strategy": old_strategy,
                "new_strategy": new_strategy,
                "changed_by": changed_by,
                "changed_at": timezone.now().isoformat()
            }
        )

    @classmethod
    def broadcast_to_all(cls, tax_configuration, old_strategy, new_strategy, changed_by):
        cls.broadcast_group(
            group="all_tax_strategy_changes",
            payload={
                "tax_configuration": tax_configuration,
                "channel": tax_configuration.channel,
                "old_strategy": old_strategy,
                "new_strategy": new_strategy,
                "changed_by": changed_by,
                "changed_at": timezone.now().isoformat()
            }
        )

# ----------------------------------------------------------------------
# Root TaxSubscription
# ----------------------------------------------------------------------

class TaxSubscription(graphene.ObjectType):
    # Tax Classes
    on_tax_class_created = OnTaxClassCreated.Field()
    on_tax_class_updated = OnTaxClassUpdated.Field()
    on_tax_class_deleted = OnTaxClassDeleted.Field()
    
    # Tax Country Rates
    on_tax_country_rate_created = OnTaxCountryRateCreated.Field()
    on_tax_country_rate_updated = OnTaxCountryRateUpdated.Field()
    on_tax_country_rate_deleted = OnTaxCountryRateDeleted.Field()
    
    # Tax Configurations
    on_tax_configuration_created = OnTaxConfigurationCreated.Field()
    on_tax_configuration_updated = OnTaxConfigurationUpdated.Field()
    
    # Country Tax Configurations
    on_tax_country_configuration_created = OnTaxCountryConfigurationCreated.Field()
    on_tax_country_configuration_updated = OnTaxCountryConfigurationUpdated.Field()
    on_tax_country_configuration_deleted = OnTaxCountryConfigurationDeleted.Field()
    
    # Analytics
    on_tax_rates_updated = OnTaxRatesUpdated.Field()
    on_tax_calculation_strategy_changed = OnTaxCalculationStrategyChanged.Field()
    
    
# Example usage in your Django views or signals
from tax.subscriptions import (OnTaxClassCreated, OnTaxConfigurationUpdated,
                               OnTaxCountryConfigurationCreated,
                               OnTaxCountryRateUpdated, OnTaxRatesUpdated)


# When a new tax class is created
def create_tax_class(name):
    tax_class = TaxClass.objects.create(name=name)
    
    OnTaxClassCreated.broadcast(tax_class)

# When tax country rate is updated
def update_tax_country_rate(tax_country_rate, new_rate, updated_by):
    old_rate = tax_country_rate.rate
    tax_country_rate.rate = new_rate
    tax_country_rate.save()
    
    OnTaxCountryRateUpdated.broadcast(
        tax_country_rate=tax_country_rate,
        old_rate=old_rate,
        new_rate=new_rate,
        updated_by=updated_by
    )

# When tax configuration is updated
def update_tax_configuration(tax_configuration, updated_fields, old_values, new_values, updated_by):
    OnTaxConfigurationUpdated.broadcast(
        tax_configuration=tax_configuration,
        updated_fields=updated_fields,
        old_charge_taxes=old_values.get('charge_taxes'),
        new_charge_taxes=new_values.get('charge_taxes'),
        old_tax_strategy=old_values.get('tax_calculation_strategy'),
        new_tax_strategy=new_values.get('tax_calculation_strategy'),
        old_display_gross=old_values.get('display_gross_prices'),
        new_display_gross=new_values.get('display_gross_prices'),
        updated_by=updated_by
    )

# When country-specific tax configuration is created
def create_country_tax_configuration(tax_configuration, country, config_data):
    country_configuration = TaxConfigurationPerCountry.objects.create(
        tax_configuration=tax_configuration,
        country=country,
        **config_data
    )
    
    OnTaxCountryConfigurationCreated.broadcast(tax_configuration, country_configuration)

# When tax rates are updated in bulk
def bulk_update_tax_rates(channel, updated_countries_data):
    updated_countries = []
    rates = []
    
    for country_data in updated_countries_data:
        tax_rate = update_tax_rate_for_country(country_data)
        updated_countries.append(country_data['country'])
        rates.append(float(tax_rate.rate))
    
    if rates:
        average_rate = sum(rates) / len(rates)
        highest_rate = max(rates)
        lowest_rate = min(rates)
        
        OnTaxRatesUpdated.broadcast_for_channel(
            channel=channel,
            updated_countries=updated_countries,
            average_rate=average_rate,
            highest_rate=highest_rate,
            lowest_rate=lowest_rate,
            countries_count=len(updated_countries)
        )

# When tax calculation strategy changes
def change_tax_calculation_strategy(tax_configuration, new_strategy, changed_by):
    old_strategy = tax_configuration.tax_calculation_strategy
    tax_configuration.tax_calculation_strategy = new_strategy
    tax_configuration.save()
    
    OnTaxCalculationStrategyChanged.broadcast_for_channel(
        channel=tax_configuration.channel,
        tax_configuration=tax_configuration,
        old_strategy=old_strategy,
        new_strategy=new_strategy,
        changed_by=changed_by
    )

# When tax class is deleted
def delete_tax_class(tax_class):
    tax_class_id = str(tax_class.id)
    tax_class_name = tax_class.name
    tax_class.delete()
    
    OnTaxClassDeleted.broadcast(tax_class_id, tax_class_name)

# When country tax rate is deleted
def delete_tax_country_rate(tax_country_rate):
    tax_class = tax_country_rate.tax_class
    OnTaxCountryRateDeleted.broadcast_for_tax_class(tax_class, tax_country_rate)
    tax_country_rate.delete()

# When country tax configuration is deleted
def delete_country_tax_configuration(country_configuration):
    tax_configuration = country_configuration.tax_configuration
    OnTaxCountryConfigurationDeleted.broadcast(tax_configuration, country_configuration)
    country_configuration.delete()

# Update tax analytics
def update_tax_analytics(channel):
    # Calculate tax rate statistics
    country_rates = TaxClassCountryRate.objects.all()
    if country_rates.exists():
        rates = [float(rate.rate) for rate in country_rates]
        average_rate = sum(rates) / len(rates)
        highest_rate = max(rates)
        lowest_rate = min(rates)
        
        OnTaxRatesUpdated.broadcast_for_channel(
            channel=channel,
            updated_countries=[rate.country.code for rate in country_rates],
            average_rate=average_rate,
            highest_rate=highest_rate,
            lowest_rate=lowest_rate,
            countries_count=len(country_rates)
        )'''