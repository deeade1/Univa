import graphene
from graphene import relay
from graphql_relay import from_global_id

from ecommerce.models.shipping import (ShippingMethod, ShippingMethodChannelListing,
                             ShippingMethodPostalCodeRule, ShippingZone)

from graphq.ecommerce.types.shipping import (ShippingMethodChannelListingNode, ShippingMethodNode,
                    ShippingMethodPostalCodeRuleNode, ShippingZoneNode)

# ------------------------
# SHIPPING ZONE MUTATIONS
# ------------------------

class CreateShippingZone(relay.ClientIDMutation):
    """Create a new Shipping Zone."""
    class Input:
        name = graphene.String(required=True)
        description = graphene.String()
        countries = graphene.List(graphene.String)
        is_active = graphene.Boolean(default_value=True)

    shipping_zone = graphene.Field(ShippingZoneNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        zone = ShippingZone.objects.create(
            name=input["name"],
            description=input.get("description", ""),
            countries=input.get("countries", []),
            is_active=input.get("is_active", True),
        )
        return CreateShippingZone(shipping_zone=zone)


class UpdateShippingZone(relay.ClientIDMutation):
    """Update an existing Shipping Zone."""
    class Input:
        id = graphene.ID(required=True)
        name = graphene.String()
        description = graphene.String()
        countries = graphene.List(graphene.String)
        is_active = graphene.Boolean()

    shipping_zone = graphene.Field(ShippingZoneNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        pk = from_global_id(input["id"])[1]
        zone = ShippingZone.objects.get(pk=pk)
        for field in ["name", "description", "countries", "is_active"]:
            if field in input and input[field] is not None:
                setattr(zone, field, input[field])
        zone.save()
        return UpdateShippingZone(shipping_zone=zone)


class DeleteShippingZone(relay.ClientIDMutation):
    """Delete a shipping zone."""
    class Input:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    deleted_shipping_zone_id = graphene.ID()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        pk = from_global_id(input["id"])[1]
        try:
            zone = ShippingZone.objects.get(pk=pk)
        except ShippingZone.DoesNotExist:
            raise Exception("Shipping zone not found.")
        deleted_id = input["id"]
        zone.delete()
        return DeleteShippingZone(ok=True, deleted_shipping_zone_id=deleted_id)


# ------------------------
# SHIPPING METHOD MUTATIONS
# ------------------------

# apps/backend/graphq/shipping/mutations.py

class CreateShippingMethod(relay.ClientIDMutation):
    """Create a new Shipping Method."""
    class Input:
        name = graphene.String(required=True)
        shipping_zone_id = graphene.ID(required=True)
        type = graphene.String(required=False)  # PRICE_BASED or WEIGHT_BASED
        minimum_order_weight = graphene.Decimal()  # ✅ Correct field
        maximum_order_weight = graphene.Decimal()  # ✅ Correct field
        tax_class_id = graphene.ID(required=False)
        excluded_product_ids = graphene.List(graphene.ID)

    shipping_method = graphene.Field(ShippingMethodNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        zone_pk = from_global_id(input["shipping_zone_id"])[1]
        zone = ShippingZone.objects.get(pk=zone_pk)

        # ✅ Use correct model fields
        method = ShippingMethod.objects.create(
            name=input["name"],
            shipping_zone=zone,
            type=input.get("type", ShippingMethodType.PRICE_BASED),
            minimum_order_weight=input.get("minimum_order_weight"),
            maximum_order_weight=input.get("maximum_order_weight"),
            tax_class_id=input.get("tax_class_id"),
        )

        # Handle excluded products if provided
        if input.get("excluded_product_ids"):
            product_ids = [from_global_id(pid)[1] for pid in input["excluded_product_ids"]]
            method.excluded_products.set(product_ids)

        return CreateShippingMethod(shipping_method=method)


class UpdateShippingMethod(relay.ClientIDMutation):
    """Update an existing Shipping Method."""
    class Input:
        id = graphene.ID(required=True)
        name = graphene.String()
        type = graphene.String()
        minimum_order_weight = graphene.Decimal()
        maximum_order_weight = graphene.Decimal()
        tax_class_id = graphene.ID()
        excluded_product_ids = graphene.List(graphene.ID)

    shipping_method = graphene.Field(ShippingMethodNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        pk = from_global_id(input["id"])[1]
        method = ShippingMethod.objects.get(pk=pk)

        # Update fields
        field_mappings = [
            "name",
            "type",
            "minimum_order_weight",
            "maximum_order_weight",
            "tax_class_id",
        ]
        for field in field_mappings:
            if field in input and input[field] is not None:
                setattr(method, field, input[field])

        # Handle excluded products
        if "excluded_product_ids" in input and input["excluded_product_ids"] is not None:
            product_ids = [from_global_id(pid)[1] for pid in input["excluded_product_ids"]]
            method.excluded_products.set(product_ids)

        method.save()
        return UpdateShippingMethod(shipping_method=method)

class UpdateShippingMethod(relay.ClientIDMutation):
    """Update an existing Shipping Method."""
    class Input:
        id = graphene.ID(required=True)
        name = graphene.String()
        price = graphene.Decimal()
        minimum_order_price = graphene.Decimal()
        maximum_order_price = graphene.Decimal()
        is_active = graphene.Boolean()

    shipping_method = graphene.Field(ShippingMethodNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        pk = from_global_id(input["id"])[1]
        method = ShippingMethod.objects.get(pk=pk)
        for field in [
            "name",
            "price",
            "minimum_order_price",
            "maximum_order_price",
            "is_active",
        ]:
            if field in input and input[field] is not None:
                setattr(method, field, input[field])
        method.save()
        return UpdateShippingMethod(shipping_method=method)


class DeleteShippingMethod(relay.ClientIDMutation):
    """Delete a shipping method."""
    class Input:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    deleted_shipping_method_id = graphene.ID()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        pk = from_global_id(input["id"])[1]
        try:
            method = ShippingMethod.objects.get(pk=pk)
        except ShippingMethod.DoesNotExist:
            raise Exception("Shipping method not found.")
        deleted_id = input["id"]
        method.delete()
        return DeleteShippingMethod(ok=True, deleted_shipping_method_id=deleted_id)

class CreateShippingMethodPostalCodeRule(relay.ClientIDMutation):
    class Input:
        shipping_method_id = graphene.ID(required=True)
        start = graphene.String(required=True)
        end = graphene.String()
        inclusion_type = graphene.String(required=True)

    postal_code_rule = graphene.Field(ShippingMethodPostalCodeRuleNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        method_pk = from_global_id(input["shipping_method_id"])[1]
        rule = ShippingMethodPostalCodeRule.objects.create(
            shipping_method_id=method_pk,
            start=input["start"],
            end=input.get("end"),
            inclusion_type=input["inclusion_type"],
        )
        return CreateShippingMethodPostalCodeRule(postal_code_rule=rule)


class UpdateShippingMethodPostalCodeRule(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        start = graphene.String()
        end = graphene.String()
        inclusion_type = graphene.String()

    postal_code_rule = graphene.Field(ShippingMethodPostalCodeRuleNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        pk = from_global_id(input["id"])[1]
        rule = ShippingMethodPostalCodeRule.objects.get(pk=pk)
        for field in ["start", "end", "inclusion_type"]:
            if field in input and input[field] is not None:
                setattr(rule, field, input[field])
        rule.save()
        return UpdateShippingMethodPostalCodeRule(postal_code_rule=rule)


class DeleteShippingMethodPostalCodeRule(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    deleted_postal_code_rule_id = graphene.ID()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        pk = from_global_id(input["id"])[1]
        try:
            rule = ShippingMethodPostalCodeRule.objects.get(pk=pk)
        except ShippingMethodPostalCodeRule.DoesNotExist:
            raise Exception("Postal code rule not found.")
        deleted_id = input["id"]
        rule.delete()
        return DeleteShippingMethodPostalCodeRule(ok=True, deleted_postal_code_rule_id=deleted_id)


# ------------------------
# CHANNEL LISTING MUTATIONS
# ------------------------

class CreateShippingMethodChannelListing(relay.ClientIDMutation):
    class Input:
        shipping_method_id = graphene.ID(required=True)
        channel_id = graphene.ID(required=True)
        price_amount = graphene.Decimal(required=True)
        currency = graphene.String(required=True)
        minimum_order_price_amount = graphene.Decimal()
        maximum_order_price_amount = graphene.Decimal()
        is_active = graphene.Boolean(default_value=True)

    channel_listing = graphene.Field(ShippingMethodChannelListingNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        method_pk = from_global_id(input["shipping_method_id"])[1]
        channel_pk = from_global_id(input["channel_id"])[1]

        listing = ShippingMethodChannelListing.objects.create(
            shipping_method_id=method_pk,
            channel_id=channel_pk,
            price_amount=input["price_amount"],
            currency=input["currency"],
            minimum_order_price_amount=input.get("minimum_order_price_amount"),
            maximum_order_price_amount=input.get("maximum_order_price_amount"),
            is_active=input.get("is_active", True),
        )
        return CreateShippingMethodChannelListing(channel_listing=listing)


class UpdateShippingMethodChannelListing(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        price_amount = graphene.Decimal()
        currency = graphene.String()
        minimum_order_price_amount = graphene.Decimal()
        maximum_order_price_amount = graphene.Decimal()
        is_active = graphene.Boolean()

    channel_listing = graphene.Field(ShippingMethodChannelListingNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        pk = from_global_id(input["id"])[1]
        listing = ShippingMethodChannelListing.objects.get(pk=pk)
        for field in [
            "price_amount",
            "currency",
            "minimum_order_price_amount",
            "maximum_order_price_amount",
            "is_active",
        ]:
            if field in input and input[field] is not None:
                setattr(listing, field, input[field])
        listing.save()
        return UpdateShippingMethodChannelListing(channel_listing=listing)


class DeleteShippingMethodChannelListing(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    deleted_channel_listing_id = graphene.ID()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        pk = from_global_id(input["id"])[1]
        try:
            listing = ShippingMethodChannelListing.objects.get(pk=pk)
        except ShippingMethodChannelListing.DoesNotExist:
            raise Exception("Channel listing not found.")
        deleted_id = input["id"]
        listing.delete()
        return DeleteShippingMethodChannelListing(ok=True, deleted_channel_listing_id=deleted_id)


# ------------------------
# ROOT MUTATIONS EXPORT
# ------------------------

class ShippingMutations(graphene.ObjectType):
    # Zones
    create_shipping_zone = CreateShippingZone.Field()
    update_shipping_zone = UpdateShippingZone.Field()
    delete_shipping_zone = DeleteShippingZone.Field()

    # Methods
    create_shipping_method = CreateShippingMethod.Field()
    update_shipping_method = UpdateShippingMethod.Field()
    delete_shipping_method = DeleteShippingMethod.Field()

    # Postal Code Rules
    create_shipping_postal_code_rule = CreateShippingMethodPostalCodeRule.Field()
    update_shipping_postal_code_rule = UpdateShippingMethodPostalCodeRule.Field()
    delete_shipping_postal_code_rule = DeleteShippingMethodPostalCodeRule.Field()

    # Channel Listings
    create_shipping_channel_listing = CreateShippingMethodChannelListing.Field()
    update_shipping_channel_listing = UpdateShippingMethodChannelListing.Field()
    delete_shipping_channel_listing = DeleteShippingMethodChannelListing.Field()



