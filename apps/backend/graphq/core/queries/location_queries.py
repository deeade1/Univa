# graphq/core/queries/location_queries.py
"""
Reusable Relay GraphQL Location Queries

Shared across:
    • Accounts
    • Banking
    • Transport
    • Logistics
    • Marketplace
    • Real Estate
    • Warehouse
    • Social

All business logic lives inside core.services.
"""

import graphene
from graphene import relay

from graphq.core.inputs.location_inputs import (
    AddressVerificationInput,
    CoordinatesInput,
    DistanceInput,
    NearbySearchInput,
    ReverseGeocodeInput,
    RouteInput,
)

from graphq.core.types.location_types import (
    AddressVerificationType,
    DistanceType,
    FraudReportType,
    GeofenceType,
    NearbyResultType,
    ReverseGeocodeType,
    RouteType,
)

# ✅ FIXED: Import from core.services (not graphq.core.services)
from core.services.address_verification import verify_address, verify_gps_against_address
from core.services.fraud_detection import FraudDetectionService
from core.services.geocoding import reverse_geocode, geocode
from core.services.nearby import get_nearby
from core.services.routing import get_route, haversine_distance


class LocationQuery(graphene.ObjectType):
    """
    Shared Relay Location Queries.
    """

    # Reverse Geocoding
    reverse_geocode = graphene.Field(
        ReverseGeocodeType,
        input=graphene.Argument(ReverseGeocodeInput, required=True),
        description="Convert coordinates into an address.",
    )

    # Verify Address
    verify_address = graphene.Field(
        AddressVerificationType,
        input=graphene.Argument(AddressVerificationInput, required=True),
        description="Verify a physical address.",
    )

    # Calculate Distance
    calculate_distance = graphene.Field(
        DistanceType,
        input=graphene.Argument(DistanceInput, required=True),
        description="Calculate distance between two points.",
    )

    # Calculate Route
    calculate_route = graphene.Field(
        RouteType,
        input=graphene.Argument(RouteInput, required=True),
        description="Calculate optimal route.",
    )

    # Nearby Search
    nearby_locations = graphene.List(
        NearbyResultType,
        input=graphene.Argument(NearbySearchInput, required=True),
        description="Search nearby locations.",
    )

    # Fraud Detection
    analyze_location_risk = graphene.Field(
        FraudReportType,
        coordinates=graphene.Argument(CoordinatesInput, required=True),
        description="Analyze fraud risk for a location.",
    )

    # Geofence
    geofence_status = graphene.Field(
        GeofenceType,
        center=graphene.Argument(CoordinatesInput, required=True),
        point=graphene.Argument(CoordinatesInput, required=True),
        radius_km=graphene.Float(required=True),
        description="Check whether a point is inside a geofence.",
    )

    # ======================================================================
    # Resolvers
    # ======================================================================

    def resolve_reverse_geocode(self, info, input):
        result = reverse_geocode(
            latitude=input.latitude,
            longitude=input.longitude,
        )
        return result

    def resolve_verify_address(self, info, input):
        if input.latitude is not None and input.longitude is not None:
            return verify_gps_against_address(
                latitude=input.latitude,
                longitude=input.longitude,
                address=input.address,
            )
        return verify_address(address=input.address)

    def resolve_calculate_distance(self, info, input):
        distance = haversine_distance(
            input.point_a.latitude,
            input.point_a.longitude,
            input.point_b.latitude,
            input.point_b.longitude,
        )
        return {
            "kilometers": round(distance, 2),
            "meters": round(distance * 1000, 2),
            "miles": round(distance * 0.621371, 2),
        }

    def resolve_calculate_route(self, info, input):
        return get_route(
            start_lat=input.origin.latitude,
            start_lon=input.origin.longitude,
            end_lat=input.destination.latitude,
            end_lon=input.destination.longitude,
        )

    def resolve_nearby_locations(self, info, input):
        # This would need a model to query - placeholder
        # In practice, you'd pass a queryset to get_nearby()
        return []

    def resolve_analyze_location_risk(self, info, coordinates):
        user = getattr(info.context, "user", None)
        return FraudDetectionService.analyze_location(
            latitude=coordinates.latitude,
            longitude=coordinates.longitude,
            user=user,
        )

    def resolve_geofence_status(self, info, center, point, radius_km):
        distance = haversine_distance(
            center.latitude,
            center.longitude,
            point.latitude,
            point.longitude,
        )
        return {
            "inside": distance <= radius_km,
            "distance_to_boundary": abs(radius_km - distance),
        }