import logging

from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
from geopy.exc import GeocoderServiceError
from geopy.geocoders import Nominatim

logger = logging.getLogger(__name__)

class GeocodingService:
    """Service for geocoding operations"""
    
    def __init__(self):
        self.geolocator = Nominatim(user_agent="realestate-application")

    def update_location_from_coords(self, instance, latitude, longitude):
        """
        Update location fields from coordinates
        """
        try:
            lat = float(latitude)
            lng = float(longitude)
            
            instance.latitude = lat
            instance.longitude = lng
            instance.location_point = Point(lng, lat)
            
            location = self.geolocator.reverse((lat, lng), exactly_one=True)
            instance.location = location.address if location else None
            
            return True
            
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid coordinates: {e}")
            raise ValidationError(_("Invalid coordinates provided"))
        except GeocoderServiceError as e:
            logger.error(f"Geocoding service error: {e}")
            raise ValidationError(_("Geocoding service unavailable"))
        except Exception as e:
            logger.error(f"Unexpected geocoding error: {e}")
            raise ValidationError(_("Location update failed"))

    def geocode_address(self, address_string):
        """
        Geocode an address string to coordinates
        """
        try:
            location = self.geolocator.geocode(address_string)
            if location:
                return {
                    'latitude': location.latitude,
                    'longitude': location.longitude,
                    'address': location.address,
                    'point': Point(location.longitude, location.latitude)
                }
            return None
        except Exception as e:
            logger.error(f"Geocoding error for address {address_string}: {e}")
            return None