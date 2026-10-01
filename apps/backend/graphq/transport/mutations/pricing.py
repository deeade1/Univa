# apps/backend/graphq/transport/mutations/pricing.py
"""
PricingProfile mutations.

Model facts that shape these mutations:
    - `service_type` is unique=True → upsert semantics keyed on it.
    - `effective_from` is `auto_now_add=True`. The client cannot set it;
      it always becomes the creation timestamp. This is a limitation of
      the model for a versioned pricing system — see note at the bottom.
    - `clean()` requires `per_minute_rate` for TAXI and validates that
      `effective_to > effective_from`. Direct `update_or_create()`
      bypasses `clean()`; we call `full_clean()` explicitly.
    - `PricingProfile.get_current_pricing()` caches per service_type
      for 1 hour. Any write must invalidate or pricing changes remain
      invisible to readers.
"""

from decimal import Decimal, InvalidOperation

import graphene
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from graphene import relay
from graphql import GraphQLError
from graphql_relay import from_global_id

from graphq.transport.types.pricing import PricingProfileNode

from transport.models.financial.pricing import PricingProfile  # adjust path if needed


_VALID_SERVICE_TYPES = {c.value for c in PricingProfile.ServiceType}
_CACHE_KEY_TEMPLATE = "current_pricing_{service_type}"


# =============================================================================
# Helpers
# =============================================================================

def _assert_staff(user):
    if not user.is_authenticated:
        raise GraphQLError("Authentication required.")
    if not user.is_staff:
        raise GraphQLError("Staff permission required.")


def _resolve_profile(global_id, *, lock=False):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid pricing_profile_id.")
    qs = PricingProfile.objects.all()
    if lock:
        qs = qs.select_for_update()
    try:
        return qs.get(pk=pk)
    except PricingProfile.DoesNotExist:
        raise GraphQLError("Pricing profile not found.")


def _parse_decimal(value, field):
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise GraphQLError(f"{field} must be a valid decimal.")


def _invalidate_pricing_cache(*service_types):
    """
    Clear the `get_current_pricing` cache for the given service types.

    Falls through silently on cache backend errors — an invalidation
    failure should never break the mutation itself.
    """
    for st in service_types:
        if st is None:
            continue
        try:
            cache.delete(_CACHE_KEY_TEMPLATE.format(service_type=st))
        except Exception:
            pass


# =============================================================================
# Upsert
# =============================================================================

class UpsertPricingProfile(relay.ClientIDMutation):
    """
    Create or update the pricing profile for a `service_type`.

    Staff-only — this is global config that determines what every
    customer pays.

    Because `effective_from` on the model is `auto_now_add=True`, the
    mutation cannot accept it. The active pricing for a service_type
    is therefore the single row for that type, updated in place.
    """

    class Input:
        service_type = graphene.String(required=True)

        base_fare = graphene.Decimal(required=True)
        per_km_rate = graphene.Decimal(required=True)
        per_minute_rate = graphene.Decimal()
        min_fare = graphene.Decimal(required=True)
        surge_multiplier = graphene.Decimal()

        is_active = graphene.Boolean()
        effective_to = graphene.DateTime()

    pricing_profile = graphene.Field(PricingProfileNode)
    created = graphene.Boolean()
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, service_type, **input):
        _assert_staff(info.context.user)

        if service_type not in _VALID_SERVICE_TYPES:
            raise GraphQLError(
                f"service_type must be one of: "
                f"{', '.join(sorted(_VALID_SERVICE_TYPES))}."
            )

        base_fare = _parse_decimal(input["base_fare"], "base_fare")
        per_km_rate = _parse_decimal(input["per_km_rate"], "per_km_rate")
        per_minute_rate = _parse_decimal(input.get("per_minute_rate"), "per_minute_rate")
        min_fare = _parse_decimal(input["min_fare"], "min_fare")
        surge_multiplier = _parse_decimal(input.get("surge_multiplier"), "surge_multiplier")

        # Bounds mirror the model validators, giving clean errors before
        # full_clean() ever runs.
        if base_fare < 0:
            raise GraphQLError("base_fare cannot be negative.")
        if per_km_rate < 0:
            raise GraphQLError("per_km_rate cannot be negative.")
        if per_minute_rate is not None and per_minute_rate < 0:
            raise GraphQLError("per_minute_rate cannot be negative.")
        if min_fare < 0:
            raise GraphQLError("min_fare cannot be negative.")
        if surge_multiplier is not None and not (1 <= surge_multiplier <= 5):
            raise GraphQLError("surge_multiplier must be between 1 and 5.")

        # Model's clean() rule: TAXI requires per_minute_rate.
        if service_type == PricingProfile.ServiceType.TAXI and per_minute_rate is None:
            # Check existing value if not provided.
            existing = PricingProfile.objects.filter(service_type=service_type).first()
            if existing is None or existing.per_minute_rate is None:
                raise GraphQLError("per_minute_rate is required for taxi services.")

        defaults = {
            "base_fare": base_fare,
            "per_km_rate": per_km_rate,
            "min_fare": min_fare,
        }
        if per_minute_rate is not None:
            defaults["per_minute_rate"] = per_minute_rate
        if surge_multiplier is not None:
            defaults["surge_multiplier"] = surge_multiplier
        if input.get("is_active") is not None:
            defaults["is_active"] = bool(input["is_active"])
        if "effective_to" in input:
            defaults["effective_to"] = input["effective_to"]

        profile, created = PricingProfile.objects.get_or_create(
            service_type=service_type,
            defaults=defaults,
        )

        if not created:
            for field, value in defaults.items():
                setattr(profile, field, value)

        try:
            # update_or_create bypasses full_clean(); do it explicitly.
            profile.full_clean()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        profile.save()

        # Invalidate the pricing cache so subsequent reads see the change.
        _invalidate_pricing_cache(service_type)

        return cls(
            pricing_profile=profile,
            created=created,
            success=True,
            message="Pricing profile saved.",
        )


