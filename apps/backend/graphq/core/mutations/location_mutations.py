# graphq/core/mutations/location_mutations.py
"""
Reusable Relay GraphQL Location Mutations.

Shared across:
    • Accounts
    • Banking
    • Transport
    • Logistics
    • Marketplace
    • Real Estate
    • Warehouse
    • Social
"""

import graphene
from graphene import relay

# ✅ FIXED: Import from graphq.core.inputs (not core.graphql.inputs)
from graphq.core.inputs.location_inputs import (
    AddressVerificationInput,
    CoordinatesInput,
    ReverseGeocodeInput,
    RouteInput,
)

from graphq.core.types.location_types import (
    AddressVerificationType,
    FraudReportType,
    GeofenceType,
    ReverseGeocodeType,
    RouteType,
)

# ✅ FIXED: Import from core.services (not core.graphql.services)
from core.services.address_verification import verify_gps_against_address
from core.services.fraud_detection import FraudDetectionService
from core.services.geocoding import reverse_geocode
from core.services.routing import get_route

from graphene_gis.scalars import LineStringScalar
from django.contrib.gis.geos import GEOSGeometry

class ReverseGeocode(relay.ClientIDMutation):
    """Reverse geocode coordinates into an address."""

    class Input:
        input = ReverseGeocodeInput(required=True)

    success = graphene.Boolean(required=True)
    message = graphene.String()
    result = graphene.Field(ReverseGeocodeType)

    @classmethod
    def mutate_and_get_payload(cls, root, info, input):
        result = reverse_geocode(
            latitude=input.latitude,
            longitude=input.longitude,
        )
        return cls(
            success=True,
            message="Reverse geocoding completed.",
            result=result,
        )


class VerifyAddress(relay.ClientIDMutation):
    """Verify an address."""

    class Input:
        input = AddressVerificationInput(required=True)

    success = graphene.Boolean(required=True)
    message = graphene.String()
    result = graphene.Field(AddressVerificationType)

    @classmethod
    def mutate_and_get_payload(cls, root, info, input):
        result = verify_gps_against_address(
            address=input.address,
            latitude=input.latitude,
            longitude=input.longitude,
        )
        return cls(
            success=True,
            message="Address verification completed.",
            result=result,
        )


class CalculateRoute(relay.ClientIDMutation):
    """Calculate optimal route."""

    class Input:
        input = RouteInput(required=True)

    success = graphene.Boolean(required=True)
    message = graphene.String()
    result = graphene.Field(RouteType)

    @classmethod
    def mutate_and_get_payload(cls, root, info, input):
        result = get_route(
            start_lat=input.origin.latitude,
            start_lon=input.origin.longitude,
            end_lat=input.destination.latitude,
            end_lon=input.destination.longitude,
        )
        return cls(
            success=True,
            message="Route calculated successfully.",
            result=result,
        )


class AnalyzeLocationRisk(relay.ClientIDMutation):
    """Analyze fraud risk for coordinates."""

    class Input:
        coordinates = CoordinatesInput(required=True)

    success = graphene.Boolean(required=True)
    message = graphene.String()
    result = graphene.Field(FraudReportType)

    @classmethod
    def mutate_and_get_payload(cls, root, info, coordinates):
        user = getattr(info.context, "user", None)
        result = FraudDetectionService.analyze_location(
            latitude=coordinates.latitude,
            longitude=coordinates.longitude,
            user=user,
        )
        return cls(
            success=True,
            message="Location analyzed successfully.",
            result=result,
        )


class CheckGeofence(relay.ClientIDMutation):
    """Determine whether a point is inside a geofence."""

    class Input:
        center = CoordinatesInput(required=True)
        point = CoordinatesInput(required=True)
        radius_km = graphene.Float(required=True)

    success = graphene.Boolean(required=True)
    message = graphene.String()
    result = graphene.Field(GeofenceType)

    @classmethod
    def mutate_and_get_payload(cls, root, info, center, point, radius_km):
        from core.services.routing import haversine_distance

        distance = haversine_distance(
            center.latitude,
            center.longitude,
            point.latitude,
            point.longitude,
        )
        result = {
            "inside": distance <= radius_km,
            "distance_to_boundary": abs(radius_km - distance),
        }
        return cls(
            success=True,
            message="Geofence evaluated successfully.",
            result=result,
        )


class LocationMutations(graphene.ObjectType):
    """Shared location Relay mutations."""

    reverse_geocode = ReverseGeocode.Field()
    verify_address = VerifyAddress.Field()
    calculate_route = CalculateRoute.Field()
    analyze_location_risk = AnalyzeLocationRisk.Field()
    check_geofence = CheckGeofence.Field()