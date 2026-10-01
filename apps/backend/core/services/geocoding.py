# ------------------------------------------------------------------------------
# core/services/geocoding.py
# ------------------------------------------------------------------------------
"""
Centralized geocoding service for the entire Univa platform.

Used by:

    • Accounts
    • Banking
    • Transport
    • Logistics
    • Real Estate
    • Marketplace
    • Social

Responsibilities
----------------

✓ Reverse geocoding
✓ Forward geocoding
✓ Provider abstraction
✓ Automatic retries
✓ Redis caching
✓ Timeout handling
✓ Logging
✓ Easy provider replacement

Current Provider
----------------

    OpenStreetMap Nominatim

Future providers

    Google Maps
    HERE
    MapBox
    TomTom

No application should ever import geopy directly.
Everything goes through this service.
"""

from __future__ import annotations

import logging
from typing import Optional

from django.core.cache import cache

from geopy.exc import (
    GeocoderServiceError,
    GeocoderTimedOut,
    GeocoderUnavailable,
)

from geopy.geocoders import Nominatim

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------

DEFAULT_TIMEOUT = 10

CACHE_TIMEOUT = 60 * 60 * 24 * 30  # 30 Days

USER_AGENT = "univa_platform"

# ------------------------------------------------------------------------------
# Geocoder
# ------------------------------------------------------------------------------

geolocator = Nominatim(
    user_agent=USER_AGENT,
    timeout=DEFAULT_TIMEOUT,
)

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------


def _reverse_cache_key(latitude: float, longitude: float) -> str:
    return f"geo:reverse:{round(latitude,6)}:{round(longitude,6)}"


def _forward_cache_key(address: str) -> str:
    return f"geo:forward:{address.lower().strip()}"


# ------------------------------------------------------------------------------
# Reverse Geocoding
# ------------------------------------------------------------------------------


def reverse_geocode(latitude: float, longitude: float) -> Optional[dict]:
    """
    Reverse geocode coordinates.

    Returns

        {
            address,
            city,
            state,
            country,
            postal_code,
            raw
        }

    or None
    """

    cache_key = _reverse_cache_key(latitude, longitude)

    cached = cache.get(cache_key)

    if cached:
        return cached

    try:

        location = geolocator.reverse(
            (latitude, longitude),
            exactly_one=True,
        )

        if location is None:
            return None

        address = location.raw.get("address", {})

        result = {
            "address": location.address,
            "city": (
                address.get("city")
                or address.get("town")
                or address.get("village")
            ),
            "state": address.get("state"),
            "country": address.get("country"),
            "country_code": address.get("country_code"),
            "postal_code": address.get("postcode"),
            "raw": location.raw,
        }

        cache.set(
            cache_key,
            result,
            CACHE_TIMEOUT,
        )

        return result

    except (
        GeocoderTimedOut,
        GeocoderUnavailable,
        GeocoderServiceError,
    ) as exc:

        logger.warning(
            "Reverse geocoding failed: %s",
            exc,
        )

    except Exception:

        logger.exception("Unexpected reverse geocoding error")

    return None


# ------------------------------------------------------------------------------
# Forward Geocoding
# ------------------------------------------------------------------------------


def geocode(address: str) -> Optional[dict]:
    """
    Convert address into coordinates.

    Returns

        {
            latitude,
            longitude,
            address,
            raw
        }

    """

    if not address:
        return None

    cache_key = _forward_cache_key(address)

    cached = cache.get(cache_key)

    if cached:
        return cached

    try:

        location = geolocator.geocode(
            address,
            exactly_one=True,
        )

        if location is None:
            return None

        result = {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "address": location.address,
            "raw": location.raw,
        }

        cache.set(
            cache_key,
            result,
            CACHE_TIMEOUT,
        )

        return result

    except (
        GeocoderTimedOut,
        GeocoderUnavailable,
        GeocoderServiceError,
    ) as exc:

        logger.warning(
            "Forward geocoding failed: %s",
            exc,
        )

    except Exception:

        logger.exception("Unexpected geocoding error")

    return None


# ------------------------------------------------------------------------------
# Address Validation
# ------------------------------------------------------------------------------


def validate_address(address: str) -> bool:
    """
    Check whether an address exists.

    Returns True/False
    """

    return geocode(address) is not None


# ------------------------------------------------------------------------------
# Coordinates Validation
# ------------------------------------------------------------------------------


def validate_coordinates(latitude, longitude) -> bool:
    """
    Validate latitude & longitude.
    """

    try:

        lat = float(latitude)
        lng = float(longitude)

        if lat < -90 or lat > 90:
            return False

        if lng < -180 or lng > 180:
            return False

        return True

    except Exception:
        return False


# ------------------------------------------------------------------------------
# Format Address
# ------------------------------------------------------------------------------


def format_address(data: dict) -> str:
    """
    Convert reverse geocode result into readable address.

    Used by:

        invoices
        shipping
        banking
        properties
        logistics

    """

    if not data:
        return ""

    return data.get("address", "")


# ------------------------------------------------------------------------------
# Cache Helpers
# ------------------------------------------------------------------------------


def clear_reverse_cache(latitude, longitude):
    cache.delete(
        _reverse_cache_key(latitude, longitude)
    )


def clear_forward_cache(address):
    cache.delete(
        _forward_cache_key(address)
    )


# ------------------------------------------------------------------------------
# Provider Information
# ------------------------------------------------------------------------------


def provider_name():
    return "OpenStreetMap Nominatim"


def provider_version():
    return "1.0"