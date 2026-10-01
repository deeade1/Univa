# ------------------------------------------------------------------------------
# core/services/nearby.py
# ------------------------------------------------------------------------------

"""
Nearby Search Service

Centralized proximity search for all Univa applications.

Used by

    • Transport
    • Logistics
    • Marketplace
    • Real Estate
    • Banking
    • Social
    • Chat

Examples

    Nearby Drivers
    Nearby Riders
    Nearby Properties
    Nearby Agents
    Nearby Warehouses
    Nearby Vendors
    Nearby Banks
    Nearby ATMs
    Nearby Friends

Requires

    Django GIS
    PostGIS
"""

from __future__ import annotations

import logging

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Generic Nearby Search
# ------------------------------------------------------------------------------


def get_nearby(
    queryset,
    latitude,
    longitude,
    radius_km=10,
    limit=50,
):
    """
    Return nearby objects ordered by distance.

    Parameters
    ----------

    queryset

        Any queryset containing a location_point field.

    latitude

    longitude

    radius_km

    limit

    Example

        Driver.objects.all()

        Property.objects.filter(active=True)

        Warehouse.objects.filter(is_active=True)
    """

    point = Point(
        float(longitude),
        float(latitude),
        srid=4326,
    )

    return (
        queryset.filter(
            location_point__distance_lte=(
                point,
                D(km=radius_km),
            )
        )
        .annotate(
            distance=Distance(
                "location_point",
                point,
            )
        )
        .order_by("distance")[:limit]
    )


# ------------------------------------------------------------------------------
# Bounding Box Search
# ------------------------------------------------------------------------------


def get_within_bbox(
    queryset,
    min_lat,
    min_lon,
    max_lat,
    max_lon,
):
    """
    Bounding box search.

    Useful for

    Maps

    Clustering

    Infinite scrolling
    """

    bbox = (
        min_lon,
        min_lat,
        max_lon,
        max_lat,
    )

    return queryset.filter(
        location_point__bboverlaps=bbox
    )


# ------------------------------------------------------------------------------
# Nearest Object
# ------------------------------------------------------------------------------


def nearest(
    queryset,
    latitude,
    longitude,
):
    """
    Return nearest object.
    """

    results = get_nearby(
        queryset,
        latitude,
        longitude,
        radius_km=500,
        limit=1,
    )

    return results.first()


# ------------------------------------------------------------------------------
# Count Nearby
# ------------------------------------------------------------------------------


def nearby_count(
    queryset,
    latitude,
    longitude,
    radius_km=10,
):
    """
    Count nearby objects.
    """

    point = Point(
        float(longitude),
        float(latitude),
        srid=4326,
    )

    return queryset.filter(
        location_point__distance_lte=(
            point,
            D(km=radius_km),
        )
    ).count()


# ------------------------------------------------------------------------------
# Exists Nearby
# ------------------------------------------------------------------------------


def exists_nearby(
    queryset,
    latitude,
    longitude,
    radius_km=10,
):
    """
    Returns True if objects exist nearby.
    """

    return nearby_count(
        queryset,
        latitude,
        longitude,
        radius_km,
    ) > 0


# ------------------------------------------------------------------------------
# Radius Expansion
# ------------------------------------------------------------------------------


def search_with_expanding_radius(
    queryset,
    latitude,
    longitude,
    radii=None,
    limit=20,
):
    """
    Expand search radius until results are found.

    Default radii

        2km
        5km
        10km
        20km
        50km
        100km
    """

    if radii is None:
        radii = [
            2,
            5,
            10,
            20,
            50,
            100,
        ]

    for radius in radii:

        results = get_nearby(
            queryset,
            latitude,
            longitude,
            radius,
            limit,
        )

        if results.exists():
            return results

    return queryset.none()


# ------------------------------------------------------------------------------
# Module Helpers
# ------------------------------------------------------------------------------


def nearby_drivers(latitude, longitude, radius=10):
    from transport.models import Driver

    return get_nearby(
        Driver.objects.filter(is_online=True),
        latitude,
        longitude,
        radius,
    )


def nearby_properties(latitude, longitude, radius=20):
    from realestate.models import Property

    return get_nearby(
        Property.objects.filter(is_active=True),
        latitude,
        longitude,
        radius,
    )


def nearby_agents(latitude, longitude, radius=20):
    from realestate.models import Agent

    return get_nearby(
        Agent.objects.filter(is_active=True),
        latitude,
        longitude,
        radius,
    )


def nearby_warehouses(latitude, longitude, radius=50):
    from warehouse.models import Warehouse

    return get_nearby(
        Warehouse.objects.filter(is_active=True),
        latitude,
        longitude,
        radius,
    )


def nearby_vendors(latitude, longitude, radius=20):
    from accounts.models import User

    return get_nearby(
        User.objects.filter(is_vendor=True),
        latitude,
        longitude,
        radius,
    )


def nearby_atms(latitude, longitude, radius=10):
    from banking.models import ATM

    return get_nearby(
        ATM.objects.filter(is_active=True),
        latitude,
        longitude,
        radius,
    )


def nearby_bank_branches(latitude, longitude, radius=20):
    from banking.models import BankBranch

    return get_nearby(
        BankBranch.objects.filter(is_active=True),
        latitude,
        longitude,
        radius,
    )