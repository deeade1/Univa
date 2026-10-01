"""
------------------------------------------------------------------------------
Location Service Types
------------------------------------------------------------------------------

These GraphQL types represent service responses and computed data.

Unlike location_nodes.py, these classes are NOT backed by Django models.

Used by

    • Routing
    • Reverse Geocoding
    • Address Verification
    • Fraud Detection
    • Nearby Search
    • Distance Calculation
    • Live Tracking

These types are shared across all applications.

    • Accounts
    • Banking
    • Transport
    • Logistics
    • Marketplace
    • Real Estate
    • Warehouse
    • Social
------------------------------------------------------------------------------
"""

import graphene


# ------------------------------------------------------------------------------
# Coordinates
# ------------------------------------------------------------------------------


class CoordinatesType(graphene.ObjectType):
    """Latitude/Longitude pair."""

    latitude = graphene.Float(required=True)
    longitude = graphene.Float(required=True)


# ------------------------------------------------------------------------------
# Distance
# ------------------------------------------------------------------------------


class DistanceType(graphene.ObjectType):
    """Distance calculation."""

    kilometers = graphene.Float()
    meters = graphene.Float()
    miles = graphene.Float()


# ------------------------------------------------------------------------------
# Route
# ------------------------------------------------------------------------------


class RouteType(graphene.ObjectType):
    """Calculated route."""

    provider = graphene.String()

    distance_km = graphene.Float()

    estimated_minutes = graphene.Int()

    polyline = graphene.String()

    steps = graphene.List(graphene.String)


# ------------------------------------------------------------------------------
# Reverse Geocode
# ------------------------------------------------------------------------------


class ReverseGeocodeType(graphene.ObjectType):
    """Reverse geocoding response."""

    address = graphene.String()

    city = graphene.String()

    state = graphene.String()

    country = graphene.String()

    postal_code = graphene.String()


# ------------------------------------------------------------------------------
# Nearby Search
# ------------------------------------------------------------------------------


class NearbyResultType(graphene.ObjectType):
    """Generic nearby search result."""

    id = graphene.ID()

    name = graphene.String()

    address = graphene.String()

    latitude = graphene.Float()

    longitude = graphene.Float()

    distance_km = graphene.Float()


# ------------------------------------------------------------------------------
# Address Verification
# ------------------------------------------------------------------------------


class AddressVerificationType(graphene.ObjectType):
    """Address verification response."""

    verified = graphene.Boolean()

    confidence = graphene.Float()

    normalized_address = graphene.String()

    message = graphene.String()


# ------------------------------------------------------------------------------
# Fraud Detection
# ------------------------------------------------------------------------------


class FraudReportType(graphene.ObjectType):
    """Fraud detection result."""

    verified = graphene.Boolean()

    risk = graphene.String()

    score = graphene.Float()

    reason = graphene.String()

    metadata = graphene.JSONString()


# ------------------------------------------------------------------------------
# Geofence
# ------------------------------------------------------------------------------


class GeofenceType(graphene.ObjectType):
    """Geofence result."""

    inside = graphene.Boolean()

    distance_to_boundary = graphene.Float()


# ------------------------------------------------------------------------------
# Live Tracking
# ------------------------------------------------------------------------------


class TrackingLocationType(graphene.ObjectType):
    """Live tracking payload."""

    latitude = graphene.Float()

    longitude = graphene.Float()

    heading = graphene.Float()

    speed = graphene.Float()

    accuracy = graphene.Float()

    timestamp = graphene.DateTime()


# ------------------------------------------------------------------------------
# Location History
# ------------------------------------------------------------------------------


class LocationHistoryType(graphene.ObjectType):
    """Historical location."""

    latitude = graphene.Float()

    longitude = graphene.Float()

    address = graphene.String()

    timestamp = graphene.DateTime()


# ------------------------------------------------------------------------------
# Generic Response
# ------------------------------------------------------------------------------


class ServiceResponseType(graphene.ObjectType):
    """Generic service response."""

    success = graphene.Boolean(required=True)

    message = graphene.String()
    
# ------------------------------------------------------------------------------
# Generic Location
# ------------------------------------------------------------------------------

class LocationType(graphene.ObjectType):
    """
    Generic location payload.

    Used by:
        • GraphQL subscriptions
        • Mutations
        • Reverse geocoding
        • Routing
        • Live tracking
        • Background services

    This is NOT backed by a Django model.
    """

    address = graphene.String(
        description="Human-readable address."
    )

    latitude = graphene.Float(
        description="Latitude."
    )

    longitude = graphene.Float(
        description="Longitude."
    )

    accuracy = graphene.Float(
        description="GPS accuracy in meters."
    )

    source = graphene.String(
        description="Location source (gps, network, manual, ip)."
    )

    timestamp = graphene.DateTime(
        description="Time the location was recorded."
    )