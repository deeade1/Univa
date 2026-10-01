# core/services/address_verification.py
"""
Enterprise Address Verification Service

Used across:
    • Banking
    • Real Estate
    • Logistics
    • Ride Sharing
    • Marketplace
    • User Profiles

Responsibilities
----------------
✓ Verify an address exists
✓ Verify GPS matches supplied address
✓ Distance calculation
✓ Confidence score
✓ Fraud detection
✓ Address normalization
✓ Duplicate detection
✓ Easy upgrade to Google Address Validation API

Current Provider
    OpenStreetMap (Nominatim)

Future Providers
    Google Address Validation API
    HERE
    Mapbox
    Loqate
"""

from __future__ import annotations

import logging
from math import atan2, cos, radians, sin, sqrt

from .geocoding import (
    geocode,
    reverse_geocode,
    validate_coordinates,
)

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------------------

EARTH_RADIUS_KM = 6371.0088


# ------------------------------------------------------------------------------
# Distance
# ------------------------------------------------------------------------------

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two coordinates.

    Returns kilometers.
    """
    lat1 = radians(float(lat1))
    lon1 = radians(float(lon1))
    lat2 = radians(float(lat2))
    lon2 = radians(float(lon2))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1)
        * cos(lat2)
        * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return EARTH_RADIUS_KM * c


# ------------------------------------------------------------------------------
# Address Exists
# ------------------------------------------------------------------------------

def verify_address(address: str):
    """
    Verify an address exists.

    Returns:
        {
            verified,
            coordinates,
            normalized_address
        }
    """
    result = geocode(address)

    if result is None:
        return {
            "verified": False,
            "coordinates": None,
            "normalized_address": None,
        }

    return {
        "verified": True,
        "coordinates": (
            result["latitude"],
            result["longitude"],
        ),
        "normalized_address": result["address"],
    }


# ------------------------------------------------------------------------------
# GPS Verification
# ------------------------------------------------------------------------------

def verify_gps_against_address(
    latitude,
    longitude,
    address,
):
    """
    Verify user's GPS matches supplied address.

    Returns:
        {
            verified,
            distance_km,
            confidence,
            normalized_address
        }
    """
    if not validate_coordinates(latitude, longitude):
        return {
            "verified": False,
            "reason": "Invalid coordinates",
        }

    address_result = geocode(address)

    if address_result is None:
        return {
            "verified": False,
            "reason": "Address not found",
        }

    distance = calculate_distance(
        latitude,
        longitude,
        address_result["latitude"],
        address_result["longitude"],
    )

    confidence = confidence_score(distance)

    return {
        "verified": confidence >= 80,
        "distance_km": round(distance, 2),
        "confidence": confidence,
        "normalized_address": address_result["address"],
    }


# ------------------------------------------------------------------------------
# Reverse Verification
# ------------------------------------------------------------------------------

def verify_reverse_address(latitude, longitude):
    """
    Verify coordinates resolve to a real address.
    """
    result = reverse_geocode(latitude, longitude)

    if result is None:
        return {
            "verified": False,
        }

    return {
        "verified": True,
        "address": result["address"],
        "city": result["city"],
        "state": result["state"],
        "country": result["country"],
    }


# ------------------------------------------------------------------------------
# Confidence Score
# ------------------------------------------------------------------------------

def confidence_score(distance_km):
    """
    Convert distance into confidence score.

        <50m      -> 100
        <100m     -> 98
        <250m     -> 95
        <500m     -> 90
        <1km      -> 85
        <2km      -> 75
        <5km      -> 60
        <10km     -> 40
        >10km     -> 0
    """
    if distance_km <= 0.05:
        return 100
    if distance_km <= 0.10:
        return 98
    if distance_km <= 0.25:
        return 95
    if distance_km <= 0.50:
        return 90
    if distance_km <= 1:
        return 85
    if distance_km <= 2:
        return 75
    if distance_km <= 5:
        return 60
    if distance_km <= 10:
        return 40
    return 0


# ------------------------------------------------------------------------------
# Fraud Risk
# ------------------------------------------------------------------------------

def fraud_risk(distance_km):
    """
    Determine fraud risk.

    Returns:
        LOW, MEDIUM, HIGH, CRITICAL
    """
    if distance_km <= 0.5:
        return "LOW"
    if distance_km <= 2:
        return "MEDIUM"
    if distance_km <= 5:
        return "HIGH"
    return "CRITICAL"


# ------------------------------------------------------------------------------
# Full Verification
# ------------------------------------------------------------------------------

def full_verification(
    latitude,
    longitude,
    address,
):
    """
    Enterprise verification.

    Used by:
        Banking
        Real Estate
        Ride
        Logistics

    Returns complete verification report.
    """
    gps = verify_gps_against_address(
        latitude,
        longitude,
        address,
    )

    if not gps.get("verified") and gps.get("reason"):
        return gps

    distance = gps["distance_km"]

    return {
        "verified": gps["verified"],
        "confidence": gps["confidence"],
        "risk": fraud_risk(distance),
        "distance_km": distance,
        "normalized_address": gps["normalized_address"],
    }


# ------------------------------------------------------------------------------
# Duplicate Location Check
# ------------------------------------------------------------------------------

def same_location(
    lat1,
    lon1,
    lat2,
    lon2,
    tolerance_meters=30,
):
    """
    Check whether two coordinates are effectively the same.

    Default tolerance: 30 meters.
    """
    distance = calculate_distance(
        lat1,
        lon1,
        lat2,
        lon2,
    )

    return distance <= (tolerance_meters / 1000)


# ------------------------------------------------------------------------------
# Normalize Address
# ------------------------------------------------------------------------------

def normalize_address(address):
    """
    Return standardized address.

    Returns None if not found.
    """
    result = geocode(address)

    if result is None:
        return None

    return result["address"]


# ==============================================================================
# ✅ ADDRESS VERIFICATION SERVICE CLASS
# ==============================================================================

class AddressVerificationService:
    """
    Service class for address verification operations.
    Provides a clean interface for GraphQL and other services.
    """
    
    @staticmethod
    def verify_address(address: str):
        """
        Verify an address exists.
        
        Args:
            address: The address to verify
        
        Returns:
            dict: Verification result with verified status, coordinates, and normalized address
        """
        return verify_address(address)
    
    @staticmethod
    def verify_gps_against_address(latitude, longitude, address):
        """
        Verify GPS coordinates match a supplied address.
        
        Args:
            latitude: The latitude to check
            longitude: The longitude to check
            address: The address to verify against
        
        Returns:
            dict: Verification result with distance, confidence, and normalized address
        """
        return verify_gps_against_address(latitude, longitude, address)
    
    @staticmethod
    def verify_reverse_address(latitude, longitude):
        """
        Verify coordinates resolve to a real address.
        
        Args:
            latitude: The latitude to check
            longitude: The longitude to check
        
        Returns:
            dict: Verification result with address details
        """
        return verify_reverse_address(latitude, longitude)
    
    @staticmethod
    def full_verification(latitude, longitude, address):
        """
        Perform complete enterprise verification.
        
        Args:
            latitude: The latitude to check
            longitude: The longitude to check
            address: The address to verify
        
        Returns:
            dict: Complete verification report with confidence, risk, and distance
        """
        return full_verification(latitude, longitude, address)
    
    @staticmethod
    def normalize_address(address):
        """
        Normalize and standardize an address.
        
        Args:
            address: The address to normalize
        
        Returns:
            str: Normalized address or None if not found
        """
        return normalize_address(address)
    
    @staticmethod
    def calculate_distance(lat1, lon1, lat2, lon2):
        """
        Calculate distance between two coordinates.
        
        Args:
            lat1: Latitude of first point
            lon1: Longitude of first point
            lat2: Latitude of second point
            lon2: Longitude of second point
        
        Returns:
            float: Distance in kilometers
        """
        return calculate_distance(lat1, lon1, lat2, lon2)
    
    @staticmethod
    def same_location(lat1, lon1, lat2, lon2, tolerance_meters=30):
        """
        Check if two coordinates are effectively the same location.
        
        Args:
            lat1: Latitude of first point
            lon1: Longitude of first point
            lat2: Latitude of second point
            lon2: Longitude of second point
            tolerance_meters: Tolerance in meters (default: 30)
        
        Returns:
            bool: True if locations are effectively the same
        """
        return same_location(lat1, lon1, lat2, lon2, tolerance_meters)
    
    @staticmethod
    def confidence_score(distance_km):
        """
        Get confidence score based on distance.
        
        Args:
            distance_km: Distance in kilometers
        
        Returns:
            int: Confidence score (0-100)
        """
        return confidence_score(distance_km)
    
    @staticmethod
    def fraud_risk(distance_km):
        """
        Get fraud risk level based on distance.
        
        Args:
            distance_km: Distance in kilometers
        
        Returns:
            str: Risk level (LOW, MEDIUM, HIGH, CRITICAL)
        """
        return fraud_risk(distance_km)