# =============================================================================
# Update by ID
# =============================================================================

class UpdatePricingProfile(relay.ClientIDMutation):
    """
    Update a specific PricingProfile by ID.

    Staff-only. Useful when there are multiple rows per service_type
    (historical + active), which is not currently the case because the
    model's unique constraint on service_type forbids it — but this
    mutation remains useful if that constraint is relaxed later.
    """

    class Input:
        pricing_profile_id = graphene.ID(required=True)

        base_fare = graphene.Decimal()
        per_km_rate = graphene.Decimal()
        per_minute_rate = graphene.Decimal()
        min_fare = graphene.Decimal()
        surge_multiplier = graphene.Decimal()

        is_active = graphene.Boolean()
        effective_to = graphene.DateTime()

    pricing_profile = graphene.Field(PricingProfileNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, pricing_profile_id, **input):
        _assert_staff(info.context.user)
        profile = _resolve_profile(pricing_profile_id, lock=True)

        update_fields = []

        for input_key, model_field in (
            ("base_fare", "base_fare"),
            ("per_km_rate", "per_km_rate"),
            ("per_minute_rate", "per_minute_rate"),
            ("min_fare", "min_fare"),
            ("surge_multiplier", "surge_multiplier"),
        ):
            if input_key in input and input[input_key] is not None:
                value = _parse_decimal(input[input_key], input_key)
                if value < 0 and input_key != "surge_multiplier":
                    raise GraphQLError(f"{input_key} cannot be negative.")
                if input_key == "surge_multiplier" and not (1 <= value <= 5):
                    raise GraphQLError(
                        "surge_multiplier must be between 1 and 5."
                    )
                setattr(profile, model_field, value)
                update_fields.append(model_field)

        if "is_active" in input and input["is_active"] is not None:
            profile.is_active = bool(input["is_active"])
            update_fields.append("is_active")

        if "effective_to" in input:
            profile.effective_to = input["effective_to"]
            update_fields.append("effective_to")

        # Re-check the TAXI rule after applying updates.
        if profile.service_type == PricingProfile.ServiceType.TAXI:
            if profile.per_minute_rate is None:
                raise GraphQLError("per_minute_rate is required for taxi services.")

        if not update_fields:
            return cls(
                pricing_profile=profile,
                success=True,
                message="Nothing to update.",
            )

        try:
            profile.full_clean()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        profile.save(update_fields=sorted(set(update_fields + ["updated_at"])))

        _invalidate_pricing_cache(profile.service_type)

        return cls(
            pricing_profile=profile,
            success=True,
            message="Pricing profile updated.",
        )


# =============================================================================
# Deactivate / activate
# =============================================================================

class SetPricingProfileActive(relay.ClientIDMutation):
    """
    Toggle `is_active` on a pricing profile.

    Staff-only. Deactivating leaves the row in place for audit purposes
    but makes `get_current_pricing()` skip it.
    """

    class Input:
        pricing_profile_id = graphene.ID(required=True)
        is_active = graphene.Boolean(required=True)

    pricing_profile = graphene.Field(PricingProfileNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, pricing_profile_id, is_active):
        _assert_staff(info.context.user)
        profile = _resolve_profile(pricing_profile_id, lock=True)

        profile.is_active = bool(is_active)
        profile.save(update_fields=["is_active", "updated_at"])

        _invalidate_pricing_cache(profile.service_type)

        return cls(
            pricing_profile=profile,
            success=True,
            message=f"Pricing profile {'activated' if is_active else 'deactivated'}.",
        )


# =============================================================================
# Delete
# =============================================================================

class DeletePricingProfile(relay.ClientIDMutation):
    """
    Delete a PricingProfile.

    Staff-only. Prefer `SetPricingProfileActive(is_active: false)` —
    deleting loses the historical record of what pricing applied when.
    """

    class Input:
        pricing_profile_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, pricing_profile_id):
        _assert_staff(info.context.user)
        profile = _resolve_profile(pricing_profile_id, lock=True)
        service_type = profile.service_type

        profile.delete()

        _invalidate_pricing_cache(service_type)

        return cls(success=True, message="Pricing profile deleted.")


# =============================================================================
# Registration
# =============================================================================

class PricingMutations(graphene.ObjectType):
    upsert_pricing_profile = UpsertPricingProfile.Field()
    update_pricing_profile = UpdatePricingProfile.Field()
    set_pricing_profile_active = SetPricingProfileActive.Field()
    delete_pricing_profile = DeletePricingProfile.Field()