# apps/backend/graphq/transport/mutations/analytics.py
"""
Analytics mutations.

Models:
    AnalyticsProfile.user   → ForeignKey. Treated as one config per user
                              by convention; upsert keyed on the caller.
    RideMetrics.ride        → OneToOneField to Trip (a proxy of ServiceRequest).
    KPI                     → System-level metric, no owner. Staff-only.
"""
#files = info.context.FILES
from decimal import Decimal, InvalidOperation

import graphene
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from graphene import relay
from graphql import GraphQLError
from graphql_relay import from_global_id

from graphq.accounts.types.user import UserNode
from graphq.transport.types.analytics import (
    AnalyticsProfileNode,
    RideMetricsNode,
    KPINode,
)
from graphq.transport.types.trip import TripNode

from transport.models.shared.analytics import AnalyticsProfile, RideMetrics, KPI
from transport.models.rides.trip import Trip


User = get_user_model()

_ALLOWED_REPORT_FREQUENCIES = {"daily", "weekly", "monthly", "quarterly"}
_ALLOWED_KPI_CATEGORIES = {
    "environmental",
    "financial",
    "operational",
    "customer",
    "safety",
}


# =============================================================================
# Helpers
# =============================================================================

def _parse_decimal(value, field):
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise GraphQLError(f"{field} must be a valid decimal.")


def _assert_staff(user):
    if not user.is_authenticated:
        raise GraphQLError("Authentication required.")
    if not user.is_staff:
        raise GraphQLError("Staff permission required.")


def _resolve_profile(global_id, *, lock=False):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid analytics_profile_id.")
    qs = AnalyticsProfile.objects.all()
    if lock:
        qs = qs.select_for_update()
    try:
        return qs.get(pk=pk)
    except AnalyticsProfile.DoesNotExist:
        raise GraphQLError("Analytics profile not found.")


def _resolve_trip(global_id):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid ride_id.")
    try:
        return Trip.objects.get(pk=pk)
    except Trip.DoesNotExist:
        raise GraphQLError("Ride not found.")


def _resolve_metrics(global_id, *, lock=False):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid ride_metrics_id.")
    qs = RideMetrics.objects.all()
    if lock:
        qs = qs.select_for_update()
    try:
        return qs.get(pk=pk)
    except RideMetrics.DoesNotExist:
        raise GraphQLError("Ride metrics not found.")


def _resolve_kpi(global_id, *, lock=False):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid kpi_id.")
    qs = KPI.objects.all()
    if lock:
        qs = qs.select_for_update()
    try:
        return qs.get(pk=pk)
    except KPI.DoesNotExist:
        raise GraphQLError("KPI not found.")


def _assert_ride_participant(ride, user):
    if not user.is_authenticated:
        raise GraphQLError("Authentication required.")
    if user.is_staff:
        return
    if ride.customer_id == user.pk:
        return
    provider = getattr(user, "service_provider", None)
    if provider is not None and ride.provider_id == provider.pk:
        return
    raise GraphQLError("Not authorized for this ride.")


# =============================================================================
# AnalyticsProfile
# =============================================================================

class UpsertAnalyticsProfile(relay.ClientIDMutation):
    """
    Create or update the authenticated user's AnalyticsProfile.

    The model has `user` as a plain ForeignKey, but conceptually this is
    one config per user — so we upsert keyed on the caller.
    """

    class Input:
        track_ride_metrics = graphene.Boolean()
        track_environmental_impact = graphene.Boolean()
        track_cost_savings = graphene.Boolean()
        track_accessibility_usage = graphene.Boolean()

        report_frequency = graphene.String()
        share_aggregate_data = graphene.Boolean()
        share_for_research = graphene.Boolean()

    user = graphene.Field(UserNode)
    analytics_profile = graphene.Field(AnalyticsProfileNode)
    created = graphene.Boolean()
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        if (
            "report_frequency" in input
            and input["report_frequency"] is not None
            and input["report_frequency"] not in _ALLOWED_REPORT_FREQUENCIES
        ):
            raise GraphQLError(
                f"report_frequency must be one of: "
                f"{', '.join(sorted(_ALLOWED_REPORT_FREQUENCIES))}."
            )

        defaults = {}
        for key in (
            "track_ride_metrics",
            "track_environmental_impact",
            "track_cost_savings",
            "track_accessibility_usage",
            "report_frequency",
            "share_aggregate_data",
            "share_for_research",
        ):
            if key in input and input[key] is not None:
                defaults[key] = input[key]

        profile, created = AnalyticsProfile.objects.get_or_create(
            user=me, defaults=defaults
        )

        if not created and defaults:
            for field, value in defaults.items():
                setattr(profile, field, value)
            try:
                profile.full_clean()
            except ValidationError as exc:
                raise GraphQLError(f"Validation failed: {exc.message_dict}")
            profile.save(update_fields=list(defaults.keys()) + ["updated_at"])

        return UpsertAnalyticsProfile(
            user=me,
            analytics_profile=profile,
            created=created,
            success=True,
            message="Analytics profile saved.",
        )


