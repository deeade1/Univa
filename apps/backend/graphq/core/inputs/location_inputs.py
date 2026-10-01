# ------------------------------------------------------------------------------
# apps/backend/graphql/core/inputs/location_inputs.py
# ------------------------------------------------------------------------------

"""
Reusable GraphQL Location Inputs

These input objects are shared across all applications.

Used by

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


# ------------------------------------------------------------------------------
# Coordinates
# ------------------------------------------------------------------------------


class CoordinatesInput(graphene.InputObjectType):
    """Latitude/Longitude coordinates."""

    latitude = graphene.Float(required=True)

    longitude = graphene.Float(required=True)


# ------------------------------------------------------------------------------
# Location
# ------------------------------------------------------------------------------


class LocationInput(graphene.InputObjectType):
    """Generic location input."""

    address = graphene.String()

    latitude = graphene.Float(required=True)

    longitude = graphene.Float(required=True)

    accuracy = graphene.Float()

    source = graphene.String(default_value="gps")


# ------------------------------------------------------------------------------
# Reverse Geocoding
# ------------------------------------------------------------------------------


class ReverseGeocodeInput(graphene.InputObjectType):
    """Reverse geocoding request."""

    latitude = graphene.Float(required=True)

    longitude = graphene.Float(required=True)


# ------------------------------------------------------------------------------
# Nearby Search
# ------------------------------------------------------------------------------


class NearbySearchInput(graphene.InputObjectType):
    """Nearby search request."""

    latitude = graphene.Float(required=True)

    longitude = graphene.Float(required=True)

    radius_km = graphene.Float(default_value=10)

    limit = graphene.Int(default_value=20)


# ------------------------------------------------------------------------------
# Route
# ------------------------------------------------------------------------------


class RouteInput(graphene.InputObjectType):
    """Route calculation request."""

    origin = graphene.Argument(
        CoordinatesInput,
        required=True,
    )

    destination = graphene.Argument(
        CoordinatesInput,
        required=True,
    )


# ------------------------------------------------------------------------------
# Distance
# ------------------------------------------------------------------------------


class DistanceInput(graphene.InputObjectType):
    """Distance calculation."""

    point_a = graphene.Argument(
        CoordinatesInput,
        required=True,
    )

    point_b = graphene.Argument(
        CoordinatesInput,
        required=True,
    )


# ------------------------------------------------------------------------------
# Address Verification
# ------------------------------------------------------------------------------


class AddressVerificationInput(graphene.InputObjectType):
    """Verify an address."""

    address = graphene.String(required=True)

    latitude = graphene.Float()

    longitude = graphene.Float()


# ------------------------------------------------------------------------------
# Tracking
# ------------------------------------------------------------------------------


class TrackingInput(graphene.InputObjectType):
    """Live tracking update."""

    latitude = graphene.Float(required=True)

    longitude = graphene.Float(required=True)

    accuracy = graphene.Float()

    heading = graphene.Float()

    speed = graphene.Float()

    source = graphene.String(default_value="gps")


# ------------------------------------------------------------------------------
# Geofence
# ------------------------------------------------------------------------------


class GeofenceInput(graphene.InputObjectType):
    """Geofence request."""

    center = graphene.Argument(
        CoordinatesInput,
        required=True,
    )

    radius_km = graphene.Float(required=True)

    point = graphene.Argument(
        CoordinatesInput,
        required=True,
    )