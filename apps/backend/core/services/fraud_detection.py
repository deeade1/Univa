# core/services/fraud_detection.py
"""
Central Fraud Detection Service

Used by:
    • Banking
    • Transport
    • Logistics
    • Marketplace
    • Real Estate
    • Social
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from core.services.routing import haversine_distance


# ------------------------------------------------------------------------------
# Risk Levels
# ------------------------------------------------------------------------------

LOW = "low"
MEDIUM = "medium"
HIGH = "high"
CRITICAL = "critical"


# ------------------------------------------------------------------------------
# Result Object
# ------------------------------------------------------------------------------

@dataclass
class FraudReport:
    verified: bool
    risk: str
    score: float
    reason: str | None = None
    metadata: dict | None = None


# ------------------------------------------------------------------------------
# GPS Validation
# ------------------------------------------------------------------------------

def valid_coordinates(latitude, longitude):
    if latitude is None or longitude is None:
        return False
    return (
        -90 <= float(latitude) <= 90 and
        -180 <= float(longitude) <= 180
    )


# ------------------------------------------------------------------------------
# Impossible Travel
# ------------------------------------------------------------------------------

def impossible_travel(
    old_lat,
    old_lon,
    new_lat,
    new_lon,
    minutes,
    max_speed_kmh=250,
):
    """Detect impossible travel."""
    if minutes <= 0:
        return True

    distance = haversine_distance(
        old_lat,
        old_lon,
        new_lat,
        new_lon,
    )
    hours = minutes / 60
    speed = distance / hours
    return speed > max_speed_kmh


# ------------------------------------------------------------------------------
# Address Match
# ------------------------------------------------------------------------------

def address_matches(supplied_address, reverse_geocoded_address):
    """Basic text comparison."""
    if not supplied_address or not reverse_geocoded_address:
        return False

    supplied = supplied_address.lower()
    actual = reverse_geocoded_address.lower()
    return supplied in actual or actual in supplied


# ------------------------------------------------------------------------------
# Coordinate Drift
# ------------------------------------------------------------------------------

def excessive_coordinate_change(
    old_lat,
    old_lon,
    new_lat,
    new_lon,
    threshold_km=30,
):
    distance = haversine_distance(
        old_lat,
        old_lon,
        new_lat,
        new_lon,
    )
    return distance > threshold_km


# ------------------------------------------------------------------------------
# Country Check
# ------------------------------------------------------------------------------

def country_matches(registered_country, detected_country):
    if not registered_country or not detected_country:
        return True
    return registered_country.upper() == detected_country.upper()


# ------------------------------------------------------------------------------
# Generic Risk Score
# ------------------------------------------------------------------------------

def calculate_risk_score(
    *,
    address_verified=True,
    country_match=True,
    impossible=False,
    coordinate_change=False,
):
    """Returns FraudReport."""
    score = 0
    reasons = []

    if not address_verified:
        score += 35
        reasons.append("Address verification failed")

    if not country_match:
        score += 30
        reasons.append("Country mismatch")

    if impossible:
        score += 50
        reasons.append("Impossible travel detected")

    if coordinate_change:
        score += 20
        reasons.append("Large coordinate jump")

    if score >= 80:
        risk = CRITICAL
    elif score >= 50:
        risk = HIGH
    elif score >= 20:
        risk = MEDIUM
    else:
        risk = LOW

    return FraudReport(
        verified=score < 50,
        risk=risk,
        score=score,
        reason=", ".join(reasons) if reasons else None,
        metadata={
            "address_verified": address_verified,
            "country_match": country_match,
            "impossible_travel": impossible,
            "coordinate_jump": coordinate_change,
        },
    )


# ------------------------------------------------------------------------------
# Property Verification
# ------------------------------------------------------------------------------

def verify_property_location(supplied_address, reverse_geocoded_address):
    matched = address_matches(supplied_address, reverse_geocoded_address)
    return calculate_risk_score(address_verified=matched)


# ------------------------------------------------------------------------------
# Driver Verification
# ------------------------------------------------------------------------------

def verify_driver_location(old_lat, old_lon, new_lat, new_lon, minutes):
    impossible = impossible_travel(old_lat, old_lon, new_lat, new_lon, minutes)
    moved = excessive_coordinate_change(old_lat, old_lon, new_lat, new_lon)
    return calculate_risk_score(impossible=impossible, coordinate_change=moved)


# ------------------------------------------------------------------------------
# Banking Verification
# ------------------------------------------------------------------------------

def verify_transaction_location(registered_country, detected_country):
    return calculate_risk_score(
        country_match=country_matches(registered_country, detected_country)
    )


# ------------------------------------------------------------------------------
# Delivery Verification
# ------------------------------------------------------------------------------

def verify_delivery_location(pickup_address, reverse_geocoded_address):
    matched = address_matches(pickup_address, reverse_geocoded_address)
    return calculate_risk_score(address_verified=matched)


# ==============================================================================
# ✅ FRAUD DETECTION SERVICE CLASS (ONLY DEFINED ONCE HERE)
# ==============================================================================

class FraudDetectionService:
    """
    Service class for fraud detection operations.
    Provides a clean interface for GraphQL and other services.
    """
    
    @staticmethod
    def analyze_location(latitude, longitude, user=None):
        """
        Analyze a location for fraud risk.
        
        Args:
            latitude: The latitude to check
            longitude: The longitude to check
            user: Optional user for context
        
        Returns:
            FraudReport: The fraud analysis result
        """
        # Validate coordinates
        if not valid_coordinates(latitude, longitude):
            return FraudReport(
                verified=False,
                risk=CRITICAL,
                score=100,
                reason="Invalid coordinates provided",
                metadata={
                    "latitude": latitude,
                    "longitude": longitude,
                    "reason": "invalid_coordinates"
                }
            )
        
        # Check for suspicious locations (e.g., middle of ocean)
        if abs(latitude) < 0.1 and abs(longitude) < 0.1:
            return FraudReport(
                verified=False,
                risk=HIGH,
                score=70,
                reason="Suspicious location (near 0,0)",
                metadata={
                    "latitude": latitude,
                    "longitude": longitude,
                    "reason": "null_island"
                }
            )
        
        # Default: Low risk
        return FraudReport(
            verified=True,
            risk=LOW,
            score=10,
            reason="Location appears normal",
            metadata={
                "latitude": latitude,
                "longitude": longitude,
                "verified": True
            }
        )
    
    @staticmethod
    def check_impossible_travel(old_lat, old_lon, new_lat, new_lon, time_delta_minutes):
        """Check if movement between two locations is physically impossible."""
        return impossible_travel(
            old_lat,
            old_lon,
            new_lat,
            new_lon,
            time_delta_minutes
        )
    
    @staticmethod
    def verify_address_match(supplied_address, geocoded_address):
        """Verify if a supplied address matches the geocoded result."""
        return address_matches(supplied_address, geocoded_address)
    
    @staticmethod
    def get_risk_level(score):
        """Get risk level from score."""
        if score >= 80:
            return CRITICAL
        elif score >= 50:
            return HIGH
        elif score >= 20:
            return MEDIUM
        return LOW
    
    @staticmethod
    def analyze_transaction_location(registered_country, detected_country):
        """Analyze location risk for a transaction."""
        return verify_transaction_location(registered_country, detected_country)
    
    @staticmethod
    def analyze_delivery_location(pickup_address, reverse_geocoded_address):
        """Analyze location risk for a delivery."""
        return verify_delivery_location(pickup_address, reverse_geocoded_address)