class UpdateAnalyticsProfile(relay.ClientIDMutation):
    """Update an AnalyticsProfile by ID. Owner or staff."""

    class Input:
        analytics_profile_id = graphene.ID(required=True)

        track_ride_metrics = graphene.Boolean()
        track_environmental_impact = graphene.Boolean()
        track_cost_savings = graphene.Boolean()
        track_accessibility_usage = graphene.Boolean()

        report_frequency = graphene.String()
        share_aggregate_data = graphene.Boolean()
        share_for_research = graphene.Boolean()

    analytics_profile = graphene.Field(AnalyticsProfileNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, analytics_profile_id, **input):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        profile = _resolve_profile(analytics_profile_id, lock=True)
        if profile.user_id != me.pk and not me.is_staff:
            raise GraphQLError("Not authorized to update this profile.")

        if (
            "report_frequency" in input
            and input["report_frequency"] is not None
            and input["report_frequency"] not in _ALLOWED_REPORT_FREQUENCIES
        ):
            raise GraphQLError(
                f"report_frequency must be one of: "
                f"{', '.join(sorted(_ALLOWED_REPORT_FREQUENCIES))}."
            )

        update_fields = []
        for field in (
            "track_ride_metrics",
            "track_environmental_impact",
            "track_cost_savings",
            "track_accessibility_usage",
            "report_frequency",
            "share_aggregate_data",
            "share_for_research",
        ):
            if field in input and input[field] is not None:
                setattr(profile, field, input[field])
                update_fields.append(field)

        if not update_fields:
            return UpdateAnalyticsProfile(
                analytics_profile=profile,
                success=True,
                message="Nothing to update.",
            )

        try:
            profile.full_clean()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        profile.save(update_fields=sorted(set(update_fields + ["updated_at"])))

        return cls(
            analytics_profile=profile,
            success=True,
            message="Analytics profile updated.",
        )


class DeleteAnalyticsProfile(relay.ClientIDMutation):
    """Delete an AnalyticsProfile. Owner or staff."""

    class Input:
        analytics_profile_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, analytics_profile_id):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        profile = _resolve_profile(analytics_profile_id, lock=True)
        if profile.user_id != me.pk and not me.is_staff:
            raise GraphQLError("Not authorized to delete this profile.")

        profile.delete()
        return DeleteAnalyticsProfile(success=True, message="Analytics profile deleted.")


# =============================================================================
# RideMetrics
# =============================================================================

