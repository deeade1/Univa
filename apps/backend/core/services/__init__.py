# core/services/__init__.py
from .geocoding import geocode, reverse_geocode, validate_coordinates
from .address_verification import (
    AddressVerificationService,
    verify_address,
    verify_gps_against_address,
    verify_reverse_address,
    full_verification,
    calculate_distance,
    confidence_score,
    fraud_risk,
    same_location,
    normalize_address,
)
from .routing import haversine_distance, estimate_eta, get_route, within_radius, trip_distance
from .nearby import get_nearby, nearest, nearby_count, exists_nearby
from .fraud_detection import (
    # ✅ Import the service class from fraud_detection.py
    FraudDetectionService,
    FraudReport,
    valid_coordinates,
    impossible_travel,
    address_matches,
    excessive_coordinate_change,
    country_matches,
    calculate_risk_score,
    verify_property_location,
    verify_driver_location,
    verify_transaction_location,
    verify_delivery_location,
    LOW,
    MEDIUM,
    HIGH,
    CRITICAL,
)

# ✅ NO DUPLICATE FraudDetectionService DEFINITION HERE
# The service is imported from fraud_detection.py above

__all__ = [
    # Geocoding
    'geocode',
    'reverse_geocode',
    'validate_coordinates',
    
    # Address Verification
    'AddressVerificationService',
    'verify_address',
    'verify_gps_against_address',
    'verify_reverse_address',
    'full_verification',
    'calculate_distance',
    'confidence_score',
    'fraud_risk',
    'same_location',
    'normalize_address',
    
    # Routing
    'haversine_distance',
    'estimate_eta',
    'get_route',
    'within_radius',
    'trip_distance',
    
    # Nearby
    'get_nearby',
    'nearest',
    'nearby_count',
    'exists_nearby',
    
    # Fraud Detection
    'FraudDetectionService',
    'FraudReport',
    'valid_coordinates',
    'impossible_travel',
    'address_matches',
    'excessive_coordinate_change',
    'country_matches',
    'calculate_risk_score',
    'verify_property_location',
    'verify_driver_location',
    'verify_transaction_location',
    'verify_delivery_location',
    'LOW',
    'MEDIUM',
    'HIGH',
    'CRITICAL',
]