class CreateRideMetrics(relay.ClientIDMutation):
    """
    Create RideMetrics for a Trip.

    `RideMetrics.ride` is a OneToOneField, so a second call for the same
    trip is rejected rather than silently overwriting.
    """

    class Input:
        ride_id = graphene.ID(required=True)

        distance_km = graphene.Float(required=True)
        duration_minutes = graphene.Float(required=True)
        average_speed_kmh = graphene.Float(required=True)

        fuel_consumption_liters = graphene.Float()
        energy_consumption_kwh = graphene.Float()

        co2_emissions_kg = graphene.Float(required=True)
        particulate_matter_emissions = graphene.Float(required=True)

        operational_cost = graphene.Decimal(required=True)
        maintenance_cost_share = graphene.Decimal(required=True)

        passenger_comfort_score = graphene.Float()
        accessibility_score = graphene.Float()

    ride = graphene.Field(TripNode)
    ride_metrics = graphene.Field(RideMetricsNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, ride_id, **input):
        me = info.context.user
        ride = _resolve_trip(ride_id)
        _assert_ride_participant(ride, me)

        if RideMetrics.objects.filter(ride=ride).exists():
            raise GraphQLError("Metrics already exist for this ride.")

        # Non-negative checks
        for field in (
            "distance_km",
            "duration_minutes",
            "average_speed_kmh",
            "co2_emissions_kg",
            "particulate_matter_emissions",
        ):
            value = input.get(field)
            if value is not None and value < 0:
                raise GraphQLError(f"{field} cannot be negative.")

        comfort = input.get("passenger_comfort_score")
        if comfort is not None and not 0 <= comfort <= 5:
            raise GraphQLError("passenger_comfort_score must be between 0 and 5.")

        accessibility = input.get("accessibility_score")
        if accessibility is not None and not 0 <= accessibility <= 100:
            raise GraphQLError("accessibility_score must be between 0 and 100.")

        payload = {
            "ride": ride,
            "distance_km": input["distance_km"],
            "duration_minutes": input["duration_minutes"],
            "average_speed_kmh": input["average_speed_kmh"],
            "fuel_consumption_liters": input.get("fuel_consumption_liters"),
            "energy_consumption_kwh": input.get("energy_consumption_kwh"),
            "co2_emissions_kg": input["co2_emissions_kg"],
            "particulate_matter_emissions": input["particulate_matter_emissions"],
            "operational_cost": _parse_decimal(
                input["operational_cost"], "operational_cost"
            ),
            "maintenance_cost_share": _parse_decimal(
                input["maintenance_cost_share"], "maintenance_cost_share"
            ),
            "passenger_comfort_score": comfort,
            "accessibility_score": accessibility,
        }
        payload = {k: v for k, v in payload.items() if v is not None}

        try:
            metrics = RideMetrics.objects.create(**payload)
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        return CreateRideMetrics(
            ride=ride,
            ride_metrics=metrics,
            success=True,
            message="Ride metrics recorded.",
        )


class UpdateRideMetrics(relay.ClientIDMutation):
    """Update RideMetrics. Participant or staff."""

    class Input:
        ride_metrics_id = graphene.ID(required=True)

        distance_km = graphene.Float()
        duration_minutes = graphene.Float()
        average_speed_kmh = graphene.Float()

        fuel_consumption_liters = graphene.Float()
        energy_consumption_kwh = graphene.Float()

        co2_emissions_kg = graphene.Float()
        particulate_matter_emissions = graphene.Float()

        operational_cost = graphene.Decimal()
        maintenance_cost_share = graphene.Decimal()

        passenger_comfort_score = graphene.Float()
        accessibility_score = graphene.Float()

    ride_metrics = graphene.Field(RideMetricsNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, ride_metrics_id, **input):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        metrics = _resolve_metrics(ride_metrics_id, lock=True)
        _assert_ride_participant(metrics.ride, me)

        update_fields = []

        scalar_map = {
            "distance_km": "distance_km",
            "duration_minutes": "duration_minutes",
            "average_speed_kmh": "average_speed_kmh",
            "fuel_consumption_liters": "fuel_consumption_liters",
            "energy_consumption_kwh": "energy_consumption_kwh",
            "co2_emissions_kg": "co2_emissions_kg",
            "particulate_matter_emissions": "particulate_matter_emissions",
            "passenger_comfort_score": "passenger_comfort_score",
            "accessibility_score": "accessibility_score",
        }
        for input_key, model_field in scalar_map.items():
            if input_key in input and input[input_key] is not None:
                value = input[input_key]
                if value < 0:
                    raise GraphQLError(f"{input_key} cannot be negative.")
                if input_key == "passenger_comfort_score" and value > 5:
                    raise GraphQLError("passenger_comfort_score max is 5.")
                if input_key == "accessibility_score" and value > 100:
                    raise GraphQLError("accessibility_score max is 100.")
                setattr(metrics, model_field, value)
                update_fields.append(model_field)

        for input_key, model_field in (
            ("operational_cost", "operational_cost"),
            ("maintenance_cost_share", "maintenance_cost_share"),
        ):
            if input_key in input and input[input_key] is not None:
                setattr(
                    metrics,
                    model_field,
                    _parse_decimal(input[input_key], input_key),
                )
                update_fields.append(model_field)

        if not update_fields:
            return cls(
                ride_metrics=metrics,
                success=True,
                message="Nothing to update.",
            )

        try:
            metrics.full_clean()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        metrics.save(update_fields=sorted(set(update_fields)))

        return UpdateRideMetrics(
            ride_metrics=metrics,
            success=True,
            message="Ride metrics updated.",
        )


class DeleteRideMetrics(relay.ClientIDMutation):
    """Delete RideMetrics. Participant or staff."""

    class Input:
        ride_metrics_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, ride_metrics_id):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        metrics = _resolve_metrics(ride_metrics_id, lock=True)
        _assert_ride_participant(metrics.ride, me)

        metrics.delete()
        return DeleteRideMetrics(success=True, message="Ride metrics deleted.")


# =============================================================================
# KPI (staff-only)
# =============================================================================

class CreateKPI(relay.ClientIDMutation):
    """Create a KPI. Staff-only — KPIs are system-level metrics."""

    class Input:
        name = graphene.String(required=True)
        description = graphene.String(required=True)
        value = graphene.Float(required=True)
        target = graphene.Float()
        unit = graphene.String(required=True)
        category = graphene.String(required=True)
        period_start = graphene.DateTime(required=True)
        period_end = graphene.DateTime(required=True)

    kpi = graphene.Field(KPINode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        _assert_staff(info.context.user)

        if input["category"] not in _ALLOWED_KPI_CATEGORIES:
            raise GraphQLError(
                f"category must be one of: "
                f"{', '.join(sorted(_ALLOWED_KPI_CATEGORIES))}."
            )

        if input["period_end"] <= input["period_start"]:
            raise GraphQLError("period_end must be after period_start.")

        try:
            kpi = KPI.objects.create(
                name=input["name"],
                description=input["description"],
                value=input["value"],
                target=input.get("target"),
                unit=input["unit"],
                category=input["category"],
                period_start=input["period_start"],
                period_end=input["period_end"],
            )
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        return CreateKP(kpi=kpi, success=True, message="KPI created.")


class UpdateKPI(relay.ClientIDMutation):
    """Update a KPI. Staff-only."""

    class Input:
        kpi_id = graphene.ID(required=True)
        name = graphene.String()
        description = graphene.String()
        value = graphene.Float()
        target = graphene.Float()
        unit = graphene.String()
        category = graphene.String()
        period_start = graphene.DateTime()
        period_end = graphene.DateTime()

    kpi = graphene.Field(KPINode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, kpi_id, **input):
        _assert_staff(info.context.user)
        kpi = _resolve_kpi(kpi_id, lock=True)

        if (
            "category" in input
            and input["category"] is not None
            and input["category"] not in _ALLOWED_KPI_CATEGORIES
        ):
            raise GraphQLError(
                f"category must be one of: "
                f"{', '.join(sorted(_ALLOWED_KPI_CATEGORIES))}."
            )

        update_fields = []
        for field in (
            "name",
            "description",
            "value",
            "target",
            "unit",
            "category",
            "period_start",
            "period_end",
        ):
            if field in input and input[field] is not None:
                setattr(kpi, field, input[field])
                update_fields.append(field)

        if not update_fields:
            return cls(kpi=kpi, success=True, message="Nothing to update.")

        if kpi.period_end <= kpi.period_start:
            raise GraphQLError("period_end must be after period_start.")

        try:
            kpi.full_clean()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        kpi.save(update_fields=sorted(set(update_fields)))

        return  UpdateKPI(kpi=kpi, success=True, message="KPI updated.")


class DeleteKPI(relay.ClientIDMutation):
    """Delete a KPI. Staff-only."""

    class Input:
        kpi_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, kpi_id):
        _assert_staff(info.context.user)
        kpi = _resolve_kpi(kpi_id, lock=True)
        kpi.delete()
        return DeleteKPI(success=True, message="KPI deleted.")


# =============================================================================
# Registration
# =============================================================================

class AnalyticsMutations(graphene.ObjectType):
    upsert_analytics_profile = UpsertAnalyticsProfile.Field()
    update_analytics_profile = UpdateAnalyticsProfile.Field()
    delete_analytics_profile = DeleteAnalyticsProfile.Field()

    create_ride_metrics = CreateRideMetrics.Field()
    update_ride_metrics = UpdateRideMetrics.Field()
    delete_ride_metrics = DeleteRideMetrics.Field()

    create_kpi = CreateKPI.Field()
    update_kpi = UpdateKPI.Field()
    delete_kpi = DeleteKPI.Field()